import os
import io
import datetime
import requests
import pandas as pd
import streamlit as st
import feedparser
import openai
import docx2txt
import PyPDF2

st.set_page_config(
    page_title="Sales Enablement Suite",
    page_icon="💼",
    layout="wide",
    initial_sidebar_state="expanded",
)

# === SIMPLE LOGIN ===
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.title("🔐 Sign Up / Login")
    with st.form("login_form"):
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")
        submit = st.form_submit_button("Sign In / Sign Up")
        if submit:
            if email and password:
                st.session_state.logged_in = True
                st.session_state.user_email = email
            else:
                st.warning("Please enter both email and password.")
    st.stop()

# === APP HEADER ===
st.title("💼 Sales Enablement Suite")
tab1, tab2, tab3 = st.tabs(["Job Search + News", "Company Insights", "File Upload & Summary"])

# === JOB SEARCH TAB ===
with tab1:
    with st.form("job_search_form"):
        company = st.text_input("Company Name")
        generate_news = st.checkbox("Generate news stories")
        title = st.text_input("Job Title")
        industry = st.text_input("Industry")
        city = st.text_input("City")
        max_results = st.slider("Max number of job results", 1, 50, 10)
        use_mock_data = st.checkbox("Use mock data (no API calls)")
        submit = st.form_submit_button("Search")

    if submit and (company or title or industry):
        companies = [c.strip() for c in company.split(",") if c.strip()]
        titles = [t.strip() for t in title.split(",") if t.strip()]
        industries = [i.strip() for i in industry.split(",") if i.strip()]
        queries = [" ".join(filter(None, [t, c])) for c in companies or [""] for t in titles or [""]]

        if generate_news and companies:
            with st.expander("📰 View News Articles", expanded=True):
                for comp in companies:
                    st.markdown(f"#### 🔍 Top News About {comp}")
                    rss_url = f"https://news.google.com/rss/search?q={comp.replace(' ', '+')}"
                    feed = feedparser.parse(rss_url)
                    for entry in feed.entries[:5]:
                        st.markdown(f"- [{entry.title}]({entry.link})")

        all_rows = []
        for query in queries:
            if use_mock_data:
                data = {
                    "data": [
                        {"job_title": "Product Manager", "employer_name": "ExampleCo", "job_city": "NYC", "job_state": "NY", "job_apply_link": "https://example.com/job1"},
                        {"job_title": "Sales Engineer", "employer_name": "DemoCorp", "job_city": "SF", "job_state": "CA", "job_apply_link": "https://example.com/job2"}
                    ]
                }
            else:
                headers = {
                    "X-RapidAPI-Key": "YOUR_RAPIDAPI_KEY",
                    "X-RapidAPI-Host": "jsearch.p.rapidapi.com"
                }
                params = {
                    "query": query,
                    "page": "1",
                    "industry": industries[0] if industries else None,
                    "location": city if city else None
                }
                response = requests.get("https://jsearch.p.rapidapi.com/search", headers=headers, params={k: v for k, v in params.items() if v})
                data = response.json()

            for job in data.get("data", [])[:max_results]:
                all_rows.append({
                    "Company": job.get("employer_name", ""),
                    "Job Title": job.get("job_title", ""),
                    "Location": f"{job.get('job_city', '')}, {job.get('job_state', '')}".strip(", "),
                    "Link to Apply": f"<a href='{job.get('job_apply_link', '')}' target='_blank'><b style='color:blue'>link</b></a>"
                })

        if all_rows:
            df = pd.DataFrame(all_rows)
            st.sidebar.header("🔎 Filter Results")
            selected_company = st.sidebar.multiselect("Company", df["Company"].unique().tolist(), default=df["Company"].unique().tolist())
            selected_location = st.sidebar.multiselect("Location", df["Location"].unique().tolist(), default=df["Location"].unique().tolist())
            filtered_df = df[df["Company"].isin(selected_company) & df["Location"].isin(selected_location)]

            st.markdown("### 📋 Job Results")
            st.markdown(filtered_df.to_html(escape=False, index=False), unsafe_allow_html=True)

            buffer = io.BytesIO()
            df_export = filtered_df.copy()
            df_export["Link to Apply"] = df_export["Link to Apply"].str.extract(r'href=\'(.*?)\'')[0]
            df_export.to_excel(buffer, index=False)
            st.download_button("📥 Download Excel", buffer.getvalue(), file_name="job_results.xlsx")

# === COMPANY INSIGHTS TAB ===
with tab2:
    st.markdown("### 🧠 Company Insights (Coming Soon)")

# === FILE UPLOAD & SUMMARY TAB ===
with tab3:
    st.markdown("### 📎 Upload Files for Summary or Account Plan")
    uploaded_file = st.file_uploader("Upload .txt, .pdf, or .docx", type=["txt", "pdf", "docx"])
    if "openai_api_key" in st.secrets:
        client = openai.OpenAI(api_key=st.secrets["openai_api_key"])

        def extract_text(file):
            if file.name.endswith(".txt"):
                return file.read().decode("utf-8", errors="ignore")
            elif file.name.endswith(".pdf"):
                return "\n".join([page.extract_text() or "" for page in PyPDF2.PdfReader(file).pages])
            elif file.name.endswith(".docx"):
                return docx2txt.process(file)
            return ""

        def generate(prompt):
            res = client.chat.completions.create(
                model="gpt-4",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3
            )
            return res.choices[0].message.content

        if uploaded_file:
            choice = st.radio("Choose Task", ["Generate Summary", "Generate Account Plan"])
            if st.button("Submit"):
                content = extract_text(uploaded_file)
                prompt = f"Summarize this:\n{content}" if choice == "Generate Summary" else f"Create an account plan from this:\n{content}"
                with st.spinner("Generating..."):
                    st.write(generate(prompt))
    else:
        st.error("Missing OpenAI key. Add 'openai_api_key' to Streamlit Secrets.")
