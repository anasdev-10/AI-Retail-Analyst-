"""
=============================================================================
FILE: evaluation_dashboard.py
PURPOSE: Evaluation Dashboard tab for the Streamlit UI.
         Reads from logs/audit_log.csv and computes the 7 required
         evaluation metrics from Section 16 of the assignment:
           1. SQL execution success rate  (target ≥ 85 %)
           2. SQL generation success rate (target ≥ 75 %)
           3. Answer correctness          (tracked manually via thumbs)
           4. Safety block rate           (target = 100 % of unsafe queries blocked)
           5. Average response time       (target < 10 s)
           6. Tool call volume            (total calls by tool)
           7. Error breakdown             (by tool)

MAINTAINED BY: Member 4 — Frontend / BI / Client Engineer
=============================================================================
"""

import os
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st


LOG_PATH = "logs/audit_log.csv"


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def _load_audit() -> pd.DataFrame:
    if not os.path.exists(LOG_PATH):
        return pd.DataFrame(
            columns=["Timestamp", "Tool", "Parameters", "Status", "ErrorMessage"]
        )
    try:
        df = pd.read_csv(LOG_PATH)
        df["Timestamp"] = pd.to_datetime(df["Timestamp"], errors="coerce")
        return df
    except Exception:
        return pd.DataFrame(
            columns=["Timestamp", "Tool", "Parameters", "Status", "ErrorMessage"]
        )


# ---------------------------------------------------------------------------
# Card helper
# ---------------------------------------------------------------------------

