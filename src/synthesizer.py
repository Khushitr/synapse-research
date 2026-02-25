import os, re
from dotenv import load_dotenv
load_dotenv()

def synthesize_report(user_query: str, chunks: list[dict], deep_mode: bool = False, stream_container=None) -> str:
    if not chunks:
        return "## No Content\n\nCould not retrieve sufficient content. Try a different query."

    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise EnvironmentError("GROQ_API_KEY is not set.")

    # Set env var so ChatGroq picks it up automatically — works on all versions
    os.environ["GROQ_API_KEY"] = api_key

    from langchain_groq import ChatGroq
    from langchain_core.messages import HumanMessage, SystemMessage

    sources: dict[str, dict] = {}
    counter = 1
    for chunk in chunks:
        url = chunk.get("url", "")
        if url and url not in sources:
            sources[url] = {"index": counter, "title": chunk.get("title", "Source"), "url": url}
            counter += 1

    formatted = []
    for chunk in chunks:
        url = chunk.get("url", "")
        idx = sources.get(url, {}).get("index", "?")
        score = chunk.get("relevance_score", 0)
        formatted.append(f"[Source {idx} | relevance={score:.2f}]:\n{chunk['text']}")
    chunks_text = "\n\n---\n\n".join(formatted)

    word_target = "1500-2000" if deep_mode else "600-900"
    depth_note = (
        "Be VERY thorough and comprehensive. Include examples, analogies, and real-world applications."
        if deep_mode else "Be clear and concise."
    )

    system = (
        "You are an expert research analyst writing for a curious, intelligent audience.\n"
        "Make complex topics fascinating — like the best science journalists do.\n\n"
        "RULES:\n"
        "1. Use ONLY information from the provided source chunks.\n"
        "2. Cite EVERY factual claim inline as [1], [2], etc.\n"
        "3. Write EXACTLY these sections with ## headings:\n"
        "   ## Introduction\n"
        "   ## Key Findings\n"
        "   ## Contradictions & Open Debates\n"
        "   ## Conclusion\n"
        f"4. {depth_note}\n"
        f"5. Target: {word_target} words.\n"
        "6. Make it ENGAGING — use analogies, surprising facts, vivid language.\n"
        "7. Do NOT include a Sources section — it will be appended automatically.\n"
        "8. Start immediately with ## Introduction."
    )

    user_prompt = (
        f"Research Question: {user_query}\n"
        f"{'[DEEP RESEARCH MODE]' if deep_mode else ''}\n\n"
        f"Source Chunks:\n{chunks_text}\n\nWrite the report now."
    )

    llm = ChatGroq(
        model="llama-3.3-70b-versatile",
        temperature=0.3,
        max_tokens=3000 if deep_mode else 1800,
    )
    response = llm.invoke([SystemMessage(content=system), HumanMessage(content=user_prompt)])
    report_body = response.content.strip()

    sorted_sources = sorted(sources.values(), key=lambda s: s["index"])
    sources_md = "\n".join(f"**[{s['index']}]** [{s['title']}]({s['url']})" for s in sorted_sources)
    return report_body + f"\n\n---\n\n## Sources\n\n{sources_md}"