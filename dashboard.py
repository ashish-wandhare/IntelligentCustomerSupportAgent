import os
from datetime import datetime

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
import streamlit as st
from streamlit_autorefresh import st_autorefresh

# =========================================================
# Configuration
# =========================================================

API_BASE_URL = os.getenv(
    "CUSTOMER_SUPPORT_API_URL",
    "http://127.0.0.1:8000",
)
REFRESH_SECONDS = 10

st.set_page_config(
    page_title="Support Intelligence | Operations",
    page_icon="🎫",
    layout="wide",
    initial_sidebar_state="expanded",
)

# =========================================================
# Enterprise styling
# =========================================================

st.markdown(
    """
    <style>
    @import url(
      'https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap'
    );

    .stApp {
        background: #F4F7FB;
        color: #17263C;
        font-family: 'Inter', sans-serif;
    }

    [data-testid="stSidebar"] {
        background: #111C2F;
        border-right: 1px solid #26364D;
    }

    [data-testid="stSidebar"] * {
        color: #E5EDF7;
    }

    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p {
        color: #B6C5D8;
    }

    .block-container {
        padding-top: 1.6rem;
        padding-bottom: 2rem;
        max-width: 1600px;
    }

    h1, h2, h3 {
        color: #17263C !important;
        letter-spacing: -0.5px;
    }

    .hero {
        background: linear-gradient(115deg, #111C2F, #1E3A5F);
        padding: 27px 30px;
        border-radius: 16px;
        margin-bottom: 22px;
        color: #FFFFFF;
        box-shadow: 0 5px 20px rgba(23, 38, 60, 0.10);
    }

    .hero-title {
        font-size: 27px;
        font-weight: 800;
        color: #FFFFFF;
        margin-bottom: 7px;
    }

    .hero-subtitle {
        color: #C3D2E4;
        font-size: 14px;
        line-height: 1.6;
    }

    .hero-status {
        display: inline-block;
        padding: 6px 11px;
        border-radius: 20px;
        background: rgba(16, 185, 129, 0.15);
        border: 1px solid rgba(110, 231, 183, 0.4);
        color: #A7F3D0;
        font-size: 11px;
        font-weight: 700;
        letter-spacing: 0.8px;
    }

    .section-label {
        font-size: 12px;
        font-weight: 800;
        color: #64748B;
        letter-spacing: 1.2px;
        margin: 12px 0 12px 0;
    }

    [data-testid="stMetric"] {
        background: #FFFFFF;
        border: 1px solid #E0E7F0;
        border-radius: 13px;
        padding: 17px 18px;
        box-shadow: 0 2px 8px rgba(23, 38, 60, 0.035);
    }

    [data-testid="stMetricLabel"] {
        color: #64748B !important;
        font-weight: 600;
        font-size: 13px;
    }

    [data-testid="stMetricValue"] {
        color: #17263C !important;
        font-weight: 800;
    }

    [data-testid="stMetricDelta"] {
        font-size: 12px;
    }

    [data-testid="stPlotlyChart"] {
        background: #FFFFFF;
        border: 1px solid #E0E7F0;
        border-radius: 13px;
        padding: 8px;
    }

    [data-testid="stDataFrame"] {
        border: 1px solid #E0E7F0;
        border-radius: 12px;
        overflow: hidden;
    }

    div.stButton > button {
        border-radius: 9px;
        font-weight: 600;
        min-height: 42px;
    }

    hr {
        border-color: #E0E7F0;
    }

    .footer {
        color: #8190A5;
        font-size: 11px;
        text-align: center;
        padding-top: 22px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# =========================================================
# Data access
# =========================================================


@st.cache_data(ttl=REFRESH_SECONDS, show_spinner=False)
def fetch_tickets(api_url: str) -> list[dict]:
    response = requests.get(
        f"{api_url.rstrip('/')}/tickets",
        params={"limit": 1000},
        timeout=10,
    )
    response.raise_for_status()
    return response.json().get("tickets", [])


def normalise_data(tickets: list[dict]) -> pd.DataFrame:
    df = pd.DataFrame(tickets)

    defaults = {
        "ticket_id": "",
        "subject": "",
        "category": "unknown",
        "priority": "unknown",
        "status": "unknown",
        "requires_human_approval": False,
        "created_at": None,
        "updated_at": None,
        "escalation_reason": "",
        "resolution": "",
    }

    for column, default in defaults.items():
        if column not in df.columns:
            df[column] = default

    for column in ("status", "category", "priority"):
        df[column] = (
            df[column]
            .fillna("unknown")
            .astype(str)
            .str.strip()
            .str.lower()
        )

    df["requires_human_approval"] = (
        df["requires_human_approval"]
        .fillna(False)
        .astype(bool)
    )

    return df


def section_title(title: str, subtitle: str = "") -> None:
    st.markdown(f"### {title}")
    if subtitle:
        st.caption(subtitle)


# =========================================================
# Sidebar
# =========================================================

with st.sidebar:
    st.markdown("## 🎫 Support Intelligence")
    st.caption("AI OPERATIONS PLATFORM")
    st.divider()

    st.markdown("### Monitoring")
    st.markdown("Operational overview")
    st.markdown("Ticket analytics")
    st.markdown("Human review queue")
    st.markdown("Ticket explorer")

    st.divider()
    st.markdown("### Connection")

    st.caption("FastAPI backend")
    st.code(API_BASE_URL, language=None)

    auto_refresh = st.toggle("Auto-refresh", value=True)

    if st.button("Refresh data now", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

    st.divider()
    st.caption("Intelligent Customer Support Agent")
    st.caption("Local development environment")

# =========================================================
# Header
# =========================================================

st.markdown(
    """
    <div class="hero">
      <div style="display:flex; justify-content:space-between;
                  align-items:flex-start; gap:20px; flex-wrap:wrap;">
        <div>
          <div class="hero-title">AI Support Operations</div>
          <div class="hero-subtitle">
            Real-time ticket intelligence, workflow monitoring,
            and human-in-the-loop oversight.
          </div>
        </div>
        <div class="hero-status">● MONITORING ACTIVE</div>
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# =========================================================
# Fetch data
# =========================================================

try:
    tickets = fetch_tickets(API_BASE_URL)
except requests.RequestException as exc:
    st.error("Unable to connect to the FastAPI backend.")
    st.markdown(
        """
        Start your API in a separate terminal:

        ```powershell
        python -m uvicorn src.customer_support.api:app --reload
        ```
        """
    )
    st.caption(f"Connection detail: {exc}")
    st.stop()

if not tickets:
    st.info("No tickets are available yet. Submit a ticket to start monitoring.")
    if auto_refresh:
        st_autorefresh(
            interval=REFRESH_SECONDS * 1000,
            key="support_refresh_empty",
        )
    st.stop()

df = normalise_data(tickets)

# =========================================================
# Filters
# =========================================================

with st.expander("Filter dashboard data", expanded=False):
    f1, f2, f3 = st.columns(3)

    with f1:
        statuses = st.multiselect(
            "Ticket status",
            sorted(df["status"].unique()),
            default=sorted(df["status"].unique()),
        )

    with f2:
        categories = st.multiselect(
            "Ticket category",
            sorted(df["category"].unique()),
            default=sorted(df["category"].unique()),
        )

    with f3:
        priorities = st.multiselect(
            "Ticket priority",
            sorted(df["priority"].unique()),
            default=sorted(df["priority"].unique()),
        )

filtered = df[
    df["status"].isin(statuses)
    & df["category"].isin(categories)
    & df["priority"].isin(priorities)
].copy()

# =========================================================
# KPI cards
# =========================================================

st.markdown(
    '<div class="section-label">OPERATIONAL OVERVIEW</div>',
    unsafe_allow_html=True,
)

total = len(filtered)
resolved = int((filtered["status"] == "resolved").sum())
failed = int((filtered["status"] == "failed").sum())

processing = int(
    filtered["status"]
    .isin(["processing", "in_progress"])
    .sum()
)

waiting_review = int(
    (
        filtered["requires_human_approval"]
        & ~filtered["status"].isin(["resolved", "failed"])
    ).sum()
)

k1, k2, k3, k4, k5 = st.columns(5)

k1.metric("Total Tickets", f"{total:,}", help="Tickets matching current filters")
k2.metric("Resolved", f"{resolved:,}")
k3.metric("Processing", f"{processing:,}")
k4.metric("Failed", f"{failed:,}")
k5.metric("Awaiting Review", f"{waiting_review:,}")

# =========================================================
# Charts
# =========================================================

st.markdown(
    '<div class="section-label">TICKET ANALYTICS</div>',
    unsafe_allow_html=True,
)

left, right = st.columns(2)

chart_layout = dict(
    paper_bgcolor="#FFFFFF",
    plot_bgcolor="#FFFFFF",
    font=dict(family="Inter, sans-serif", color="#526178", size=12),
    margin=dict(l=20, r=20, t=55, b=25),
    title_font=dict(size=16, color="#17263C"),
    legend=dict(font=dict(size=11)),
)

with left:
    status_counts = (
        filtered["status"]
        .value_counts()
        .rename_axis("Status")
        .reset_index(name="Tickets")
    )

    fig_status = px.pie(
        status_counts,
        names="Status",
        values="Tickets",
        hole=0.68,
        title="Ticket Status Distribution",
        color_discrete_sequence=[
            "#2563EB",
            "#0D9488",
            "#D97706",
            "#DC4C64",
            "#7C3AED",
            "#94A3B8",
        ],
    )
    fig_status.update_traces(
        textposition="inside",
        textinfo="percent",
        marker=dict(line=dict(color="#FFFFFF", width=3)),
        hovertemplate="%{label}: %{value}<extra></extra>",
    )
    fig_status.update_layout(**chart_layout)
    st.plotly_chart(fig_status, use_container_width=True)

with right:
    category_counts = (
        filtered["category"]
        .value_counts()
        .rename_axis("Category")
        .reset_index(name="Tickets")
    )

    fig_category = px.bar(
        category_counts,
        x="Category",
        y="Tickets",
        title="Tickets by Category",
        color="Tickets",
        color_continuous_scale=["#C7D9F5", "#2457A7"],
    )
    fig_category.update_layout(
        **chart_layout,
        coloraxis_showscale=False,
        xaxis_title="",
        yaxis_title="Number of tickets",
        xaxis=dict(showgrid=False),
        yaxis=dict(gridcolor="#EDF1F6", rangemode="tozero"),
    )
    fig_category.update_traces(
        marker_line_width=0,
        hovertemplate="%{x}: %{y}<extra></extra>",
    )
    st.plotly_chart(fig_category, use_container_width=True)

priority_col, summary_col = st.columns([1.2, 1])

with priority_col:
    priority_counts = (
        filtered["priority"]
        .value_counts()
        .rename_axis("Priority")
        .reset_index(name="Tickets")
    )

    fig_priority = px.bar(
        priority_counts,
        x="Priority",
        y="Tickets",
        color="Priority",
        title="Priority Distribution",
        color_discrete_map={
            "critical": "#B91C1C",
            "high": "#EA580C",
            "medium": "#D97706",
            "low": "#0D9488",
            "unknown": "#94A3B8",
        },
    )
    fig_priority.update_layout(
        **chart_layout,
        showlegend=False,
        xaxis_title="",
        yaxis_title="Number of tickets",
        xaxis=dict(showgrid=False),
        yaxis=dict(gridcolor="#EDF1F6", rangemode="tozero"),
    )
    fig_priority.update_traces(
        marker_line_width=0,
        hovertemplate="%{x}: %{y}<extra></extra>",
    )
    st.plotly_chart(fig_priority, use_container_width=True)

with summary_col:
    section_title("Workflow Health", "Current distribution of ticket states")

    status_counts_map = filtered["status"].value_counts().to_dict()

    for state, count in sorted(status_counts_map.items()):
        share = count / max(total, 1)
        st.markdown(f"**{state.replace('_', ' ').title()}**")
        st.progress(share, text=f"{count:,} ticket(s) · {share:.0%}")

    st.caption(
        "Workflow health reflects the tickets returned by the API "
        "and the filters selected above."
    )

# =========================================================
# Human review queue
# =========================================================

st.markdown(
    '<div class="section-label">HUMAN-IN-THE-LOOP OVERSIGHT</div>',
    unsafe_allow_html=True,
)

review_df = filtered[
    filtered["requires_human_approval"]
    & ~filtered["status"].isin(["resolved", "failed"])
].copy()

if review_df.empty:
    st.success("Review queue clear — no matching tickets await human review.")
else:
    st.warning(f"{len(review_df)} ticket(s) need human review.")

    review_columns = [
        col for col in (
            "ticket_id",
            "subject",
            "category",
            "priority",
            "status",
            "escalation_reason",
            "updated_at",
        )
        if col in review_df.columns
    ]

    st.dataframe(
        review_df[review_columns],
        use_container_width=True,
        hide_index=True,
    )

# =========================================================
# Ticket explorer
# =========================================================

st.markdown(
    '<div class="section-label">TICKET EXPLORER</div>',
    unsafe_allow_html=True,
)

search_text = st.text_input(
    "Search tickets",
    placeholder="Search by ticket ID or subject...",
)

explorer_df = filtered.copy()

if search_text.strip():
    query = search_text.strip()
    mask = (
        explorer_df["ticket_id"].astype(str).str.contains(
            query, case=False, na=False
        )
        | explorer_df["subject"].astype(str).str.contains(
            query, case=False, na=False
        )
    )
    explorer_df = explorer_df[mask]

if "updated_at" in explorer_df.columns:
    explorer_df = explorer_df.sort_values(
        "updated_at",
        ascending=False,
        na_position="last",
    )

table_columns = [
    col for col in (
        "ticket_id",
        "subject",
        "category",
        "priority",
        "status",
        "requires_human_approval",
        "created_at",
        "updated_at",
    )
    if col in explorer_df.columns
]

st.caption(f"{len(explorer_df):,} ticket(s) displayed")

st.dataframe(
    explorer_df[table_columns],
    use_container_width=True,
    hide_index=True,
    height=380,
)

# =========================================================
# Footer and refresh
# =========================================================

st.markdown("---")

last_updated = datetime.now().astimezone().strftime("%d %b %Y, %I:%M:%S %p")

st.markdown(
    f"""
    <div class="footer">
      SUPPORT INTELLIGENCE · AI OPERATIONS<br>
      Dashboard rendered: {last_updated} ·
      Refresh interval: {REFRESH_SECONDS}s ·
      Source: FastAPI
    </div>
    """,
    unsafe_allow_html=True,
)

if auto_refresh:
    st_autorefresh(
        interval=REFRESH_SECONDS * 1000,
        key="support_dashboard_refresh",
    )