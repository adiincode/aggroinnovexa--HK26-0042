import html

import pandas as pd
import requests
import streamlit as st

st.set_page_config(page_title="TrueWrite", page_icon="✒️", layout="wide")

if "base" not in st.session_state:
    st.session_state["base"] = "http://localhost:8000"

# --------------------------------------------------------------------------
# Styling: marker-pen highlights on a cool paper background
# --------------------------------------------------------------------------
st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=Newsreader:ital,wght@0,400;0,500;1,400&family=Instrument+Sans:wght@500;600;700&display=swap');

:root{
  --ink:#172033; --muted:#5B6676; --line:#D9DEE5; --teal:#0B7A75;
  --red:#FF9E9E; --orange:#FFC47D; --yellow:#FFE873;
}
.block-container{padding-top:2rem; max-width:1150px;}
.brand{font-family:'Instrument Sans',sans-serif; font-weight:700; font-size:2.2rem; color:var(--ink); letter-spacing:-0.02em; line-height:1.1;}
.tag{color:var(--muted); margin:.2rem 0 1.2rem 0;}
h1,h2,h3,h4{font-family:'Instrument Sans',sans-serif !important; color:var(--ink); letter-spacing:-0.01em;}

.stat{background:#fff; border:1px solid var(--line); border-radius:12px; padding:1rem 1.2rem; height:100%;}
.stat .l{color:var(--muted); font-size:.88rem;}
.stat .n{font-family:'Instrument Sans',sans-serif; font-size:2.5rem; font-weight:700; line-height:1.15; color:var(--ink);}
.stat .s{color:var(--muted); font-size:.82rem; margin-top:.15rem;}

.legend{display:flex; gap:.6rem; flex-wrap:wrap; margin:.8rem 0 .6rem 0;}
.chip{display:inline-flex; align-items:center; gap:.45rem; background:#fff; border:1px solid var(--line); border-radius:999px; padding:.25rem .8rem; font-size:.88rem; color:var(--ink);}
.dot{width:.8rem; height:.8rem; border-radius:3px; display:inline-block;}
.dot-red{background:var(--red);} .dot-orange{background:var(--orange);} .dot-yellow{background:var(--yellow);}

.paper{font-family:'Newsreader',Georgia,serif; font-size:1.14rem; line-height:1.9; color:var(--ink);
  background:#fff; border:1px solid var(--line); border-radius:6px; padding:1.8rem 2.2rem; box-shadow:0 1px 0 var(--line);}
.mk{padding:0 .1em; cursor:help; -webkit-box-decoration-break:clone; box-decoration-break:clone;}
.mk-red{background:linear-gradient(transparent 10%, var(--red) 10%, var(--red) 92%, transparent 92%);}
.mk-orange{background:linear-gradient(transparent 10%, var(--orange) 10%, var(--orange) 92%, transparent 92%);}
.mk-yellow{background:linear-gradient(transparent 10%, var(--yellow) 10%, var(--yellow) 92%, transparent 92%);}

.quote{font-family:'Newsreader',Georgia,serif; font-size:1.05rem; line-height:1.7; border-left:3px solid var(--line); padding:.2rem 0 .2rem .9rem; color:var(--ink);}

.codebox{background:var(--ink); color:#E8ECF2; border-radius:10px; padding:.8rem 0; font-family:ui-monospace,Consolas,monospace; font-size:.92rem; overflow-x:auto;}
.cl{white-space:pre; padding:.12rem 1rem; border-left:3px solid transparent;}
.cl.on{background:rgba(255,232,115,.18); border-left-color:var(--yellow);}
.ln{display:inline-block; width:2.4em; color:#7C8AA0; user-select:none;}
</style>
""",
    unsafe_allow_html=True,
)

LABELS = {
    "copied": "Copied",
    "paraphrased": "Paraphrased",
    "ai": "Likely AI-written",
}


# --------------------------------------------------------------------------
# API helper
# --------------------------------------------------------------------------
def api(method, path, quiet=False, timeout=300, **kw):
    url = st.session_state["base"].rstrip("/") + path
    try:
        r = requests.request(method, url, timeout=timeout, **kw)
    except requests.exceptions.ConnectionError:
        if not quiet:
            st.error(
                "Can't reach the backend. Start it with `uvicorn main:app --reload` "
                "or fix the Backend URL in the sidebar."
            )
        return None
    except requests.exceptions.Timeout:
        if not quiet:
            st.error("The backend took too long to answer. Try again in a minute.")
        return None
    if not r.ok:
        if not quiet:
            try:
                detail = r.json().get("detail", r.text)
            except Exception:
                detail = r.text
            st.error(f"Backend error {r.status_code}: {detail}")
        return None
    try:
        return r.json()
    except Exception:
        return None


# --------------------------------------------------------------------------
# Rendering helpers
# --------------------------------------------------------------------------
def stat_card(label, value, sub="", color="var(--ink)"):
    return (
        f'<div class="stat"><div class="l">{label}</div>'
        f'<div class="n" style="color:{color}">{value}</div>'
        f'<div class="s">{sub}</div></div>'
    )


def originality_color(score):
    if score is None:
        return "var(--ink)"
    if score >= 80:
        return "#0B7A75"
    if score >= 50:
        return "#B7791F"
    return "#C0392B"


def render_report(rep):
    sents = rep.get("sentences", [])
    orig = rep.get("originality_score")
    ai = rep.get("ai_probability")
    counts = rep.get("counts", {})

    name = rep.get("student_name")
    if name:
        st.markdown(f"### {html.escape(name)}")

    c1, c2, c3 = st.columns(3)
    c1.markdown(
        stat_card(
            "Originality",
            f"{orig:.0f}%" if orig is not None else "n/a",
            "higher means more original",
            originality_color(orig),
        ),
        unsafe_allow_html=True,
    )
    c2.markdown(
        stat_card(
            "AI-writing likelihood",
            f"{ai * 100:.0f}%" if ai is not None else "n/a",
            "an estimate, not proof",
        ),
        unsafe_allow_html=True,
    )
    c3.markdown(
        stat_card(
            "Confidence",
            html.escape(str(rep.get("confidence", "n/a"))),
            f"{rep.get('word_count', 0)} words, {rep.get('sentence_count', 0)} sentences",
        ),
        unsafe_allow_html=True,
    )

    decision = rep.get("decision")
    if decision:
        label = {"accepted": "Accepted by educator", "flagged": "Flagged by educator"}.get(
            decision, decision
        )
        st.caption(f"Educator decision: {label}")

    st.markdown(
        '<div class="legend">'
        f'<span class="chip"><span class="dot dot-red"></span>Copied {counts.get("copied", 0)}</span>'
        f'<span class="chip"><span class="dot dot-orange"></span>Paraphrased {counts.get("paraphrased", 0)}</span>'
        f'<span class="chip"><span class="dot dot-yellow"></span>Likely AI-written {counts.get("ai", 0)}</span>'
        "</div>",
        unsafe_allow_html=True,
    )

    for n in rep.get("notes", []):
        st.info(n)

    parts = []
    for s in sents:
        txt = html.escape(s.get("text", ""))
        if s.get("label") != "clean" and s.get("color"):
            tip = html.escape(s.get("reason") or "", quote=True)
            parts.append(f'<span class="mk mk-{s["color"]}" title="{tip}">{txt}</span>')
        else:
            parts.append(txt)
    st.markdown(f'<div class="paper">{" ".join(parts)}</div>', unsafe_allow_html=True)
    st.caption("Hover over a highlighted sentence to see why it was flagged.")

    flagged = [s for s in sents if s.get("label") != "clean"]
    st.markdown("#### Evidence")
    if not flagged:
        st.success("No sentences were flagged.")
    for s in flagged:
        title = f"{LABELS.get(s['label'], s['label'])}: {s['text'][:80]}"
        with st.expander(title):
            a, b = st.columns(2)
            a.caption("Student's sentence")
            a.markdown(
                f'<div class="quote">{html.escape(s["text"])}</div>',
                unsafe_allow_html=True,
            )
            if s.get("matched_text"):
                b.caption(f"Matched passage from {s.get('source')}")
                b.markdown(
                    f'<div class="quote">{html.escape(s["matched_text"])}</div>',
                    unsafe_allow_html=True,
                )
            else:
                b.caption("Why it was flagged")
                b.write(s.get("reason") or "")
            st.markdown(f"**Reason:** {s.get('reason') or ''}")

    sig = rep.get("ai_signals") or {}
    with st.expander("AI-writing signals"):
        st.write(
            {
                "Classifier score": sig.get("classifier_score"),
                "Mean perplexity (lower is more predictable)": sig.get("mean_perplexity"),
                "Burstiness (lower is more uniform)": sig.get("burstiness"),
            }
        )

    st.caption(rep.get("disclaimer", ""))


def render_quiz(data, key):
    if not data:
        return
    st.markdown("#### Summary")
    st.write(data.get("summary", ""))
    questions = data.get("questions", [])
    if questions:
        st.markdown("#### Practice questions")
    for i, q in enumerate(questions):
        st.markdown(f"**{i + 1}. {q.get('question', '')}**")
        options = q.get("options", [])
        choice = st.radio(
            "Pick one",
            options,
            index=None,
            key=f"{key}_{i}",
            label_visibility="collapsed",
        )
        if choice is not None:
            idx = q.get("answer_index", 0)
            correct = options[idx] if 0 <= idx < len(options) else None
            if choice == correct:
                st.success("Correct.")
            else:
                st.error(f"Not quite. The answer is: {correct}")
            if q.get("explanation"):
                st.caption(q["explanation"])


def render_trace(tr, code):
    if tr.get("error"):
        st.error(tr["error"])
    if tr.get("explanation"):
        st.info(tr["explanation"])
    steps = tr.get("steps", [])
    if not steps:
        return
    if tr.get("truncated"):
        st.warning("Tracing stopped after 300 steps.")

    i = st.slider("Step", 1, len(steps), 1) if len(steps) > 1 else 1
    step = steps[i - 1]

    col_code, col_state = st.columns([3, 2])
    with col_code:
        rows = []
        for n, ln in enumerate(code.splitlines(), 1):
            cls = "cl on" if n == step["line"] else "cl"
            rows.append(
                f'<div class="{cls}"><span class="ln">{n}</span>{html.escape(ln) or " "}</div>'
            )
        st.markdown(f'<div class="codebox">{"".join(rows)}</div>', unsafe_allow_html=True)
    with col_state:
        st.markdown("**Variables**")
        vars_ = step.get("variables", {})
        if vars_:
            st.dataframe(
                pd.DataFrame({"name": list(vars_.keys()), "value": list(vars_.values())}),
                hide_index=True,
            )
        else:
            st.caption("No variables yet.")
        st.markdown("**Output so far**")
        st.code(step.get("output") or "(nothing printed yet)", language=None)
    st.caption("Variables show the state before the highlighted line runs.")

    if tr.get("output"):
        with st.expander("Final output"):
            st.code(tr["output"], language=None)


# --------------------------------------------------------------------------
# Sidebar: backend + assignment
# --------------------------------------------------------------------------
with st.sidebar:
    st.markdown("### Setup")
    st.text_input("Backend URL", key="base")
    health = api("GET", "/health", quiet=True, timeout=5)
    if health:
        st.success("Backend connected")
    else:
        st.error("Backend offline")

    st.markdown("### Assignment")
    assignments = api("GET", "/assignments", quiet=True, timeout=15) or []
    chosen = None
    if assignments:
        chosen = st.selectbox(
            "Working on", assignments, format_func=lambda a: a["title"]
        )
    else:
        st.caption("No assignments yet. Create the first one below.")

    with st.expander("Create an assignment", expanded=not assignments):
        new_title = st.text_input("Title", key="new_title")
        if st.button("Create assignment"):
            if new_title.strip():
                made = api("POST", "/assignments", json={"title": new_title.strip()})
                if made:
                    st.rerun()
            else:
                st.warning("Enter a title first.")

# --------------------------------------------------------------------------
# Main page
# --------------------------------------------------------------------------
st.markdown('<div class="brand">TrueWrite</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="tag">Every flag comes with its reason. You make the call.</div>',
    unsafe_allow_html=True,
)

tab_check, tab_subs, tab_learn = st.tabs(["Check a submission", "Submissions", "Learning tools"])

# ---- Tab 1: check -------------------------------------------------------
with tab_check:
    if not chosen:
        st.info("Create an assignment in the sidebar to start.")
    else:
        with st.form("submit_form"):
            student = st.text_input("Student name")
            text = st.text_area("Paste the essay", height=220)
            up = st.file_uploader("Or upload a PDF or TXT file", type=["pdf", "txt"])
            go = st.form_submit_button("Run check", type="primary")
        st.caption("If you add both text and a file, the file is used.")

        if go:
            if not student.strip():
                st.warning("Enter the student's name.")
            elif not text.strip() and up is None:
                st.warning("Paste some text or upload a file.")
            else:
                data = {"assignment_id": chosen["id"], "student_name": student.strip()}
                if text.strip():
                    data["text"] = text
                files = {"file": (up.name, up.getvalue())} if up else None
                with st.spinner("Checking. The first run is slow while the models load."):
                    res = api("POST", "/submissions", data=data, files=files)
                if res:
                    st.session_state["last_report"] = res

        if st.session_state.get("last_report"):
            render_report(st.session_state["last_report"])
            st.caption("Open this submission in the Submissions tab to add a note and a decision.")

# ---- Tab 2: submissions -------------------------------------------------
with tab_subs:
    if not chosen:
        st.info("Create an assignment in the sidebar to start.")
    else:
        stats = api("GET", f"/assignments/{chosen['id']}/stats")
        if stats:
            s1, s2, s3, s4 = st.columns(4)
            s1.markdown(
                stat_card("Submissions", stats["total_submissions"], f"{stats['analyzed']} analyzed"),
                unsafe_allow_html=True,
            )
            avg_o = stats.get("avg_originality")
            s2.markdown(
                stat_card(
                    "Average originality",
                    f"{avg_o:.0f}%" if avg_o is not None else "n/a",
                    "across analyzed work",
                    originality_color(avg_o),
                ),
                unsafe_allow_html=True,
            )
            s3.markdown(
                stat_card("Needs a closer look", stats["high_risk_count"], "low originality or high AI estimate"),
                unsafe_allow_html=True,
            )
            d = stats.get("decisions", {})
            s4.markdown(
                stat_card(
                    "Decisions",
                    f"{d.get('accepted', 0)} / {d.get('flagged', 0)}",
                    f"accepted / flagged, {d.get('pending', 0)} pending",
                ),
                unsafe_allow_html=True,
            )
            st.write("")

        subs = api("GET", "/submissions", params={"assignment_id": chosen["id"]}) or []
        if not subs:
            st.info("No submissions yet. Run a check in the first tab.")
        else:
            df = pd.DataFrame(
                [
                    {
                        "Student": s["student_name"],
                        "Originality %": s["originality_score"],
                        "AI likelihood %": round((s["ai_probability"] or 0) * 100),
                        "Confidence": s["confidence"],
                        "Decision": s["decision"] or "pending",
                        "Submitted": str(s["created_at"])[:16].replace("T", " "),
                    }
                    for s in subs
                ]
            )
            st.dataframe(df, hide_index=True)

            pick = st.selectbox(
                "Open a submission",
                subs,
                format_func=lambda s: f"{s['student_name']} (#{s['id']})",
            )
            rep = api("GET", f"/submissions/{pick['id']}/report")
            if rep:
                render_report(rep)

                st.markdown("#### Your review")
                options = ["undecided", "accepted", "flagged"]
                names = {
                    "undecided": "Not decided",
                    "accepted": "Accept",
                    "flagged": "Flag for follow-up",
                }
                current = rep.get("decision") or "undecided"
                with st.form(f"review_{pick['id']}"):
                    note = st.text_area("Note", value=rep.get("educator_note") or "")
                    choice = st.radio(
                        "Decision",
                        options,
                        index=options.index(current) if current in options else 0,
                        format_func=lambda o: names[o],
                        horizontal=True,
                    )
                    save = st.form_submit_button("Save review", type="primary")
                if save:
                    payload = {"note": note}
                    if choice != "undecided":
                        payload["decision"] = choice
                    done = api("POST", f"/submissions/{pick['id']}/review", json=payload)
                    if done:
                        st.success("Review saved.")

# ---- Tab 3: learning tools ---------------------------------------------
with tab_learn:
    t_notes, t_video, t_code = st.tabs(["Notes to quiz", "Video to quiz", "Code visualizer"])

    with t_notes:
        with st.form("notes_form"):
            n_text = st.text_area("Paste your notes", height=200)
            n_file = st.file_uploader("Or upload a PDF or TXT file", type=["pdf", "txt"], key="notes_file")
            n_count = st.slider("Number of questions", 3, 10, 5, key="notes_count")
            n_go = st.form_submit_button("Make summary and quiz", type="primary")
        if n_go:
            if not n_text.strip() and n_file is None:
                st.warning("Paste some text or upload a file.")
            else:
                data = {"num_questions": n_count}
                if n_text.strip():
                    data["text"] = n_text
                files = {"file": (n_file.name, n_file.getvalue())} if n_file else None
                with st.spinner("Reading your notes..."):
                    st.session_state["quiz_notes"] = api("POST", "/text/process", data=data, files=files)
        render_quiz(st.session_state.get("quiz_notes"), "qn")

    with t_video:
        with st.form("video_form"):
            v_url = st.text_input("YouTube link")
            v_count = st.slider("Number of questions", 3, 10, 5, key="video_count")
            v_go = st.form_submit_button("Make summary and quiz", type="primary")
        if v_go:
            if not v_url.strip():
                st.warning("Paste a YouTube link.")
            else:
                with st.spinner("Fetching the transcript..."):
                    st.session_state["quiz_video"] = api(
                        "POST", "/video/process", json={"url": v_url.strip(), "num_questions": v_count}
                    )
        vq = st.session_state.get("quiz_video")
        render_quiz(vq, "qv")
        if vq and vq.get("transcript_preview"):
            with st.expander("Transcript preview"):
                st.write(vq["transcript_preview"])

    with t_code:
        sample = "total = 0\nfor i in range(1, 4):\n    total = total + i\n    print(total)\n"
        code_in = st.text_area("Python code", value=sample, height=180, key="code_in")
        explain = st.checkbox("Add a plain-language explanation", value=True)
        if st.button("Trace the code", type="primary"):
            with st.spinner("Running the code..."):
                res = api(
                    "POST",
                    "/code/visualize",
                    json={"code": code_in, "explain": explain},
                    timeout=60,
                )
            if res:
                st.session_state["trace"] = res
                st.session_state["trace_code"] = code_in
        if st.session_state.get("trace"):
            render_trace(st.session_state["trace"], st.session_state.get("trace_code", ""))