"""
synthesizer.py — Report Synthesizer
Supports deep_mode for longer, more detailed reports.
"""
import os
from langchain_groq import ChatGroq
from langchain.schema import HumanMessage, SystemMessage
from dotenv import load_dotenv
load_dotenv()

def synthesize_report(user_query: str, chunks: list[dict], deep_mode: bool = False, stream_container=None) -> str:
    if not chunks:
        return "## ⚠️ No Content\n\nCould not retrieve sufficient content. Try a different query."

    sources: dict[str, dict] = {}
    counter = 1
    for chunk in chunks:
        url = chunk.get("url","")
        if url and url not in sources:
            sources[url] = {"index": counter, "title": chunk.get("title","Source"), "url": url}
            counter += 1

    formatted = []
    for chunk in chunks:
        url = chunk.get("url","")
        idx = sources.get(url,{}).get("index","?")
        score = chunk.get("relevance_score",0)
        formatted.append(f"[Source {idx} | relevance={score:.2f}]:\n{chunk['text']}")
    chunks_text = "\n\n---\n\n".join(formatted)

    word_target = "1500-2000" if deep_mode else "600-900"
    depth_note  = "Be VERY thorough, detailed, and comprehensive. Include examples, analogies, and real-world applications." if deep_mode else "Be clear and concise."

    system = f"""You are an expert research analyst writing for a curious, intelligent audience.
Your goal is to make complex topics fascinating and accessible — like the best science journalists do.

STRICT RULES:
1. Use ONLY information from the provided source chunks. No outside knowledge.
2. Cite EVERY factual claim inline as [1], [2], etc. matching the [Source N] labels.
3. Write EXACTLY these sections with ## headings:
   ## Introduction
   ## Key Findings
   ## Contradictions & Open Debates
   ## Conclusion
4. {depth_note}
5. Target word count: {word_target} words.
6. Make it ENGAGING — use analogies, surprising facts, and vivid language.
7. Do NOT include a Sources section — it will be appended automatically.
8. Start immediately with ## Introduction. No preamble."""

    user_prompt = f"""Research Question: {user_query}
{"[DEEP RESEARCH MODE — write a comprehensive, detailed report]" if deep_mode else ""}

Retrieved Source Chunks:
{chunks_text}

Write the report now."""

    llm = ChatGroq(
        model="llama-3.3-70b-versatile",
        api_key=os.getenv("GROQ_API_KEY"),
        temperature=0.3,
        max_tokens=3000 if deep_mode else 1800,
    )
    response = llm.invoke([SystemMessage(content=system), HumanMessage(content=user_prompt)])
    report_body = response.content.strip()

    sorted_sources = sorted(sources.values(), key=lambda s: s["index"])
    sources_md = "\n".join(f"**[{s['index']}]** [{s['title']}]({s['url']})" for s in sorted_sources)
    return report_body + f"\n\n---\n\n## Sources\n\n{sources_md}"