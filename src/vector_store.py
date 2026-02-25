"""
vector_store.py — Free API embeddings (No torch, Cloud safe)
"""

import os
import requests
import numpy as np

HF_API_KEY = os.getenv("HF_API_KEY")
HF_MODEL = "sentence-transformers/all-MiniLM-L6-v2"

def _embed_texts(texts):
    headers = {
        "Authorization": f"Bearer {HF_API_KEY}"
    }

    response = requests.post(
        f"https://api-inference.huggingface.co/pipeline/feature-extraction/{HF_MODEL}",
        headers=headers,
        json={"inputs": texts}
    )

    if response.status_code != 200:
        raise Exception(f"HuggingFace API error: {response.text}")

    embeddings = response.json()

    # If single input, wrap it
    if isinstance(embeddings[0][0], float):
        embeddings = [embeddings]

    return np.array(embeddings)


def embed_and_store(chunks):
    if not chunks:
        return {"embeddings": np.array([]), "chunks": []}

    texts = [c["text"] for c in chunks]
    embeddings = _embed_texts(texts)

    return {"embeddings": embeddings, "chunks": chunks}


def retrieve_relevant_chunks(store, query, top_k=8):
    embeddings = store.get("embeddings")
    chunks = store.get("chunks", [])

    if embeddings is None or len(embeddings) == 0:
        return []

    q = _embed_texts([query])[0]

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