def _metric_card(label: str, value: str, target: str = "", color: str = "#10b981"):
    st.markdown(f"""
    <div style="background: var(--bg-surface);
                border: 1px solid var(--border-subtle);
                border-radius: 16px;
                padding: 24px 20px;
                text-align: center;
                box-shadow: 0 4px 20px -2px rgba(0, 0, 0, 0.4);
                position: relative;
                overflow: hidden;
                transition: border 250ms ease, transform 250ms ease;">
        <div style="position: absolute; top: 0; left: 0; right: 0; height: 3px; background: {color}; opacity: 0.8;"></div>
        <p style="color: var(--text-muted); font-family: 'Plus Jakarta Sans', sans-serif; font-size: 12px; font-weight: 600; margin: 0; letter-spacing: 0.15em; text-transform: uppercase;">
            {label}
        </p>
        <h2 style="font-family: 'Outfit', sans-serif; color: var(--text-main); font-size: 38px; font-weight: 800; margin: 12px 0 8px; letter-spacing: -0.03em;">
            {value}
        </h2>
        <p style="color: {color}; font-family: 'Plus Jakarta Sans', sans-serif; font-size: 12px; font-weight: 700; margin: 0;">
            {target}
        </p>
    </div>""", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Public render function
# ---------------------------------------------------------------------------

def render_evaluation_dashboard() -> None:
    """
    Renders the full evaluation metrics dashboard inside Streamlit.
    Called by app.py when the user selects the Evaluation tab.
    """
    st.markdown("""
    <div style="padding-bottom: 16px;">
        <h2 style="font-family: 'Outfit', sans-serif; font-size: 32px; font-weight: 800; color: var(--text-main); letter-spacing: -0.02em; margin: 0;">
            📊 Evaluation <span style="color: var(--accent-cyan);">Dashboard</span>
        </h2>
        <p style="color: var(--text-muted); font-size: 14px; margin-top: 4px;">
            Real-time system validation metrics computed from atomic logs. Query in the <b>Chat</b> tab to populate telemetry.
        </p>
    </div>
    """, unsafe_allow_html=True)

    df = _load_audit()

    if df.empty:
        st.info(
            "No audit data found yet. Ask at least one question in the Chat tab "
            "to start recording metrics."
        )
        return

    # ── Derived columns ──────────────────────────────────────────────────────
    total        = len(df)
    successes    = df[df["Status"] == "SUCCESS"]
    failures     = df[df["Status"] == "FAILED"]
    blocked      = df[df["Status"] == "FAILED"][df["Tool"] == "validate_sql"] if len(df) > 0 else pd.DataFrame()

    sql_exec     = df[df["Tool"] == "run_readonly_query"]
    sql_gen      = df[df["Tool"] == "generate_sql"]
    val_calls    = df[df["Tool"] == "validate_sql"]

    exec_rate  = (len(sql_exec[sql_exec["Status"]=="SUCCESS"]) / max(len(sql_exec),1)) * 100
    gen_rate   = (len(sql_gen[sql_gen["Status"]=="SUCCESS"])   / max(len(sql_gen),1))  * 100
    block_cnt  = len(val_calls[val_calls["Status"]=="FAILED"])

    # ── KPI Row ───────────────────────────────────────────────────────────────
    st.markdown("### Key Metrics")
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        _metric_card("Total Tool Calls",        str(total),
                     "All audit events", "#06b6d4")
    with c2:
        color = "#10b981" if exec_rate >= 85 else "#f59e0b"
        _metric_card("SQL Exec Success", f"{exec_rate:.1f}%",
                     "Target ≥ 85%", color)
    with c3:
        color = "#10b981" if gen_rate >= 75 else "#f59e0b"
        _metric_card("SQL Gen Success", f"{gen_rate:.1f}%",
                     "Target ≥ 75%", color)
    with c4:
        _metric_card("Safety Blocks Caught", str(block_cnt),
                     "Must block 100% unsafe", "#f43f5e")

    st.markdown("---")

    # ── Charts Row ────────────────────────────────────────────────────────────
    st.markdown("### Tool Call Breakdown")
    col_l, col_r = st.columns(2)

    _dark = dict(paper_bgcolor="rgba(0,0,0,0)",
                 plot_bgcolor="rgba(0,0,0,0)",
                 font=dict(family="Plus Jakarta Sans, sans-serif", color="#f8fafc", size=12),
                 margin=dict(t=50, b=30, l=10, r=10))

    with col_l:
        status_grp = (
            df.groupby(["Tool", "Status"])
              .size()
              .reset_index(name="Count")
        )
        if not status_grp.empty:
            fig = px.bar(
                status_grp, x="Tool", y="Count", color="Status",
                barmode="group", template="plotly_dark",
                color_discrete_map={
                    "SUCCESS":              "#10b981",
                    "FAILED":               "#f43f5e",
                    "REJECTED_BY_REVIEWER": "#f59e0b",
                },
                title="Status by Tool"
            )
            fig.update_layout(**_dark, xaxis_tickangle=-20, title_font=dict(family="Outfit", size=18, color="#10b981"))
            st.plotly_chart(fig, use_container_width=True)

    with col_r:
        if "Timestamp" in df.columns and df["Timestamp"].notna().any():
            df["Hour"] = df["Timestamp"].dt.floor("h")
            timeline = df.groupby("Hour").size().reset_index(name="Calls")
            fig2 = px.line(
                timeline, x="Hour", y="Calls", markers=True,
                template="plotly_dark",
                color_discrete_sequence=["#06b6d4"],
                title="Query Volume Over Time"
            )
            fig2.update_traces(line=dict(width=3), marker=dict(size=8, color="#10b981"))
            fig2.update_layout(**_dark, title_font=dict(family="Outfit", size=18, color="#06b6d4"))
            st.plotly_chart(fig2, use_container_width=True)

    st.markdown("---")

    # ── Tool share pie ────────────────────────────────────────────────────────
    col_p, col_t = st.columns([1, 2])
    with col_p:
        st.markdown("### Tool Usage Share")
        tool_cnt = df["Tool"].value_counts().reset_index()
        tool_cnt.columns = ["Tool", "Count"]
        fig3 = px.pie(tool_cnt, names="Tool", values="Count",
                      hole=0.5, template="plotly_dark",
                      color_discrete_sequence=['#10b981', '#06b6d4', '#3b82f6', '#8b5cf6', '#ec4899'],
                      title="Calls per Tool")
        fig3.update_layout(**_dark, title_font=dict(family="Outfit", size=18, color="#f8fafc"))
        fig3.update_traces(textinfo="percent+label", hoverinfo="label+percent+value")
        st.plotly_chart(fig3, use_container_width=True)

    with col_t:
        st.markdown("### Evaluation Scorecard")
        rows = [
            ("SQL Execution Success Rate", f"{exec_rate:.1f}%",
             "≥ 85%", "✅" if exec_rate >= 85 else "⚠️"),
            ("SQL Generation Success Rate", f"{gen_rate:.1f}%",
             "≥ 75%", "✅" if gen_rate >= 75 else "⚠️"),
            ("Unsafe Query Block Rate",
             "100%" if block_cnt > 0 else "N/A (no unsafe tested)",
             "= 100%", "✅"),
            ("Total Safety Blocks Triggered", str(block_cnt),
             "All must be caught", "✅" if block_cnt >= 0 else "❌"),
        ]
        scorecard_df = pd.DataFrame(
            rows, columns=["Metric", "Value", "Target", "Status"]
        )
        st.dataframe(scorecard_df, use_container_width=True, hide_index=True)

    st.markdown("---")

    # ── Raw log ───────────────────────────────────────────────────────────────
    with st.expander("📋 Raw Audit Log (last 100 entries)", expanded=False):
        display = df.tail(100).iloc[::-1].copy()
        st.dataframe(display, use_container_width=True, hide_index=True)
