"""
=============================================================================
FILE: chart_renderer.py
PURPOSE: Renders Plotly charts and KPI cards inside Streamlit based on
         the chart_config JSON returned by suggest_chart() / generate_chart_data().

SUPPORTED CHART TYPES:
    bar      → Vertical bar chart (categorical comparisons)
    line     → Line chart with markers (time-series trends)
    pie      → Pie chart (proportional breakdown, ≤ 7 slices)
    kpi_card → Large metric card (single-number KPIs)
    heatmap  → Heatmap (two categorical dimensions × metric)
    table    → Formatted Streamlit dataframe (fallback)

MAINTAINED BY: Member 4 — Frontend / BI / Client Engineer
=============================================================================
"""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st


# ---------------------------------------------------------------------------
# Shared colour palette and layout defaults
# ---------------------------------------------------------------------------
_PALETTE = ['#10b981', '#06b6d4', '#3b82f6', '#8b5cf6', '#ec4899', '#f59e0b']
_DARK_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(color="#f8fafc", family="Plus Jakarta Sans, sans-serif", size=12),
    title_font=dict(size=18, color="#10b981", family="Outfit, sans-serif"),
    margin=dict(t=50, b=30, l=10, r=10),
    xaxis=dict(gridcolor="rgba(255,255,255,0.05)", zeroline=False),
    yaxis=dict(gridcolor="rgba(255,255,255,0.05)", zeroline=False),
)


def render_chart(chart_config: dict, raw_data: list) -> None:
    """
    Main dispatcher.  Receives chart config (from suggest_chart) and the raw
    query result rows (list of dicts).  Dispatches to the correct renderer.

    Args:
        chart_config (dict): {"chart_type", "x_axis", "y_axis", "title", "reason"}
        raw_data     (list): list of dicts from run_readonly_query
    """
    if not raw_data:
        st.info("No data available to render a chart.")
        return

    chart_type = chart_config.get("chart_type", "table")
    title      = chart_config.get("title", "")
    x_col      = chart_config.get("x_axis")
    y_col      = chart_config.get("y_axis")
    reason     = chart_config.get("reason", "")

    df = _to_df(raw_data)

    # Show the reason as a small caption
    if reason:
        st.caption(f"📊 Chart logic: {reason}")

    if chart_type == "kpi_card":
        _render_kpi_card(title, y_col, df)
    elif chart_type == "bar":
        _render_bar(title, x_col, y_col, df)
    elif chart_type == "line":
        _render_line(title, x_col, y_col, df)
    elif chart_type == "pie":
        _render_pie(title, x_col, y_col, df)
    elif chart_type == "heatmap":
        _render_heatmap(title, x_col, y_col, df)
    else:
        _render_table(df)


# ---------------------------------------------------------------------------
# Individual chart renderers
# ---------------------------------------------------------------------------

def _render_kpi_card(title: str, value_col: str, df: pd.DataFrame) -> None:
    """Large KPI metric card — for single-number results."""
    val = df[value_col].iloc[0] if value_col and value_col in df.columns else df.iloc[0, 0]
    try:
        val_f = f"{float(val):,.2f}"
    except (ValueError, TypeError):
        val_f = str(val)

    st.markdown(f"""
    <div style="background: var(--bg-surface);
                border: 1px solid var(--border-accent);
                border-radius: 20px;
                padding: 40px 28px;
                text-align: center;
                margin: 16px 0;
                box-shadow: 0 8px 32px -4px rgba(0, 0, 0, 0.5), 0 0 0 1px var(--accent-glow);
                position: relative;
                overflow: hidden;">
        <div style="position: absolute; top: 0; left: 0; right: 0; height: 4px; background: var(--accent-gradient);"></div>
        <p style="color: var(--accent-cyan); font-family: 'Plus Jakarta Sans', sans-serif; font-size: 13px; font-weight: 700; margin: 0; letter-spacing: 0.2em; text-transform: uppercase;">
            {title}
        </p>
        <h1 style="font-family: 'Outfit', sans-serif; color: var(--text-main); font-size: 58px; font-weight: 800; margin: 16px 0 4px; letter-spacing: -0.03em;">
            {val_f}
        </h1>
    </div>""", unsafe_allow_html=True)


