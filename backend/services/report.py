WEIGHTS = {"copied": 1.0, "paraphrased": 0.7, "ai": 0.4}

DISCLAIMER = (
    "This report is an indicator, not a verdict. AI detection is probabilistic and can be "
    "wrong, especially for non-native English writers and short texts. The educator makes the final decision."
)


def build_report(sentences, plag_flags, ai_result, reference_count: int) -> dict:
    plag_by_idx = {f["index"]: f for f in plag_flags}
    ai_by_idx = {f["index"]: f for f in ai_result["flags"]}

    items = []
    counts = {"copied": 0, "paraphrased": 0, "ai": 0}
    weight_sum = 0.0

    for i, text in enumerate(sentences):
        flag = plag_by_idx.get(i) or ai_by_idx.get(i)  # plagiarism ko priority
        if flag:
            label = flag["label"]
            counts[label] += 1
            weight_sum += WEIGHTS[label] * float(flag["similarity"])
            items.append({
                "index": i,
                "text": text,
                "label": label,
                "color": flag["color"],
                "strength": flag["similarity"],
                "source": flag["source"],
                "matched_text": flag["matched_text"],
                "reason": flag["reason"],
            })
        else:
            items.append({
                "index": i, "text": text, "label": "clean", "color": None,
                "strength": None, "source": None, "matched_text": None, "reason": None,
            })

    total = max(len(sentences), 1)
    originality = round(max(0.0, 100.0 * (1.0 - weight_sum / total)), 1)

    words = sum(len(s.split()) for s in sentences)
    points = 0
    if words >= 300:
        points += 2
    elif words >= 120:
        points += 1
    if reference_count >= 50:
        points += 1
    clf = ai_result.get("classifier_score")
    if clf is not None and (clf >= 0.75 or clf <= 0.25):
        points += 1
    confidence = "High" if points >= 3 else "Medium" if points == 2 else "Low"

    notes = []
    if words < 120:
        notes.append("Short text: signals are weak, treat results with extra caution.")
    if reference_count == 0:
        notes.append("No reference texts available, so plagiarism matching could not run.")
    if clf is None:
        notes.append("AI classifier unavailable, AI estimate uses statistical signals only.")

    return {
        "originality_score": originality,
        "ai_probability": ai_result["ai_probability"],
        "confidence": confidence,
        "word_count": words,
        "sentence_count": len(sentences),
        "counts": counts,
        "ai_signals": {
            "classifier_score": ai_result["classifier_score"],
            "mean_perplexity": ai_result["mean_perplexity"],
            "burstiness": ai_result["burstiness"],
        },
        "sentences": items,
        "notes": notes,
        "disclaimer": DISCLAIMER,
    }