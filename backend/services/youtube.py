import re

from youtube_transcript_api import YouTubeTranscriptApi


def extract_video_id(url: str) -> str:
    m = re.search(r"(?:v=|youtu\.be/|embed/|shorts/)([A-Za-z0-9_-]{11})", url)
    if not m:
        raise ValueError("Invalid YouTube link")
    return m.group(1)


def get_transcript(url: str) -> str:
    video_id = extract_video_id(url)
    langs = ["en", "hi"]
    api = YouTubeTranscriptApi()
    if hasattr(api, "fetch"):
        fetched = api.fetch(video_id, languages=langs)
        parts = [s.text for s in fetched]
    else:
        parts = [x["text"] for x in YouTubeTranscriptApi.get_transcript(video_id, languages=langs)]
    text = " ".join(parts).strip()
    if not text:
        raise ValueError("No transcript found for this video")
    return text