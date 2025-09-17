from jigsawstack import JigsawStack
from dotenv import load_dotenv
import requests
load_dotenv()

jigsaw = JigsawStack()


with open("audio_clips/elevated.mp3", "rb") as f:
    resp = jigsaw.store.upload(
        f,
        {
            "overwrite": True,
            "temp_public_url": True
        }
    )
    if resp.get("status") != "success":
        print("Upload failed:", resp)
        exit(1)
    print("Upload response:", resp)


    with open("audio_clips/elevated_downloaded.mp3", "wb") as f:
        f.write(requests.get(resp["temp_public_url"]).content)