# 🔬 AI Research Assistant

> An agentic RAG pipeline that takes any research question, searches the web, reads and filters the pages, and synthesizes a structured, cited report — all in under 45 seconds.

![Python](https://img.shields.io/badge/Python-3.11+-blue?logo=python)
![Streamlit](https://img.shields.io/badge/Streamlit-1.40-red?logo=streamlit)
![LangChain](https://img.shields.io/badge/LangChain-0.3.7-green)
![License](https://img.shields.io/badge/License-MIT-yellow)

---

## 🌐 Live Demo

**→ [your-app-name.streamlit.app](https://your-app-name.streamlit.app)**
*(replace with your actual Streamlit Cloud link after deployment)*

---

## What it does

1. **You type a question** — e.g. *"How does CRISPR gene editing work?"*
2. **The Agent (Llama 3.3 70B)** plans 3 optimized search queries targeting different angles
3. **Search API** fetches the top 5 results per query (15 results total, deduplicated)
4. **Scraper** fetches each page, strips nav/ads/boilerplate, extracts clean paragraph text
5. **Chunker** splits cleaned text into 500-char overlapping segments
6. **RAG (ChromaDB + MiniLM)** embeds all chunks locally and retrieves the 12 most relevant ones
7. **LLM (Llama 3.3 70B)** synthesizes a structured report with inline citations
8. **You get** a 4-section Markdown report (Intro, Key Findings, Contradictions, Conclusion + Sources)

---

## System Architecture

```
User Query
    │
    ▼
┌─────────────────────────────┐
│  🤖 AGENT (agent.py)        │
│  Llama 3.3 70B via Groq     │
│  Generates 3 search queries │
└──────────────┬──────────────┘
               │ 3 queries
               ▼
┌─────────────────────────────┐
│  🔍 SEARCH (search.py)      │
│  SerpAPI or Brave Search    │
│  5 results × 3 queries      │
│  Deduplicates by URL        │
└──────────────┬──────────────┘
               │ ~10-15 URLs
               ▼
┌─────────────────────────────┐
│  📄 SCRAPER (scraper.py)    │
│  requests + BeautifulSoup   │
│  Strips nav/ads/scripts     │
│  Extracts <p> text only     │
└──────────────┬──────────────┘
               │ Cleaned text per page
               ▼
┌─────────────────────────────┐
│  ✂️ CHUNKER (chunker.py)    │
│  RecursiveCharacterSplitter │
│  500 chars, 50 overlap      │
│  Tags each chunk with URL   │
└──────────────┬──────────────┘
               │ ~100-200 chunks
               ▼
┌─────────────────────────────┐
│  🧠 VECTOR STORE            │
│  (vector_store.py)          │
│  all-MiniLM-L6-v2 embeddings│
│  ChromaDB cosine search     │
│  Retrieves top 12 chunks    │
└──────────────┬──────────────┘
               │ 12 most relevant chunks
               ▼
┌─────────────────────────────┐
│  📝 SYNTHESIZER             │
│  (synthesizer.py)           │
│  Llama 3.3 70B via Groq     │
│  Structured report + cites  │
└──────────────┬──────────────┘
               │
               ▼
         📋 REPORT
```

---

## Tech Stack

| Component | Technology | Why |
|-----------|-----------|-----|
| LLM | Llama 3.3 70B via **Groq** | Free, fast (~500 tok/s), no cost |
| Agent framework | **LangChain** | ChatGroq integration, prompt management |
| Search | **SerpAPI** or **Brave Search** | Free tiers available |
| Scraping | **requests + BeautifulSoup** | Reliable HTML parsing |
| Text splitting | **LangChain TextSplitter** | Smart sentence-aware chunking |
| Embeddings | **all-MiniLM-L6-v2** | 100% local, 22MB, no API cost |
| Vector DB | **ChromaDB** | Local in-memory, no setup |
| UI | **Streamlit** | Fast Python web UI |

---

## Local Setup

### Prerequisites
- Python 3.11+
- Git

### 1. Clone the repo

```bash
git clone https://github.com/yourusername/research-assistant.git
cd research-assistant
```

### 2. Create virtual environment

```bash
python -m venv venv

# macOS/Linux
source venv/bin/activate

# Windows
venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

> ⚠️ First install downloads the MiniLM model (~22MB). This only happens once.

### 4. Set up API keys

```bash
cp .env.example .env
```

Edit `.env` and fill in your keys:

```env
GROQ_API_KEY=your_groq_key     # https://console.groq.com (free)
SERPAPI_KEY=your_serpapi_key   # https://serpapi.com (100/month free)
# OR
BRAVE_API_KEY=your_brave_key   # https://brave.com/search/api (2000/month free)
```

### 5. Run the app

```bash
streamlit run app.py
```

The app opens at `http://localhost:8501`

---

## Deployment (Streamlit Community Cloud)

1. Push your repo to GitHub (make sure `.env` is in `.gitignore`)
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Click **New app** → select your repo → set `app.py` as main file
4. Go to **Settings → Secrets** and paste:

```toml
GROQ_API_KEY = "your_groq_key"
SERPAPI_KEY = "your_serpapi_key"
```

5. Click **Deploy** — you get a live public URL

---

## File Structure

```
research-assistant/
├── app.py                  # Streamlit UI + pipeline orchestration
├── requirements.txt        # All Python dependencies
├── .env.example            # API key template (copy → .env)
├── .gitignore              # Excludes .env, __pycache__, etc.
├── README.md               # This file
│
├── src/                    # All pipeline modules
│   ├── __init__.py
│   ├── agent.py            # LLM query planner (agentic layer)
│   ├── search.py           # SerpAPI / Brave Search integration
│   ├── scraper.py          # HTML fetcher + cleaner
│   ├── chunker.py          # Text splitter
│   ├── vector_store.py     # ChromaDB + MiniLM RAG
│   └── synthesizer.py      # Report generator
│
└── .streamlit/
    └── secrets.toml        # (gitignored) Streamlit Cloud secrets
```

---

## APIs Used

| API | Purpose | Free Tier | Link |
|-----|---------|-----------|------|
| **Groq** | LLM inference (Llama 3.3 70B) | Generous free tier | [console.groq.com](https://console.groq.com) |
| **SerpAPI** | Google Search results | 100 searches/month | [serpapi.com](https://serpapi.com) |
| **Brave Search** | Web search (alternative) | 2000 queries/month | [brave.com/search/api](https://brave.com/search/api/) |

**Zero-cost local components**: MiniLM embeddings, ChromaDB — run entirely on your machine.

---

## Example Output

**Query:** *"What are the latest breakthroughs in fusion energy?"*

```markdown
## Introduction
Nuclear fusion has long been considered the holy grail of clean energy...

## Key Findings
The National Ignition Facility achieved ignition in December 2022 [1], marking...
Private companies like Commonwealth Fusion Systems have raised over $1.8B [2]...

## Contradictions & Open Debates
While NIF's achievement was historic, critics note it required 300x more energy [3]
to power the facility than the 3.15 MJ delivered to the target...

## Conclusion
Fusion energy is transitioning from theoretical to engineering challenges...

## Sources
[1] NIF Ignition Achievement — https://...
[2] CFS Funding Round — https://...
```

---

## License

MIT — free to use, modify, and deploy.
