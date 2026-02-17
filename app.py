"""
Sales Analytics Dashboard — Streamlit app backed by an Excel datasource.
Run: streamlit run app.py
"""

from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

DEFAULT_DATA_PATH = Path(__file__).parent / "data" / "sample_sales.xlsx"

st.set_page_config(page_title="Sales Dashboard", page_icon="📊", layout="wide")
st.title("📊 Sales Analytics Dashboard")

# ── Sidebar: data source & filters ───────────────────────────────────────────
with st.sidebar:
    st.header("Data Source")
    uploaded = st.file_uploader("Upload an Excel file (.xlsx)", type=["xlsx"])

    if uploaded:
        df_raw = pd.read_excel(uploaded)
        st.success(f"Loaded {len(df_raw):,} rows from uploaded file.")
    elif DEFAULT_DATA_PATH.exists():
        df_raw = pd.read_excel(DEFAULT_DATA_PATH)
        st.info(f"Using sample data ({len(df_raw):,} rows).")
    else:
        st.error(
            "No data found. Run `python sample_data.py` to generate sample data, "
            "or upload an Excel file above."
        )
        st.stop()

    # Ensure Date column is datetime
    if "Date" in df_raw.columns:
        df_raw["Date"] = pd.to_datetime(df_raw["Date"])

    st.divider()
    st.header("Filters")

    regions = sorted(df_raw["Region"].unique()) if "Region" in df_raw.columns else []
    selected_regions = st.multiselect("Region", regions, default=regions)

    products = sorted(df_raw["Product"].unique()) if "Product" in df_raw.columns else []
    selected_products = st.multiselect("Product", products, default=products)

# Apply filters
df = df_raw.copy()
if selected_regions:
    df = df[df["Region"].isin(selected_regions)]
if selected_products:
    df = df[df["Product"].isin(selected_products)]

if df.empty:
    st.warning("No data matches the selected filters.")
    st.stop()

# ── Tabs ──────────────────────────────────────────────────────────────────────
tab_overview, tab_charts, tab_data = st.tabs(["Overview", "Charts", "Data"])

# ── Overview tab ──────────────────────────────────────────────────────────────
with tab_overview:
    total_revenue = df["Revenue"].sum() if "Revenue" in df.columns else 0
    total_units = df["Units Sold"].sum() if "Units Sold" in df.columns else 0
    total_profit = df["Profit"].sum() if "Profit" in df.columns else 0

    top_product = (
        df.groupby("Product")["Revenue"].sum().idxmax()
        if "Product" in df.columns and "Revenue" in df.columns
        else "N/A"
    )
    top_region = (
        df.groupby("Region")["Revenue"].sum().idxmax()
        if "Region" in df.columns and "Revenue" in df.columns
        else "N/A"
    )

    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Total Revenue", f"${total_revenue:,.0f}")
    col2.metric("Total Profit", f"${total_profit:,.0f}")
    col3.metric("Units Sold", f"{total_units:,}")
    col4.metric("Top Product", top_product)
    col5.metric("Top Region", top_region)

    st.divider()
    st.subheader("Filtered Data Preview")
    st.dataframe(df.head(50), use_container_width=True)

# ── Charts tab ────────────────────────────────────────────────────────────────
with tab_charts:
    if "Date" in df.columns and "Revenue" in df.columns:
        df["Month"] = df["Date"].dt.to_period("M").dt.to_timestamp()
        monthly = df.groupby("Month")["Revenue"].sum().reset_index()
        fig_line = px.line(
            monthly, x="Month", y="Revenue",
            title="Monthly Revenue",
            labels={"Revenue": "Revenue ($)", "Month": "Month"},
            markers=True,
        )
        st.plotly_chart(fig_line, use_container_width=True)

    col_left, col_right = st.columns(2)

    with col_left:
        if "Region" in df.columns and "Revenue" in df.columns:
            region_rev = df.groupby("Region")["Revenue"].sum().reset_index()
            fig_bar = px.bar(
                region_rev, x="Region", y="Revenue",
                title="Revenue by Region",
                labels={"Revenue": "Revenue ($)"},
                color="Region",
            )
            st.plotly_chart(fig_bar, use_container_width=True)

    with col_right:
        if "Product" in df.columns and "Revenue" in df.columns:
            product_rev = (
                df.groupby("Product")["Revenue"].sum()
                .sort_values(ascending=False)
                .reset_index()
            )
            fig_prod = px.bar(
                product_rev, x="Revenue", y="Product",
                title="Revenue by Product",
                labels={"Revenue": "Revenue ($)"},
                orientation="h",
                color="Product",
            )
            fig_prod.update_layout(showlegend=False)
            st.plotly_chart(fig_prod, use_container_width=True)

    if "Product" in df.columns and "Units Sold" in df.columns:
        units_by_product = df.groupby("Product")["Units Sold"].sum().reset_index()
        fig_pie = px.pie(
            units_by_product, names="Product", values="Units Sold",
            title="Units Sold by Product",
        )
        st.plotly_chart(fig_pie, use_container_width=True)

# ── Data tab ──────────────────────────────────────────────────────────────────
with tab_data:
    st.subheader(f"Full Dataset ({len(df):,} rows)")
    st.dataframe(df, use_container_width=True)

    csv = df.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="Download as CSV",
        data=csv,
        file_name="sales_data_filtered.csv",
        mime="text/csv",
    )
