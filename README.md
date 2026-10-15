# TrueWrite

**A plagiarism and AI-content checker that shows its work, so teachers can make fair calls.**

Built for the AS-01 problem statement (AI-Powered Plagiarism & AI-Generated Content Detector).

- Live demo: `ADD_LINK_HERE`
- Demo video: `ADD_LINK_HERE`
- Backend API docs: `https://YOUR-CLOUD-RUN-URL/docs`

---

## Why we built this

Ask any teacher right now and they will tell you the same thing: they can no longer tell who wrote what.

A student copies a paragraph from Wikipedia and changes a few words. Another pastes a ChatGPT answer and fixes the grammar. Old plagiarism checkers look for matching words, so both of these walk straight through.

And there is a second, quieter problem. Most tools just throw a number at the teacher, like "63% plagiarised", with no explanation. A teacher cannot confront a student with a number. Worse, AI detectors are known to get it wrong sometimes, and a wrong accusation can hurt a student who did nothing wrong.

So we set ourselves two rules while building this:

1. **Catch more**, including paraphrased and AI-written text.
2. **Explain everything**, so the teacher decides, not the algorithm.

---

## What makes TrueWrite different

### 1. It explains every flag
Every highlighted sentence comes with a reason and evidence. Not "suspicious", but something like *"84% semantic match with this passage from Source X"* or *"very uniform sentence structure and low word unpredictability"*. The teacher sees the original and the matching text side by side.

### 2. It catches paraphrasing, not only copy-paste
We compare **meaning**, not just words. Sentence embeddings let us notice that "The mitochondria produces energy for the cell" and "Cells get their power from the mitochondria" are the same idea. This is exactly where traditional checkers fall short.

### 3. Plagiarism and AI-writing in one report
One upload gives you one report with three clear labels:

| Colour | Meaning |
|---|---|
| Red | Copied (near-exact match) |
| Orange | Paraphrased (same meaning, different words) |
| Yellow | Likely AI-written |

### 4. Built around fairness, not accusation
We are honest about something most tools hide: AI detection is a probability, not proof, and it can be less reliable on writing by non-native English speakers. So:

- Every result shows a **confidence level**, not just a score.
- The report clearly says it is an *indicator*, not a verdict.
- The **educator makes the final decision**. They can accept, flag, or leave a note. Nothing is automatic.

### 5. It checks students against each other
Copying from a classmate will not show up on the internet, so we also compare every submission against the others in the same assignment. This is where a lot of real-world copying happens.

### 6. It works on a phone
The whole thing is a Flutter app. A teacher can review submissions on the bus, not just at a desk.

### 7. It helps the student too
Catching someone is half the job. If a submission is flagged, the student gets a **"Learn this topic"** button that turns their own text into a summary and a short quiz. The goal is that they understand the material, not just that they get caught.

---

## How it works

```
Student uploads text / PDF
        |
        v
Extract text, clean it, split into sentences
        |
        +--> Plagiarism engine
        |      - TF-IDF for exact and near-exact matches
        |      - Sentence embeddings for paraphrase detection
        |      - Comparison against reference texts AND other submissions
        |
        +--> AI-writing engine
        |      - Pretrained transformer classifier
        |      - Perplexity and burstiness signals
        |
        v
Combine results -> originality score, confidence, flagged sentences with reasons
        |
        v
Saved in PostgreSQL -> Educator dashboard
```

### The plagiarism side
We first run a fast TF-IDF pass to catch obvious copying. Then every remaining sentence is turned into an embedding (`all-MiniLM-L6-v2`) and compared by cosine similarity. A sentence that is far from the source in wording but close in meaning gets flagged as paraphrased.

### The AI-writing side
We use two signals together, because either one alone is shaky:

- A transformer-based classifier trained to separate human and AI text.
- Statistical signals such as perplexity and burstiness. Human writing tends to be less predictable and more uneven. AI text tends to be smooth and consistent.

### The originality score
Originality is based on how much of the document is flagged, weighted by how strong each match is. We show the score together with a confidence level so a borderline number is not mistaken for certainty.

---

## Features

**Main product (integrity checking)**
- Upload text, paste text, or upload a PDF
- Sentence-level highlighting with reasons and matched sources
- Originality score with confidence level
- Class-wide comparison between submissions
- Educator dashboard: submissions list, report view, notes, accept/flag
- Class statistics

