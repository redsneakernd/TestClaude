"""
Multi-page Streamlit app backed by Excel datasources.
Run: streamlit run app.py
"""

from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

DEFAULT_DATA_PATH   = Path(__file__).parent / "data" / "sample_sales.xlsx"
CHURCH_DIR_PATH     = Path(__file__).parent / "data" / "church_directory.xlsx"

st.set_page_config(page_title="Dashboard", page_icon="📊", layout="wide")

# ── Top-level page selector ───────────────────────────────────────────────────
page = st.sidebar.radio(
    "Navigate",
    ["📊 Sales Dashboard", "⛪ Church Directory"],
    label_visibility="collapsed",
)

# ══════════════════════════════════════════════════════════════════════════════
# PAGE 1 — SALES DASHBOARD
# ══════════════════════════════════════════════════════════════════════════════
if page == "📊 Sales Dashboard":
    st.title("📊 Sales Analytics Dashboard")

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

        if "Date" in df_raw.columns:
            df_raw["Date"] = pd.to_datetime(df_raw["Date"])

        st.divider()
        st.header("Filters")

        regions = sorted(df_raw["Region"].unique()) if "Region" in df_raw.columns else []
        selected_regions = st.multiselect("Region", regions, default=regions)

        products = sorted(df_raw["Product"].unique()) if "Product" in df_raw.columns else []
        selected_products = st.multiselect("Product", products, default=products)

    df = df_raw.copy()
    if selected_regions:
        df = df[df["Region"].isin(selected_regions)]
    if selected_products:
        df = df[df["Product"].isin(selected_products)]

    if df.empty:
        st.warning("No data matches the selected filters.")
        st.stop()

    tab_overview, tab_charts, tab_data = st.tabs(["Overview", "Charts", "Data"])

    with tab_overview:
        total_revenue = df["Revenue"].sum() if "Revenue" in df.columns else 0
        total_units   = df["Units Sold"].sum() if "Units Sold" in df.columns else 0
        total_profit  = df["Profit"].sum() if "Profit" in df.columns else 0
        top_product   = (
            df.groupby("Product")["Revenue"].sum().idxmax()
            if "Product" in df.columns and "Revenue" in df.columns else "N/A"
        )
        top_region = (
            df.groupby("Region")["Revenue"].sum().idxmax()
            if "Region" in df.columns and "Revenue" in df.columns else "N/A"
        )

        col1, col2, col3, col4, col5 = st.columns(5)
        col1.metric("Total Revenue", f"${total_revenue:,.0f}")
        col2.metric("Total Profit",  f"${total_profit:,.0f}")
        col3.metric("Units Sold",    f"{total_units:,}")
        col4.metric("Top Product",   top_product)
        col5.metric("Top Region",    top_region)

        st.divider()
        st.subheader("Filtered Data Preview")
        st.dataframe(df.head(50), use_container_width=True)

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
                    .sort_values(ascending=False).reset_index()
                )
                fig_prod = px.bar(
                    product_rev, x="Revenue", y="Product",
                    title="Revenue by Product",
                    labels={"Revenue": "Revenue ($)"},
                    orientation="h", color="Product",
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

    with tab_data:
        st.subheader(f"Full Dataset ({len(df):,} rows)")
        st.dataframe(df, use_container_width=True)
        csv = df.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="Download as CSV", data=csv,
            file_name="sales_data_filtered.csv", mime="text/csv",
        )


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 2 — CHURCH DIRECTORY
# ══════════════════════════════════════════════════════════════════════════════
else:
    st.title("⛪ Assembly of God Church Directory")
    st.caption("2023–24 Directory of Congregations · The Fig Tree · WA · ID · MT · OR · WY")

    if not CHURCH_DIR_PATH.exists():
        st.error("Church directory not found. Run `python3 church_directory.py` to generate it.")
        st.stop()

    cd = pd.read_excel(CHURCH_DIR_PATH)

    # ── Sidebar filters ───────────────────────────────────────────────────
    with st.sidebar:
        st.header("Filters")

        all_states   = sorted(cd["State"].dropna().unique())
        sel_states   = st.multiselect("State", all_states, default=all_states)

        all_regions  = sorted(cd["Region"].dropna().unique())
        sel_regions  = st.multiselect("Region / District", all_regions, default=all_regions)

        search_text  = st.text_input("🔍 Search (name, city, pastor)", "")

    # Apply filters
    filt = cd.copy()
    if sel_states:
        filt = filt[filt["State"].isin(sel_states)]
    if sel_regions:
        filt = filt[filt["Region"].isin(sel_regions)]
    if search_text:
        mask = (
            filt["Name"].str.contains(search_text, case=False, na=False) |
            filt["City"].str.contains(search_text, case=False, na=False) |
            filt["Pastor"].str.contains(search_text, case=False, na=False)
        )
        filt = filt[mask]

    # ── Summary metrics ───────────────────────────────────────────────────
    col1, col2, col3 = st.columns(3)
    col1.metric("Churches Shown",    f"{len(filt):,}")
    col2.metric("States Represented", filt["State"].nunique())
    col3.metric("Total in Directory", f"{len(cd):,}")

    st.divider()

    # ── Charts ────────────────────────────────────────────────────────────
    tab_map, tab_charts, tab_list = st.tabs(["📋 Directory", "📈 Charts", "⬇️ Export"])

    with tab_map:
        st.subheader(f"Showing {len(filt):,} churches")

        # Render each church as a clean card-style row
        for _, row in filt.iterrows():
            with st.container():
                c1, c2, c3 = st.columns([3, 2, 2])
                with c1:
                    st.markdown(f"**{row['Name']}**")
                    addr_parts = [str(row['Address']), str(row['City']), str(row['State']), str(row['Zip'])]
                    st.caption(" · ".join(p for p in addr_parts if p and p != "nan"))
                with c2:
                    if row["Pastor"] and str(row["Pastor"]) != "nan":
                        st.markdown(f"👤 {row['Pastor']}")
                    if row["Phone"] and str(row["Phone"]) != "nan":
                        st.markdown(f"📞 {row['Phone']}")
                with c3:
                    if row["Email"] and str(row["Email"]) != "nan":
                        st.markdown(f"✉️ {row['Email']}")
                    if row["Website"] and str(row["Website"]) != "nan":
                        st.markdown(f"🌐 [{row['Website']}](https://{row['Website']})")
                st.divider()

    with tab_charts:
        col_l, col_r = st.columns(2)

        with col_l:
            by_state = filt.groupby("State").size().reset_index(name="Churches")
            fig_state = px.bar(
                by_state.sort_values("Churches", ascending=False),
                x="State", y="Churches",
                title="Churches by State",
                color="State",
            )
            st.plotly_chart(fig_state, use_container_width=True)

        with col_r:
            by_region = filt.groupby("Region").size().reset_index(name="Churches")
            fig_region = px.bar(
                by_region.sort_values("Churches", ascending=False),
                x="Churches", y="Region",
                title="Churches by Region / District",
                orientation="h",
                color="Region",
            )
            fig_region.update_layout(showlegend=False, height=500)
            st.plotly_chart(fig_region, use_container_width=True)

        fig_pie = px.pie(
            by_state, names="State", values="Churches",
            title="Distribution by State",
        )
        st.plotly_chart(fig_pie, use_container_width=True)

    with tab_list:
        st.subheader("Full Filtered Directory")
        st.dataframe(filt, use_container_width=True)
        csv = filt.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="⬇️ Download as CSV",
            data=csv,
            file_name="church_directory_filtered.csv",
            mime="text/csv",
        )
