import io
import re

from pypdf import PdfReader

MIN_WORDS = 4


def extract_text_from_pdf(data: bytes) -> str:
    reader = PdfReader(io.BytesIO(data))
    pages = [(page.extract_text() or "") for page in reader.pages]
    return "\n\n".join(pages)


def clean_text(text: str) -> str:
    text = text.replace("\r", "\n")
    text = re.sub(r"-\n(?=[a-z])", "", text)              # hyphenated line breaks
    text = re.sub(r"(?m)^\s*\d{1,3}\s*$", "", text)       # lone page numbers
    text = re.sub(r"\n\s*\n+", "\n\n", text)              # paragraph breaks
    text = re.sub(r"(?<!\n)\n(?!\n)", " ", text)          # single newline -> space
    text = re.sub(r"[ \t]+", " ", text)
    return text.strip()


def split_sentences(text: str) -> list[str]:
    text = clean_text(text)
    sentences: list[str] = []
    for para in text.split("\n\n"):
        parts = re.split(r'(?<=[.!?])\s+(?=[A-Z0-9"\'(])', para.strip())
        for p in parts:
            p = p.strip()
            if len(p.split()) >= MIN_WORDS:
                sentences.append(p)
    return sentences