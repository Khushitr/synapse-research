import os, ast, re
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage
from dotenv import load_dotenv
load_dotenv()

def generate_search_queries(user_query: str) -> list[str]:
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise EnvironmentError("GROQ_API_KEY is not set. Add it to your .env file or Streamlit secrets.")

    llm = ChatGroq(
        model="llama-3.3-70b-versatile",
        api_key=api_key,
        temperature=0.3,
        max_tokens=256,
    )

    system_prompt = """You are a research query optimizer. Given a user's question, generate exactly 3 distinct,
optimized search queries targeting different angles of the topic.
Return ONLY a valid Python list of 3 strings — nothing else.
Example: ["CRISPR Cas9 mechanism", "CRISPR clinical trials 2024", "CRISPR ethical risks"]"""

    try:
        response = llm.invoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"Generate 3 search queries for: {user_query}"),
        ])
        content = response.content.strip()
        match = re.search(r"\[.*?\]", content, re.DOTALL)
        if match:
            queries = ast.literal_eval(match.group())
            if isinstance(queries, list) and len(queries) >= 3:
                return [str(q).strip() for q in queries[:3]]
    except EnvironmentError:
        raise
    except Exception as e:
        print(f"[agent.py] parse error: {e}")

    return [
        user_query,
        f"{user_query} latest research 2024",
        f"{user_query} overview explained",
    ]