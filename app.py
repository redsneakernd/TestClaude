"""
Multi-page Streamlit app backed by Excel datasources.
Run: streamlit run app.py
"""

from pathlib import Path

import pandas as pd
import plotly.express as px
import requests
import streamlit as st

DEFAULT_DATA_PATH   = Path(__file__).parent / "data" / "sample_sales.xlsx"
CHURCH_DIR_PATH     = Path(__file__).parent / "data" / "church_directory.xlsx"

st.set_page_config(page_title="Dashboard", page_icon="📊", layout="wide")

# ── Top-level page selector ───────────────────────────────────────────────────
page = st.sidebar.radio(
    "Navigate",
    ["📊 Sales Dashboard", "⛪ Church Directory", "📸 Find a Photographer"],
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

    # ── Summary metrics + top-level download ─────────────────────────────
    col1, col2, col3, col4 = st.columns([2, 2, 2, 3])
    col1.metric("Churches Shown",     f"{len(filt):,}")
    col2.metric("States Represented", filt["State"].nunique())
    col3.metric("Total in Directory", f"{len(cd):,}")
    with col4:
        csv_all = filt.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="⬇️ Download Full Directory as CSV",
            data=csv_all,
            file_name="church_directory.csv",
            mime="text/csv",
            use_container_width=True,
        )

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


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 3 — FIND A PHOTOGRAPHER
# ══════════════════════════════════════════════════════════════════════════════
elif page == "📸 Find a Photographer":
    FAP_BASE = "https://zmddzjnhmgfsrdkhwvxc.supabase.co/functions/v1/public-api"

    st.title("📸 Find a Photographer")

    # API key — prefer st.secrets, fall back to sidebar input
    api_key = st.secrets.get("FAP_API_KEY", "") if hasattr(st.secrets, "get") else ""
    if not api_key:
        if "fap_api_key" not in st.session_state:
            st.session_state.fap_api_key = ""
        with st.sidebar:
            st.header("API Configuration")
            entered = st.text_input(
                "FindAPhotographer API Key",
                value=st.session_state.fap_api_key,
                type="password",
                placeholder="sk_live_...",
            )
            if entered:
                st.session_state.fap_api_key = entered
        api_key = st.session_state.fap_api_key

    if not api_key:
        st.info(
            "Enter your FindAPhotographer API key in the sidebar to get started.  \n"
            "You can also set `FAP_API_KEY` in `.streamlit/secrets.toml` to skip this step."
        )
        st.stop()

    fap_headers = {"x-api-key": api_key}

    @st.cache_data(ttl=3600, show_spinner=False)
    def load_specialties(_key: str) -> list[str]:
        try:
            r = requests.get(f"{FAP_BASE}/v1/specialties", headers={"x-api-key": _key}, timeout=10)
            if r.ok:
                raw = r.json()
                items = raw if isinstance(raw, list) else raw.get("data", [])
                return [i if isinstance(i, str) else i.get("name", str(i)) for i in items]
        except Exception:
            pass
        return []

    def search_photographers(city: str, state: str, limit: int = 100) -> tuple[list, int]:
        params: dict = {"limit": limit}
        if city:
            params["city"] = city
        if state:
            params["state"] = state
        try:
            r = requests.get(
                f"{FAP_BASE}/v1/photographers",
                headers=fap_headers,
                params=params,
                timeout=15,
            )
            if r.ok:
                raw = r.json()
                if isinstance(raw, list):
                    return raw, len(raw)
                return raw.get("data", []), raw.get("total", 0)
            st.error(f"API error {r.status_code}: {r.text[:200]}")
        except requests.exceptions.RequestException as exc:
            st.error(f"Request failed: {exc}")
        return [], 0

    def _num(p: dict, *fields) -> float | None:
        for f in fields:
            if f in p:
                try:
                    return float(p[f])
                except (ValueError, TypeError):
                    pass
        return None

    def get_rating(p: dict) -> float:
        v = _num(p, "rating", "review_rating", "avg_rating", "average_rating", "score")
        return v or 0.0

    def get_price(p: dict) -> float | None:
        return _num(p, "min_price", "price_from", "starting_price", "rate", "hourly_rate")

    # ── Sidebar search form ───────────────────────────────────────────────────
    with st.sidebar:
        st.header("Search Filters")
        city_input  = st.text_input("City", "")
        state_input = st.text_input("State (abbrev.)", "")

        specialty_options = load_specialties(api_key)
        sel_specialties = (
            st.multiselect("Specialty", specialty_options)
            if specialty_options
            else st.multiselect("Specialty", [], placeholder="Loading…")
        )

        budget_min, budget_max = st.slider(
            "Budget range ($)", min_value=0, max_value=10_000,
            value=(0, 5_000), step=100,
        )

        search_clicked = st.button("Search", type="primary", use_container_width=True)

    # ── Results ───────────────────────────────────────────────────────────────
    if not search_clicked:
        st.markdown(
            "Use the sidebar to filter by **city**, **state**, **specialty**, and **budget**, "
            "then click **Search**."
        )
        st.stop()

    with st.spinner("Searching…"):
        results, total_api = search_photographers(city_input.strip(), state_input.strip())

    if not results:
        st.warning("No photographers found. Try a different city or state.")
        st.stop()

    # Client-side specialty filter
    if sel_specialties:
        def matches_specialty(p: dict) -> bool:
            raw = p.get("specialties", p.get("specialty", ""))
            tags = raw if isinstance(raw, list) else [raw]
            tags_lower = {str(t).lower() for t in tags}
            return any(s.lower() in tags_lower for s in sel_specialties)
        results = [p for p in results if matches_specialty(p)]

    # Client-side budget filter (skip entries where price is unknown)
    results = [
        p for p in results
        if (get_price(p) is None) or (budget_min <= get_price(p) <= budget_max)
    ]

    # Sort by rating descending
    results.sort(key=get_rating, reverse=True)

    count = len(results)
    st.subheader(f"{count} photographer{'s' if count != 1 else ''} found")

    for p in results:
        name     = p.get("name") or p.get("display_name") or p.get("business_name") or "Unknown"
        p_city   = p.get("city", "")
        p_state  = p.get("state", "")
        location = ", ".join(filter(None, [p_city, p_state]))
        rating   = get_rating(p)
        price    = get_price(p)
        bio      = p.get("bio") or p.get("description") or p.get("about") or ""
        spec_raw = p.get("specialties", p.get("specialty", ""))
        spec_str = ", ".join(spec_raw) if isinstance(spec_raw, list) else str(spec_raw or "")
        stars    = ("★" * round(rating) + "☆" * (5 - round(rating))) if rating else ""

        header = f"{name}  {stars}  —  {location}" if location else f"{name}  {stars}"
        with st.expander(header, expanded=True):
            col_info, col_stats = st.columns([3, 1])
            with col_info:
                if spec_str:
                    st.markdown(f"**Specialty:** {spec_str}")
                if bio:
                    st.markdown(bio)
            with col_stats:
                if rating:
                    st.metric("Rating", f"{rating:.1f} / 5")
                if price is not None:
                    st.metric("Starting at", f"${price:,.0f}")

            # Copyable / tweakable text block
            copy_lines = [f"Name: {name}"]
            if location:
                copy_lines.append(f"Location: {location}")
            if spec_str:
                copy_lines.append(f"Specialty: {spec_str}")
            if rating:
                copy_lines.append(f"Rating: {rating:.1f} / 5")
            if price is not None:
                copy_lines.append(f"Starting price: ${price:,.0f}")
            if bio:
                copy_lines += ["", bio]

            st.text_area(
                "Copy / tweak",
                value="\n".join(copy_lines),
                height=160,
                key=f"copy_{p.get('id', name)}",
            )
