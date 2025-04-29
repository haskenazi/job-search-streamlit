import streamlit as st
import pandas as pd
import requests
import io

# --- CONFIG ---
API_KEY = '23428cd089msh050d7a2a05dd217p106bd6jsn4eb35fc7fe14'
API_URL = 'https://jsearch.p.rapidapi.com/search'

headers = {
    "X-RapidAPI-Key": API_KEY,
    "X-RapidAPI-Host": "jsearch.p.rapidapi.com"
}

# --- UI FORM ---
st.title("Job Search Tool (Powered by JSearch)")
st.markdown("Fill out the fields below to search for job postings.")

with st.form("job_search_form"):
    company = st.text_input("Company Name")
    title = st.text_input("Job Title")
    industry = st.text_input("Industry")
    city = st.text_input("City")
    max_results = st.slider("Max number of job results", 1, 50, 10)
    submit = st.form_submit_button("Search")

if submit:
    query_parts = []
    if title:
        query_parts.append(title)
    if company:
        query_parts.append(company)
    query = " ".join(query_parts)

    params = {
        "query": query,
        "page": "1",
        "industry": industry if industry else None,
        "location": city if city else None
    }
    params = {k: v for k, v in params.items() if v is not None}

    try:
        response = requests.get(API_URL, headers=headers, params=params)
        response.raise_for_status()
        data = response.json()
    except Exception as e:
        st.error(f"API error: {e}")
        st.stop()

    jobs = data.get('data', [])[:max_results]
    if not jobs:
        st.warning("No job results found.")
    else:
        rows = []
        for job in jobs:
            row = {
                "Input Company": company,
                "Input Title": title,
                "Input Industry": industry,
                "Input City": city,
                "Job Title": job.get("job_title", ""),
                "Employer": job.get("employer_name", ""),
                "Location": (job.get("job_city") or "") + (", " + (job.get("job_state") or "") if job.get("job_state") else ""),
                "Apply Link": job.get("job_apply_link", "")
            }
            rows.append(row)

        df = pd.DataFrame(rows)
        st.success(f"Found {len(df)} job postings.")
        st.dataframe(df)

        # Offer download
        buffer = io.BytesIO()
        df.to_excel(buffer, index=False)
        st.download_button("📥 Download Excel", buffer.getvalue(), file_name="job_results.xlsx")
