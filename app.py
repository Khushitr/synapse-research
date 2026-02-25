import time, sys, os, datetime, json, base64, zlib, re
import streamlit as st
import streamlit.components.v1 as components
from io import BytesIO

_root = os.path.dirname(os.path.abspath(__file__))
if _root not in sys.path:
    sys.path.insert(0, _root)
os.chdir(_root)

from src.agent import generate_search_queries
from src.search import search_web
from src.scraper import fetch_and_clean
from src.chunker import chunk_pages
from src.vector_store import embed_and_store, retrieve_relevant_chunks
from src.synthesizer import synthesize_report

st.set_page_config(
    page_title="Synapse AI Research",
    page_icon="S",
    layout="wide",
    initial_sidebar_state="expanded",
)

for k, v in {
    "history": [], "viewing": None,
    "deep_mode": False, "show_think": True,
    "show_map": False, "run_query": "",
}.items():
    if k not in st.session_state:
        st.session_state[k] = v

# Restore from share link
params = st.query_params
if "share" in params and not st.session_state.history:
    try:
        raw = zlib.decompress(base64.urlsafe_b64decode(params["share"].encode()))
        entry = json.loads(raw.decode())
        st.session_state.history = [entry]
        st.session_state.viewing = 0
    except Exception:
        pass

# Handle mind map click-to-search via query param
if "mc" in params and not st.session_state.run_query:
    clicked_topic = params["mc"]
    if clicked_topic:
        st.session_state.run_query = clicked_topic
        st.session_state.viewing = None

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@300;400;500;600;700&family=Poppins:wght@300;400;500;600;700&family=Playfair+Display:wght@400;500;600;700&family=Pacifico&display=swap');