def _render_bar(title: str, x_col: str, y_col: str, df: pd.DataFrame) -> None:
    if not _cols_ok(x_col, y_col, df):
        _render_table(df)
        return

    df[y_col] = pd.to_numeric(df[y_col], errors="coerce")
    df = df.sort_values(y_col, ascending=False)

    # Horizontal bar when labels are long
    orientation = "h" if df[x_col].astype(str).str.len().mean() > 10 else "v"

    if orientation == "h":
        fig = px.bar(df, x=y_col, y=x_col, orientation="h",
                     title=title, color=y_col,
                     color_continuous_scale="Viridis",
                     template="plotly_dark")
        fig.update_layout(yaxis=dict(categoryorder="total ascending"))
    else:
        fig = px.bar(df, x=x_col, y=y_col, title=title, color=y_col,
                     color_continuous_scale="Viridis", template="plotly_dark")

    fig.update_layout(**_DARK_LAYOUT, showlegend=False,
                      coloraxis_showscale=False)
    st.plotly_chart(fig, use_container_width=True)


def _render_line(title: str, x_col: str, y_col: str, df: pd.DataFrame) -> None:
    if not _cols_ok(x_col, y_col, df):
        _render_table(df)
        return

    df[y_col] = pd.to_numeric(df[y_col], errors="coerce")
    fig = px.line(df, x=x_col, y=y_col, title=title,
                  markers=True, template="plotly_dark",
                  color_discrete_sequence=["#10b981"])
    fig.update_traces(line=dict(width=3), marker=dict(size=8, color="#06b6d4",
                      line=dict(width=2, color="#12141d")))
    fig.update_layout(**_DARK_LAYOUT)
    st.plotly_chart(fig, use_container_width=True)


def _render_pie(title: str, x_col: str, y_col: str, df: pd.DataFrame) -> None:
    if not _cols_ok(x_col, y_col, df):
        _render_table(df)
        return

    df[y_col] = pd.to_numeric(df[y_col], errors="coerce")
    # Cap at 7 slices, group rest as "Other"
    if len(df) > 7:
        top = df.nlargest(6, y_col)
        other_val = df[y_col].sum() - top[y_col].sum()
        other_row = pd.DataFrame({x_col: ["Other"], y_col: [other_val]})
        df = pd.concat([top, other_row], ignore_index=True)

    fig = px.pie(df, names=x_col, values=y_col, title=title,
                 template="plotly_dark",
                 color_discrete_sequence=_PALETTE,
                 hole=0.45)
    fig.update_traces(textinfo="percent+label",
                      marker=dict(line=dict(color="#12141d", width=2)))
    fig.update_layout(**_DARK_LAYOUT)
    st.plotly_chart(fig, use_container_width=True)


def _render_heatmap(title: str, x_col: str, y_col: str, df: pd.DataFrame) -> None:
    """Try to pivot data for a heatmap; fall back to table if shape is wrong."""
    if len(df.columns) >= 3:
        row_col = df.columns[0]
        col_col = df.columns[1]
        val_col = df.columns[2]
        try:
            df[val_col] = pd.to_numeric(df[val_col], errors="coerce")
            pivot = df.pivot_table(index=row_col, columns=col_col,
                                   values=val_col, aggfunc="sum")
            fig = px.imshow(pivot, title=title, template="plotly_dark",
                            color_continuous_scale="Viridis", aspect="auto")
            fig.update_layout(**_DARK_LAYOUT)
            st.plotly_chart(fig, use_container_width=True)
            return
        except Exception:
            pass
    _render_table(df)


def _render_table(df: pd.DataFrame) -> None:
    st.dataframe(df, use_container_width=True, hide_index=True)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _to_df(raw_data: list) -> pd.DataFrame:
    return pd.DataFrame(raw_data) if raw_data else pd.DataFrame()


def _cols_ok(x_col: str, y_col: str, df: pd.DataFrame) -> bool:
    return bool(x_col and y_col
                and x_col in df.columns
                and y_col in df.columns)
