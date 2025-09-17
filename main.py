import io
import numpy as np
import faiss
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from jigsawstack import JigsawStack
from dotenv import load_dotenv
load_dotenv()

# ---------- Data classes ----------
@dataclass
class Segment:
    artist: str
    title: str
    text: str
    start: float
    end: float
    speaker_label: Optional[str]
    source_url: str
    track_id: str  # unique per uploaded track

@dataclass
class TrackFP:
    artist: str
    title: str
    track_id: str
    speaker_vec: np.ndarray  # fingerprint for whole track

# ---------- Vector Stores ----------
class FaissIP:
    """Inner-product index with L2-normalized vectors -> cosine similarity."""
    def __init__(self):
        self.index: Optional[faiss.IndexFlatIP] = None
        self.vecs: Optional[np.ndarray] = None
        self.meta: List[Any] = []

    def add(self, mat: np.ndarray, metas: List[Any]):
        faiss.normalize_L2(mat)
        if self.index is None:
            d = mat.shape[1]
            self.index = faiss.IndexFlatIP(d)
            self.vecs = mat.copy()
            self.index.add(self.vecs)
            self.meta = list(metas)
        else:
            self.vecs = np.vstack([self.vecs, mat])
            self.index.add(mat)
            self.meta.extend(metas)

    def search(self, q: np.ndarray, k: int = 5) -> List[Tuple[float, Any]]:
        if self.index is None:
            return []
        qv = q.astype("float32").reshape(1, -1)
        faiss.normalize_L2(qv)
        D, I = self.index.search(qv, k)
        out = []
        for d, i in zip(D[0], I[0]):
            if i == -1: continue
            out.append((float(d), self.meta[i]))
        return out

# ---------- App state ----------
app = FastAPI(title="Songs RAG with JigsawStack Embedding v2")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_methods=["*"], allow_headers=["*"],
)
js = JigsawStack()  # reads JIGSAWSTACK_API_KEY

CONTENT = FaissIP()       # transcript segment embeddings
SPEAKERS = FaissIP()      # track-level speaker fingerprints
TRACK_FP: Dict[str, TrackFP] = {}  # track_id -> TrackFP

# ---------- Schemas ----------
class WhoSaidIn(BaseModel):
    quote: str
    k: int = 5

class MoreFromArtistIn(BaseModel):
    track_id: str
    top_n: int = 5

# ---------- Helpers ----------
def upload_and_url(file_bytes: bytes) -> str:
    buf = file_bytes
    up = js.store.upload(buf, {"overwrite": True, "temp_public_url": True})
    url = up.get("temp_public_url", None)
    if not url:
        raise HTTPException(500, "Upload failed")
    return url

def stt_chunks(url: str, by_speaker: bool = True) -> List[Segment]:
    stt = js.audio.speech_to_text({"url": url, "by_speaker": by_speaker, "language": "auto",})
    segs = []
    if isinstance(stt, dict):
        # prefer diarized segments if present
        stream = stt.get("speakers") if by_speaker and stt.get("speakers") else stt.get("chunks", [])
        for seg in stream:
            text = (seg.get("text") or "").strip()
            if not text: continue
            ts = seg.get("timestamp") or [0, 0]
            speaker = seg.get("speaker")
            segs.append((text, float(ts[0]), float(ts[1]), str(speaker) if speaker else None))
    return segs

def emb_text_vec(text: str) -> np.ndarray:
    r = js.embedding_v2({"type": "text", "text": text})
    return np.array(r["embeddings"][0], dtype="float32")

def emb_audio_fp(url: str) -> Optional[np.ndarray]:
    r = js.embedding_v2({"type": "audio", "url": url, "speaker_fingerprint": True, })
    fps = r.get("speaker_embeddings")
    if fps:
        return np.array(fps[0], dtype="float32")
    return None

