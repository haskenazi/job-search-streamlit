import os
import requests
import pandas as pd
from openpyxl import load_workbook
import streamlit as st
import feedparser
import io

st.set_page_config(
    page_title="Job Search Tool",
    page_icon="🧭",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("🔍 Job Search + News Insights")

# === FORM INPUTS (in narrower columns) ===
with st.container():
    col1, col2 = st.columns([2, 1])
    with col1:
        with st.form("job_search_form"):
            company = st.text_input("Company Name")
            generate_news = st.checkbox("Generate news stories")
            title = st.text_input("Job Title")
            industry = st.text_input("Industry")
            city = st.text_input("City")
            max_results = st.slider("Max number of job results", 1, 50, 10)
            use_mock_data = st.checkbox("Use mock data (no API calls)")
            submit = st.form_submit_button("Search")

# === PROCESSING ===
if submit:
    companies = [c.strip() for c in company.split(",") if c.strip()]
    titles = [t.strip() for t in title.split(",") if t.strip()]
    industries = [i.strip() for i in industry.split(",") if i.strip()]

    queries = []
    for c in companies or [""]:
        for t in titles or [""]:
            queries.append(" ".join(filter(None, [t, c])))

    # === NEWS SECTION ===
    if generate_news and companies:
        for comp in companies:
            st.subheader(f"📰 Top News About {comp}")
            rss_url = f"https://news.google.com/rss/search?q={comp.replace(' ', '+')}"
            feed = feedparser.parse(rss_url)
            for entry in feed.entries[:5]:
                st.markdown(f"- [{entry.title}]({entry.link})")

    # === JOB SEARCH SECTION ===
    all_rows = []
    for query in queries:
        if use_mock_data:
            data = {
                "data": [
                    {
                        "job_title": "Senior Product Manager",
                        "employer_name": "ExampleCorp",
                        "job_city": "New York",
                        "job_state": "NY",
                        "job_description": "Lead cross-functional teams...",
                        "job_apply_link": "https://example.com/apply1"
                    },
                    {
                        "job_title": "Technical Account Manager",
                        "employer_name": "MockTech Inc.",
                        "job_city": "San Francisco",
                        "job_state": "CA",
                        "job_description": "Manage client relationships...",
                        "job_apply_link": "https://example.com/apply2"
                    }
                ]
            }
        else:
            headers = {
                "X-RapidAPI-Key": "23428cd089msh050d7a2a05dd217p106bd6jsn4eb35fc7fe14",
                "X-RapidAPI-Host": "jsearch.p.rapidapi.com"
            }
            params = {
                "query": query,
                "page": "1",
                "industry": industries[0] if industries else None,
                "location": city if city else None
            }
            params = {k: v for k, v in params.items() if v is not None}

            try:
                response = requests.get("https://jsearch.p.rapidapi.com/search", headers=headers, params=params)
                response.raise_for_status()
                data = response.json()
            except Exception as e:
                st.error(f"API error for query '{query}': {e}")
                continue

        jobs = data.get('data', [])[:max_results]
        for job in jobs:
            apply_link = job.get("job_apply_link", "")
            row = {
                "Company": job.get("employer_name", ""),
                "Job Title": job.get("job_title", ""),
                "Location": (job.get("job_city") or "") + (", " + (job.get("job_state") or "") if job.get("job_state") else ""),
                "Link to Apply": f"<a href='{apply_link}' target='_blank'><b style='color:blue'>link</b></a>" if apply_link else ""
            }
            all_rows.append(row)

    if not all_rows:
        st.warning("No job results found.")
    else:
        df = pd.DataFrame(all_rows)

        # === FILTERS ===
        st.sidebar.header("🔎 Filter Results")
        selected_company = st.sidebar.multiselect("Filter by Company", options=sorted(df["Company"].unique()), default=sorted(df["Company"].unique()))
        selected_location = st.sidebar.multiselect("Filter by Location", options=sorted(df["Location"].unique()), default=sorted(df["Location"].unique()))

        filtered_df = df[df["Company"].isin(selected_company) & df["Location"].isin(selected_location)]

        st.success(f"Showing {len(filtered_df)} of {len(df)} job postings.")
        st.markdown("### 📋 Job Results")
        st.markdown(filtered_df.to_html(escape=False, index=False), unsafe_allow_html=True)

        # Offer download
        buffer = io.BytesIO()
        df_download = filtered_df.copy()
        df_download["Link to Apply"] = df_download["Link to Apply"].str.extract(r'href=\'(.*?)\'')[0]
        df_download.to_excel(buffer, index=False)
        st.download_button("📥 Download Excel", buffer.getvalue(), file_name="job_results.xlsx")
