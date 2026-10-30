"""AWS Cost Optimization Toolkit — Streamlit dashboard.

Dark-themed FinOps dashboard. Original UI, capabilities inspired by (not copied
from) the AWS Cost Optimization Hub. Runs entirely offline on synthetic data.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# Ensure src is importable when run via `streamlit run app/dashboard.py`.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from costtk.engine.engine import RecommendationEngine  # noqa: E402
from costtk.models import RecommendationStatus  # noqa: E402
from costtk.providers.sample import SyntheticProvider  # noqa: E402

SIMULATION_LABEL = "SIMULATED AWS ENVIRONMENT — ESTIMATED SAVINGS, NOT REALIZED CUSTOMER RESULTS"

# ---- Page config + dark theme -----------------------------------------------
st.set_page_config(
    page_title="AWS Cost Optimization Toolkit",
    page_icon="💸",
    layout="wide",
    initial_sidebar_state="expanded",
)

_CSS = """
<style>
  .stApp { background: #0e1117; }
  .sim-label {
    background: #1f2937; color: #fbbf24; font-weight: 700;
    padding: 12px 16px; border-radius: 8px; border: 1px solid #fbbf24;
    text-align: center; letter-spacing: 0.03em; margin-bottom: 16px;
  }
  div[data-testid="stMetric"] {
    background: #161b22; border: 1px solid #30363d; border-radius: 8px;
    padding: 12px 16px;
  }
  div[data-testid="stMetricValue"] { font-size: 1.6rem; font-weight: 700; }
</style>
"""
st.markdown(_CSS, unsafe_allow_html=True)


@st.cache_resource
def load_result():
    provider = SyntheticProvider(seed=42)
    return RecommendationEngine(provider).analyze()


result = load_result()
recs = result.recommendations

# ---- Build dataframe ---------------------------------------------------------
rows = []
for r in recs:
    rows.append(
        {
            "Action": r.action.value,
            "Resource Type": r.resource_type.value,
            "Resource ID": r.resource_id,
            "Account": r.account_id,
            "Region": r.region,
            "Current Cost": r.current_monthly_cost,
            "Projected Cost": r.projected_monthly_cost,
            "Gross Savings": r.gross_savings,
            "Net Savings": r.net_savings,
            "Savings %": r.savings_percentage,
            "Effort": r.effort.value,
            "Risk": r.risk.value,
            "Restart": "Yes" if r.restart_required else "No",
            "Rollback": "Yes" if r.rollback_possible else "No",
            "Status": r.status.value,
            "Classification": r.classification.value,
            "Confidence": r.evidence_confidence,
            "Notes": r.notes,
        }
    )
df = pd.DataFrame(rows)

# Environment isn't directly on Recommendation model; derive from resource.
# (engine keeps resource_type but not environment — map via resource_id lookup.)
env_map = {r.resource_id: r.environment for r in result.resources}
df["Environment"] = df["Resource ID"].map(env_map).fillna("prod")


# ---- Sidebar filters ---------------------------------------------------------
st.sidebar.header("Filters")
accounts = st.sidebar.multiselect("AWS Account", sorted(df["Account"].unique()))
regions = st.sidebar.multiselect("Region", sorted(df["Region"].unique()))
envs = st.sidebar.multiselect("Environment", sorted(df["Environment"].unique()))
rtypes = st.sidebar.multiselect("Resource Type", sorted(df["Resource Type"].unique()))
actions = st.sidebar.multiselect("Optimization Action", sorted(df["Action"].unique()))
efforts = st.sidebar.multiselect("Effort", sorted(df["Effort"].unique()))
risks = st.sidebar.multiselect("Risk", sorted(df["Risk"].unique()))
restart = st.sidebar.selectbox("Restart Required", ["Any", "Yes", "No"])
rollback = st.sidebar.selectbox("Rollback Possible", ["Any", "Yes", "No"])
statuses = st.sidebar.multiselect("Recommendation Status", sorted(df["Status"].unique()))
min_savings = st.sidebar.slider("Min Monthly Savings ($)", 0.0, 200.0, 0.0, 5.0)

view = df
if accounts:
    view = view[view["Account"].isin(accounts)]
if regions:
    view = view[view["Region"].isin(regions)]
if envs:
    view = view[view["Environment"].isin(envs)]
if rtypes:
    view = view[view["Resource Type"].isin(rtypes)]
if actions:
    view = view[view["Action"].isin(actions)]
if efforts:
    view = view[view["Effort"].isin(efforts)]
if risks:
    view = view[view["Risk"].isin(risks)]
if restart != "Any":
    view = view[view["Restart"] == restart]
if rollback != "Any":
    view = view[view["Rollback"] == rollback]
if statuses:
    view = view[view["Status"].isin(statuses)]
view = view[view["Net Savings"] >= min_savings]

# ---- Header ------------------------------------------------------------------
st.markdown("# 💸 AWS Cost Optimization Toolkit")
st.markdown(f'<div class="sim-label">{SIMULATION_LABEL}</div>', unsafe_allow_html=True)

# ---- KPI row -----------------------------------------------------------------
metrics = [
    ("Total Resources", f"{len(result.resources)}"),
    ("Current Monthly Cost", f"${result.baseline_monthly_cost:,.0f}"),
    ("Projected Monthly Cost", f"${result.projected_monthly_cost:,.0f}"),
    ("Estimated Monthly Savings", f"${result.ledger.actionable:,.0f}"),
    ("Savings %", f"{result.savings_percentage:.1f}%"),
    ("Annualized Savings", f"${result.ledger.actionable * 12:,.0f}"),
    ("Recommendations", f"{len(view)}"),
    ("High-Risk Recs", f"{int((view['Risk'] == 'High').sum())}"),
]
for i in range(0, len(metrics), 4):
    cols = st.columns(4)
    for c, (label, val) in zip(cols, metrics[i : i + 4]):
        c.metric(label, val)

# ---- Before vs after + savings by category ----
st.subheader("Before vs After Monthly Cost")
col1, col2 = st.columns([1, 2])
with col1:
    c1 = go.Bar(
        x=["Current", "Optimized"],
        y=[result.baseline_monthly_cost, result.projected_monthly_cost],
        marker_color=["#ef4444", "#22c55e"],
        text=[f"${result.baseline_monthly_cost:,.0f}", f"${result.projected_monthly_cost:,.0f}"],
        textposition="auto",
    )
    fig1 = go.Figure(c1)
    fig1.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=10, r=10, t=10, b=10),
        height=360,
    )
    st.plotly_chart(fig1, use_container_width=True)

with col2:
    by_action = view.groupby("Action")["Net Savings"].sum().reset_index().sort_values(
        "Net Savings", ascending=False
    )
    fig2 = px.bar(
        by_action,
        x="Net Savings",
        y="Action",
        orientation="h",
        color="Net Savings",
        color_continuous_scale="Viridis",
        labels={"Net Savings": "Monthly Savings ($)"},
    )
    fig2.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        height=360,
        coloraxis_showscale=False,
        margin=dict(l=10, r=10, t=10, b=10),
    )
    st.plotly_chart(fig2, use_container_width=True)

# ---- Savings by account / resource type ----
st.subheader("Savings Distribution")
c3, c4 = st.columns(2)
with c3:
    by_acct = view.groupby("Account")["Net Savings"].sum().reset_index().sort_values(
        "Net Savings", ascending=True
    )
    fig3 = px.bar(
        by_acct, x="Net Savings", y="Account", orientation="h", color="Net Savings",
        color_continuous_scale="Blues",
    )
    fig3.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)",
                       plot_bgcolor="rgba(0,0,0,0)", height=340,
                       coloraxis_showscale=False, margin=dict(l=10, r=10, t=30, b=10))
    fig3.update_layout(title="Monthly Savings by Account")
    st.plotly_chart(fig3, use_container_width=True)

with c4:
    by_type = view.groupby("Resource Type")["Net Savings"].sum().reset_index().sort_values(
        "Net Savings", ascending=True
    )
    fig4 = px.bar(by_type, x="Net Savings", y="Resource Type", orientation="h",
                  color="Net Savings", color_continuous_scale="Greens")
    fig4.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)",
                       plot_bgcolor="rgba(0,0,0,0)", height=340,
                       coloraxis_showscale=False, margin=dict(l=10, r=10, t=30, b=10))
    fig4.update_layout(title="Monthly Savings by Resource Type")
    st.plotly_chart(fig4, use_container_width=True)

# ---- Top recommendations table ----
st.subheader("Top Optimization Recommendations")
top = view.sort_values("Net Savings", ascending=False).head(15)
fig5 = go.Figure(
    data=[
        go.Bar(
            x=top["Net Savings"],
            y=top["Resource ID"] + " · " + top["Action"],
            orientation="h",
            marker_color=["#f59e0b"] * len(top),
        )
    ]
)
fig5.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)",
                   plot_bgcolor="rgba(0,0,0,0)", height=420,
                   margin=dict(l=10, r=10, t=10, b=10),
                   xaxis_title="Net Monthly Savings ($)")
st.plotly_chart(fig5, use_container_width=True)

# ---- Searchable table + CSV export ----
st.subheader("Recommendation Table")
search = st.text_input("Search (resource, account, action…)", "")
table_view = view
if search:
    mask = table_view.apply(
        lambda row: row.astype(str).str.contains(search, case=False, na=False).any(), axis=1
    )
    table_view = table_view[mask]

st.dataframe(
    table_view.drop(columns=["Notes"])
    .sort_values("Net Savings", ascending=False),
    use_container_width=True,
    height=360,
)

csv_bytes = table_view.to_csv(index=False).encode("utf-8")
st.download_button(
    "⬇ Download CSV Report",
    data=csv_bytes,
    file_name="aws-cost-optimization-recommendations.csv",
    mime="text/csv",
)

st.caption(
    "Synthetic data · computed savings from documented pricing assumptions · "
    f"no AWS account accessed · {len(result.resources)} resources, "
    f"{len(recs)} recommendations"
)
