# Setup & Local Development Guide

This guide walks through setting up and running the PartSelect Support Assistant on your own machine. There are two services: a **Python FastAPI backend** and a **Next.js frontend**. Both must be running for the app to work.

---

## Prerequisites

| Tool | Version | Notes |
|------|---------|-------|
| Python | 3.8+ | Tested on 3.8; should work on 3.10+ |
| Node.js | 18+ | For the Next.js frontend |
| npm | 9+ | Comes with Node |
| Git | any | To clone the repo |

---

## 1. Clone the repo

```bash
git clone <repo-url>
cd partselect-instalily-case-study
```

---

## 2. Backend — Environment variables

Create `backend/.env` by copying the example:

```bash
cp backend/.env.example backend/.env
```

Then fill in the values:

```env
# Required — Anthropic API key for Claude Sonnet + Haiku
ANTHROPIC_API_KEY=sk-ant-...

# Required — Voyage AI key for generating/querying embeddings
# Sign up free at https://www.voyageai.com
EMBEDDING_API_KEY=pa-...

# Optional — comma-separated allowed CORS origins (default: localhost:3000)
ALLOWED_ORIGINS=http://localhost:3000

# Optional — embedding model (default: voyage-3-lite, cheapest option)
EMBEDDING_PROVIDER=voyage
EMBEDDING_MODEL=voyage-3-lite
```

### What happens without these keys

| Key missing | Effect |
|-------------|--------|
| `ANTHROPIC_API_KEY` | Server **fails to start** — Pydantic-settings treats this as a required field with no default. For local testing without a key, add a dummy value and expect all `/api/chat` requests to return HTTP 500. |
| `EMBEDDING_API_KEY` | The app **starts fine**. Vector search is skipped when `vector_index.json` doesn't exist or can't be queried. Agents fall back to catalog-only responses (products.json + compatibility.json data), which still work but without RAG guide retrieval. |

### Swapping out Claude

The LLM integration is isolated to one file: `backend/app/llm/claude_client.py`. To replace Claude with another provider (OpenAI, Gemini, etc.):
1. Rewrite `chat_claude()` and `chat_claude_json()` to call your provider's SDK.
2. Update `MODEL_FULL` and `MODEL_FAST` constants to your model names.
3. Nothing else in the codebase needs to change.

Similarly, the embedding provider is isolated to `backend/app/tools/embeddings.py`. Adding an OpenAI or Cohere embedding backend means adding a new `_embed_<provider>()` function there.

---

## 3. Backend — Install and run

```bash
cd backend

# Create a virtual environment
python -m venv .venv

# Activate it
# Windows:
.venv\Scripts\activate
# macOS / Linux:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Build the vector index (required for RAG to work)
# This calls the Voyage AI API — takes ~10–30 seconds depending on guide count
PYTHONPATH=. python scripts/build_index.py

# Start the API server
uvicorn app.main:app --reload
```

The backend runs at **`http://localhost:8000`**.

To verify it started: open `http://localhost:8000/api/health` — should return `{"status": "ok"}`.

> **Windows note:** Use `.venv\Scripts\activate` and `set PYTHONPATH=.` before the build script, or prefix with `PYTHONPATH=.` using Git Bash / WSL.

---

## 4. Frontend — Environment variables

`frontend/.env.local` should contain:

```env
# URL of the FastAPI backend (default shown below)
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

This file already exists in the repo with the default value. Only change it if your backend runs on a different port.

---

## 5. Frontend — Install and run

```bash
cd frontend

# Install dependencies
npm install

# Start the dev server
npm run dev
```

The frontend runs at **`http://localhost:3000`**.

---

## 6. First run

1. Open `http://localhost:3000` — you land on the home page.
2. Click **Start Chat** or navigate to `/support` — you are redirected to `/login` (middleware auth guard).
3. Log in with a demo account:
   - `instalily` / `instalily`
   - `harshit` / `harshit`
4. The support page opens with three columns: **Conversations** (left), **Chat** (centre), **Cart** (right).

---

## 7. (Optional) Rebuild the vector index

The index only needs to be rebuilt when you:
- Add or edit guides in `install_guides.jsonl` or `troubleshooting_guides.jsonl`
- Change the chunking strategy in `scripts/build_index.py`
- Switch to a different embedding model

```bash
cd backend
PYTHONPATH=. python scripts/build_index.py
```

Output is written to `backend/app/data/vector_index.json`.

---

## 8. (Optional) Run RAG evaluation

```bash
cd backend
PYTHONPATH=. python scripts/eval_rag.py
```

Prints per-query pass/fail and overall `Recall@3` across 8 labelled queries.

---

## 9. (Optional) Update product images / scrape new parts

Two offline scripts are included for data maintenance. These do **not** run in production:

```bash
# Fix broken product image URLs using Playwright (real browser rendering)
# Requires: pip install playwright && playwright install chromium
cd backend
python scripts/update_image_urls.py --headless

# Scrape new part numbers from PartSelect and append to products.json
python scripts/scrape_partselect.py --input part_numbers.txt
```

---

## 10. Common issues

| Problem | Likely cause | Fix |
|---------|-------------|-----|
| `pydantic_settings.env_file not found` | Running from wrong directory | Run `uvicorn` from inside `backend/` |
| `ANTHROPIC_API_KEY missing` | `.env` not created | Copy `.env.example` to `.env` and fill in the key |
| `/api/chat` returns 401 | No auth token in request | Log in at `/login` first |
| Vector search returns nothing | Index not built | Run `build_index.py` |
| CORS error in browser | Frontend origin not allowed | Add `http://localhost:3000` to `ALLOWED_ORIGINS` in `.env` |
| `ModuleNotFoundError: app` | PYTHONPATH not set | Prefix script commands with `PYTHONPATH=.` |
| Login button has no effect | Backend not running | Start `uvicorn app.main:app --reload` first |

---

## Directory structure (quick reference)

```
partselect-instalily-case-study/
├── backend/
│   ├── .env                  ← your local secrets (not committed)
│   ├── .env.example          ← template
│   ├── requirements.txt
│   ├── app/
│   │   ├── main.py
│   │   ├── api/              ← FastAPI routers
│   │   ├── core/             ← config, security, logging
│   │   ├── data/             ← all JSON data files
│   │   ├── llm/              ← Claude client (swap here for other LLMs)
│   │   ├── models/           ← Pydantic schemas
│   │   ├── services/         ← business logic (agent, thread store, cart store)
│   │   └── tools/            ← retrieval, embeddings, rerank, products
│   └── scripts/              ← offline build / eval / scrape tools
└── frontend/
    ├── .env.local            ← frontend env (API base URL)
    ├── middleware.ts          ← auth guard (runs at edge)
    ├── app/                  ← Next.js App Router pages
    ├── components/           ← React components
    ├── context/              ← AuthContext
    └── lib/                  ← API clients, types
```
