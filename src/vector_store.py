"""
vector_store.py — Pure numpy RAG, no ChromaDB
"""
import numpy as np
from sentence_transformers import SentenceTransformer

_model = None

def _get_model():
    global _model
    if _model is None:
        _model = SentenceTransformer("all-MiniLM-L6-v2")
    return _model

def embed_and_store(chunks):
    model = _get_model()
    if not chunks:
        return {"embeddings": np.array([]), "chunks": []}
    texts = [c["text"] for c in chunks]
    embeddings = model.encode(texts, show_progress_bar=False, batch_size=64)
    return {"embeddings": np.array(embeddings), "chunks": chunks}

def retrieve_relevant_chunks(store, query, top_k=8):
    model = _get_model()
    embeddings = store.get("embeddings")
    chunks = store.get("chunks", [])
    if embeddings is None or len(embeddings) == 0:
        return []
    q = model.encode([query])[0]
    q_norm = q / (np.linalg.norm(q) + 1e-9)
    m_norm = embeddings / (np.linalg.norm(embeddings, axis=1, keepdims=True) + 1e-9)
    scores = m_norm @ q_norm
    top_i = np.argsort(scores)[::-1][:min(top_k, len(chunks))]
    result = []
    for i in top_i:
        c = chunks[i].copy()
        c["relevance_score"] = round(float(scores[i]), 4)
        result.append(c)
    return result