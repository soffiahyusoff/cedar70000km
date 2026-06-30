
import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, date
import uuid

# =========================
# CONFIG
# =========================
GOAL_KM = 70000
START_DATE = date(2026, 7, 1)
END_DATE = date(2027, 3, 1)
MAX_DISTANCE = 100

# =========================
# DATABASE SETUP
# =========================
conn = sqlite3.connect("challenge.db", check_same_thread=False)
c = conn.cursor()

c.execute("""
CREATE TABLE IF NOT EXISTS participants (
    participant_id TEXT PRIMARY KEY,
    name TEXT,
    grad_year TEXT,
    cca TEXT,
    name_key TEXT,
    cca_key TEXT,
    UNIQUE(name_key, grad_year, cca_key)
)
""")

c.execute("""
CREATE TABLE IF NOT EXISTS distance_logs (
    submission_id TEXT PRIMARY KEY,
    participant_id TEXT,
    distance REAL,
    activity_date TEXT,
    timestamp TEXT
)
""")
conn.commit()

# =========================
# HELPERS
# =========================
def clean_text(value):
    return " ".join(value.strip().split())

def key_text(value):
    return clean_text(value).lower()

def add_participant(name, grad_year, cca):
    participant_id = str(uuid.uuid4())[:8]
    name_clean = clean_text(name)
    cca_clean = clean_text(cca)
    grad_year_clean = clean_text(grad_year)

    c.execute("""
        INSERT OR IGNORE INTO participants
        (participant_id, name, grad_year, cca, name_key, cca_key)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        participant_id,
        name_clean,
        grad_year_clean,
        cca_clean,
        key_text(name_clean),
        key_text(cca_clean)
    ))
    conn.commit()

def get_participants():
    return pd.read_sql("SELECT * FROM participants", conn)

def add_submission(submission_id, participant_id, distance, activity_date):
    c.execute("""
        INSERT INTO distance_logs
        VALUES (?, ?, ?, ?, ?)
    """, (
        submission_id,
        participant_id,
        distance,
        activity_date,
        datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ))
    conn.commit()

def get_data():
    return pd.read_sql("""
        SELECT d.*, p.name, p.grad_year, p.cca
        FROM distance_logs d
        JOIN participants p
        ON d.participant_id = p.participant_id
    """, conn)

# =========================
# UI HEADER
# =========================
st.title("🏃‍♀️ Cedar Girls 70th Anniversary Distance Challenge")

st.markdown("""
**🎯 Goal:** 70,000 km  
**📅 Period:** 1 July 2026 → 1 March 2027  
""")

# =========================
# LOAD DATA
# =========================
participants_df = get_participants()
df = get_data()

# =========================
# FORM INPUT
# =========================
st.header("📥 Submit Your Distance")

selected_participant_id = None

if participants_df.empty:
    st.warning("No participants available. Please contact admin to add participants.")

else:
    # ✅ Create display column
    participants_df["display"] = (
        participants_df["name"] + " (" +
        participants_df["grad_year"] + ", " +
        participants_df["cca"] + ")"
    )

    # ✅ Sort once
    participants_df_sorted = participants_df.sort_values(by=["name", "grad_year"])


    if "selected_display" not in st.session_state:
        st.session_state["selected_display"] = None
    
      selected_display = st.selectbox(
        "Select your name",
        participants_df_sorted["display"],
        index=None,
        placeholder="Start typing to search..."
    )
    
    # ✅ Only proceed if something is selected
    if selected_display:
        filtered_participant = participants_df_sorted[
            participants_df_sorted["display"] == selected_display
        ]
    
        if not filtered_participant.empty:
            participant_row = filtered_participant.iloc[0]
            selected_participant_id = participant_row["participant_id"]

    participant_row = filtered_participant.iloc[0]

    selected_participant_id = participant_row["participant_id"]

activity_date = st.date_input(
    "Date of activity",
    min_value=START_DATE,
    max_value=END_DATE
)

distance = st.number_input("Distance (km)", min_value=0.1)


# ✅ ✅ MOVE SUBMIT BUTTON HERE
submit_clicked = st.button("Submit")

if submit_clicked:

    if participants_df.empty:
        st.error("🚫 No participants available.")
        st.stop()

    if distance <= 0:
        st.warning("Distance must be greater than 0.")
        st.stop()

    if distance > MAX_DISTANCE:
        st.warning(f"Distance too large (> {MAX_DISTANCE} km).")
        st.stop()

    existing = c.execute("""
        SELECT 1 FROM distance_logs
        WHERE participant_id=? AND activity_date=?
    """, (
        selected_participant_id,
        activity_date.strftime("%Y-%m-%d")
    )).fetchone()

    if existing:
        st.error("❌ Already submitted today")
        st.stop()

    submission_id = str(uuid.uuid4())[:8]

    add_submission(
        submission_id,
        selected_participant_id,
        distance,
        activity_date.strftime("%Y-%m-%d")
    )

    st.success("✅ Submitted!")
    st.rerun()




# =========================
# ADMIN PANEL (HIDDEN)
# =========================
st.markdown("---")
admin_password = st.text_input("🔐 Admin Access", type="password")

if admin_password == st.secrets.get("ADMIN_PASSWORD", ""):

    st.header("🔧 Admin Controls")

    # ✅ Add participants
    st.subheader("➕ Add Participants")
    with st.expander("Add new participant"):
        name = st.text_input("Name", key="admin_name")
        year = st.text_input("Graduation Year")
        cca = st.text_input("CCA")

        if st.button("Add Participant"):
            if name and year and cca:
                add_participant(name, year, cca)
                st.success("✅ Added")
                st.rerun()
            else:
                st.warning("Fill all fields")

    # ✅ View participant list
    st.subheader("📋 Participant List")
    if not participants_df.empty:
        st.dataframe(
            participants_df[["name", "grad_year", "cca"]],
            use_container_width=True
        )
    else:
        st.info("No participants found.")

    # ✅ ✅ EDIT PARTICIPANT (NOW HIDDEN PROPERLY)
    st.subheader("✏️ Edit Participant")

    if not participants_df.empty:
        participants_df["display"] = (
            participants_df["name"] + " (" +
            participants_df["grad_year"] + ", " +
            participants_df["cca"] + ")"
        )

        selected_edit = st.selectbox(
            "Select participant to edit",
            participants_df["display"],
            key="edit_select"
        )

        row = participants_df[
            participants_df["display"] == selected_edit
        ].iloc[0]

        edit_name = st.text_input("Update Name", value=row["name"], key="edit_name")
        edit_year = st.text_input("Update Graduation Year", value=row["grad_year"], key="edit_year")
        edit_cca = st.text_input("Update CCA", value=row["cca"], key="edit_cca")

        if st.button("Update Participant"):
            if edit_name and edit_year and edit_cca:
                c.execute("""
                    UPDATE participants
                    SET name=?, grad_year=?, cca=?, name_key=?, cca_key=?
                    WHERE participant_id=?
                """, (
                    edit_name.strip(),
                    edit_year.strip(),
                    edit_cca.strip(),
                    edit_name.strip().lower(),
                    edit_cca.strip().lower(),
                    row["participant_id"]
                ))
                conn.commit()
                st.success("✅ Participant updated")
                st.rerun()
            else:
                st.warning("All fields required")

    # ✅ View + delete entries (your existing section)
    if not df.empty:
        st.subheader("🧾 Entries")
        st.dataframe(df)

        delete_id = st.text_input("Submission ID to delete")

        if st.button("Delete Entry"):
            c.execute("DELETE FROM distance_logs WHERE submission_id=?", (delete_id,))
            conn.commit()
            st.success("✅ Deleted")
            st.rerun()

        if st.button("⚠️ Delete ALL Entries"):
            c.execute("DELETE FROM distance_logs")
            conn.commit()
            st.success("✅ All cleared")
            st.rerun()



# =========================
# DISPLAY
# =========================
st.header("📊 Progress")

if not df.empty:
    total_km = df["distance"].sum()
    st.metric("Total KM", f"{total_km:.2f}")
    st.progress(min(total_km / GOAL_KM, 1.0))

    st.subheader("🏆 Leaderboard")
    leaderboard = df.groupby(["name", "grad_year", "cca"])["distance"].sum().sort_values(ascending=False)
    st.dataframe(leaderboard.reset_index())

else:
    st.info("No data yet.")

# =========================
# TIMELINE
# =========================
st.header("📅 Timeline")

today = date.today()

if today < START_DATE:
    st.info("Event not started")
elif today > END_DATE:
    st.success("Event completed")
else:
    progress_days = (today - START_DATE).days / (END_DATE - START_DATE).days
    st.progress(progress_days)