**Student tools (bonus)**
- **Code Visualizer:** run Python code and step through it line by line, watching variables change, with a plain-language explanation
- **Notes to Quiz:** paste text or upload a PDF, get a summary and practice questions
- **Video to Quiz:** paste a YouTube link, get a transcript-based summary and questions

---

## Tech stack

| Layer | What we used |
|---|---|
| Mobile app | Flutter |
| Backend | Python, FastAPI |
| NLP / ML | scikit-learn, Hugging Face Transformers, sentence-transformers |
| LLM (for summaries and quizzes) | Groq API |
| Database | PostgreSQL |
| Packaging | Docker |
| Hosting | Google Cloud Run |

---

## Running it locally

### Backend

```bash
git clone https://github.com/YOUR_USERNAME/truewrite.git
cd truewrite/backend

python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

Create a `.env` file:

```
GROQ_API_KEY=your_key_here
DATABASE_URL=postgresql://user:password@host:5432/dbname
```

Start the server:

```bash
uvicorn main:app --reload
```

API docs will be at `http://localhost:8000/docs`.

### With Docker

```bash
docker build -t truewrite .
docker run -p 8080:8080 --env-file .env truewrite
```

### Flutter app

```bash
cd ../app
flutter pub get
```

Open `lib/services/api_service.dart` and set `base` to your backend URL, then:

```bash
flutter run
```

---

## Deploying to Google Cloud Run

```bash
gcloud config set project YOUR_PROJECT_ID
gcloud services enable run.googleapis.com cloudbuild.googleapis.com secretmanager.googleapis.com

echo -n "YOUR_GROQ_KEY" | gcloud secrets create GROQ_API_KEY --data-file=-

cd backend
gcloud run deploy truewrite \
  --source . \
  --region asia-south1 \
  --allow-unauthenticated \
  --memory 2Gi \
  --timeout 300 \
  --set-secrets GROQ_API_KEY=GROQ_API_KEY:latest
```

---

## API overview

| Method | Endpoint | What it does |
|---|---|---|
| POST | `/assignments` | Create an assignment |
| POST | `/submissions` | Submit work and run the analysis |
| GET | `/submissions?assignment_id=` | List submissions for the dashboard |
| GET | `/submissions/{id}/report` | Full report with highlights and evidence |
| POST | `/submissions/{id}/review` | Educator note and decision |
| GET | `/assignments/{id}/stats` | Class-level statistics |
| POST | `/code/visualize` | Step-by-step execution trace |
| POST | `/text/process` | Summary and questions from text or PDF |
| POST | `/video/process` | Summary and questions from a YouTube link |

---

## How well does it work?

We tested on a small set of samples we prepared ourselves: original essays, copy-pasted text, paraphrased text, and AI-generated text.

| Test | Result |
|---|---|
| Copy-paste detection | `FILL_IN_FROM_YOUR_TESTS` |
| Paraphrase detection | `FILL_IN_FROM_YOUR_TESTS` |
| AI-text detection | `FILL_IN_FROM_YOUR_TESTS` |
| False positives on human text | `FILL_IN_FROM_YOUR_TESTS` |

These come from a small test set, so please treat them as a starting point and not as a benchmark.

---

## Limitations (we would rather tell you)

- AI detection is probabilistic. It can miss AI text that has been heavily edited, and it can wrongly flag some human writing. This is why a human always makes the final call.
- Our reference collection is limited. Matches are only as good as the sources we compare against. Web-scale checking is on the roadmap.
- Very short submissions give weak signals.
- Currently tuned for English.
- The code visualizer runs code in a restricted environment, so some Python features are intentionally unavailable.

---

## What we would build next

- Web search as a reference source
- DOCX support
- Regional language support, starting with Hindi
- Teacher-side controls for adjusting sensitivity
- Writing-history comparison, so a student's work is compared with their own earlier style
- Proper login and institution-level accounts

---

## Project structure

```
truewrite/
├── backend/
│   ├── main.py
│   ├── db.py
│   ├── models.py
│   ├── routers/        # integrity, assignments, code, text, video
│   ├── services/       # extract, plagiarism, ai_detect, report, llm, tracer, youtube
│   ├── requirements.txt
│   └── Dockerfile
└── app/                # Flutter app
```

---

## Team

| Name | Role |
|---|---|
| `NAME` | `ROLE` |
| `NAME` | `ROLE` |
| `NAME` | `ROLE` |

---

## A note on responsible use

TrueWrite is meant to support teachers, not replace their judgement. A flag is a reason to look closer, never a reason to punish on its own. Please use it that way.
