# Who Sang That?

A RAG-powered API that identifies which artist sang a specific lyric and finds similar tracks by voice fingerprint. Powered by JigsawStack

## Features

- **Lyric Search**: Find who sang a specific line with timestamp precision
- **Voice Similarity**: Discover more tracks by the same artist using speaker fingerprints
- **Speaker Diarization**: Automatic speaker separation in audio files
- **Multimodal Embeddings**: Powered by JigsawStack's [embedding v2 API](https://jigsawstack.com/docs/api-reference/ai/embedding-v2)

## Quick Start

```bash
# Install dependencies
pip install fastapi jigsawstack faiss-cpu python-multipart python-dotenv

#or
uv sync

# Get your JigsawStack API key at https://jigsawstack.com/
# Set your JigsawStack API key
echo "JIGSAWSTACK_API_KEY=your_key_here" > .env

# Run the server
uvicorn main:app --reload
```

## API Endpoints

### Upload Songs
```bash
POST /ingest-songs
# Upload audio files with artist/title metadata
```

### Find Who Said What
```bash
POST /who-said
{
  "quote": "your favorite lyric here",
  "k": 5
}
```

### More From Artist
```bash
POST /more-from-artist
{
  "track_id": "artist:title:hash",
  "top_n": 5
}
```

## Tech Stack

- **FastAPI** for the REST API
- **FAISS** for vector similarity search
- **JigsawStack** for audio transcription and embeddings
- **NumPy** for vector operations
