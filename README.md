<div align="center">

# CampusBrief

**Turn long campus briefs into structured Action Cards — not summaries, but what to do next.**

Built for **UNNC 30H AI Hackathon 2026** | Campus Track

Shihao Liu &middot; Pu Xu &middot; Yuchi Dai

</div>

---

## Problem

Students receive long, unstructured briefs (assignments, exams, competitions, scholarships...) but struggle to quickly identify **what to do, by when, and what's at risk**. Generic AI summaries tell you what the text *says* — not what you should *do*.

## Solution

Paste or upload any campus document. CampusBrief runs a **3-step AI pipeline** and outputs a structured **Action Card** with deadlines, team steps, and risk flags — ready to execute.

```
Input (brief)  ──→  Classify  ──→  Extract  ──→  Plan  ──→  Action Card
```

| Step | What it does |
|------|-------------|
| **Classify** | Identifies document type (6 categories) with confidence score |
| **Extract** | Pulls structured fields — requirements, deadlines, deliverables, constraints |
| **Plan** | Generates team action steps, timeline, and risk flags |

> Each step uses a **dedicated prompt with type-specific strategy** — not a single generic call.

## Features

- **6 document types** — Assignment, Competition, Event, Exam, Application, Notice (auto-detected)
- **Action Card output** — 5 modules: overview, key requirements, team actions, deadlines, risk flags
- **Timeline view** — visual deadline timeline with `.ics` calendar export
- **vs Summary comparison** — side-by-side: generic summary vs structured Action Card
- **File upload** — drag-and-drop PDF / DOCX / TXT
- **Bilingual** — works with both English and Chinese content
- **History** — SQLite persistence, revisit past results
- **Demo mode** — fully offline with pre-computed results for all 6 types

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Flask (Python) |
| AI Model | MiniMax-M2.5 via OpenAI SDK |
| Frontend | Vanilla HTML / CSS / JS |
| Database | SQLite |
| Icons | Lucide |

## Product Brief

[CampusBrief_Product_Brief](docs/CampusBrief_Product_Brief.pdf)

---

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Configure environment
cp .env.example .env
# Edit .env — add your MiniMax API key, or set DEMO_MODE=true

# 3. Run
python run.py
# Open http://localhost:5000 / http://127.0.0.1:5000
```

## Project Structure

```
CampusBrief/
├── run.py                  # Entry point
├── requirements.txt
├── .env.example
├── .gitignore
├── README.md
│
├── src/                    # Backend source code
│   ├── __init__.py
│   ├── server.py           # Flask API server
│   ├── pipeline.py         # 3-step AI pipeline (Classify → Extract → Plan)
│   ├── prompts.py          # All LLM prompt templates
│   ├── database.py         # SQLite persistence layer
│   └── utils.py            # JSON parsing, demo data, sample loader
│
├── static/
│   ├── css/style.css       # UI styles (glassmorphism design)
│   └── js/app.js           # Frontend logic
│
├── templates/
│   └── index.html          # Main page
│
├── samples/                # 6 demo brief files
│   ├── demo_assignment.txt
│   ├── demo_hackathon.txt
│   ├── demo_event.txt
│   ├── demo_exam.txt
│   ├── demo_application.txt
│   └── demo_notice.txt
│
├── data/
│   └── campusbrief.db      # SQLite database (auto-created)
│
└── docs/
    └── CampusBrief_Product_Brief.pdf
```

## Key Files

| File | Description | Link |
|------|-------------|------|
| `src/pipeline.py` | Core 3-step AI pipeline logic | [View](./src/pipeline.py) |
| `src/prompts.py` | All LLM prompt templates with type-specific strategies | [View](./src/prompts.py) |
| `src/server.py` | Flask REST API & file upload handling | [View](./src/server.py) |
| `static/js/app.js` | Frontend: UI rendering, timeline, calendar export | [View](./static/js/app.js) |
| `static/css/style.css` | Full UI design | [View](./static/css/style.css) |
| `src/utils.py` | Demo data & JSON parsing utilities | [View](./src/utils.py) |

## Why Not Just Summarize?

| | Generic Summary | CampusBrief Action Card |
|---|---|---|
| **Output** | Paragraph of text | Structured 5-module card |
| **Focus** | What the text says | What to do next |
| **Deadlines** | Buried in prose | Extracted + timeline |
| **Team steps** | None | Ordered action plan |
| **Risk flags** | None | Missing info surfaced |

## AI Depth

This is **not** a single-prompt LLM wrapper. Each generation makes **4 LLM calls** across two pipelines:

**Main pipeline (3 chained calls — output of each feeds into the next):**

1. **Classifier** — determines document type + confidence, enabling type-specific downstream behavior
2. **Extractor** — uses type-aware prompts to pull structured fields (e.g., grading criteria for assignments, eligibility for scholarships)
3. **Planner** — generates actionable steps, team workflow, and risk flags adapted to the document type

**Comparison pipeline (1 independent call):**

4. **Naive Summarizer** — generates a generic summary using a simple prompt, displayed side-by-side with the Action Card so users can see the difference

Classification confidence, extraction completeness, and planning quality are all visible in the UI's **Pipeline Trace** log.

---

<div align="center">

**UNNC 30H AI Hackathon 2026** — Campus Track &middot; Powered by MiniMax-M2.5

</div>
