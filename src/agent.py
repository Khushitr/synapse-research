"""
agent.py — Agentic Query Planner
----------------------------------
Uses Llama 3.3 70B (via Groq) to convert a raw user question into
3 optimized, distinct search queries. This is the "agentic" layer:
the LLM reasons about the query and decides HOW to search, not just what.
"""

import os
import ast
import re
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage
from dotenv import load_dotenv

load_dotenv()


def generate_search_queries(user_query: str) -> list[str]:
    """
    Takes the user's raw query and returns 3 optimized search query strings.

    Example:
        Input:  "How does CRISPR work?"
        Output: ["CRISPR mechanism DNA editing 2024",
                 "CRISPR Cas9 clinical applications",
                 "CRISPR off-target effects risks research"]
    """
    llm = ChatGroq(
        model="llama-3.3-70b-versatile",
        api_key=os.getenv("GROQ_API_KEY"),
        temperature=0.3,
        max_tokens=256,
    )

    system_prompt = """You are a research query optimizer. Given a user's question or topic,
generate exactly 3 distinct, optimized search queries that will collectively retrieve
comprehensive information about the topic from different angles.

Rules:
- Each query must target a DIFFERENT aspect or angle of the topic
- Use specific, concrete search terms (not vague phrases)
- Avoid redundancy between queries
- Return ONLY a valid Python list of exactly 3 strings — nothing else, no explanation

Example output:
["CRISPR Cas9 mechanism how it works", "CRISPR gene editing clinical trials 2024", "CRISPR ethical concerns off-target effects"]"""

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=f"Generate 3 optimized search queries for: {user_query}"),
    ]

    try:
        response = llm.invoke(messages)
        content = response.content.strip()

        # Parse Python list from response
        match = re.search(r"\[.*?\]", content, re.DOTALL)
        if match:
            queries = ast.literal_eval(match.group())
            if isinstance(queries, list) and len(queries) >= 3:
                return [str(q).strip() for q in queries[:3]]
    except Exception as e:
        print(f"[agent.py] LLM parse error: {e}")

    # Fallback: generate basic variants manually
    print("[agent.py] Falling back to manual query generation")
    return [
        user_query,
        f"{user_query} latest research 2024",
        f"{user_query} overview explained",
    ]
