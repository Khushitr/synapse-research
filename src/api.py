"""
api.py — FastAPI REST API wrapper for Synapse Research Assistant
Run with: uvicorn api:app --host 0.0.0.0 --port 8000 --reload

Endpoints:
  POST /research          — Run full pipeline, return report
  GET  /health            — Health check
  GET  /docs              — Auto-generated Swagger UI (built-in)
"""
import os, sys, time
_root = os.path.dirname(os.path.abspath(__file__))
if _root not in sys.path:
    sys.path.insert(0, _root)

from fastapi import FastAPI, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from dotenv import load_dotenv
load_dotenv()

from src.agent import generate_search_queries
from src.search import search_web
from src.scraper import fetch_and_clean
from src.chunker import chunk_pages
from src.vector_store import embed_and_store, retrieve_relevant_chunks
from src.synthesizer import synthesize_report

app = FastAPI(
    title="Synapse Research API",
    description="""
## Synapse Research Assistant API

Agentic RAG pipeline that:
1. Generates optimized search queries (LLM agent)
2. Searches the web (SerpAPI / Brave)
3. Fetches and cleans page content
4. Chunks and embeds text (MiniLM)
5. Retrieves relevant chunks (cosine similarity)
6. Synthesizes a structured, cited report (Llama 3.3 70B)

### Authentication
Include your API key in the `X-API-Key` header.  
Set `SYNAPSE_API_KEY` in your `.env` to enable key protection.  
Leave unset to run without authentication (open access).
    """,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Auth ─────────────────────────────────────────────────────────────────────
def verify_key(x_api_key: str = Header(default=None)):
    required = os.getenv("SYNAPSE_API_KEY")
    if required and x_api_key != required:
        raise HTTPException(status_code=401, detail="Invalid or missing X-API-Key header")

# ── Models ───────────────────────────────────────────────────────────────────
class ResearchRequest(BaseModel):
    query: str
    deep_mode: bool = False
    results_per_query: int = 4
    top_k_chunks: int = 8

    class Config:
        json_schema_extra = {
            "example": {
                "query": "How does CRISPR gene editing work?",
                "deep_mode": False,
                "results_per_query": 4,
                "top_k_chunks": 8
            }
        }

class ResearchResponse(BaseModel):
    query: str
    report: str
    search_queries: list[str]
    sources_found: int
    pages_extracted: int
    chunks_created: int
    elapsed_seconds: float
    deep_mode: bool

# ── Routes ───────────────────────────────────────────────────────────────────
@app.get("/health")
def health():
    return {"status": "ok", "service": "Synapse Research API", "version": "1.0.0"}

@app.post("/research", response_model=ResearchResponse)
def research(req: ResearchRequest, x_api_key: str = Header(default=None)):
    verify_key(x_api_key)
    start = time.time()

    if not req.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")
    if len(req.query) > 500:
        raise HTTPException(status_code=400, detail="Query too long (max 500 chars)")

    try:
        queries = generate_search_queries(req.query)
        results = search_web(queries, results_per_query=req.results_per_query)
        if not results:
            raise HTTPException(status_code=503, detail="Search API returned no results")

        pages = fetch_and_clean(results)
        ok = sum(1 for p in pages if p["status"] == "success")
        chunks = chunk_pages(pages)
        if not chunks:
            raise HTTPException(status_code=503, detail="Could not extract content from any pages")

        store = embed_and_store(chunks)
        relevant = retrieve_relevant_chunks(store, req.query, top_k=req.top_k_chunks)
        report = synthesize_report(req.query, relevant, deep_mode=req.deep_mode)

        return ResearchResponse(
            query=req.query,
            report=report,
            search_queries=queries,
            sources_found=len(results),
            pages_extracted=ok,
            chunks_created=len(chunks),
            elapsed_seconds=round(time.time() - start, 2),
            deep_mode=req.deep_mode,
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Pipeline error: {str(e)}")

@app.get("/")
def root():
    return {"message": "Synapse Research API", "docs": "/docs", "health": "/health"}