# ---------- Routes ----------
@app.post("/ingest-songs")
async def ingest_songs(
    files: List[UploadFile] = File(...),
    artists: List[str] = Form(...),
    titles: List[str] = Form(...),
):
    """
    Ingest multiple songs. For each track:
      1) Upload -> temp URL
      2) Transcribe with timestamps + diarization
      3) Embed each transcript chunk (text) -> CONTENT index
      4) Compute a track-level speaker fingerprint -> SPEAKERS index
    """
    if not (len(files) == len(artists) == len(titles)):
        raise HTTPException(400, "files, artists, titles sizes must match")

    total_segments = 0
    for file, artist, title in zip(files, artists, titles):
        data = await file.read()
        url = upload_and_url(data)
        track_id = f"{artist}:{title}:{hash(url) & 0xfffffff}"

        #(2) STT + diarization
        chunks = stt_chunks(url, by_speaker=True)
        if not chunks:
            continue

        # (3) Embed transcript chunks
        mat = []
        metas = []
        for text, s, e, spk in chunks:
            vec = emb_text_vec(text)
            mat.append(vec)
            metas.append(Segment(artist=artist, title=title, text=text,
                                 start=s, end=e, speaker_label=spk,
                                 source_url=url, track_id=track_id))
        CONTENT.add(np.vstack(mat), metas)
        total_segments += len(metas)

        # (4) Track speaker fingerprint
        fp = emb_audio_fp(url)
        if fp is not None:
            SPEAKERS.add(fp.reshape(1, -1), [track_id])
            TRACK_FP[track_id] = TrackFP(artist=artist, title=title,
                                         track_id=track_id, speaker_vec=fp)

    return {"success": True, "tracks": len(files), "segments_indexed": total_segments}

@app.post("/who-said")
def who_said(body: WhoSaidIn):
    """
    Given a quoted line, find best matching segment and report artist/title/timestamp.
    Then offer "more from this artist" using speaker-fingerprint similarity across tracks.
    """
    if CONTENT.index is None:
        raise HTTPException(400, "Index empty. Call /ingest-songs first.")

    qv = emb_text_vec(body.quote)
    hits = CONTENT.search(qv, k=body.k)
    if not hits:
        return {"answer": "I couldn't find that line.", "candidates": []}

    # pick top
    score, seg = hits[0]
    answer = {
        "artist": seg.artist,
        "title": seg.title,
        "timestamp": [round(seg.start, 2), round(seg.end, 2)],
        "track_id": seg.track_id,
        "source_url": seg.source_url,
        "match_score": round(score, 4),
        "snippet": seg.text[:140]  # preview
    }

    # nearest other tracks by same voice (speaker fingerprint), excluding this track
    suggestions = []
    if seg.track_id in TRACK_FP and SPEAKERS.index is not None:
        fp = TRACK_FP[seg.track_id].speaker_vec
        nn = SPEAKERS.search(fp, k=max(3, body.k + 1))  # include self, filter below
        for sim, t_id in nn:
            if t_id == seg.track_id:  # skip same track
                continue
            meta = TRACK_FP.get(t_id)
            if not meta: continue
            suggestions.append({
                "artist": meta.artist,
                "title": meta.title,
                "track_id": meta.track_id,
                "similarity": round(sim, 4),
            })

    # (Optional) style it with a generation call; here we format directly:
    say = (
        f"{answer['artist']} said it in “{answer['title']}” "
        f"[{answer['timestamp'][0]}s–{answer['timestamp'][1]}s]. "
        f"I can search more songs by this voice if you want."
    )
    return {"answer": say, "best": answer, "more_by_voice": suggestions}

@app.post("/more-from-artist")
def more_from_artist(body: MoreFromArtistIn):
    if body.track_id not in TRACK_FP or SPEAKERS.index is None:
        raise HTTPException(400, "Unknown track_id or empty speaker index")
    fp = TRACK_FP[body.track_id].speaker_vec
    nn = SPEAKERS.search(fp, k=max(2, body.top_n + 1))
    out = []
    for sim, t_id in nn:
        if t_id == body.track_id:
            continue
        meta = TRACK_FP.get(t_id)
        if not meta: continue

        if sim < 0.6:  # threshold for "same voice"
            continue
        out.append({"artist": meta.artist, "title": meta.title, "track_id": t_id, "similarity": round(sim,4)})
    return {"results": out}
