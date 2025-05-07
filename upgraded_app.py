import os
import requests
import pandas as pd
from openpyxl import load_workbook
import streamlit as st
import feedparser
import io
import datetime
import openai
import docx2txt
import PyPDF2

st.set_page_config(
    page_title="Sales Enablement Suite",
    page_icon="💼",
    layout="wide",
    initial_sidebar_state="expanded",
)

# === SIMPLE LOGIN (REPLACE FOR PROD) ===
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

# === MAIN APP ===
st.title("💼 Sales Enablement Suite")
tab1, tab2, tab3 = st.tabs(["Job Search + News", "Company Insights", "File Upload & Summary"])

# === TAB 1: JOB SEARCH ===
with tab1:
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

                if submit and not (company or title or industry):
                    st.warning("Please enter at least one search input.")

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
                    "X-RapidAPI-Key": "YOUR_RAPIDAPI_KEY",
                    "X-RapidAPI-Host": "jsearch.p.rapidapi.com"
                }
                params = {
                    "query": query,
                    "page": "1",
                    "industry": industries[0] if industries else None,
                    "location": city if city else None
                }
                try:
                    response = requests.get("https://jsearch.p.rapidapi.com/search", headers=headers, params={k: v for k, v in params.items() if v})
                    data = response.json()
                except Exception as e:
                    st.error(f"API error for query '{query}': {e}")
                    continue

            for job in data.get("data", [])[:max_results]:
                link = job.get("job_apply_link", "")
                all_rows.append({
                    "Company": job.get("employer_name", ""),
                    "Job Title": job.get("job_title", ""),
                    "Location": f"{job.get('job_city', '')}, {job.get('job_state', '')}".strip(", "),
                    "Link to Apply": f"<a href='{link}' target='_blank'><b style='color:blue'>link</b></a>" if link else ""
                })

        if all_rows:
            df = pd.DataFrame(all_rows)
            st.sidebar.header("🔎 Filter Results")
            selected_company = st.sidebar.multiselect("Company", df["Company"].unique().tolist(), default=df["Company"].unique().tolist())
            selected_location = st.sidebar.multiselect("Location", df["Location"].unique().tolist(), default=df["Location"].unique().tolist())
            filtered_df = df[df["Company"].isin(selected_company) & df["Location"].isin(selected_location)]

            st.success(f"Showing {len(filtered_df)} of {len(df)} job postings.")
            st.markdown("### 📋 Job Results")
            st.markdown(filtered_df.to_html(escape=False, index=False), unsafe_allow_html=True)

            buffer = io.BytesIO()
            df_export = filtered_df.copy()
            df_export["Link to Apply"] = df_export["Link to Apply"].str.extract(r'href=\'(.*?)\'')[0]
            df_export.to_excel(buffer, index=False)

            print(f"Download by {st.session_state.user_email} at {datetime.datetime.now()} ({len(df_export)} rows)")
            st.download_button("📥 Download Excel", buffer.getvalue(), file_name="job_results.xlsx")
        else:
            st.warning("No job results found.")

# === TAB 2: COMPANY INSIGHTS ===
with tab2:
    st.markdown("### 🧠 Company Insights (Coming Soon)")
    st.info("This section will include funding, hiring, tech stack insights via Crunchbase or Clearbit.")

# === TAB 3: FILE UPLOAD & SUMMARY ===
with tab3:
    st.markdown("### 📎 Upload Files for Summary or Account Plan")
    uploaded_file = st.file_uploader("Upload .txt, .pdf, or .docx", type=["txt", "pdf", "docx"])
    openai.api_key = st.secrets["openai_api_key"] if "openai_api_key" in st.secrets else ""

    def extract_text(file):
        if file.name.endswith(".txt"):
            return file.read().decode("utf-8", errors="ignore")
        elif file.name.endswith(".pdf"):
            pdf_reader = PyPDF2.PdfReader(file)
            return "\n".join(page.extract_text() or "" for page in pdf_reader.pages)
        elif file.name.endswith(".docx"):
            return docx2txt.process(file)
        return ""

    def generate(prompt):
        return openai.ChatCompletion.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3
        ).choices[0].message["content"]

    if uploaded_file and openai.api_key:
        choice = st.radio("What do you want to generate?", ["Generate Summary", "Generate Account Plan"])
        if st.button("Submit"):
            with st.spinner("Generating..."):
                content = extract_text(uploaded_file)
                prompt = f"Summarize this:\n{content}" if choice == "Generate Summary" else f"Create an account plan based on this:\n{content}"
                result = generate(prompt)
                st.markdown("#### 🧾 Result:")
                st.write(result)
    elif uploaded_file:
        st.error("No OpenAI key found. Add it in Streamlit Cloud → Settings → Secrets.")
