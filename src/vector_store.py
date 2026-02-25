"""
vector_store.py — Pure local embeddings, zero external API calls.

Primary:  sentence-transformers all-MiniLM-L6-v2 (runs fully locally)
Fallback: TF-IDF cosine similarity (pure numpy, no downloads needed)

The HuggingFace *inference* API is never used.
"""

import numpy as np

_st_model = None          # sentence-transformers model (lazy loaded)
_use_tfidf = False        # flipped to True if ST fails to load


# ── sentence-transformers (primary) ──────────────────────────────────────────

def _load_st_model():
    global _st_model, _use_tfidf
    if _st_model is not None:
        return _st_model
    try:
        # IMPORTANT: set env vars BEFORE importing so the library never tries
        # to call the remote inference API
        import os
        os.environ["TOKENIZERS_PARALLELISM"] = "false"
        os.environ["TRANSFORMERS_OFFLINE"] = "0"   # allow model download once
        os.environ["HF_HUB_DISABLE_IMPLICIT_TOKEN"] = "1"

        from sentence_transformers import SentenceTransformer
        _st_model = SentenceTransformer("all-MiniLM-L6-v2", device="cpu")
        print("[vector_store] Loaded all-MiniLM-L6-v2 locally")
        return _st_model
    except Exception as e:
        print(f"[vector_store] sentence-transformers failed ({e}), switching to TF-IDF")
        _use_tfidf = True
        return None


# ── TF-IDF fallback (pure numpy, no internet) ────────────────────────────────

def _tfidf_vectorize(texts: list[str], vocab: dict | None = None):
    """Returns (matrix, vocab) where matrix rows are L2-normalised TF-IDF vectors."""
    import re, math

    tokenize = lambda t: re.findall(r"[a-z]+", t.lower())

    # Build vocab from texts if not provided
    if vocab is None:
        all_words: set[str] = set()
        for t in texts:
            all_words.update(tokenize(t))
        vocab = {w: i for i, w in enumerate(sorted(all_words))}

    n_docs = len(texts)
    mat = np.zeros((n_docs, len(vocab)), dtype=np.float32)

    # TF
    for d, text in enumerate(texts):
        tokens = tokenize(text)
        for tok in tokens:
            if tok in vocab:
                mat[d, vocab[tok]] += 1
        if tokens:
            mat[d] /= len(tokens)   # normalize TF

    # IDF
    df = (mat > 0).sum(axis=0).astype(np.float32)
    idf = np.log((n_docs + 1) / (df + 1)) + 1.0
    mat = mat * idf

    # L2 normalize
    norms = np.linalg.norm(mat, axis=1, keepdims=True) + 1e-9
    mat = mat / norms

    return mat, vocab


# ── Public API ────────────────────────────────────────────────────────────────

def embed_and_store(chunks: list[dict]) -> dict:
    if not chunks:
        return {"embeddings": np.array([]), "chunks": [], "tfidf_vocab": None}

    texts = [c["text"] for c in chunks]

    model = _load_st_model()

    if not _use_tfidf and model is not None:
        try:
            embeddings = model.encode(
                texts,
                show_progress_bar=False,
                batch_size=32,
                convert_to_numpy=True,
            )
            print(f"[vector_store] Embedded {len(texts)} chunks with ST, shape={embeddings.shape}")
            return {"embeddings": np.array(embeddings), "chunks": chunks, "tfidf_vocab": None}
        except Exception as e:
            print(f"[vector_store] ST encode failed ({e}), falling back to TF-IDF")

    # TF-IDF fallback
    print(f"[vector_store] Using TF-IDF fallback for {len(texts)} chunks")
    matrix, vocab = _tfidf_vectorize(texts)
    return {"embeddings": matrix, "chunks": chunks, "tfidf_vocab": vocab}


def retrieve_relevant_chunks(store: dict, query: str, top_k: int = 8) -> list[dict]:
    embeddings = store.get("embeddings")
    chunks     = store.get("chunks", [])
    vocab      = store.get("tfidf_vocab")

    if embeddings is None or len(embeddings) == 0:
        return []

    # Embed the query using the same method as the chunks
    model = _load_st_model()

    if not _use_tfidf and model is not None and vocab is None:
        try:
            q_vec = model.encode([query], convert_to_numpy=True)[0]
        except Exception:
            q_vec = None
    else:
        q_vec = None

    if q_vec is None:
        # TF-IDF path — must use same vocab
        if vocab is None:
            # Rebuild vocab from chunk texts (shouldn't happen but safe)
            _, vocab = _tfidf_vectorize([c["text"] for c in chunks])
        q_mat, _ = _tfidf_vectorize([query], vocab=vocab)
        q_vec = q_mat[0]

    # Cosine similarity
    q_norm = q_vec / (np.linalg.norm(q_vec) + 1e-9)
    m_norm = embeddings / (np.linalg.norm(embeddings, axis=1, keepdims=True) + 1e-9)
    scores = m_norm @ q_norm

    top_i = np.argsort(scores)[::-1][:min(top_k, len(chunks))]
    result = []
    for i in top_i:
        c = chunks[i].copy()
        c["relevance_score"] = round(float(scores[i]), 4)
        result.append(c)

    print(f"[vector_store] Retrieved {len(result)} chunks, top score={result[0]['relevance_score']}")
    return result