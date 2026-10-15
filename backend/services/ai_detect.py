import math

# Classifier model. Agar load na ho to koi aur HF human-vs-AI model yahan daal sakte ho.
CLASSIFIER_MODEL = "Hello-SimpleAI/chatgpt-detector-roberta"
AI_LABELS = {"chatgpt", "ai", "fake", "machine", "generated", "label_1"}

# Tunable thresholds
AI_THRESHOLD = 0.5      # document AI probability is se upar ho tabhi sentences yellow
PPL_FLAG = 50.0         # is se kam perplexity wale sentences "predictable" maane jayenge
MAX_SENTENCES = 80
MIN_WORDS_STRONG = 120

_clf = None
_lm = None


def _get_clf():
    global _clf
    if _clf is None:
        from transformers import pipeline
        _clf = pipeline(
            "text-classification",
            model=CLASSIFIER_MODEL,
            top_k=None,
            truncation=True,
            max_length=512,
        )
    return _clf


def _get_lm():
    global _lm
    if _lm is None:
        from transformers import AutoModelForCausalLM, AutoTokenizer
        tok = AutoTokenizer.from_pretrained("distilgpt2")
        model = AutoModelForCausalLM.from_pretrained("distilgpt2")
        model.eval()
        _lm = (tok, model)
    return _lm


def _chunks(sentences: list[str], words_per_chunk: int = 200, max_chunks: int = 5) -> list[str]:
    chunks, cur, count = [], [], 0
    for s in sentences:
        cur.append(s)
        count += len(s.split())
        if count >= words_per_chunk:
            chunks.append(" ".join(cur))
            cur, count = [], 0
    if cur:
        chunks.append(" ".join(cur))
    return chunks[:max_chunks]


def _classifier_score(sentences: list[str]):
    try:
        clf = _get_clf()
        results = clf(_chunks(sentences))
        scores = []
        for res in results:
            ai = 0.0
            for r in res:
                if r["label"].lower() in AI_LABELS:
                    ai = float(r["score"])
                    break
            scores.append(ai)
        return sum(scores) / len(scores) if scores else None
    except Exception as e:  # model load/network issue
        print(f"[ai_detect] classifier unavailable: {e}")
        return None


def _perplexity(sentence: str):
    import torch
    tok, model = _get_lm()
    enc = tok(sentence, return_tensors="pt", truncation=True, max_length=128)
    if enc["input_ids"].shape[1] < 3:
        return None
    with torch.no_grad():
        out = model(**enc, labels=enc["input_ids"])
    return float(math.exp(float(out.loss)))


def _clip(x: float) -> float:
    return max(0.0, min(1.0, x))


def detect_ai(sentences: list[str]) -> dict:
    words = sum(len(s.split()) for s in sentences)
    result = {
        "ai_probability": 0.0,
        "classifier_score": None,
        "mean_perplexity": None,
        "burstiness": None,
        "flags": [],
        "weak_signal": words < MIN_WORDS_STRONG,
    }
    if not sentences:
        return result

    clf_score = _classifier_score(sentences)

    ppls: dict[int, float] = {}
    try:
        for i, s in enumerate(sentences[:MAX_SENTENCES]):
            p = _perplexity(s)
            if p is not None:
                ppls[i] = p
    except Exception as e:
        print(f"[ai_detect] perplexity unavailable: {e}")
        ppls = {}

    ppl_score = burst_score = None
    if len(ppls) >= 2:
        vals = list(ppls.values())
        mean = sum(vals) / len(vals)
        std = math.sqrt(sum((v - mean) ** 2 for v in vals) / len(vals))
        burst = std / mean if mean else 0.0
        ppl_score = _clip((120.0 - mean) / 100.0)
        burst_score = _clip((0.9 - burst) / 0.6)
        result["mean_perplexity"] = round(mean, 1)
        result["burstiness"] = round(burst, 3)

    if clf_score is not None and ppl_score is not None:
        prob = 0.6 * clf_score + 0.25 * ppl_score + 0.15 * burst_score
    elif ppl_score is not None:
        prob = 0.65 * ppl_score + 0.35 * burst_score
    elif clf_score is not None:
        prob = clf_score
    else:
        prob = 0.0

    prob = round(float(_clip(prob)), 3)
    result["ai_probability"] = prob
    result["classifier_score"] = round(clf_score, 3) if clf_score is not None else None

    if prob >= AI_THRESHOLD:
        for i, p in ppls.items():
            if p <= PPL_FLAG:
                result["flags"].append({
                    "index": i,
                    "sentence": sentences[i],
                    "label": "ai",
                    "color": "yellow",
                    "similarity": prob,
                    "source": None,
                    "matched_text": None,
                    "reason": (
                        f"Likely AI-written: document AI probability {round(prob * 100)}%, "
                        f"and this sentence is very predictable (perplexity {round(p)})"
                    ),
                })
    return result