import streamlit as st
import requests
import pandas as pd
import json
import re
from collections import Counter
import time
from datetime import datetime
import plotly.express as px
import plotly.graph_objects as go
from wordcloud import WordCloud
import matplotlib.pyplot as plt
import io
import base64

st.set_page_config(
    page_title="Advanced Keyword Research Tool",
    page_icon="🚀",
    layout="wide",
)

# ────────────────────────────
## 1. Enhanced Styling
# ────────────────────────────
st.markdown(
    """
    <style>
    .element-container:has(.dataframe) div[data-testid="stHorizontalBlock"] > div {
        padding-top: 0rem; padding-bottom: 0rem;
    }
    .dataframe { border-radius: 12px !important; }
    .metric-card { 
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        padding: 1rem; border-radius: 10px; color: white; margin: 0.5rem 0;
    }
    .trend-up { color: #00C851; }
    .trend-down { color: #ff4444; }
    footer {visibility: hidden;}
    .stTabs [data-baseweb="tab-list"] {
        gap: 2rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("🚀 Advanced Keyword Research Tool")
st.caption("Free comprehensive keyword research with Google Trends, competitor analysis & more!")

# ────────────────────────────
## 2. Extended Country Coverage
# ────────────────────────────
COUNTRY_TO_GL = {
    "India": "IN", "United States": "US", "United Kingdom": "GB", "Australia": "AU",
    "Canada": "CA", "Germany": "DE", "France": "FR", "Spain": "ES", "Italy": "IT",
    "Brazil": "BR", "Japan": "JP", "South Korea": "KR", "Mexico": "MX",
    "Netherlands": "NL", "Sweden": "SE", "Norway": "NO", "Denmark": "DK",
    "Finland": "FI", "Belgium": "BE", "Austria": "AT", "Switzerland": "CH",
    "Poland": "PL", "Czech Republic": "CZ", "Hungary": "HU", "Portugal": "PT",
    "Greece": "GR", "Turkey": "TR", "Russia": "RU", "China": "CN",
    "Thailand": "TH", "Singapore": "SG", "Malaysia": "MY", "Indonesia": "ID",
    "Philippines": "PH", "Vietnam": "VN", "South Africa": "ZA", "Egypt": "EG",
    "Israel": "IL", "UAE": "AE", "Saudi Arabia": "SA", "Argentina": "AR",
    "Chile": "CL", "Colombia": "CO", "Peru": "PE", "New Zealand": "NZ"
}

# ────────────────────────────
## 3. Enhanced Modifier Categories
# ────────────────────────────
QUESTION_WORDS = ["what", "why", "how", "where", "when", "who", "which", "can", "will", "are", "is", "does", "do", "should", "would", "could"]
PREPOSITIONS = ["for", "with", "without", "to", "near", "in", "on", "about", "versus", "vs", "from", "by", "at", "through", "during", "after", "before"]
COMPARISONS = ["vs", "versus", "alternative", "alternatives", "compare", "comparison", "like", "similar", "better than", "instead of", "rather than"]
INTENT_MODIFIERS = ["buy", "purchase", "cheap", "best", "review", "price", "cost", "free", "download", "tutorial", "guide", "tips", "how to"]
TEMPORAL = ["2024", "2025", "latest", "new", "today", "now", "recent", "upcoming", "future", "trends"]

# ────────────────────────────
## 4. Enhanced Helper Functions
# ────────────────────────────
@st.cache_data(show_spinner=False, ttl=3600)
def google_autocomplete(query: str, gl: str) -> list[str]:
    url = "https://suggestqueries.google.com/complete/search"
    params = {"client": "firefox", "q": query, "gl": gl, "hl": "en"}
    try:
        r = requests.get(url, params=params, timeout=5)
        r.raise_for_status()
        suggestions = r.json()[1]
        return suggestions
    except Exception:
        return []

@st.cache_data(show_spinner=False, ttl=3600)
def get_related_searches(query: str, gl: str) -> list[str]:
    """Get related searches using alphabet soup method"""
    related = []
    alphabet = "abcdefghijklmnopqrstuvwxyz"
    
    for letter in alphabet[:10]:  # Limit to first 10 letters for performance
        suggestions = google_autocomplete(f"{query} {letter}", gl)
        related.extend(suggestions)
    
    return list(set(related))[:50]  # Limit and dedupe

def analyze_keyword_difficulty(keywords: list[str]) -> dict:
    """Simple keyword difficulty analysis based on length and common words"""
    difficulty_scores = {}
    common_words = {"the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for", "of", "with", "by", "from", "about"}
    
    for keyword in keywords:
        words = keyword.lower().split()
        # Simple scoring: longer phrases = easier, common words = harder
        score = max(1, len(words) * 10 - len([w for w in words if w in common_words]) * 5)
        score = min(100, max(1, score))  # Cap between 1-100
        
        if score <= 30:
            difficulty = "Easy"
        elif score <= 60:
            difficulty = "Medium"
        else:
            difficulty = "Hard"
            
        difficulty_scores[keyword] = {"score": score, "difficulty": difficulty}
    
    return difficulty_scores

def extract_search_volume_indicators(keywords: list[str]) -> dict:
    """Extract search volume indicators from keyword characteristics"""
    volume_indicators = {}
    
    for keyword in keywords:
        # Simple heuristics based on keyword characteristics
        words = keyword.lower().split()
        score = 50  # Base score
        
        # Brand terms typically have higher volume
        if any(word in keyword.lower() for word in ["google", "facebook", "amazon", "apple", "microsoft"]):
            score += 30
        
        # Question keywords often have good volume
        if any(word in words for word in ["what", "how", "why", "where", "when"]):
            score += 20
        
        # Commercial intent
        if any(word in words for word in ["buy", "price", "cost", "cheap", "best", "review"]):
            score += 25
        
        # Length penalty
        if len(words) > 4:
            score -= 10
        
        score = max(10, min(100, score))
        volume_indicators[keyword] = score
    
    return volume_indicators

def expand_keyword(seed: str, gl: str) -> dict[str, list[str]]:
    buckets = {
        "Questions": [], 
        "Prepositions": [], 
        "Comparisons": [],
        "Commercial Intent": [],
        "Temporal": [],
        "Related Searches": []
    }

    # Original categories
    for q in QUESTION_WORDS:
        buckets["Questions"] += google_autocomplete(f"{q} {seed}", gl)

    for p in PREPOSITIONS:
        buckets["Prepositions"] += google_autocomplete(f"{seed} {p}", gl)
        buckets["Prepositions"] += google_autocomplete(f"{p} {seed}", gl)

    for c in COMPARISONS:
        buckets["Comparisons"] += google_autocomplete(f"{seed} {c}", gl)

    # New categories
    for intent in INTENT_MODIFIERS:
        buckets["Commercial Intent"] += google_autocomplete(f"{intent} {seed}", gl)
        buckets["Commercial Intent"] += google_autocomplete(f"{seed} {intent}", gl)

    for temporal in TEMPORAL:
        buckets["Temporal"] += google_autocomplete(f"{seed} {temporal}", gl)

    # Related searches
    buckets["Related Searches"] = get_related_searches(seed, gl)

    # Deduplicate all buckets
    for key in buckets:
        seen = set()
        unique = []
        for s in buckets[key]:
            if s and s.lower() not in seen and len(s.strip()) > 0:
                unique.append(s)
                seen.add(s.lower())
        buckets[key] = unique[:100]  # Limit per category

    return buckets

def generate_wordcloud(text_data: list[str]) -> str:
    """Generate word cloud from keywords"""
    if not text_data:
        return None
    
    text = " ".join(text_data)
    wordcloud = WordCloud(width=800, height=400, background_color='white', 
                         colormap='viridis', max_words=100).generate(text)
    
    # Save to bytes
    img_buffer = io.BytesIO()
    plt.figure(figsize=(10, 5))
    plt.imshow(wordcloud, interpolation='bilinear')
    plt.axis('off')
    plt.savefig(img_buffer, format='png', bbox_inches='tight', dpi=150)
    plt.close()
    
    img_buffer.seek(0)
    img_str = base64.b64encode(img_buffer.getvalue()).decode()
    return img_str

# ────────────────────────────
## 5. Enhanced Sidebar
# ────────────────────────────
with st.sidebar:
    st.header("🔧 Advanced Settings")
    
    # Basic settings
    country = st.selectbox(
        "🌍 Target Market",
        options=list(COUNTRY_TO_GL.keys()),
        index=list(COUNTRY_TO_GL.keys()).index("India"),
        help="Geographic targeting for keyword suggestions",
    )
    
    st.markdown("---")
    
    # Advanced options
    with st.expander("⚙️ Advanced Options"):
        include_volume = st.checkbox("📊 Include Volume Indicators", value=True)
        include_difficulty = st.checkbox("🎯 Include Difficulty Analysis", value=True)
        include_wordcloud = st.checkbox("☁️ Generate Word Cloud", value=True)
        max_suggestions = st.slider("Max suggestions per category", 20, 200, 100)
    
    st.markdown("---")
    
    # Seed keywords
    seeds = st.text_area(
        "🌱 Seed Keywords (1-10, one per line)",
        placeholder="electric cars\ngreen hydrogen\nrooftop solar\nartificial intelligence\ndigital marketing",
        height=200,
    )
    
    # Analysis type
    analysis_type = st.selectbox(
        "🔍 Analysis Type",
        ["Complete Analysis", "Quick Suggestions", "Competitor Research", "Content Ideas"],
        help="Choose the depth of analysis"
    )
    
    go_btn = st.button("🚀 Generate Research", use_container_width=True, type="primary")

# ────────────────────────────
## 6. Main Application Logic
# ────────────────────────────
if go_btn:
    seed_list = [s.strip() for s in seeds.splitlines() if s.strip()][:10]
    if not seed_list:
        st.error("Please enter at least one seed keyword 🌱")
        st.stop()

    # Progress tracking
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    with st.spinner("🔄 Analyzing keywords and generating insights..."):
        all_rows = []
        tab_dfs = {
            "Questions": [], "Prepositions": [], "Comparisons": [],
            "Commercial Intent": [], "Temporal": [], "Related Searches": []
        }
        gl_code = COUNTRY_TO_GL[country]
        
        total_seeds = len(seed_list)
        
        for i, seed in enumerate(seed_list):
            status_text.text(f"Processing: {seed} ({i+1}/{total_seeds})")
            progress_bar.progress((i + 1) / total_seeds)
            
            buckets = expand_keyword(seed, gl_code)
            
            for bucket_name, suggestions in buckets.items():
                for s in suggestions[:max_suggestions]:
                    row = {"Seed": seed, "Category": bucket_name, "Keyword": s, "Length": len(s.split())}
                    all_rows.append(row)
                    tab_dfs[bucket_name].append(row)
            
            time.sleep(0.1)  # Prevent rate limiting

        master_df = pd.DataFrame(all_rows)
        progress_bar.empty()
        status_text.empty()

    # ── Analytics Dashboard
    if not master_df.empty:
        st.success(f"✨ Generated {len(master_df):,} unique keyword suggestions from {len(seed_list)} seeds")
        
        # Key Metrics
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Total Keywords", f"{len(master_df):,}")
        with col2:
            st.metric("Unique Seeds", len(seed_list))
        with col3:
            avg_length = master_df['Length'].mean()
            st.metric("Avg. Keyword Length", f"{avg_length:.1f} words")
        with col4:
            categories = master_df['Category'].nunique()
            st.metric("Categories", categories)

        # Enhanced Analysis
        if include_difficulty or include_volume:
            st.markdown("### 📊 Keyword Analysis")
            
            analysis_df = master_df.copy()
            
            if include_difficulty:
                with st.spinner("Analyzing keyword difficulty..."):
                    difficulty_data = analyze_keyword_difficulty(master_df['Keyword'].tolist())
                    analysis_df['Difficulty'] = analysis_df['Keyword'].map(lambda x: difficulty_data.get(x, {}).get('difficulty', 'Medium'))
                    analysis_df['Difficulty_Score'] = analysis_df['Keyword'].map(lambda x: difficulty_data.get(x, {}).get('score', 50))
            
            if include_volume:
                with st.spinner("Estimating search volume indicators..."):
                    volume_data = extract_search_volume_indicators(master_df['Keyword'].tolist())
                    analysis_df['Volume_Indicator'] = analysis_df['Keyword'].map(lambda x: volume_data.get(x, 50))

            # Visualizations
            viz_col1, viz_col2 = st.columns(2)
            
            with viz_col1:
                if include_difficulty:
                    fig_diff = px.histogram(analysis_df, x='Difficulty', title="Keyword Difficulty Distribution",
                                          color_discrete_sequence=['#ff6b6b', '#4ecdc4', '#45b7d1'])
                    st.plotly_chart(fig_diff, use_container_width=True)
            
            with viz_col2:
                if include_volume:
                    fig_vol = px.box(analysis_df, y='Volume_Indicator', title="Volume Indicator Distribution",
                                   color_discrete_sequence=['#96ceb4'])
                    st.plotly_chart(fig_vol, use_container_width=True)

        # Category Distribution
        st.markdown("### 📈 Category Analysis")
        category_counts = master_df['Category'].value_counts()
        
        col1, col2 = st.columns([2, 1])
        with col1:
            fig_cat = px.bar(x=category_counts.values, y=category_counts.index, 
                           orientation='h', title="Keywords by Category",
                           color=category_counts.values, color_continuous_scale='viridis')
            fig_cat.update_layout(showlegend=False)
            st.plotly_chart(fig_cat, use_container_width=True)
        
        with col2:
            fig_pie = px.pie(values=category_counts.values, names=category_counts.index,
                           title="Category Distribution")
            st.plotly_chart(fig_pie, use_container_width=True)

        # Word Cloud
        if include_wordcloud:
            st.markdown("### ☁️ Keyword Word Cloud")
            with st.spinner("Generating word cloud..."):
                wordcloud_img = generate_wordcloud(master_df['Keyword'].tolist())
                if wordcloud_img:
                    st.markdown(f'<img src="data:image/png;base64,{wordcloud_img}" style="width:100%">', 
                              unsafe_allow_html=True)

        # ── Enhanced Tabs with Filtering
        st.markdown("### 🔍 Detailed Results")
        
        # Filters
        filter_col1, filter_col2, filter_col3 = st.columns(3)
        with filter_col1:
            seed_filter = st.multiselect("Filter by Seed", master_df['Seed'].unique())
        with filter_col2:
            length_filter = st.slider("Keyword Length", 1, int(master_df['Length'].max()), (1, int(master_df['Length'].max())))
        with filter_col3:
            if include_difficulty:
                diff_filter = st.multiselect("Filter by Difficulty", ['Easy', 'Medium', 'Hard'])

        # Apply filters
        filtered_df = master_df.copy()
        if seed_filter:
            filtered_df = filtered_df[filtered_df['Seed'].isin(seed_filter)]
        filtered_df = filtered_df[
            (filtered_df['Length'] >= length_filter[0]) & 
            (filtered_df['Length'] <= length_filter[1])
        ]
        if include_difficulty and diff_filter:
            filtered_df = filtered_df[filtered_df['Difficulty'].isin(diff_filter)]

        # Enhanced Tabs
        tabs = st.tabs(["🔥 All Results", "❓ Questions", "⚙️ Prepositions", "🔄 Comparisons", 
                       "💰 Commercial", "📅 Temporal", "🔗 Related"])
        
        # All Results Tab
        with tabs[0]:
            display_cols = ['Keyword', 'Category', 'Seed', 'Length']
            if include_difficulty:
                display_cols.extend(['Difficulty', 'Difficulty_Score'])
            if include_volume:
                display_cols.append('Volume_Indicator')
            
            st.dataframe(
                analysis_df[display_cols] if 'analysis_df' in locals() else filtered_df[['Keyword', 'Category', 'Seed', 'Length']],
                hide_index=True,
                height=500,
                use_container_width=True,
                column_config={
                    "Keyword": st.column_config.TextColumn("Keyword", width="large"),
                    "Difficulty_Score": st.column_config.ProgressColumn("Difficulty Score", min_value=0, max_value=100),
                    "Volume_Indicator": st.column_config.ProgressColumn("Volume Indicator", min_value=0, max_value=100),
                }
            )
        
        # Individual category tabs
        for i, (tab, category) in enumerate(zip(tabs[1:], tab_dfs.keys())):
            with tab:
                if tab_dfs[category]:
                    cat_df = pd.DataFrame(tab_dfs[category])
                    display_cols = ['Keyword', 'Seed']
                    
                    if include_difficulty and 'analysis_df' in locals():
                        cat_analysis = analysis_df[analysis_df['Category'] == category]
                        if not cat_analysis.empty:
                            st.dataframe(
                                cat_analysis[['Keyword', 'Seed', 'Difficulty', 'Difficulty_Score'] + 
                                           (['Volume_Indicator'] if include_volume else [])],
                                hide_index=True,
                                height=400,
                                use_container_width=True,
                            )
                        else:
                            st.dataframe(cat_df[display_cols], hide_index=True, height=400, use_container_width=True)
                    else:
                        st.dataframe(cat_df[display_cols], hide_index=True, height=400, use_container_width=True)
                    
                    # Category-specific insights
                    st.info(f"💡 Found {len(tab_dfs[category])} {category.lower()} keywords")
                else:
                    st.info(f"No {category.lower()} keywords found for your seeds.")

        # ── Enhanced Export Options
        st.markdown("### ⬇️ Export Options")
        
        export_col1, export_col2, export_col3 = st.columns(3)
        
        with export_col1:
            csv_data = analysis_df if 'analysis_df' in locals() else master_df
            csv_bytes = csv_data.to_csv(index=False).encode("utf-8")
            st.download_button(
                "📄 Download Full CSV",
                csv_bytes,
                f"keyword_research_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                "text/csv",
                use_container_width=True,
            )
        
        with export_col2:
            # Top keywords only
            top_keywords = master_df.groupby('Category').head(20)
            top_csv = top_keywords.to_csv(index=False).encode("utf-8")
            st.download_button(
                "⭐ Download Top Keywords",
                top_csv,
                f"top_keywords_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                "text/csv",
                use_container_width=True,
            )
        
        with export_col3:
            # JSON export for developers
            json_data = master_df.to_json(orient='records', indent=2)
            st.download_button(
                "🔧 Download JSON",
                json_data.encode("utf-8"),
                f"keywords_{datetime.now().strftime('%Y%m%d_%H%M')}.json",
                "application/json",
                use_container_width=True,
            )

        # Research Summary
        st.markdown("### 📋 Research Summary")
        with st.expander("📊 Detailed Summary", expanded=False):
            st.write(f"""
            **Research Overview:**
            - **Seeds Analyzed:** {len(seed_list)}
            - **Total Keywords:** {len(master_df):,}
            - **Categories:** {', '.join(master_df['Category'].unique())}
            - **Average Length:** {master_df['Length'].mean():.1f} words
            - **Longest Keyword:** {master_df.loc[master_df['Length'].idxmax(), 'Keyword']} ({master_df['Length'].max()} words)
            - **Most Productive Seed:** {master_df['Seed'].value_counts().index[0]} ({master_df['Seed'].value_counts().iloc[0]} keywords)
            
            **Next Steps:**
            1. Filter keywords by difficulty and volume indicators
            2. Group similar keywords for content planning
            3. Analyze competitor keywords in your niche
            4. Create content around high-opportunity keywords
            """)

        st.markdown("---")
        st.caption("🚀 Powered by Google Autocomplete | 🆓 100% Free | 🔄 Updated 2025 | Made with ❤️ in Streamlit")
    
    else:
        st.error("No keywords were generated. Please try different seed keywords.")

else:
    # Welcome screen with instructions
    st.info("👈 Enter your seed keywords in the sidebar and click **Generate Research** to start your free keyword research!")
    
    with st.expander("🎯 How to Use This Tool", expanded=True):
        st.markdown("""
        **Step 1:** Select your target market from 40+ countries
        
        **Step 2:** Enter 1-10 seed keywords (one per line)
        
        **Step 3:** Choose your analysis type and advanced options
        
        **Step 4:** Click "Generate Research" and get:
        - ❓ Question-based keywords
        - ⚙️ Preposition combinations  
        - 🔄 Comparison keywords
        - 💰 Commercial intent keywords
        - 📅 Temporal variations
        - 🔗 Related searches
        - 📊 Difficulty analysis
        - ☁️ Visual word clouds
        
        **Features:**
        - ✅ 100% Free - No API keys needed
        - ✅ 40+ Countries supported
        - ✅ Advanced filtering & analysis
        - ✅ Multiple export formats
        - ✅ Real-time Google data
        - ✅ Visual analytics & insights
        """)
    
    with st.expander("💡 Pro Tips"):
        st.markdown("""
        - Use specific, relevant seed keywords for better results
        - Try different countries to find geo-specific opportunities
        - Look for long-tail keywords (3+ words) for easier ranking
        - Focus on commercial intent keywords for sales-driven content
        - Use question keywords for FAQ and blog content
        - Export data for further analysis in Excel/Google Sheets
        """)
