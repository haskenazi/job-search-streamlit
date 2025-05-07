import streamlit as st
import sqlite3
import pandas as pd
from streamlit_sortables import sort_items

# DB setup
conn = sqlite3.connect("gig_staffing.db", check_same_thread=False)
c = conn.cursor()

# Create tables
c.execute('''CREATE TABLE IF NOT EXISTS gigs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    client_name TEXT,
    gig_name TEXT,
    date TEXT,
    venue TEXT
)''')

c.execute('''CREATE TABLE IF NOT EXISTS singers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    first_name TEXT,
    last_name TEXT,
    email TEXT
)''')

c.execute('''CREATE TABLE IF NOT EXISTS gig_singer_status (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    gig_id INTEGER,
    singer_id INTEGER,
    status TEXT,
    UNIQUE(gig_id, singer_id)
)''')

conn.commit()

# Constants
STATUSES = ["Inquired", "Available", "Not Available", "Booked", "Possible"]

# Pages
def home():
    st.title("Gig Staffing Dashboard")

    gigs = pd.read_sql_query("SELECT * FROM gigs", conn)
    if gigs.empty:
        st.info("No gigs created yet.")
        return

    selected_gig = st.selectbox("Select a gig", gigs["gig_name"])
    gig_id = gigs[gigs["gig_name"] == selected_gig]["id"].values[0]

    status_df = pd.read_sql_query(f"""
        SELECT s.id, s.first_name || ' ' || s.last_name as name, g.status
        FROM gig_singer_status g
        JOIN singers s ON g.singer_id = s.id
        WHERE g.gig_id = ?
    """, conn, params=(gig_id,))

    if status_df.empty:
        st.info("No singers assigned to this gig yet.")
        return

    name_to_id = dict(zip(status_df["name"], status_df["id"]))

    st.subheader("Reassign Singers by Dragging Between Columns")

    # Convert to a list of dicts format required by sort_items
    initial = [
        {"title": status, "items": status_df[status_df["status"] == status]["name"].tolist()}
        for status in STATUSES
    ]

    new_lists = sort_items(initial, direction="horizontal")

    # Flatten the result and rebuild the status assignment
    new_status_map = {}
    for col in new_lists:
        for name in col["items"]:
            new_status_map[name] = col["title"]

    for name, sid in name_to_id.items():
        new_status = new_status_map.get(name)
        if new_status:
            c.execute("INSERT OR REPLACE INTO gig_singer_status (gig_id, singer_id, status) VALUES (?, ?, ?)",
                      (gig_id, sid, new_status))
    conn.commit()
    st.success("Statuses updated.")


def manage_gigs():
    st.title("Manage Gigs")
    with st.form("Add Gig"):
        client = st.text_input("Client Name")
        gig_name = st.text_input("Gig Name")
        date = st.date_input("Date")
        venue = st.text_input("Venue")
        submitted = st.form_submit_button("Create Gig")
        if submitted:
            c.execute("INSERT INTO gigs (client_name, gig_name, date, venue) VALUES (?, ?, ?, ?)",
                      (client, gig_name, date.isoformat(), venue))
            conn.commit()
            st.success("Gig created.")


def manage_singers():
    st.title("Manage Singers")
    with st.form("Add Singer"):
        fname = st.text_input("First Name")
        lname = st.text_input("Last Name")
        email = st.text_input("Email")
        submitted = st.form_submit_button("Add Singer")
        if submitted:
            c.execute("INSERT INTO singers (first_name, last_name, email) VALUES (?, ?, ?)",
                      (fname, lname, email))
            conn.commit()
            st.success("Singer added.")


def assign_singers():
    st.title("Assign Singers to Gig")

    gigs = pd.read_sql_query("SELECT * FROM gigs", conn)
    singers = pd.read_sql_query("SELECT * FROM singers", conn)

    if gigs.empty or singers.empty:
        st.info("Create gigs and singers first.")
        return

    selected_gig = st.selectbox("Select Gig", gigs["gig_name"])
    gig_id = gigs[gigs["gig_name"] == selected_gig]["id"].values[0]

    for _, row in singers.iterrows():
        sid = row["id"]
        name = row["first_name"] + " " + row["last_name"]
        current = c.execute("SELECT status FROM gig_singer_status WHERE gig_id = ? AND singer_id = ?", (gig_id, sid)).fetchone()
        default = current[0] if current else "Inquired"
        new_status = st.selectbox(f"{name} Status", STATUSES, index=STATUSES.index(default), key=f"{gig_id}-{sid}")
        c.execute("INSERT OR REPLACE INTO gig_singer_status (gig_id, singer_id, status) VALUES (?, ?, ?)",
                  (gig_id, sid, new_status))
    conn.commit()
    st.success("Statuses updated.")


# Navigation
page = st.sidebar.selectbox("Page", ["Home", "Manage Gigs", "Manage Singers", "Assign Singers"])

if page == "Home":
    home()
elif page == "Manage Gigs":
    manage_gigs()
elif page == "Manage Singers":
    manage_singers()
elif page == "Assign Singers":
    assign_singers()
