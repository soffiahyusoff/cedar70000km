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

    c.execute("""
        INSERT OR IGNORE INTO participants
        (participant_id, name, grad_year, cca, name_key, cca_key)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        participant_id,
        name.strip(),
        grad_year.strip(),
        cca.strip(),
        name.strip().lower(),
        cca.strip().lower()
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
# HEADER
# =========================
st.image("cedar70000km3.png", use_container_width=True

st.title("🏃‍♀️‍➡️ Cedar Girls 70th Anniversary Distance Challenge")

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
# FORM
# =========================
st.header("📥 Submit Your Distance")

selected_participant_id = None

if participants_df.empty:
    st.warning("No participants available. Please contact admin.")

else:
    participants_df["display"] = (
        participants_df["name"] + " (" +
        participants_df["grad_year"] + ", " +
        participants_df["cca"] + ")"
    )

    participants_df = participants_df.sort_values(by=["name", "grad_year"])

    selected_display = st.selectbox(
        "Select your name",
        participants_df["display"]
    )

    participant_row = participants_df[
        participants_df["display"] == selected_display
    ].iloc[0]

    selected_participant_id = participant_row["participant_id"]

    st.caption(f"✅ Selected: {selected_display}")

# ✅ Inputs ALWAYS present
activity_date = st.date_input(
    "Date of activity",
    min_value=START_DATE,
    max_value=END_DATE
)

distance = st.number_input("Distance (km)", min_value=0.1)

# ✅ Submit button placed correctly
if st.button("Submit"):

    if participants_df.empty:
        st.error("No participants available.")
        st.stop()

    if distance <= 0:
        st.warning("Distance must be greater than 0.")
        st.stop()

    if distance > MAX_DISTANCE:
        st.warning("Distance too large.")
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

    # Add participants
    with st.expander("➕ Add participant"):
        name = st.text_input("Name", key="admin_name")
        year = st.text_input("Graduation Year")
        cca = st.text_input("CCA")

        if st.button("Add Participant"):
            if name and year and cca:
                add_participant(name, year, cca)
                st.success("✅ Added")
                st.rerun()

    # Participant list
    st.subheader("📋 Participant List")
    if not participants_df.empty:
        st.dataframe(participants_df[["name", "grad_year", "cca"]])

    # Edit participants
    st.subheader("✏️ Edit Participant")

    if not participants_df.empty:
        selected_edit = st.selectbox("Select participant", participants_df["display"], key="edit")

        row = participants_df[participants_df["display"] == selected_edit].iloc[0]

        edit_name = st.text_input("Name", value=row["name"])
        edit_year = st.text_input("Year", value=row["grad_year"])
        edit_cca = st.text_input("CCA", value=row["cca"])

        if st.button("Update"):
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
            st.success("✅ Updated")
            st.rerun()

    # =========================
    # 🗑 DELETE PARTICIPANT
    # =========================
    st.subheader("🗑 Delete Participant")

    if not participants_df.empty:

        participants_df["display"] = (
            participants_df["name"] + " (" +
            participants_df["grad_year"] + ", " +
            participants_df["cca"] + ")"
        )

        selected_delete = st.selectbox(
            "Select participant to delete",
            participants_df["display"],
            key="delete_participant"
        )

        delete_row = participants_df[
            participants_df["display"] == selected_delete
        ].iloc[0]

        confirm_delete = st.checkbox("⚠️ Confirm deletion of this participant and ALL their entries")

        if st.button("Delete Participant") and confirm_delete:

            participant_id = delete_row["participant_id"]

            # ✅ Delete ALL submissions linked to participant
            c.execute("DELETE FROM distance_logs WHERE participant_id=?", (participant_id,))

            # ✅ Delete participant
            c.execute("DELETE FROM participants WHERE participant_id=?", (participant_id,))

            conn.commit()

            st.success("✅ Participant and all related entries deleted")
            st.rerun()


    
    # Delete entries
    if not df.empty:
        delete_id = st.text_input("Delete submission ID")

        if st.button("Delete Entry"):
            c.execute("DELETE FROM distance_logs WHERE submission_id=?", (delete_id,))
            conn.commit()
            st.success("✅ Deleted")

        if st.button("⚠️ Delete ALL"):
            c.execute("DELETE FROM distance_logs")
            conn.commit()
            st.success("✅ Cleared all")


# =========================
# VIEW INDIVIDUAL ENTRIES
# =========================
#st.subheader("🧾 All Submissions")

#if not df.empty:
  #  st.dataframe(
  #      df[
  #          ["submission_id", "name", "grad_year", "cca", "distance", "activity_date"]
  #      ].sort_values(by="activity_date", ascending=False),
  #      use_container_width=True
  #  )
#else:
   # st.info("No submissions yet.")


# =========================
# PROGRESS
# =========================

st.header("📊 Progress")

# ✅ ALWAYS refresh latest data here
df = get_data()

if not df.empty:
    total_km = df["distance"].sum()
    st.metric("Total KM", f"{total_km:.2f}")
    st.progress(min(total_km / GOAL_KM, 1.0))

    st.subheader("🏆 Leaderboard")
    leaderboard = df.groupby(["name", "grad_year", "cca"])["distance"].sum().sort_values(ascending=False)
    st.dataframe(leaderboard.reset_index())

    # ✅ ✅ ADD THIS (your missing table)
    st.subheader("🧾 All Submissions")
    st.dataframe(
        df[["submission_id", "name", "grad_year", "cca", "distance", "activity_date"]]
        .sort_values(by="activity_date", ascending=False),
        use_container_width=True
    )

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
