"""
=============================================================================

=============================================================================
"""

# ── 1. IMPORTS & PATH SETUP ──────────────────────────────────────────────────

import os
import sys
import json
import csv
import time
import random
from datetime import datetime
import traceback 
# Ensure retail_analyst/ root is on the Python path so sub-modules resolve
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import streamlit as st
import pandas as pd
from dotenv import load_dotenv
from server.hf_client import chat_completion
import yaml

from server.db_connector import DatabaseConnector
from server.sql_validator import SQLValidator, SQLValidationError
from server.prompts import (
    get_analyst_system_prompt,
    get_sql_generation_prompt,
    get_sql_review_prompt,
    get_result_explanation_prompt,
    get_visualization_prompt,
)
from chart_renderer import render_chart
from evaluation_dashboard import render_evaluation_dashboard

load_dotenv()

# ── 2. PAGE CONFIG & GLOBAL CSS ──────────────────────────────────────────────

if __name__ == '__main__':
    st.set_page_config(
        page_title="Retail AI Analyst",
        page_icon="📊",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    
    st.markdown("""
    <style>
    /* ── Premium Fonts Pairing ── */
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@400;500;600;700;800&family=Plus+Jakarta+Sans:wght@400;500;600;700&display=swap');
    
    :root {
        --bg-base: #090a0f;
        --bg-surface: #12141d;
        --bg-surface-hover: #1a1d2b;
        --accent-emerald: #10b981;
        --accent-cyan: #06b6d4;
        --accent-gradient: linear-gradient(135deg, #059669 0%, #10b981 50%, #06b6d4 100%);
        --accent-glow: rgba(16, 185, 129, 0.25);
        --text-main: #f8fafc;
        --text-muted: #94a3b8;
        --border-subtle: rgba(255, 255, 255, 0.06);
        --border-accent: rgba(16, 185, 129, 0.25);
        
        --anim-fast: 150ms cubic-bezier(0.4, 0, 0.2, 1);
        --anim-base: 250ms cubic-bezier(0.4, 0, 0.2, 1);
        --anim-slow: 400ms cubic-bezier(0.4, 0, 0.2, 1);
    }
    
    /* ── Typography & Global Reset ── */
    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', sans-serif;
        color: var(--text-main);
        font-feature-settings: "cv02", "cv03", "cv04", "ss01";
        -webkit-font-smoothing: antialiased;
    }
    
    h1, h2, h3, h4, h5, h6 {
        font-family: 'Outfit', sans-serif !important;
        font-weight: 700 !important;
        letter-spacing: -0.02em !important;
    }
    
    /* ── Depth & Atmosphere Background ── */
    .stApp {
        background: radial-gradient(circle at 50% 0%, rgba(16, 185, 129, 0.08) 0%, transparent 60%),
                    radial-gradient(circle at 100% 100%, rgba(6, 182, 212, 0.05) 0%, transparent 50%),
                    var(--bg-base);
        background-attachment: fixed;
    }
    
    /* ── Subtle Entrance Animations ── */
    @keyframes smoothFadeSlide {
        from { opacity: 0; transform: translateY(12px); }
        to { opacity: 1; transform: translateY(0); }
    }
    
    [data-testid="stChatMessage"], [data-testid="stExpander"], .stDataFrame {
        animation: smoothFadeSlide var(--anim-slow) forwards;
    }
    
    /* ── Sidebar Polish ── */
    [data-testid="stSidebar"] {
        background-color: rgba(14, 16, 23, 0.8) !important;
        backdrop-filter: blur(20px) !important;
        border-right: 1px solid var(--border-subtle) !important;
    }
    
    [data-testid="stSidebar"] * {
        color: var(--text-muted);
        transition: color var(--anim-fast);
    }
    
    [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h4 {
        color: var(--text-main) !important;
    }
    
    /* ── Sleek Chat Input Container ── */
    [data-testid="stChatInput"] {
        padding-bottom: 24px !important;
    }
    
    [data-testid="stChatInput"] textarea {
        background: var(--bg-surface) !important;
        border: 1px solid var(--border-subtle) !important;
        border-radius: 14px !important;
        color: var(--text-main) !important;
        padding: 14px 18px !important;
        font-size: 15px !important;
        box-shadow: 0 8px 32px -4px rgba(0, 0, 0, 0.4) !important;
        transition: border var(--anim-base), box-shadow var(--anim-base) !important;
    }
    
    [data-testid="stChatInput"] textarea:focus {
        border-color: var(--accent-emerald) !important;
        box-shadow: 0 0 0 2px var(--accent-glow), 0 8px 32px -4px rgba(0, 0, 0, 0.6) !important;
    }
    
    /* ── Chat Message Bubbles ── */
    [data-testid="stChatMessage"] {
        border-radius: 16px !important;
        border: 1px solid var(--border-subtle) !important;
        background: var(--bg-surface) !important;
        padding: 20px !important;
        margin-bottom: 16px !important;
        box-shadow: 0 4px 20px -2px rgba(0, 0, 0, 0.3) !important;
    }
    
    [data-testid="stChatMessage"]:hover {
        border-color: var(--border-accent) !important;
    }
    
    /* ── Buttons Refinement ── */
    .stButton > button {
        background: var(--bg-surface) !important;
        color: var(--text-main) !important;
        border: 1px solid var(--border-subtle) !important;
        border-radius: 12px !important;
        font-family: 'Outfit', sans-serif !important;
        font-weight: 600 !important;
        font-size: 14px !important;
        letter-spacing: 0.02em !important;
        padding: 12px 20px !important;
        transition: all var(--anim-base) !important;
        width: 100% !important;
        box-shadow: 0 2px 10px rgba(0, 0, 0, 0.2) !important;
    }
    
    .stButton > button:hover {
        background: var(--accent-gradient) !important;
        color: #fff !important;
        border-color: transparent !important;
        transform: translateY(-2px) !important;
        box-shadow: 0 8px 25px -4px var(--accent-glow) !important;
    }
    
    .stButton > button:active {
        transform: translateY(0) !important;
    }
    
    /* ── Expanders Customization ── */
    [data-testid="stExpander"] {
        background: var(--bg-surface) !important;
        border: 1px solid var(--border-subtle) !important;
        border-radius: 14px !important;
        overflow: hidden !important;
        transition: border var(--anim-base) !important;
    }
    
    [data-testid="stExpander"]:hover {
        border-color: var(--border-accent) !important;
    }
    
    [data-testid="stExpander"] summary {
        font-family: 'Outfit', sans-serif !important;
        font-weight: 600 !important;
        color: var(--text-main) !important;
        padding: 16px !important;
    }
    
    /* ── Premium Segmented Control Tabs ── */
    [data-baseweb="tab-list"] {
        background: var(--bg-surface) !important;
        border: 1px solid var(--border-subtle) !important;
        border-radius: 14px !important;
        padding: 6px !important;
        gap: 6px !important;
    }
    
    [data-baseweb="tab"] {
        border-radius: 10px !important;
        color: var(--text-muted) !important;
        font-family: 'Outfit', sans-serif !important;
        font-weight: 600 !important;
        font-size: 14px !important;
        padding: 10px 20px !important;
        transition: all var(--anim-fast) !important;
    }
    
    [aria-selected="true"][data-baseweb="tab"] {
        background: var(--accent-gradient) !important;
        color: #fff !important;
        box-shadow: 0 4px 15px -2px var(--accent-glow) !important;
    }
    
    /* ── Styled Dataframe ── */
    .stDataFrame {
        border-radius: 14px !important;
        border: 1px solid var(--border-subtle) !important;
        overflow: hidden !important;
    }
    
    /* ── Code Blocks Refinement ── */
    pre code {
        font-family: 'JetBrains Mono', 'Courier New', monospace !important;
        font-size: 13px !important;
        line-height: 1.6 !important;
    }
    
    code {
        background: rgba(16, 185, 129, 0.1) !important;
        color: var(--accent-emerald) !important;
        border-radius: 6px !important;
        padding: 2px 6px !important;
    }
    
    /* ── Custom Banners ── */
    .stSuccess, .stError, .stWarning, .stInfo {
        border-radius: 14px !important;
        border: 1px solid var(--border-subtle) !important;
        backdrop-filter: blur(10px) !important;
    }
    
    /* ── Sleek Scrollbars ── */
    ::-webkit-scrollbar { width: 6px; height: 6px; }
    ::-webkit-scrollbar-track { background: var(--bg-base); }
    ::-webkit-scrollbar-thumb { background: rgba(255, 255, 255, 0.1); border-radius: 3px; }
    ::-webkit-scrollbar-thumb:hover { background: var(--border-accent); }
    </style>
    """, unsafe_allow_html=True)


# ── 3. BACKEND INITIALISATION ─────────────────────────────────────────────────

@st.cache_resource
def init_backend():
    db  = DatabaseConnector()
    # Use script directory to find semantic model regardless of working directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    sem_model_path = os.path.join(script_dir, "semantic", "semantic_model.yml")
    with open(sem_model_path, "r", encoding="utf-8") as f:
        sem_data = yaml.safe_load(f)
        sem_text = yaml.dump(sem_data)
    validator = SQLValidator(sem_data)
    return db, validator, sem_data, sem_text

db, validator, sem_data, sem_text = init_backend()
LLM_MODEL = os.getenv("MODEL_ID", "Qwen/Qwen2.5-7B-Instruct")
SYSTEM_PROMPT = get_analyst_system_prompt()


# ── Audit logger ─────────────────────────────────────────────────────────────

def _audit(tool: str, params: str, status: str, err: str = ""):
    os.makedirs("logs", exist_ok=True)
    log = "logs/audit_log.csv"
    first = not os.path.isfile(log)
    with open(log, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if first:
            w.writerow(["Timestamp", "Tool", "Parameters", "Status", "ErrorMessage"])
        w.writerow([datetime.now().isoformat(), tool, params[:300], status, err])


# ── 4. PIPELINE HELPERS ───────────────────────────────────────────────────────

def _call_llm(prompt: str, system: str = "", max_tokens: int = 1024,
                 temperature: float = 0.1, max_retries: int = 4) -> str:
    """
    Wrapper around Gemini (primary) or Hugging Face Inference API (fallback).
    Automatically retries with exponential backoff on rate-limit errors.
    """
    gemini_key = os.getenv("GEMINI_API_KEY")
    
    if gemini_key:
        import google.generativeai as genai
        genai.configure(api_key=gemini_key)
        # We use gemini-2.5-flash since it's blazingly fast and has a high free tier
        model = genai.GenerativeModel(
            model_name="gemini-2.5-flash",
            system_instruction=system if system else None
        )
        
        for attempt in range(max_retries):
            try:
                response = model.generate_content(
                    prompt,
                    generation_config=genai.types.GenerationConfig(
                        max_output_tokens=max_tokens,
                        temperature=temperature,
                    )
                )
                return response.text.strip()
            except Exception as e:
                err_str = str(e).lower()
                if "429" in err_str or "quota" in err_str or "rate limit" in err_str:
                    if attempt < max_retries - 1:
                        time.sleep((2 ** attempt) + random.uniform(0.5, 1.5))
                        continue
                raise
    else:
        # Fallback to Hugging Face
        if system:
            full_prompt = f"{system}\n\n{prompt}"
        else:
            full_prompt = prompt

        for attempt in range(max_retries):
            try:
                messages = []
                if system:
                    messages.append({"role": "system", "content": system})
                messages.append({"role": "user", "content": full_prompt})
                resp = chat_completion(
                    messages,
                    model_id=LLM_MODEL,
                    max_new_tokens=max_tokens,
                    temperature=temperature,
                )
                return resp.strip()
            except Exception as e:
                err_str = str(e).lower()
                if "rate_limit" in err_str or "quota" in err_str or "overload" in err_str or "throttled" in err_str:
                    if attempt < max_retries - 1:
                        wait = (2 ** attempt) + random.uniform(0.5, 1.5)
                        time.sleep(wait)
                        continue
                    else:
                        raise RuntimeError(
                            f"HF API rate limit reached after {max_retries} retries. "
                            "Please wait a moment and try again, or check your API quota."
                        )
                raise


def _clean_sql(raw: str) -> str:
    """Strip markdown code fences Gemini sometimes wraps around SQL."""
    for fence in ("```sql", "```SQL", "```"):
        raw = raw.replace(fence, "")
    return raw.strip().rstrip(";")


def _check_ambiguity_builtin(question: str) -> str | None:
    """
    Lightweight rule-based ambiguity check (no API call needed).
    Returns a clarifying question if the input is clearly too vague, else None.
    This preserves the 'controlled analyst' behaviour without burning API quota.
    """
    q = question.strip().lower()

    # Safety test questions — always pass through to validator
    if any(kw in q for kw in ["delete", "drop", "update", "insert", "truncate"]):
        return None

    # Too short or no domain keywords at all
    words = q.split()
    domain_keywords = [
        "sale", "revenue", "profit", "return", "order", "product", "store",
        "category", "customer", "inventory", "stock", "trend", "region",
        "margin", "aov", "quantity", "brand", "subcategory", "tier", "month",
        "year", "quarter", "2024", "2025", "2026", "electronics", "fashion",
        "punjab", "karachi", "lahore", "top", "highest", "lowest", "average"
    ]
    has_domain = any(kw in q for kw in domain_keywords)

    if len(words) <= 3 and not has_domain:
        return "Could you be more specific? For example: 'What is total net sales by category for 2025?'"

    if q in ("show data", "show me data", "give me data", "what", "tell me", "show"):
        return "What specific retail metric or report would you like to see?"

    return None  # Clear enough — proceed


def run_full_pipeline(question: str, conversation_history: list) -> dict:
    """
    Full text-to-answer pipeline (3 Gemini calls per question):
      1. Rule-based ambiguity check (no API call)
      2. Build context-aware prompt (conversation history)
      3. Generate SQL with Gemini  [API call 1]
      4. Validate & sanitize SQL (SQLValidator — programmatic)
      5. Execute against PostgreSQL
      6. Explain result in plain English [API call 2]
      7. Recommend best chart type    [API call 3]
      8. Audit-log each step

    Returns a dict with keys:
        sql, explanation, chart_config, data, columns, error, blocked,
        clarification_needed, elapsed_seconds
    """
    result = dict(sql="", explanation="", chart_config={},
                  data=[], columns=[], error="", blocked=False,
                  clarification_needed=None, elapsed_seconds=0.0)
    t0 = time.time()

    # ── Step 0: Rule-based ambiguity check (0 API calls) ─────────────────────
    is_followup = len(conversation_history) > 0 and len(question.split()) < 12
    if not is_followup:
        clarification = _check_ambiguity_builtin(question)
        if clarification:
            result["clarification_needed"] = clarification
            result["elapsed_seconds"] = round(time.time() - t0, 2)
            _audit("clarify_question", question, "NEEDS_CLARIFICATION", clarification)
            return result

    # ── Build schema + context ───────────────────────────────────────────────
    schema_info = db.get_schema_info()

    # Append conversation history as additional context in the prompt
    history_text = ""
    if conversation_history:
        history_text = "\n\nPREVIOUS CONVERSATION CONTEXT:\n"
        for msg in conversation_history[-6:]:   # last 3 Q&A pairs
            role = "User" if msg["role"] == "user" else "Assistant"
            history_text += f"{role}: {msg['content'][:300]}\n"

    full_question = question + history_text

    # ── Step 1: Generate SQL ──────────────────────────────────────────────────
    try:
        gen_prompt = get_sql_generation_prompt(full_question, schema_info, sem_text)
        raw_sql    = _call_llm(gen_prompt, system=SYSTEM_PROMPT, max_tokens=1024)
        sql        = _clean_sql(raw_sql)
        _audit("generate_sql", question, "SUCCESS")
    except Exception as e:
       tb = traceback.format_exc()
       result["error"] = f"SQL generation failed: {e}"
       _audit("generate_sql", question, "FAILED", tb)
       print(tb)
       return result

    # ── Auto-Heal Loop ────────────────────────────────────────────────────────
    max_heal_attempts = 3
    last_error = ""
    
    for attempt in range(max_heal_attempts):
        # Step 2: Validate & sanitize
        try:
            safe_sql = validator.validate_and_sanitize(sql)
            result["sql"] = safe_sql
            _audit("validate_sql", sql, "SUCCESS")
        except SQLValidationError as ve:
            result["error"]   = f"🛡️ Safety validator blocked this query: {ve}"
            result["blocked"] = True
            result["sql"]     = sql
            _audit("validate_sql", sql, "FAILED", str(ve))
            return result

        # Step 4: Execute query
        try:
            rows = db.run_query(safe_sql)
            data = [dict(r) for r in rows]
            result["data"]    = data
            result["columns"] = list(data[0].keys()) if data else []
            _audit("run_readonly_query", safe_sql, "SUCCESS")
            last_error = ""
            break # Success, break out of heal loop!
        except Exception as e:
            last_error = str(e)
            _audit("run_readonly_query", safe_sql, "FAILED", last_error)
            
            # If we still have attempts left, try to auto-heal
            if attempt < max_heal_attempts - 1:
                heal_prompt = f"The following PostgreSQL query failed with an error:\n\nQuery:\n```sql\n{sql}\n```\n\nError: {last_error}\n\nPlease fix the query based on the schema and the error message. Output ONLY the fixed SQL code without any markdown or explanation."
                try:
                    raw_sql = _call_llm(heal_prompt, system=SYSTEM_PROMPT, max_tokens=1024)
                    sql = _clean_sql(raw_sql)
                    continue # Retry the loop with new SQL
                except Exception as heal_err:
                    last_error += f" | Auto-heal failed: {heal_err}"
                    break # Break and fail
            else:
                break # Reached max attempts
                
    if last_error:
        result["error"] = f"Query execution failed: {last_error}"
        return result

    # ── Step 5: Explain result ───────────────────────────────────────────────
    try:
        expl_prompt    = get_result_explanation_prompt(
            question, result["columns"],
            [[row[c] for c in result["columns"]] for row in data[:20]]
        )
        result["explanation"] = _call_llm(
            expl_prompt, system=SYSTEM_PROMPT,
            max_tokens=1024, temperature=0.3
        )
        _audit("explain_result", question, "SUCCESS")
    except Exception as e:
        result["explanation"] = "Explanation unavailable."
        _audit("explain_result", question, "FAILED", str(e))

    # ── Step 6: Chart recommendation ─────────────────────────────────────────
    try:
        viz_prompt = get_visualization_prompt(
            question, result["columns"],
            [[row[c] for c in result["columns"]] for row in data[:5]]
        )
        chart_raw  = _call_llm(viz_prompt, max_tokens=500)
        # Strip any markdown fences LLM wraps around JSON
        for f in ("```json", "```JSON", "```"):
            chart_raw = chart_raw.replace(f, "")
        result["chart_config"] = json.loads(chart_raw.strip())
        _audit("suggest_chart", question, "SUCCESS")
    except Exception as e:
        result["chart_config"] = {"chart_type": "table"}
        _audit("suggest_chart", question, "FAILED", str(e))

    result["elapsed_seconds"] = round(time.time() - t0, 2)
    return result


# ── 5. SIDEBAR ─────────────────────────────────────────────────────────────────
def main_ui():

    with st.sidebar:
        # Brand
        st.markdown("""
        <div style="text-align:center; padding: 12px 0 28px;">
            <div style="display:inline-flex; align-items:center; justify-content:center; width:64px; height:64px; border-radius:18px; background:var(--accent-glow); border:1px solid var(--accent-emerald); box-shadow:0 8px 24px -4px var(--accent-glow); margin-bottom:12px;">
                <span style="font-size:32px; color:var(--accent-emerald);">⬡</span>
            </div>
            <h2 style="font-family:'Outfit', sans-serif; font-size:24px; font-weight:800; color:var(--text-main); margin:0; letter-spacing:-0.03em;">
                RETAIL <span style="color:var(--accent-emerald);">ANALYST</span>
            </h2>
            <p style="color:var(--accent-cyan); font-size:11px; font-weight:700; margin:4px 0 0; letter-spacing:0.2em; text-transform:uppercase;">
                ENTERPRISE BI ENGINE
            </p>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("---")

        # ── Demo Questions (Section 19) ──────────────────────────────────────────
        st.markdown("#### 🚀 Demo Questions")
        # Exact 5 demo questions from Assignment Section 19
        DEMO_QUESTIONS = [
            "What is the total net sales by category for 2025?",
            "Which store has the highest average order value in Punjab?",
            "Which subcategory has the highest return rate?",
            "Delete low-profit products from the database.",   # Safety test — must be blocked
            "Show monthly trend for Electronics and recommend a chart.",
        ]

        for i, q in enumerate(DEMO_QUESTIONS, 1):
            if st.button(f"Q{i}: {q[:45]}...", key=f"demo_{i}"):
                st.session_state["pending_question"] = q

        st.markdown("---")

        # ── Query History ────────────────────────────────────────────────────────
        st.markdown("#### 🕑 Query History")
        history = st.session_state.get("messages", [])
        user_msgs = [m["content"] for m in history if m["role"] == "user"]
        if user_msgs:
            for idx, uq in enumerate(reversed(user_msgs[-10:])):
                st.markdown(
                    f'<p style="color:#aaa; font-size:12px; padding:4px 8px; '
                    f'border-left:2px solid #667eea; margin:4px 0;">'
                    f'{uq[:55]}{"..." if len(uq)>55 else ""}</p>',
                    unsafe_allow_html=True
                )
        else:
            st.caption("No queries yet.")

        st.markdown("---")

        # ── Clear chat ───────────────────────────────────────────────────────────
        if st.button("🗑️ Clear Conversation"):
            st.session_state["messages"] = []
            st.session_state["pending_question"] = ""
            st.rerun()

        # ── DB status ────────────────────────────────────────────────────────────
        st.markdown("#### 🔌 System Status")
        try:
            chk = db.run_query("SELECT COUNT(*) AS c FROM retail_dw.dim_store")
            st.success(f"✅ DB Connected · {chk[0]['c']} stores")
        except Exception as e:
            st.error(f"❌ DB Error: {e}")


    # ── 6. MAIN AREA ───────────────────────────────────────────────────────────────

    # Hero header
    st.markdown("""
    <div style="padding: 48px 0 32px; text-align: center; position: relative;">
        <div style="display: inline-flex; align-items: center; gap: 8px; background: rgba(16, 185, 129, 0.1); border: 1px solid rgba(16, 185, 129, 0.2); padding: 6px 16px; border-radius: 30px; margin-bottom: 16px;">
            <span style="display: inline-block; width: 8px; height: 8px; border-radius: 50%; background: var(--accent-emerald); box-shadow: 0 0 12px var(--accent-emerald);"></span>
            <span style="color: var(--accent-emerald); font-size: 12px; font-weight: 700; letter-spacing: 0.08em; text-transform: uppercase;">Production Data Engine Active</span>
        </div>
        <h1 style="font-family: 'Outfit', sans-serif; font-size: 54px; font-weight: 800; color: var(--text-main); line-height: 1.15; letter-spacing: -0.04em; margin: 0;">
            Autonomous <span style="background: var(--accent-gradient); -webkit-background-clip: text; -webkit-text-fill-color: transparent;">Retail Intelligence</span>
        </h1>
        <p style="color: var(--text-muted); font-size: 18px; max-width: 640px; margin: 16px auto 0; line-height: 1.6; font-weight: 400;">
            Query 2.5 million atomic POS transactions instantly. Backed by verified Kimball dimensional constraints and Google Gemini 2.5 real-time schema grounding.
        </p>
    </div>
    """, unsafe_allow_html=True)

    # Tabs
    tab_chat, tab_eval = st.tabs(["💬  Chat", "📊  Evaluation Dashboard"])

    # Session state
    if "messages" not in st.session_state:
        st.session_state["messages"] = []
    if "pending_question" not in st.session_state:
        st.session_state["pending_question"] = ""

    # ── TAB 1: CHAT ───────────────────────────────────────────────────────────────
    with tab_chat:

        # Render existing messages
        for msg in st.session_state["messages"]:
            with st.chat_message(msg["role"], avatar="🧑" if msg["role"]=="user" else "🤖"):
                if msg["role"] == "user":
                    st.markdown(msg["content"])
                else:
                    # Assistant messages carry a structured payload
                    payload = msg.get("payload", {})
                    st.markdown(payload.get("explanation", msg["content"]))

                    # SQL panel
                    if payload.get("sql"):
                        with st.expander("🔍 SQL Used  (Explainability)", expanded=False):
                            st.code(payload["sql"], language="sql")

                    # Chart
                    if payload.get("data") and payload.get("chart_config"):
                        render_chart(payload["chart_config"], payload["data"])

                    # Data table
                    if payload.get("data"):
                        with st.expander(
                            f"📋 Raw Data  ({len(payload['data'])} rows)", expanded=False
                        ):
                            st.dataframe(
                                pd.DataFrame(payload["data"]),
                                use_container_width=True, hide_index=True
                            )

                    # Timing
                    if payload.get("elapsed_seconds"):
                        st.caption(f"⏱ Response time: {payload['elapsed_seconds']}s")

                    # Error / blocked
                    if payload.get("error"):
                        if payload.get("blocked"):
                            st.error(f"🛡️ Safety Block: {payload['error']}")
                        else:
                            st.error(payload["error"])

    # ── TAB 2: EVALUATION DASHBOARD ───────────────────────────────────────────────
    with tab_eval:
        render_evaluation_dashboard()
        if st.button("🔄 Refresh Metrics"):
            st.rerun()

    # ── Chat input (OUTSIDE tabs) ─────────────────────────────────────────────────
    st.divider()

    # Handle demo button
    auto_q = st.session_state.pop("pending_question", "")

    # Chat input
    user_input = st.chat_input("Ask a retail analytics question…") or auto_q

    if user_input:
        # Add user message
        st.session_state["messages"].append({"role": "user", "content": user_input})
        with st.chat_message("user", avatar="🧑"):
            st.markdown(user_input)

        # Run pipeline
        with st.chat_message("assistant", avatar="🤖"):
            status_box = st.empty()
            status_box.info("⚙️ Step 1/3 — Generating SQL from your question…")
            payload = run_full_pipeline(
                user_input, st.session_state["messages"][:-1]
            )
            status_box.empty()  # Clear status once done

            # ── Clarification needed (analyst asks instead of guessing) ──────
            if payload.get("clarification_needed"):
                clarify_msg = payload["clarification_needed"]
                st.markdown(f"❓ **Clarification needed:** {clarify_msg}")
                st.caption(
                    "_As a controlled data analyst (not a general chatbot), "
                    "I ask for clarification rather than guessing your intent._"
                )
                # Save to history so follow-up has context
                st.session_state["messages"].append({
                    "role": "assistant",
                    "content": clarify_msg,
                    "payload": payload,
                })
                st.stop()

            # ── Display explanation ──────────────────────────────────────────
            if payload["explanation"]:
                st.markdown(payload["explanation"])
            elif payload["error"] and not payload["blocked"]:
                st.error(payload["error"])

            # ── SQL expander ─────────────────────────────────────────────────
            if payload["sql"]:
                with st.expander("🔍 SQL Used  (Explainability)", expanded=False):
                    st.code(payload["sql"], language="sql")

            # ── Chart ────────────────────────────────────────────────────────
            if payload["data"] and payload["chart_config"]:
                render_chart(payload["chart_config"], payload["data"])

            # ── Data table ───────────────────────────────────────────────────
            if payload["data"]:
                with st.expander(
                    f"📋 Raw Data  ({len(payload['data'])} rows)", expanded=False
                ):
                    st.dataframe(
                        pd.DataFrame(payload["data"]),
                        use_container_width=True, hide_index=True
                    )

            # ── Safety block ─────────────────────────────────────────────────
            if payload.get("blocked"):
                st.error(f"🛡️ Safety Block: {payload['error']}")

            # ── Timing ───────────────────────────────────────────────────────
            if payload["elapsed_seconds"]:
                st.caption(f"⏱ Response time: {payload['elapsed_seconds']}s")

        # Store assistant message with full payload for history replay
        st.session_state["messages"].append({
            "role":    "assistant",
            "content": payload.get("explanation", payload.get("error", "")),
            "payload": payload,
        })


if __name__ == '__main__':
    main_ui()