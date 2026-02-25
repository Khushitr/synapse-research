"""
chunker.py — Text Chunker
---------------------------
Splits each cleaned page into overlapping chunks so that:
  - No single chunk is too long for the embedding model
  - Overlap preserves sentence context across chunk boundaries
  - Each chunk carries its source URL as metadata (essential for citations)

Uses LangChain's RecursiveCharacterTextSplitter which tries to split
on paragraph → sentence → word → character boundaries in that order.

chunk_size=500, chunk_overlap=50 means:
  - Each chunk is ≤500 characters
  - 50 characters of the previous chunk are repeated at the start of the next
    (so ideas spanning a boundary aren't lost)
"""

from langchain.text_splitter import RecursiveCharacterTextSplitter


def chunk_pages(
    pages: list[dict],
    chunk_size: int = 500,
    chunk_overlap: int = 50,
) -> list[dict]:
    """
    Split cleaned page text into overlapping chunks with source metadata.

    Args:
        pages:          List of dicts from scraper.py [{url, title, text, status}]
        chunk_size:     Max characters per chunk
        chunk_overlap:  Characters of overlap between consecutive chunks

    Returns:
        List of dicts: [{text, url, title, chunk_id}]

    Example:
        Input page text (1200 chars) → output: ~3 chunks of ~500 chars each
        Each chunk tagged with: url="https://...", title="Article Title"
    """
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=len,
        separators=["\n\n", "\n", ". ", "! ", "? ", " ", ""],
    )

    all_chunks = []

    for page in pages:
        text = page.get("text", "").strip()
        url = page.get("url", "")
        title = page.get("title", "")

        # Skip pages with almost no content
        if not text or len(text) < 80:
            continue

        raw_chunks = splitter.split_text(text)

        for i, chunk_text in enumerate(raw_chunks):
            chunk_text = chunk_text.strip()
            # Skip chunks that are too small to be meaningful
            if len(chunk_text) < 30:
                continue

            all_chunks.append({
                "text": chunk_text,
                "url": url,
                "title": title,
                # chunk_id: deterministic hash so same page+chunk = same id
                "chunk_id": f"{abs(hash(url))%999999:06d}_{i:04d}",
            })

    print(f"[chunker.py] Created {len(all_chunks)} chunks from {len(pages)} pages")
    return all_chunks
