"""
Multi-page Streamlit app backed by Excel datasources.
Run: streamlit run app.py
"""

import time
from datetime import datetime, timedelta, timezone
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
    ["📊 Sales Dashboard", "⛪ Church Directory", "📞 Webex Call Queues"],
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
# PAGE 3 — WEBEX CALL QUEUE STATS
# ══════════════════════════════════════════════════════════════════════════════
elif page == "📞 Webex Call Queues":
    from webex_api import WebexAPI

    st.title("📞 Webex Call Queue Stats")

    # ── Sidebar: credentials & options ───────────────────────────────────
    with st.sidebar:
        st.header("Webex Credentials")
        st.markdown(
            "Obtain a **Personal Access Token** from "
            "[developer.webex.com](https://developer.webex.com/docs/getting-started) "
            "(valid 12 hours) or create an OAuth Integration for long-lived access."
        )
        token = st.text_input("Access Token", type="password", key="webex_token")
        org_id = st.text_input(
            "Org ID (optional)",
            help="Leave blank to use the org tied to your token.",
            key="webex_org_id",
        )

        st.divider()
        st.header("Required Scopes")
        st.code(
            "spark-admin:telephony_config_read\n"
            "spark-admin:calling_cdr_read\n"
            "analytics:read_all",
            language=None,
        )
        st.caption(
            "Personal Access Tokens include all scopes. "
            "For CDR data the admin account must also have the "
            "**Webex Calling Detailed Call History API access** role enabled in Control Hub."
        )

    if not token:
        st.info("Enter your Webex Access Token in the sidebar to get started.")
        st.stop()

    # ── Validate token (cached for this session) ──────────────────────────
    if "webex_me" not in st.session_state or st.session_state.get("webex_token_used") != token:
        try:
            api = WebexAPI(token)
            me = api.get_me()
            st.session_state["webex_me"] = me
            st.session_state["webex_token_used"] = token
            st.session_state["webex_api"] = api
        except requests.HTTPError as e:
            st.error(f"Authentication failed ({e.response.status_code}). Check your token.")
            st.stop()
    else:
        api = st.session_state["webex_api"]
        me = st.session_state["webex_me"]

    st.caption(f"Connected as **{me.get('displayName', 'Unknown')}** ({me.get('emails', [''])[0]})")

    # ── Tabs ──────────────────────────────────────────────────────────────
    tab_live, tab_cdr, tab_reports = st.tabs(
        ["🟢 Live Queue Status", "📋 Call History (CDR)", "📄 Reports"]
    )

    # ══ TAB 1 — LIVE QUEUE STATUS ══════════════════════════════════════════
    with tab_live:
        st.subheader("Live Queue Status")
        st.caption(
            "Queue configuration and agent availability are polled on demand. "
            "**Calls currently waiting/active in queue** are not exposed by the Webex Calling "
            "REST API — use the Call History tab for recent activity or Control Hub for a "
            "true real-time view. Click **Refresh** to re-poll."
        )

        col_refresh, col_auto, col_interval = st.columns([1, 1, 1])
        with col_refresh:
            do_refresh = st.button("🔄 Refresh", use_container_width=True)
        with col_auto:
            auto_refresh = st.toggle("Auto-refresh", value=False)
        with col_interval:
            refresh_secs = st.selectbox("Interval", [30, 60, 120, 300], index=1, format_func=lambda s: f"{s}s")

        # Fetch queues
        try:
            with st.spinner("Fetching call queues…"):
                queues = api.list_queues(org_id=org_id or None)
        except requests.HTTPError as e:
            st.error(f"Could not fetch queues: {e}")
            st.stop()

        if not queues:
            st.warning("No call queues found for this organization.")
        else:
            # Fetch agents (all at once; filter per queue client-side)
            try:
                all_agents = api.list_queue_agents()
                available_agents = api.list_available_agents()
            except requests.HTTPError:
                all_agents = []
                available_agents = []

            # Build lookup: queueId → agent counts
            agents_by_queue: dict[str, int] = {}
            for a in all_agents:
                qid = a.get("queueId", "")
                agents_by_queue[qid] = agents_by_queue.get(qid, 0) + 1

            avail_by_queue: dict[str, int] = {}
            for a in available_agents:
                qid = a.get("queueId", "")
                avail_by_queue[qid] = avail_by_queue.get(qid, 0) + 1

            # Summary metrics
            total_queues = len(queues)
            total_agents = len(set(a.get("id") for a in all_agents))
            total_avail = len(set(a.get("id") for a in available_agents))

            m1, m2, m3 = st.columns(3)
            m1.metric("Call Queues", total_queues)
            m2.metric("Total Agents (across queues)", total_agents)
            m3.metric("Available Agents", total_avail)

            st.divider()

            # Queue cards
            for q in queues:
                qid = q.get("id", "")
                qname = q.get("name", "Unknown")
                location = q.get("locationName", q.get("location", ""))
                phone = q.get("phoneNumber", "") or q.get("extension", "")
                routing = q.get("callPolicies", {}).get("policyType", q.get("routingType", ""))
                n_agents = agents_by_queue.get(qid, 0)
                n_avail = avail_by_queue.get(qid, 0)
                n_busy = n_agents - n_avail

                with st.container(border=True):
                    hc1, hc2, hc3, hc4 = st.columns([3, 2, 1, 1])
                    with hc1:
                        st.markdown(f"**{qname}**")
                        st.caption(f"{location}  ·  {phone}  ·  Routing: {routing or 'N/A'}")
                    with hc2:
                        st.caption("Agents")
                        st.markdown(f"**{n_agents}** total  ·  **{n_avail}** available  ·  **{n_busy}** busy")
                    with hc3:
                        enabled = q.get("enabled", True)
                        st.markdown("🟢 Enabled" if enabled else "🔴 Disabled")
                    with hc4:
                        st.markdown(f"ID: `{qid[:8]}…`")

            st.divider()

            # Raw data expander
            with st.expander("Raw queue data (JSON)"):
                st.json(queues)

        # Auto-refresh
        if auto_refresh:
            time.sleep(refresh_secs)
            st.rerun()

    # ══ TAB 2 — CALL HISTORY (CDR) ════════════════════════════════════════
    with tab_cdr:
        st.subheader("Detailed Call History (CDR)")
        st.caption(
            "Pulls individual call records from the Webex analytics endpoint. "
            "**Range**: data is available from ~5 minutes ago up to 48 hours back. "
            "For longer history use the **Reports** tab. "
            "Requires the `spark-admin:calling_cdr_read` scope and the "
            "**Webex Calling Detailed Call History API access** admin role in Control Hub."
        )

        # Date/time range picker
        now_utc = datetime.now(timezone.utc)
        default_start = now_utc - timedelta(hours=8)
        # Clamp end to 5 minutes ago
        default_end = now_utc - timedelta(minutes=6)

        cdr_c1, cdr_c2 = st.columns(2)
        with cdr_c1:
            cdr_start_date = st.date_input("Start date", value=default_start.date(), key="cdr_sd")
            cdr_start_hour = st.number_input("Start hour (0–23, UTC)", 0, 23, int(default_start.hour), key="cdr_sh")
        with cdr_c2:
            cdr_end_date = st.date_input("End date", value=default_end.date(), key="cdr_ed")
            cdr_end_hour = st.number_input("End hour (0–23, UTC)", 0, 23, int(default_end.hour), key="cdr_eh")

        start_dt = datetime(
            cdr_start_date.year, cdr_start_date.month, cdr_start_date.day,
            int(cdr_start_hour), 0, 0, tzinfo=timezone.utc,
        )
        end_dt = datetime(
            cdr_end_date.year, cdr_end_date.month, cdr_end_date.day,
            int(cdr_end_hour), 59, 59, tzinfo=timezone.utc,
        )

        # Validate range
        min_start = now_utc - timedelta(hours=48)
        max_end = now_utc - timedelta(minutes=5)
        range_ok = True
        if start_dt < min_start:
            st.warning(f"Start time adjusted: CDR data is only available for the past 48 hours. Use Reports for older data.")
            range_ok = False
        if end_dt > max_end:
            st.warning("End time must be at least 5 minutes in the past.")
            range_ok = False
        if start_dt >= end_dt:
            st.error("Start time must be before end time.")
            range_ok = False

        if st.button("Fetch Call History", disabled=not range_ok):
            start_iso = start_dt.strftime("%Y-%m-%dT%H:%M:%S.000Z")
            end_iso = end_dt.strftime("%Y-%m-%dT%H:%M:%S.999Z")

            try:
                with st.spinner("Fetching CDR data…"):
                    records = api.get_call_history(start_iso, end_iso)
            except requests.HTTPError as e:
                status = e.response.status_code if e.response is not None else "?"
                if status == 403:
                    st.error(
                        "403 Forbidden: Your token lacks `spark-admin:calling_cdr_read` scope "
                        "or the admin account does not have the "
                        "**Webex Calling Detailed Call History API access** role enabled. "
                        "Enable it in Control Hub → Users → (your admin) → Administrator Roles."
                    )
                else:
                    st.error(f"CDR fetch failed ({status}): {e}")
                st.stop()

            if not records:
                st.info("No call records found for the selected time range.")
            else:
                df_cdr = pd.DataFrame(records)
                st.session_state["cdr_df"] = df_cdr

        df_cdr = st.session_state.get("cdr_df")
        if df_cdr is not None and not df_cdr.empty:
            # ── Normalise common CDR column names ──────────────────────────
            # Webex CDR columns use Title Case with spaces; normalise for safety
            df_cdr.columns = [c.strip() for c in df_cdr.columns]

            # Identify key columns (flexible to minor naming variations)
            def find_col(df: pd.DataFrame, *candidates: str) -> Optional[str]:
                for c in candidates:
                    if c in df.columns:
                        return c
                    # case-insensitive fallback
                    match = next((col for col in df.columns if col.lower() == c.lower()), None)
                    if match:
                        return match
                return None

            col_answer   = find_col(df_cdr, "Answer Time", "answerTime", "answer_time")
            col_release  = find_col(df_cdr, "Release Time", "releaseTime", "release_time")
            col_duration = find_col(df_cdr, "Duration", "Call Duration", "callDuration")
            col_type     = find_col(df_cdr, "Call Type", "callType", "type")
            col_dir      = find_col(df_cdr, "Direction", "direction")
            col_outcome  = find_col(df_cdr, "Call Outcome", "callOutcome", "outcome")
            col_queue    = find_col(df_cdr, "Hunt Group Name", "Queue Name", "queueName", "Hunt Pilot DN")
            col_wait     = find_col(df_cdr, "Queue Wait Time", "Waiting Duration", "waitTime", "Wait Duration")
            col_user     = find_col(df_cdr, "User", "displayName", "userName", "Answering User")

            # Parse timestamps
            if col_answer:
                df_cdr[col_answer] = pd.to_datetime(df_cdr[col_answer], errors="coerce", utc=True)
            if col_release:
                df_cdr[col_release] = pd.to_datetime(df_cdr[col_release], errors="coerce", utc=True)

            # ── Summary metrics ────────────────────────────────────────────
            total_calls = len(df_cdr)
            answered = df_cdr[col_outcome].str.lower().str.contains("answer", na=False).sum() if col_outcome else "N/A"
            abandoned = df_cdr[col_outcome].str.lower().str.contains("abandon|miss", na=False).sum() if col_outcome else "N/A"
            avg_dur_s = df_cdr[col_duration].mean() if col_duration and pd.api.types.is_numeric_dtype(df_cdr[col_duration]) else None
            avg_wait_s = df_cdr[col_wait].mean() if col_wait and pd.api.types.is_numeric_dtype(df_cdr[col_wait]) else None

            sm1, sm2, sm3, sm4, sm5 = st.columns(5)
            sm1.metric("Total Calls", f"{total_calls:,}")
            sm2.metric("Answered", f"{answered:,}" if isinstance(answered, (int, float)) else answered)
            sm3.metric("Abandoned / Missed", f"{abandoned:,}" if isinstance(abandoned, (int, float)) else abandoned)
            sm4.metric("Avg Handle Time", f"{avg_dur_s/60:.1f} min" if avg_dur_s else "N/A")
            sm5.metric("Avg Queue Wait", f"{avg_wait_s:.0f} s" if avg_wait_s else "N/A")

            st.divider()

            # ── Charts ─────────────────────────────────────────────────────
            chart_c1, chart_c2 = st.columns(2)

            with chart_c1:
                if col_outcome:
                    outcome_counts = df_cdr[col_outcome].value_counts().reset_index()
                    outcome_counts.columns = ["Outcome", "Count"]
                    fig_outcome = px.pie(outcome_counts, names="Outcome", values="Count", title="Call Outcomes")
                    st.plotly_chart(fig_outcome, use_container_width=True)

            with chart_c2:
                if col_answer:
                    df_hourly = df_cdr.copy()
                    df_hourly["Hour"] = df_cdr[col_answer].dt.floor("h")
                    hourly_counts = df_hourly.groupby("Hour").size().reset_index(name="Calls")
                    fig_hourly = px.bar(
                        hourly_counts, x="Hour", y="Calls",
                        title="Calls per Hour",
                        labels={"Hour": "Hour (UTC)"},
                    )
                    st.plotly_chart(fig_hourly, use_container_width=True)

            if col_queue:
                queue_counts = df_cdr[col_queue].value_counts().head(15).reset_index()
                queue_counts.columns = ["Queue / Hunt Group", "Calls"]
                fig_q = px.bar(
                    queue_counts, x="Calls", y="Queue / Hunt Group",
                    orientation="h", title="Calls by Queue (top 15)",
                    color="Queue / Hunt Group",
                )
                fig_q.update_layout(showlegend=False)
                st.plotly_chart(fig_q, use_container_width=True)

            # ── Full data table ────────────────────────────────────────────
            st.subheader(f"Call Records ({total_calls:,} rows)")
            st.dataframe(df_cdr, use_container_width=True)

            csv_cdr = df_cdr.to_csv(index=False).encode("utf-8")
            st.download_button(
                "⬇️ Download CDR as CSV",
                data=csv_cdr,
                file_name="webex_call_history.csv",
                mime="text/csv",
            )

    # ══ TAB 3 — REPORTS (async, longer history) ════════════════════════════
    with tab_reports:
        st.subheader("Reports (Async — up to 3 months)")
        st.caption(
            "Use the Webex Reports API to generate Detailed Call History or Call Queue Stats "
            "reports for longer date ranges (up to ~3 months per template). "
            "Reports are generated asynchronously; click **Generate** and then **Check Status** "
            "until the download link appears. Requires `analytics:read_all` scope."
        )

        rpt_c1, rpt_c2 = st.columns(2)

        # ── List templates ─────────────────────────────────────────────────
        with rpt_c1:
            st.markdown("#### 1. Choose a Report Template")
            if st.button("Load Templates"):
                try:
                    with st.spinner("Loading templates…"):
                        templates = api.list_report_templates()
                    st.session_state["webex_templates"] = templates
                except requests.HTTPError as e:
                    st.error(f"Could not load templates ({e.response.status_code if e.response else '?'}): {e}")

            templates = st.session_state.get("webex_templates", [])
            if templates:
                # Filter to calling/queue-relevant templates
                calling_templates = [
                    t for t in templates
                    if any(kw in t.get("title", t.get("name", "")).lower()
                           for kw in ["call", "queue", "cdp", "cdr", "agent"])
                ] or templates  # fallback: show all if filter is empty

                template_names = [f"{t.get('title', t.get('name', 'Unknown'))} (ID: {t.get('Id', t.get('id'))})" for t in calling_templates]
                selected_template_idx = st.selectbox("Template", range(len(template_names)), format_func=lambda i: template_names[i])
                selected_template = calling_templates[selected_template_idx]
                template_id = selected_template.get("Id") or selected_template.get("id")

                max_days = selected_template.get("maxDays", 90)
                st.caption(f"Max date range for this template: **{max_days} days**")

                rpt_start = st.date_input("Report Start Date", value=(datetime.now() - timedelta(days=7)).date(), key="rpt_sd")
                rpt_end = st.date_input("Report End Date", value=datetime.now().date(), key="rpt_ed")

                if st.button("Generate Report"):
                    delta = (rpt_end - rpt_start).days
                    if delta > max_days:
                        st.error(f"Date range ({delta} days) exceeds template max ({max_days} days).")
                    elif rpt_start > rpt_end:
                        st.error("Start date must be before end date.")
                    else:
                        try:
                            with st.spinner("Submitting report request…"):
                                report_id = api.create_report(
                                    template_id=int(template_id),
                                    start_date=rpt_start.strftime("%Y-%m-%d"),
                                    end_date=rpt_end.strftime("%Y-%m-%d"),
                                )
                            st.success(f"Report created. ID: `{report_id}`")
                            st.session_state["webex_report_id"] = report_id
                        except requests.HTTPError as e:
                            st.error(f"Report creation failed: {e}")

        # ── Poll & download ────────────────────────────────────────────────
        with rpt_c2:
            st.markdown("#### 2. Check Status & Download")

            report_id_input = st.text_input(
                "Report ID",
                value=st.session_state.get("webex_report_id", ""),
                key="rpt_id_input",
            )

            if st.button("Check Status") and report_id_input:
                try:
                    with st.spinner("Checking report status…"):
                        rpt = api.get_report(report_id_input.strip())
                    status = rpt.get("status", "unknown")
                    st.json(rpt)

                    if status.lower() == "done":
                        download_url = rpt.get("downloadURL") or rpt.get("downloadUrl")
                        if download_url:
                            st.success("Report is ready! Click below to download.")
                            st.session_state["webex_report_url"] = download_url
                        else:
                            st.warning("Status is 'done' but no downloadURL found in response.")
                    elif status.lower() in ("inprogress", "in_progress", "running"):
                        st.info("Report is still generating. Check again in 30–60 seconds.")
                    else:
                        st.warning(f"Report status: {status}")
                except requests.HTTPError as e:
                    st.error(f"Could not fetch report status: {e}")

            download_url = st.session_state.get("webex_report_url")
            if download_url:
                if st.button("⬇️ Download Report"):
                    try:
                        with st.spinner("Downloading report…"):
                            df_report = api.download_report(download_url)
                        st.success(f"Downloaded {len(df_report):,} rows.")
                        st.dataframe(df_report, use_container_width=True)
                        csv_rpt = df_report.to_csv(index=False).encode("utf-8")
                        st.download_button(
                            "⬇️ Save as CSV",
                            data=csv_rpt,
                            file_name="webex_report.csv",
                            mime="text/csv",
                        )
                        # Offer cleanup
                        if st.button("🗑️ Delete this report from Webex (frees quota)"):
                            try:
                                api.delete_report(report_id_input.strip())
                                st.success("Report deleted.")
                                st.session_state.pop("webex_report_url", None)
                                st.session_state.pop("webex_report_id", None)
                            except requests.HTTPError as e:
                                st.error(f"Delete failed: {e}")
                    except Exception as e:
                        st.error(f"Download failed: {e}")

        # ── List existing reports ──────────────────────────────────────────
        st.divider()
        st.markdown("#### Previously Generated Reports")
        if st.button("List My Reports"):
            try:
                with st.spinner("Loading reports…"):
                    existing = api.list_reports()
                if not existing:
                    st.info("No reports found.")
                else:
                    df_rpts = pd.DataFrame(existing)
                    st.dataframe(df_rpts, use_container_width=True)
