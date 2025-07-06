import streamlit as st
import requests
import pandas as pd

st.set_page_config(
    page_title="Answer‑the‑Public‑Style Keyword Generator",
    page_icon="🗝️",
    layout="wide",
)

# ────────────────────────────
## 1. Styling tweaks
# ────────────────────────────
st.markdown(
    """
    <style>
    .element-container:has(.dataframe) div[data-testid="stHorizontalBlock"] > div {
        padding-top: 0rem; padding-bottom: 0rem;
    }
    .dataframe { border-radius: 12px !important; }
    footer {visibility: hidden;}
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("🗝️ Answer‑the‑Public‑Style Keyword Generator")

# ────────────────────────────
## 2. Country codes
# ────────────────────────────
COUNTRY_TO_GL = {
    "India": "IN",
    "United States": "US",
    "United Kingdom": "GB",
    "Australia": "AU",
    "Canada": "CA",
    "Germany": "DE",
    "France": "FR",
    "Spain": "ES",
    "Italy": "IT",
    "Brazil": "BR",
}

# ────────────────────────────
## 3. Modifier buckets
# ────────────────────────────
QUESTION_WORDS = ["what", "why", "how", "where", "when", "who", "which", "can", "will", "are"]
PREPOSITIONS = ["for", "with", "without", "to", "near", "in", "on", "about", "versus", "vs"]
COMPARISONS = ["vs", "versus", "alternative", "alternatives", "compare", "comparison", "like"]

# ────────────────────────────
## 4. Helper for Google Suggest
# ────────────────────────────
@st.cache_data(show_spinner=False)
def google_autocomplete(query: str, gl: str) -> list[str]:
    url = "https://suggestqueries.google.com/complete/search"
    params = {"client": "firefox", "q": query, "gl": gl, "hl": "en"}
    try:
        r = requests.get(url, params=params, timeout=4)
        r.raise_for_status()
        suggestions = r.json()[1]
        return suggestions
    except Exception:
        return []

def expand_keyword(seed: str, gl: str) -> dict[str, list[str]]:
    buckets = {"Questions": [], "Prepositions": [], "Comparisons": []}

    for q in QUESTION_WORDS:
        buckets["Questions"] += google_autocomplete(f"{q} {seed}", gl)

    for p in PREPOSITIONS:
        buckets["Prepositions"] += google_autocomplete(f"{seed} {p}", gl)
        buckets["Prepositions"] += google_autocomplete(f"{p} {seed}", gl)

    for c in COMPARISONS:
        buckets["Comparisons"] += google_autocomplete(f"{seed} {c}", gl)
        buckets["Comparisons"] += google_autocomplete(f"{c} {seed}", gl)

    for key in buckets:
        seen = set()
        unique = []
        for s in buckets[key]:
            if s.lower() not in seen:
                unique.append(s)
                seen.add(s.lower())
        buckets[key] = unique

    return buckets

# ────────────────────────────
## 5. Sidebar – input panel
# ────────────────────────────
with st.sidebar:
    st.header("🔧 Settings")
    country = st.selectbox(
        "Country / Market",
        options=list(COUNTRY_TO_GL.keys()),
        index=list(COUNTRY_TO_GL.keys()).index("India"),
        help="Affects Google’s autosuggest geo‑targeting (gl parameter).",
    )
    st.markdown("---")
    seeds = st.text_area(
        "Seed Keywords (1‑5, one per line)",
        placeholder="e.g. electric cars\ngreen hydrogen\nrooftop solar",
        height=160,
    )
    go_btn = st.button("⚡ Generate Ideas", use_container_width=True)

# ────────────────────────────
## 6. Main logic
# ────────────────────────────
if go_btn:
    seed_list = [s.strip() for s in seeds.splitlines() if s.strip()][:5]
    if not seed_list:
        st.error("Please enter at least one seed keyword 🚀")
        st.stop()

    with st.spinner("Crunching suggestions…"):
        all_rows = []
        tab_dfs = {"Questions": [], "Prepositions": [], "Comparisons": []}
        gl_code = COUNTRY_TO_GL[country]

        for seed in seed_list:
            buckets = expand_keyword(seed, gl_code)
            for bucket_name, suggestions in buckets.items():
                for s in suggestions:
                    row = {"Seed": seed, "Bucket": bucket_name, "Suggestion": s}
                    all_rows.append(row)
                    tab_dfs[bucket_name].append(row)

        master_df = pd.DataFrame(all_rows)

    st.success(f"✨ Generated {len(master_df):,} unique suggestions")

    # ── Tabs
    tabs = st.tabs(["Questions ❓", "Prepositions ⚙️", "Comparisons 🔄"])
    for tab, name in zip(tabs, tab_dfs):
        sub_df = pd.DataFrame(tab_dfs[name])
        tab.dataframe(
            sub_df[["Suggestion", "Seed"]],
            hide_index=True,
            height=420,
            use_container_width=True,
        )

    # ── Downloads (CSV only)
    st.markdown("### ⬇️ Export")

    csv_bytes = master_df.to_csv(index=False).encode("utf-8")
    st.download_button(
        "Download CSV",
        csv_bytes,
        "keyword_suggestions.csv",
        "text/csv",
        use_container_width=True,
    )

    st.caption("Powered by Google Autocomplete · No paid APIs harmed 🐱‍💻")
else:
    st.info("Add one or more seed keywords in the sidebar and hit **Generate Ideas** ⬅️")
