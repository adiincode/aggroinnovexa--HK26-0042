from pathlib import Path

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from services.extract import split_sentences

REF_DIR = Path(__file__).resolve().parent.parent / "references"

# Thresholds: apne test samples par tune karna
TFIDF_COPIED = 0.80
EMB_COPIED = 0.95
EMB_PARAPHRASED = 0.75

_model = None
_ref_cache = {"items": None, "emb": None}


def _get_model():
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer("all-MiniLM-L6-v2")
    return _model


def _embed(texts):
    return _get_model().encode(
        texts,
        convert_to_numpy=True,
        normalize_embeddings=True,
        show_progress_bar=False,
    )


def load_reference_items():
    """references/*.txt ke sentences. Ek baar load hote hain (server restart par refresh)."""
    if _ref_cache["items"] is None:
        items = []
        if REF_DIR.exists():
            for f in sorted(REF_DIR.glob("*.txt")):
                content = f.read_text(encoding="utf-8", errors="ignore")
                for s in split_sentences(content):
                    items.append({"text": s, "source": f.stem.replace("_", " ")})
        _ref_cache["items"] = items
        _ref_cache["emb"] = _embed([i["text"] for i in items]) if items else None
    return _ref_cache["items"], _ref_cache["emb"]


def analyze_plagiarism(sentences: list[str], peer_items: list[dict] | None = None) -> list[dict]:
    file_items, file_emb = load_reference_items()
    peer_items = peer_items or []
    items = list(file_items) + list(peer_items)

    if not sentences or not items:
        return []

    ref_texts = [i["text"] for i in items]

    # Pass 1: TF-IDF (exact / near-exact)
    try:
        vec = TfidfVectorizer(ngram_range=(1, 2), stop_words="english")
        vec.fit(ref_texts + sentences)
        tfidf_sim = cosine_similarity(vec.transform(sentences), vec.transform(ref_texts))
    except ValueError:
        tfidf_sim = np.zeros((len(sentences), len(items)))
    tfidf_idx = tfidf_sim.argmax(axis=1)
    tfidf_best = tfidf_sim.max(axis=1)

    # Pass 2: sentence embeddings (paraphrase)
    sent_emb = _embed(sentences)
    parts = []
    if file_emb is not None:
        parts.append(file_emb)
    if peer_items:
        parts.append(_embed([p["text"] for p in peer_items]))
    ref_emb = np.vstack(parts)
    emb_sim = sent_emb @ ref_emb.T
    emb_idx = emb_sim.argmax(axis=1)
    emb_best = emb_sim.max(axis=1)

    flags = []
    for i, sentence in enumerate(sentences):
        t_sim, t_i = float(tfidf_best[i]), int(tfidf_idx[i])
        e_sim, e_i = float(emb_best[i]), int(emb_idx[i])

        if t_sim >= TFIDF_COPIED:
            label, sim, src = "copied", t_sim, items[t_i]
            reason = f"{round(sim * 100)}% word-level match with a passage from {src['source']}"
        elif e_sim >= EMB_COPIED:
            label, sim, src = "copied", e_sim, items[e_i]
            reason = f"{round(sim * 100)}% near-identical match with a passage from {src['source']}"
        elif e_sim >= EMB_PARAPHRASED:
            label, sim, src = "paraphrased", e_sim, items[e_i]
            reason = (
                f"{round(sim * 100)}% semantic match with a passage from {src['source']} "
                f"(same meaning, different words)"
            )
        else:
            continue

        flags.append({
            "index": i,
            "sentence": sentence,
            "label": label,
            "color": "red" if label == "copied" else "orange",
            "similarity": round(sim, 3),
            "source": src["source"],
            "matched_text": src["text"],
            "reason": reason,
        })
    return flags