*, *::before, *::after { box-sizing: border-box; }
.stApp { background: #09090f !important; color: #e2e4f0 !important; font-family: 'Space Grotesk', sans-serif !important; }
html, body, div, p, span, button, input, label, h1, h2, h3, h4, li { font-family: 'Space Grotesk', sans-serif !important; color: inherit; }
.block-container { padding: 2.5rem 3rem 5rem !important; max-width: 820px !important; }
#MainMenu, footer, header, [data-testid="stToolbar"], [data-testid="stDecoration"] { visibility: hidden !important; height: 0 !important; }
::-webkit-scrollbar { width: 5px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: #21213a; border-radius: 99px; }

section[data-testid="stSidebar"] { background: #0d0d18 !important; border-right: 1px solid #171730 !important; min-width: 270px !important; max-width: 270px !important; }
section[data-testid="stSidebar"] .block-container { padding: 0 !important; max-width: 100% !important; }
section[data-testid="stSidebar"] p, section[data-testid="stSidebar"] span, section[data-testid="stSidebar"] div, section[data-testid="stSidebar"] label { color: #e2e4f0 !important; }
section[data-testid="stSidebar"] div[data-testid="stButton"] > button { background: transparent !important; border: none !important; color: #4a4a7a !important; text-align: left !important; padding: 0.45rem 1rem !important; white-space: normal !important; height: auto !important; width: 100% !important; font-size: 0.8rem !important; border-radius: 8px !important; line-height: 1.45 !important; transition: all 0.15s !important; display: block !important; margin: 1px 0 !important; font-weight: 400 !important; }
section[data-testid="stSidebar"] div[data-testid="stButton"] > button:hover { background: rgba(139,92,246,0.08) !important; color: #a78bfa !important; }

div[data-testid="stTextInput"] input { background: #12121f !important; border: 1.5px solid #1e1e38 !important; border-radius: 14px !important; color: #e8eaf8 !important; font-size: 1rem !important; padding: 1rem 1.3rem !important; caret-color: #8b5cf6; transition: all 0.2s; }
div[data-testid="stTextInput"] input:focus { border-color: #7c3aed !important; background: #16163a !important; box-shadow: 0 0 0 3px rgba(124,58,237,0.12) !important; }
div[data-testid="stTextInput"] input::placeholder { color: #2a2a4a !important; }
div[data-testid="stTextInput"] label { display: none !important; }
div[data-testid="stTextInput"] > div, div[data-testid="stTextInput"] > div > div { background: transparent !important; border: none !important; }

div[data-testid="stFormSubmitButton"] > button { background: linear-gradient(135deg, #7c3aed, #6d28d9) !important; border: none !important; border-radius: 12px !important; color: #fff !important; font-weight: 600 !important; font-size: 0.9rem !important; padding: 0.9rem 1.6rem !important; height: auto !important; box-shadow: 0 4px 20px rgba(124,58,237,0.3) !important; transition: all 0.2s !important; }
div[data-testid="stFormSubmitButton"] > button:hover { transform: translateY(-2px) !important; box-shadow: 0 8px 30px rgba(124,58,237,0.4) !important; }

div[data-testid="stProgress"] > div { background: #16162a !important; border-radius: 99px !important; height: 2px !important; }
div[data-testid="stProgress"] > div > div { background: linear-gradient(90deg,#7c3aed,#a78bfa,#38bdf8,#a78bfa,#7c3aed) !important; background-size:300% 100% !important; animation: sweep 1.8s linear infinite !important; border-radius:99px !important; }
@keyframes sweep { 0%{background-position:100%} 100%{background-position:-100%} }

div[data-testid="stInfo"] { background: rgba(124,58,237,0.07) !important; border: 1px solid rgba(124,58,237,0.2) !important; border-radius: 10px !important; }
div[data-testid="stInfo"] p { color: #9d7ef5 !important; font-size: 0.8rem !important; }
div[data-testid="stSuccess"] { background: rgba(52,211,153,0.06) !important; border: 1px solid rgba(52,211,153,0.2) !important; border-radius: 10px !important; }
div[data-testid="stSuccess"] p { color: #5ecba1 !important; font-size: 0.8rem !important; }
div[data-testid="stError"] { background: rgba(239,68,68,0.06) !important; border: 1px solid rgba(239,68,68,0.2) !important; border-radius: 10px !important; }
div[data-testid="stError"] p { color: #f87171 !important; }
div[data-testid="stWarning"] { background: rgba(251,191,36,0.06) !important; border: 1px solid rgba(251,191,36,0.2) !important; border-radius: 10px !important; }

div[data-testid="stExpander"] { background: #0f0f1e !important; border: 1px solid #1a1a30 !important; border-radius: 14px !important; }
div[data-testid="stExpander"] summary { color: #3a3a5a !important; font-size: 0.75rem !important; letter-spacing: 0.06em !important; }
div[data-testid="stExpander"] summary:hover { color: #8b5cf6 !important; }

div[data-testid="stMarkdown"] h2 { color: #f0f2ff !important; font-family: 'Playfair Display', serif !important; font-size: 1.25rem !important; font-weight: 600 !important; margin: 2rem 0 0.7rem !important; padding-bottom: 0.5rem !important; border-bottom: 1px solid #1a1a2e !important; }
div[data-testid="stMarkdown"] h3 { color: #dddff5 !important; font-size: 1rem !important; font-weight: 600 !important; margin: 1.2rem 0 0.4rem !important; }
div[data-testid="stMarkdown"] p { color: #c8cae8 !important; line-height: 1.85 !important; font-size: 0.94rem !important; margin-bottom: 0.7rem !important; }
div[data-testid="stMarkdown"] strong { color: #e2e4f8 !important; font-weight: 600 !important; }
div[data-testid="stMarkdown"] a { color: #8b5cf6 !important; text-decoration: none !important; border-bottom: 1px solid rgba(139,92,246,0.25) !important; }
div[data-testid="stMarkdown"] a:hover { border-color: #8b5cf6 !important; }
div[data-testid="stMarkdown"] hr { border: none !important; border-top: 1px solid #1a1a2e !important; margin: 1.8rem 0 !important; }
div[data-testid="stMarkdown"] ul li { color: #c8cae8 !important; margin-bottom: 0.3rem !important; }

div[data-testid="stDownloadButton"] button { background: transparent !important; border: 1px solid #1e1e38 !important; color: #4a4a7a !important; border-radius: 8px !important; font-size: 0.75rem !important; padding: 0.38rem 1rem !important; transition: all 0.18s !important; }
div[data-testid="stDownloadButton"] button:hover { border-color: rgba(139,92,246,0.35) !important; color: #8b5cf6 !important; background: rgba(139,92,246,0.05) !important; }
div[data-testid="stForm"] { border: none !important; background: transparent !important; padding: 0 !important; }
hr { border: none !important; border-top: 1px solid #141428 !important; }

.brand { padding: 1.3rem 1.3rem 1rem; border-bottom: 1px solid #141428; }
.brand-name { font-family: 'Pacifico', cursive; font-size: 1.3rem; background: linear-gradient(135deg, #a78bfa, #60a5fa); -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text; }
.brand-tag { font-size: 0.6rem; color: #2a2a4a; letter-spacing: 0.14em; text-transform: uppercase; margin-top: 2px; }
.sb-section { font-size: 0.6rem; color: #2a2a4a; letter-spacing: 0.16em; text-transform: uppercase; padding: 0.9rem 1.2rem 0.35rem; }
.sb-empty { font-size: 0.68rem; color: #2a2a4a; padding: 0.3rem 1.2rem 0.8rem; line-height: 1.8; }
.pipe-wrap { padding: 0.9rem 1rem 1.3rem; border-top: 1px solid #141428; }
.pipe-head { font-size: 0.58rem; color: #2a2a4a; letter-spacing: 0.16em; text-transform: uppercase; padding: 0 0.3rem; margin-bottom: 0.55rem; }
.pipe-row { display: flex; align-items: flex-start; gap: 0.6rem; padding: 0.35rem 0.5rem; border-radius: 7px; transition: background 0.15s; }
.pipe-row:hover { background: rgba(139,92,246,0.04); }
.pipe-num { font-size: 0.58rem; color: #2a2a4a; flex-shrink: 0; padding-top: 2px; }
.pipe-name { font-size: 0.78rem; font-weight: 600; color: #4a4a7a; }
.pipe-desc { font-size: 0.63rem; color: #2a2a48; }

.hero { padding: 2.5rem 0 0.5rem; }
.hero-badge { display: inline-flex; align-items: center; gap: 0.5rem; background: rgba(139,92,246,0.08); border: 1px solid rgba(139,92,246,0.18); color: #9d7ef5; font-size: 0.68rem; padding: 0.28rem 0.8rem; border-radius: 20px; margin-bottom: 1.2rem; letter-spacing: 0.08em; }
.hero-h1 { font-family: 'Playfair Display', serif; font-size: clamp(2rem, 4vw, 2.9rem); font-weight: 700; color: #ebebfa; letter-spacing: -0.02em; line-height: 1.1; margin-bottom: 0.8rem; }
.hero-grad { background: linear-gradient(135deg, #a78bfa 0%, #818cf8 50%, #60a5fa 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text; }
.hero-sub { font-size: 0.93rem; color: #9090c0; line-height: 1.65; max-width: 430px; margin-bottom: 2rem; font-family: 'Poppins', sans-serif; }

.pill-outer { position: relative; overflow: hidden; margin: 1.6rem 0 0.4rem; }
.pill-outer::before { content:''; position:absolute; left:0; top:0; bottom:0; width:55px; background:linear-gradient(90deg,#09090f 60%,transparent); z-index:2; pointer-events:none; }
.pill-outer::after { content:''; position:absolute; right:0; top:0; bottom:0; width:55px; background:linear-gradient(-90deg,#09090f 60%,transparent); z-index:2; pointer-events:none; }
.pill-track { display:flex; gap:0.55rem; width:max-content; animation:slidepills 32s linear infinite; padding:0.3rem 0; }
.pill-track:hover { animation-play-state:paused; }
@keyframes slidepills { 0%{transform:translateX(0)} 100%{transform:translateX(-50%)} }
.ex-pill { background: #111122; border: 1px solid #1c1c35; border-radius: 30px; padding: 0.5rem 1.1rem; font-size: 0.82rem; color: #7070a8; white-space: nowrap; cursor: pointer; transition: all 0.22s; user-select: none; flex-shrink: 0; }
.ex-pill:hover { background: #1a1a35; border-color: rgba(139,92,246,0.4); color: #b09af5; transform: translateY(-2px); box-shadow: 0 6px 20px rgba(139,92,246,0.12); }
.pill-lbl { font-size: 0.6rem; color: #3a3a60; letter-spacing: 0.14em; text-transform: uppercase; }
.search-hint { font-size: 0.62rem; color: #3a3a60; text-align: right; margin-top: 0.4rem; letter-spacing: 0.04em; }

.result-q { font-family: 'Playfair Display', serif; font-size: 1.7rem; font-weight: 700; color: #f4f5ff; letter-spacing: -0.02em; line-height: 1.2; margin-bottom: 0.3rem; }
.result-meta { font-size: 0.65rem; color: #5050a0; letter-spacing: 0.08em; }
.stats-row { display: grid; grid-template-columns: repeat(4,1fr); gap: 0.6rem; margin: 1.3rem 0 1.6rem; }
.stat-card { background: #0f0f1e; border: 1px solid #191930; border-radius: 12px; padding: 0.85rem 0.6rem 0.7rem; text-align: center; transition: border-color 0.2s; }
.stat-card:hover { border-color: rgba(139,92,246,0.25); }
.stat-v { font-size: 1.4rem; font-weight: 600; color: #8b5cf6; line-height: 1; display: block; }
.stat-l { font-size: 0.6rem; color: #5050a0; letter-spacing: 0.1em; text-transform: uppercase; margin-top: 5px; display: block; }
.sdiv { display:flex; align-items:center; gap:0.9rem; margin:2rem 0 1rem; }
.sdiv-line { flex:1; height:1px; background:#141428; }
.sdiv-lbl { font-size:0.6rem; color:#5050a0; letter-spacing:0.16em; text-transform:uppercase; white-space:nowrap; }

.think-row { display:flex; align-items:flex-start; gap:0.8rem; padding:0.6rem 0.8rem; border-radius:9px; background:#0f0f1e; border:1px solid #181830; margin:4px 0; }
.think-icon { font-size:1rem; flex-shrink:0; }
.think-label { font-size:0.72rem; font-weight:600; color:#9090cc; font-family:'Poppins',sans-serif; }
.think-val { font-size:0.82rem; color:#c0c2e0; }
.log-entry { display:flex; align-items:center; gap:0.9rem; padding:0.45rem 0.75rem; border-radius:7px; background:#0d0d1a; border:1px solid #161628; margin:2px 0; }
.log-tag { font-size:0.7rem; color:#6868a8; min-width:68px; flex-shrink:0; }
.log-val { font-size:0.7rem; color:#8080b8; }

.img-strip { display:flex; gap:0.75rem; margin:1.2rem 0; flex-wrap:wrap; }
.img-card { flex:1; min-width:180px; max-width:260px; border-radius:12px; overflow:hidden; border:1px solid #1a1a30; }
.img-card img { width:100%; height:150px; object-fit:cover; display:block; }
.img-cap { font-size:0.65rem; color:#5050a0; padding:0.35rem 0.6rem; background:#0f0f1e; letter-spacing:0.04em; }

.mm-btn-row { display: flex; flex-wrap: wrap; gap: 0.5rem; margin: 0.8rem 0 0.3rem; }
.mm-lbl { font-size: 0.6rem; color: #3a3a60; letter-spacing: 0.14em; text-transform: uppercase; margin-bottom: 0.5rem; }

.share-box input { font-size:0.73rem !important; color:#5a5a8a !important; background:#0d0d1a !important; border-color:#161628 !important; padding:0.5rem 0.8rem !important; border-radius:8px !important; }
.empty-wrap { padding:5rem 0; text-align:center; }
.empty-glyph { font-family:'Pacifico',cursive; font-size:2rem; color:#2a2a48; margin-bottom:0.8rem; }
.empty-lines { font-size:0.72rem; color:#3a3a60; line-height:2.4; letter-spacing:0.06em; }
.mode-badge { display:inline-block; background:rgba(139,92,246,0.1); border:1px solid rgba(139,92,246,0.2); color:#8b5cf6; font-size:0.65rem; padding:0.18rem 0.55rem; border-radius:5px; margin:1px; }
</style>
"""

st.markdown(CSS, unsafe_allow_html=True)



_MINDMAP_TEMPLATE = "<!DOCTYPE html><html><head><style>* {box-sizing:border-box;margin:0;padding:0;}body {background:#1c1d26;font-family:'Space Grotesk','Segoe UI',sans-serif;overflow:hidden;}#wrap {width:100%;height:480px;position:relative;}svg {position:absolute;top:0;left:0;width:100%;height:100%;pointer-events:none;overflow:visible;}.nd {position:absolute;display:flex;align-items:center;gap:8px;transform:translate(-50%,-50%);}.box {background:#272a38;border:1px solid #353848;border-radius:10px;padding:10px 16px;font-size:13px;font-weight:500;color:#dde2f0;white-space:nowrap;max-width:175px;overflow:hidden;text-overflow:ellipsis;transition:all 0.2s;cursor:default;}.box.root {background:#1e1a3d;border:1.5px solid #4a3fa0;font-size:14px;font-weight:600;color:#e8e4ff;padding:13px 22px;max-width:210px;white-space:normal;text-align:center;line-height:1.4;border-radius:12px;}.box:not(.root):hover {background:#2e3148;border-color:#6060a0;}.btn {width:28px;height:28px;border-radius:50%;background:#1e1e30;border:1px solid #353848;color:#7070a8;font-size:16px;display:flex;align-items:center;justify-content:center;cursor:pointer;flex-shrink:0;transition:all 0.2s;user-select:none;}.btn:hover {background:#4a3fa0;border-color:#7c6af7;color:#fff;transform:scale(1.15);box-shadow:0 0 14px rgba(124,106,247,0.5);}.tip {position:fixed;background:rgba(10,10,22,0.97);border:1px solid #2a2d50;color:#c8cae8;padding:8px 12px;border-radius:10px;font-size:11px;pointer-events:none;display:none;z-index:999;max-width:200px;line-height:1.7;box-shadow:0 8px 30px rgba(0,0,0,0.5);}.tip b {color:#a78bfa;display:block;margin-bottom:3px;}.info {position:absolute;top:10px;left:12px;font-size:11px;color:#3a3a60;letter-spacing:0.05em;}.hint {position:absolute;bottom:10px;right:12px;font-size:10px;color:#3a3a58;letter-spacing:0.07em;text-transform:uppercase;}</style></head><body><div id='wrap'><svg id='svg'></svg><div class='info'>subtopic map</div><div class='hint'>click &rsaquo; to deep-search</div></div><div class='tip' id='tip'></div><script>const DATA=__NODES__;const ROOT=__ROOT__;const wrap=document.getElementById('wrap');const svgEl=document.getElementById('svg');const tip=document.getElementById('tip');function drawPath(x1,y1,x2,y2,col){  const p=document.createElementNS('http://www.w3.org/2000/svg','path');  const cx=(x1+x2)/2;  p.setAttribute('d','M'+x1+','+y1+' C'+cx+','+y1+' '+cx+','+y2+' '+x2+','+y2);  p.setAttribute('stroke',col);p.setAttribute('stroke-width','1.5');  p.setAttribute('fill','none');p.setAttribute('opacity','0.45');  svgEl.appendChild(p);}function makeNode(label,isRoot,children,hue){  const w=document.createElement('div');w.className='nd';  const box=document.createElement('div');box.className=isRoot?'box root':'box';  box.textContent=label;w.appendChild(box);  if(!isRoot){    const btn=document.createElement('div');btn.className='btn';    btn.innerHTML='&rsaquo;';    btn.addEventListener('click',()=>{      const u=new URL(window.parent.location.href);      u.searchParams.set('mc',label);      window.parent.location.href=u.toString();});    w.appendChild(btn);    box.addEventListener('mouseenter',e=>{      tip.style.display='block';      tip.innerHTML='<b>'+label+'</b>'+children.map(c=>'&bull; '+c).join('<br>');});    box.addEventListener('mousemove',e=>{      tip.style.left=(e.clientX+14)+'px';tip.style.top=(e.clientY-10)+'px';});    box.addEventListener('mouseleave',()=>{tip.style.display='none';});}  return w;}function layout(){  wrap.querySelectorAll('.nd').forEach(n=>n.remove());svgEl.innerHTML='';  svgEl.setAttribute('viewBox','0 0 '+wrap.offsetWidth+' '+wrap.offsetHeight);  const W=wrap.offsetWidth,H=wrap.offsetHeight,N=DATA.length;  const rx=W*0.22,ry=H*0.5,bx=W*0.62;  const hues=[255,275,240,290,225,265];  const rEl=makeNode(ROOT,true,[],260);  rEl.style.left=rx+'px';rEl.style.top=ry+'px';wrap.appendChild(rEl);  DATA.forEach((s,i)=>{    const t=N<=1?0.5:i/(N-1);    const by=H*0.08+t*H*0.84;    const hue=hues[i%hues.length];    const col='hsl('+hue+',60%,58%)';    drawPath(rx,ry,bx,by,col);    const el=makeNode(s.label,false,s.children,hue);    el.style.left=bx+'px';el.style.top=by+'px';wrap.appendChild(el);});}window.addEventListener('resize',layout);layout();</script></body></html>"

def generate_subtopics(query):
    from langchain_groq import ChatGroq
    from langchain.schema import HumanMessage, SystemMessage
    from dotenv import load_dotenv
    load_dotenv()
    llm = ChatGroq(model="llama-3.3-70b-versatile", groq_api_key=os.getenv("GROQ_API_KEY"), temperature=0.4, max_tokens=600)
    system_msg = (
        "You are a knowledge graph designer. Given a topic, output exactly 6 subtopics "
        "that EXTEND the subject beyond a basic overview. "
        "Cover: history, core mechanisms, real-world applications, controversies/challenges, "
        "future directions, and comparisons with alternatives. "
        "Return ONLY valid JSON array, nothing else, no markdown: "
        '[{"label":"Name up to 4 words","children":["child1 up to 4 words","child2","child3"]}] '
        "Exactly 6 objects. Exactly 3 children each."
    )
    try:
        import re
        resp = llm.invoke([SystemMessage(content=system_msg), HumanMessage(content=f"Topic: {query}")])
        text = resp.content.strip()
        m = re.search(r"\[.*?\]", text, re.DOTALL)
        if m:
            data = json.loads(m.group())
            if isinstance(data, list) and len(data) >= 4:
                return data[:6]
    except Exception as e:
        print(f"subtopics error: {e}")
    return [
        {"label": "History & Origins",       "children": ["Early development", "Key pioneers", "Timeline"]},
        {"label": "Core Mechanisms",          "children": ["How it works", "Key components", "Process flow"]},
        {"label": "Real-World Applications",  "children": ["Industry use cases", "Consumer products", "Research uses"]},
        {"label": "Challenges & Limits",      "children": ["Technical barriers", "Ethical concerns", "Cost issues"]},
        {"label": "Future Directions",        "children": ["Emerging research", "Next decade", "Open problems"]},
        {"label": "Comparisons",              "children": ["vs alternatives", "Pros and cons", "Expert opinions"]},
    ]

def render_mindmap(query, report):
    """Horizontal tree mind map. Subtopics are LLM-generated extensions of the topic."""
    subtopics = generate_subtopics(query)
    nodes_json = json.dumps(subtopics)
    root_json  = json.dumps(query.title()[:38])

    html = _MINDMAP_TEMPLATE.replace("__NODES__", nodes_json).replace("__ROOT__", root_json)
    components.html(html, height=490, scrolling=False)

    st.markdown('<div style="font-size:0.6rem;color:#3a3a60;letter-spacing:0.14em;text-transform:uppercase;margin:0.7rem 0 0.4rem">// click any branch to research it deeper</div>', unsafe_allow_html=True)
    cols = st.columns(3)
    for i, sub in enumerate(subtopics):
        with cols[i % 3]:
            key = f"mm_{i}_{abs(hash(query + sub['label'])) % 99999}"
            if st.button(f"+ {sub['label']}", key=key, use_container_width=True):
                st.session_state.run_query = sub['label']
                st.session_state.viewing   = None
                st.rerun()

def render_images(query):
    """Topic-relevant images using loremflickr (free, keyword-based)."""
    import urllib.parse
    kw = query.lower().strip().replace("?","").replace("!","")
    words = [w for w in kw.split() if len(w) > 2]
    primary   = urllib.parse.quote_plus(kw[:30])
    secondary = [urllib.parse.quote_plus(w) for w in words[:3]]
    while len(secondary) < 3:
        secondary.append("technology")
    seeds = [abs(hash(query + str(i))) % 9000 + 100 for i in range(3)]

    html = '<div class="img-strip">'
    for i, (kwd, seed) in enumerate(zip(secondary, seeds)):
        combined = urllib.parse.quote_plus(f"{kw} {words[i] if i < len(words) else kwd}"[:40])
        url = f"https://loremflickr.com/600/300/{combined}?lock={seed}"
        fallback = f"https://loremflickr.com/600/300/{primary}?lock={seed+300}"
        label = words[i] if i < len(words) else kwd
        html += (
            f'<div class="img-card">'
            f'<img src="{url}" alt="{label}" loading="lazy" '
            f'onerror="this.onerror=null;this.src=\'{fallback}\'">'
            f'<div class="img-cap">&#9670; {label}</div>'
            f'</div>'
        )
    html += '</div>'
    st.markdown(html, unsafe_allow_html=True)

def make_pdf(query, report, stats, thinking):
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.lib import colors
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=(595,842), leftMargin=0.9*inch, rightMargin=0.9*inch, topMargin=0.9*inch, bottomMargin=0.9*inch)
    styles = getSampleStyleSheet()
    T = ParagraphStyle("T", parent=styles["Heading1"], fontSize=20, spaceAfter=8, textColor=colors.HexColor("#1a1a2e"), fontName="Helvetica-Bold")
    H = ParagraphStyle("H", parent=styles["Heading2"], fontSize=13, spaceAfter=4, textColor=colors.HexColor("#2d2d6b"), fontName="Helvetica-Bold", spaceBefore=14)
    N = ParagraphStyle("N", parent=styles["Normal"], fontSize=10, spaceAfter=4, textColor=colors.HexColor("#3a3a5c"), leading=16)
    M = ParagraphStyle("M", parent=styles["Normal"], fontSize=8, spaceAfter=8, textColor=colors.HexColor("#888888"), fontName="Helvetica-Oblique")
    elems = []
    elems.append(Paragraph(query.title(), T))
    meta = f"Synapse AI Research | {datetime.datetime.now().strftime('%B %d, %Y %H:%M')} | {stats.get('elapsed','?')}s | {stats.get('sources','?')} sources"
    elems.append(Paragraph(meta, M))
    elems.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#ccccee"), spaceAfter=14))
    cleaned = re.sub(r'\*\*(.*?)\*\*', r'\1', report)
    cleaned = re.sub(r'\*(.*?)\*', r'\1', cleaned)
    for line in cleaned.split("\n"):
        line = line.strip()
        if not line: elems.append(Spacer(1, 0.1*inch)); continue
        if line.startswith("## "): elems.append(Paragraph(line[3:], H))
        elif line.startswith("# "): elems.append(Paragraph(line[2:], T))
        else:
            line = re.sub(r'https?://\S+', '', line)
            try: elems.append(Paragraph(line, N))
            except: pass
    doc.build(elems)
    return buf.getvalue()


def make_share_link(entry):
    shareable = {k: entry[k] for k in ("query","report","stats","thinking","ts") if k in entry}
    raw = json.dumps(shareable).encode()
    encoded = base64.urlsafe_b64encode(zlib.compress(raw)).decode()
    try:
        host = st.get_option("browser.serverAddress") or "localhost"
        port = st.get_option("browser.serverPort") or 8501
        return f"http://{host}:{port}/?share={encoded}"
    except Exception:
        return f"?share={encoded}"


def run_pipeline(query, deep=False):
    start = time.time()
    log, think = [], {}
    box = st.empty()
    bar = st.progress(0)
    def tick(msg, pct): box.info(f"> {msg}"); bar.progress(pct)
    try:
        tick("agent - planning queries ...", 8)
        queries = generate_search_queries(query)
        think["queries_planned"] = queries
        log.append(("agent", f"{len(queries)} queries"))

        n = 5 if deep else 4
        tick(f"search - {len(queries)} queries x {n} ...", 22)
        results = search_web(queries, results_per_query=n)
        think["sources_found"] = len(results)
        if not results: box.error("No results. Check API key."); return None, log, think, queries, {}
        log.append(("search", f"{len(results)} URLs"))

        tick(f"scraper - fetching {len(results)} pages ...", 40)
        pages = fetch_and_clean(results)
        ok = sum(1 for p in pages if p["status"] == "success")
        think["pages_extracted"] = f"{ok}/{len(pages)}"
        log.append(("scraper", f"{ok}/{len(pages)} OK"))

        tick("chunker - splitting ...", 56)
        chunks = chunk_pages(pages)
        think["chunks_created"] = len(chunks)
        log.append(("chunker", f"{len(chunks)} chunks"))
        if not chunks: box.warning("No usable content."); return None, log, think, queries, {}

        top_k = 12 if deep else 8
        tick(f"rag - embedding {len(chunks)} chunks, top {top_k} ...", 70)
        store = embed_and_store(chunks)
        relevant = retrieve_relevant_chunks(store, query, top_k=top_k)
        avg = round(sum(c["relevance_score"] for c in relevant) / max(len(relevant),1), 3)
        think["rag_avg_score"] = avg
        think["chunks_used"] = len(relevant)
        log.append(("rag", f"{len(relevant)} chunks, avg {avg}"))

        tick("llm - synthesizing report ...", 86)
        report = synthesize_report(query, relevant, deep_mode=deep)

        elapsed = round(time.time()-start, 1)
        think["total_time"] = f"{elapsed}s"
        log.append(("done", f"{elapsed}s"))
        bar.progress(100); box.success(f"Done in {elapsed}s")

        return report, log, think, queries, {"elapsed": elapsed, "sources": len(results), "ok": ok, "chunks": len(chunks)}
    except EnvironmentError as e: box.error(str(e)); return None, log, think, None, {}
    except Exception as e: box.error(str(e)); st.exception(e); return None, log, think, None, {}


def render_entry(entry):
    q, report = entry["query"], entry["report"]
    s, log = entry["stats"], entry["log"]
    think = entry.get("thinking", {})
    queries = entry.get("queries", [])
    ts = entry.get("ts", "")
    deep = entry.get("deep", False)

    badge = '<span class="mode-badge">Deep Mode</span>' if deep else ""
    st.markdown(f'<div class="result-q">{q}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="result-meta">{ts} &nbsp;&middot;&nbsp; {s.get("elapsed","?")}s &nbsp;&middot;&nbsp; {s.get("sources","?")} sources &nbsp;{badge}</div>', unsafe_allow_html=True)

    st.markdown(f"""<div class="stats-row">
        <div class="stat-card"><span class="stat-v">{s.get("elapsed","?")}s</span><span class="stat-l">runtime</span></div>
        <div class="stat-card"><span class="stat-v">{s.get("sources","?")}</span><span class="stat-l">sources</span></div>
        <div class="stat-card"><span class="stat-v">{s.get("ok","?")}</span><span class="stat-l">pages read</span></div>
        <div class="stat-card"><span class="stat-v">{s.get("chunks","?")}</span><span class="stat-l">chunks</span></div>
    </div>""", unsafe_allow_html=True)

    st.markdown('<div class="sdiv"><div class="sdiv-line"></div><div class="sdiv-lbl">visuals</div><div class="sdiv-line"></div></div>', unsafe_allow_html=True)
    render_images(q)

    st.markdown('<div class="sdiv"><div class="sdiv-line"></div><div class="sdiv-lbl">report</div><div class="sdiv-line"></div></div>', unsafe_allow_html=True)
    rph = st.empty()
    words = report.split()
    streamed = ""
    for i, w in enumerate(words):
        streamed += w + " "
        if i % 15 == 0 or i == len(words)-1:
            rph.markdown(streamed)
    rph.markdown(report)

    if st.session_state.show_think and think:
        st.markdown('<div class="sdiv"><div class="sdiv-line"></div><div class="sdiv-lbl">ai thinking</div><div class="sdiv-line"></div></div>', unsafe_allow_html=True)
        icons = {"queries_planned":"brain","sources_found":"search","pages_extracted":"page","chunks_created":"cut","rag_avg_score":"diamond","chunks_used":"box","total_time":"clock"}
        emoji_map = {"brain":"🧠","search":"🔍","page":"📄","cut":"✂️","diamond":"◈","box":"📦","clock":"⏱"}
        for k, v in think.items():
            icon = emoji_map.get(icons.get(k,"diamond"), "◈")
            label = k.replace("_"," ").title()
            val = ", ".join(v) if isinstance(v,list) else str(v)
            st.markdown(f'<div class="think-row"><div class="think-icon">{icon}</div><div><div class="think-label">{label}</div><div class="think-val">{val}</div></div></div>', unsafe_allow_html=True)

    if st.session_state.show_map:
        st.markdown('<div class="sdiv"><div class="sdiv-line"></div><div class="sdiv-lbl">mind map</div><div class="sdiv-line"></div></div>', unsafe_allow_html=True)
        render_mindmap(q, report)

    st.markdown('<div class="sdiv" style="margin-top:2.5rem"><div class="sdiv-line"></div><div class="sdiv-lbl">pipeline log</div><div class="sdiv-line"></div></div>', unsafe_allow_html=True)
    with st.expander("// pipeline details", expanded=False):
        if queries:
            st.markdown("".join(f'<span style="display:inline-block;background:rgba(139,92,246,0.07);border:1px solid rgba(139,92,246,0.15);color:#7070b8;font-size:0.68rem;padding:0.2rem 0.55rem;border-radius:5px;margin:2px;font-family:monospace">+ {q2}</span>' for q2 in queries), unsafe_allow_html=True)
            st.markdown("<br>", unsafe_allow_html=True)
        for step, detail in log:
            st.markdown(f'<div class="log-entry"><div class="log-tag">[{step}]</div><div class="log-val">{detail}</div></div>', unsafe_allow_html=True)

    st.markdown('<div class="sdiv"><div class="sdiv-line"></div><div class="sdiv-lbl">export & share</div><div class="sdiv-line"></div></div>', unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1,1,2])
    with c1:
        st.download_button("Download MD", data=f"# {q}\n\n---\n\n{report}", file_name=f"synapse_{q[:20].replace(' ','_').lower()}.md", mime="text/markdown", key=f"md_{abs(hash(q))%99999}")
    with c2:
        try:
            pdf_bytes = make_pdf(q, report, s, think)
            st.download_button("Download PDF", data=pdf_bytes, file_name=f"synapse_{q[:20].replace(' ','_').lower()}.pdf", mime="application/pdf", key=f"pdf_{abs(hash(q))%99999}")
        except Exception as e:
            st.caption(f"PDF: {e}")
    with c3:
        share = make_share_link(entry)
        st.markdown('<div class="share-box">', unsafe_allow_html=True)
        st.text_input("Share link", value=share, key=f"share_{abs(hash(q))%99999}", label_visibility="collapsed")
        st.markdown('</div>', unsafe_allow_html=True)


def main():
    EXAMPLES = [
        "How do black holes form?","Latest in fusion energy","How does CRISPR work?",
        "Quantum computing explained","How are LLMs trained?","What is Neuralink?",
        "What causes inflation?","mRNA vaccine technology","Dark matter explained",
        "James Webb discoveries","How does the internet work?","AI consciousness debate",
        "How do black holes form?","Latest in fusion energy","How does CRISPR work?",
    ]
    PIPE_STEPS = [
        ("01","Agent","Plans search queries"),("02","Search","Fetches web results"),
        ("03","Scraper","Extracts page text"),("04","Chunker","Splits into segments"),
        ("05","RAG","Retrieves top chunks"),("06","LLM","Writes the report"),
    ]

    with st.sidebar:
        st.markdown('<div class="brand"><div class="brand-name">Synapse</div><div class="brand-tag">research terminal · rag + agent</div></div>', unsafe_allow_html=True)

        st.markdown('<div class="sb-section">// options</div>', unsafe_allow_html=True)
        st.session_state.deep_mode  = st.toggle("Deep Research", value=st.session_state.deep_mode)
        st.session_state.show_think = st.toggle("AI Thinking", value=st.session_state.show_think)
        st.session_state.show_map   = st.toggle("Mind Map", value=st.session_state.show_map)

        st.markdown('<div class="sb-section">// recent</div>', unsafe_allow_html=True)
        history = st.session_state.history
        if history:
            for i, entry in enumerate(reversed(history[-12:])):
                idx = len(history)-1-i
                active = "active  " if st.session_state.viewing == idx else ""
                if st.button(active + entry["query"][:34], key=f"h_{idx}", use_container_width=True):
                    st.session_state.viewing = idx; st.rerun()
        else:
            st.markdown('<div class="sb-empty">No searches yet.<br>Ask anything below.</div>', unsafe_allow_html=True)

        pipe_html = '<div class="pipe-wrap"><div class="pipe-head">// pipeline</div>'
        for num, name, desc in PIPE_STEPS:
            pipe_html += f'<div class="pipe-row"><div class="pipe-num">{num}</div><div><div class="pipe-name">{name}</div><div class="pipe-desc">{desc}</div></div></div>'
        pipe_html += '</div>'
        st.markdown(pipe_html, unsafe_allow_html=True)

    viewing = st.session_state.viewing
    show_hero = viewing is None and not st.session_state.get("run_query")

    if show_hero:
        st.markdown('<div class="hero"><div class="hero-badge">Agentic - RAG - Llama 3.3 70B</div><div class="hero-h1">Research anything.<br><span class="hero-grad">Instantly sourced.</span></div><div class="hero-sub">Ask a question. The agent plans the search, reads the web, and synthesizes a cited report with images, mind maps and PDF export.</div></div>', unsafe_allow_html=True)

    with st.form("sf", clear_on_submit=False):
        c1, c2 = st.columns([6,1])
        with c1:
            auto = st.session_state.get("run_query","")
            typed = st.text_input("q", value=auto, placeholder="Ask anything - press Enter or click Run", label_visibility="collapsed", key="qi")
        with c2:
            submitted = st.form_submit_button("Run", use_container_width=True)

    st.markdown('<div class="search-hint">press enter to search</div>', unsafe_allow_html=True)

    if show_hero:
        pills = "".join(f'<span class="ex-pill">{e}</span>' for e in EXAMPLES)
        st.markdown(f'<div style="margin-top:1.6rem"><div class="pill-lbl">// try an example</div><div class="pill-outer"><div class="pill-track">{pills}</div></div></div>', unsafe_allow_html=True)
        with st.sidebar:
            st.markdown('<div class="sb-section">// examples</div>', unsafe_allow_html=True)
            for ex in EXAMPLES[:6]:
                if st.button(ex, key=f"ex_{ex[:22]}", use_container_width=True):
                    st.session_state.run_query = ex; st.session_state.viewing = None; st.rerun()

    query_to_run = ""
    auto_q = st.session_state.get("run_query","")
    if submitted and typed.strip():
        query_to_run = typed.strip(); st.session_state.run_query = ""
    elif auto_q:
        query_to_run = auto_q; st.session_state.run_query = ""

    if query_to_run:
        st.markdown("<hr>", unsafe_allow_html=True)
        report, log, think, queries, stats = run_pipeline(query_to_run, st.session_state.deep_mode)
        if report and stats:
            entry = {
                "query": query_to_run, "report": report, "log": log,
                "thinking": think, "queries": queries, "stats": stats,
                "deep": st.session_state.deep_mode,
                "ts": datetime.datetime.now().strftime("%H:%M %b %d"),
            }
            st.session_state.history.append(entry)
            st.session_state.viewing = len(st.session_state.history)-1
            st.rerun()

    viewing = st.session_state.viewing
    history = st.session_state.history

    if viewing is not None and viewing < len(history):
        st.markdown("<br>", unsafe_allow_html=True)
        render_entry(history[viewing])
    elif show_hero:
        st.markdown('<div class="empty-wrap"><div class="empty-glyph">Synapse</div><div class="empty-lines">type a question above<br>press enter to run<br>or pick an example</div></div>', unsafe_allow_html=True)

if __name__ == "__main__":
    main()