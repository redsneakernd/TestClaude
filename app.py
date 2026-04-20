"""
Find a Photographer — Streamlit app powered by the FindAPhotographer API.
Run: streamlit run app.py
"""

import requests
import streamlit as st

FAP_BASE = "https://zmddzjnhmgfsrdkhwvxc.supabase.co/functions/v1/public-api"

st.set_page_config(page_title="Find a Photographer", page_icon="📸", layout="wide")
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


# ── Sidebar search form ───────────────────────────────────────────────────────
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

# ── Results ───────────────────────────────────────────────────────────────────
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

# Client-side budget filter (include entries where price is unknown)
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
