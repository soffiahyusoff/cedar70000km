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

# Participants table
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

# Distance logs table
c.execute("""
CREATE TABLE IF NOT EXISTS distance_logs (
    submission_id TEXT PRIMARY KEY,
    participant_id TEXT,
    distance REAL,
    activity_date TEXT,
    timestamp TEXT,
    FOREIGN KEY (participant_id) REFERENCES participants(participant_id)
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
        INSERT INTO participants
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
    return participant_id

def get_or_create_participant(name, grad_year, cca):
    name_clean = clean_text(name)
    grad_year_clean = clean_text(grad_year)
    cca_clean = clean_text(cca)

    row = c.execute("""
        SELECT participant_id
        FROM participants
        WHERE name_key = ? AND grad_year = ? AND cca_key = ?
    """, (
        key_text(name_clean),
        grad_year_clean,
        key_text(cca_clean)
    )).fetchone()

    if row:
        return row[0]

    return add_participant(name_clean, grad_year_clean, cca_clean)

def get_participants():
    return pd.read_sql("""
        SELECT participant_id, name, grad_year, cca
        FROM participants
        ORDER BY name, grad_year, cca
    """, conn)

def add_submission(submission_id, participant_id, distance, activity_date):
    c.execute("""
        INSERT INTO distance_logs
        (submission_id, participant_id, distance, activity_date, timestamp)
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
        SELECT
            d.submission_id,
            p.participant_id,
            p.name,
            p.grad_year,
            p.cca,
            d.distance,
            d.activity_date,
            d.timestamp
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

Let’s achieve this together 💜
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

participant_mode = st.radio(
    "Participant option",
    ["Select existing participant", "Add new participant"],
    horizontal=True
)

selected_participant_id = None
name = ""
grad_year = ""
cca = ""

if participant_mode == "Select existing participant":
    if participants_df.empty:
        st.info("No participants added yet. Please add a new participant first.")
        participant_mode = "Add new participant"
    else:
        names = sorted(participants_df["name"].dropna().unique().tolist())
        selected_name = st.selectbox("Name", names)

        filtered_years = participants_df[
            participants_df["name"] == selected_name
        ]["grad_year"].dropna().unique().tolist()
        filtered_years = sorted(filtered_years, reverse=True)

        selected_grad_year = st.selectbox("Graduation Year", filtered_years)

        filtered_ccas = participants_df[
            (participants_df["name"] == selected_name) &
            (participants_df["grad_year"] == selected_grad_year)
        ]["cca"].dropna().unique().tolist()
        filtered_ccas = sorted(filtered_ccas)

        selected_cca = st.selectbox("CCA", filtered_ccas)

        participant_row = participants_df[
            (participants_df["name"] == selected_name) &
            (participants_df["grad_year"] == selected_grad_year) &
            (participants_df["cca"] == selected_cca)
        ].iloc[0]

        selected_participant_id = participant_row["participant_id"]
        name = participant_row["name"]
        grad_year = participant_row["grad_year"]
        cca = participant_row["cca"]

if participant_mode == "Add new participant":
    name = st.text_input("Enter participant name")
    grad_year = st.text_input("Graduation Year (e.g. 2015)")
    cca = st.text_input("CCA (e.g. Choir, Netball, Debate)")

activity_date = st.date_input(
    "Date of activity",
    min_value=START_DATE,
    max_value=END_DATE
)

distance = st.number_input(
    "Distance covered (km)",
    min_value=0.1,
    step=0.1
)

# =========================
# ADMIN ACCESS (HIDDEN)
# =========================
st.markdown("---")

admin_password = st.text_input("🔐 Admin Access", type="password")

if admin_password == "cedar70th":

    # =========================
    # ADMIN PANEL (ONLY VISIBLE AFTER LOGIN)
    # =========================
    st.header("🔧 Admin Controls")

    if not df.empty:

        st.subheader("🧾 All Distance Entries")

        st.dataframe(
            df[["submission_id", "name", "grad_year", "cca", "distance", "activity_date"]],
            use_container_width=True
        )

        # -------------------------
        # DELETE SINGLE ENTRY
        # -------------------------
        st.subheader("🗑 Delete Individual Entry")

        delete_id = st.text_input("Enter submission_id")

        if st.button("Delete Entry"):
            if delete_id:
                c.execute("""
                    DELETE FROM distance_logs
                    WHERE submission_id = ?
                """, (delete_id,))
                conn.commit()
                st.success("✅ Entry deleted")
                st.rerun()
            else:
                st.warning("Enter a valid submission_id")

        # -------------------------
        # DELETE ALL ENTRIES
        # -------------------------
        st.subheader("⚠️ Reset All Distance Entries")

        confirm = st.checkbox("I confirm I want to delete ALL entries")

        if st.button("Delete ALL entries") and confirm:
            c.execute("DELETE FROM distance_logs")
            conn.commit()
            st.success("✅ All entries cleared")
            st.rerun()

    else:
        st.info("No entries available.")

# 👉 NOTHING else is shown if password is wrong
# =========================
# SUBMIT
# =========================
if st.button("Submit"):

    if not name.strip():
        st.warning("Please enter or select a participant name.")
        st.stop()

    if not grad_year.strip():
        st.warning("Please enter or select graduation year.")
        st.stop()

    if not cca.strip():
        st.warning("Please enter or select CCA.")
        st.stop()

    if distance <= 0:
        st.warning("Distance must be greater than 0.")
        st.stop()

    if distance > MAX_DISTANCE:
        st.warning(f"Distance too large (> {MAX_DISTANCE} km). Please verify.")
        st.stop()

    # Create participant if needed
    if participant_mode == "Add new participant":
        selected_participant_id = get_or_create_participant(name, grad_year, cca)

    # Prevent duplicate submission for same participant on same date
    existing = c.execute("""
        SELECT 1
        FROM distance_logs
        WHERE participant_id = ? AND activity_date = ?
    """, (
        selected_participant_id,
        activity_date.strftime("%Y-%m-%d")
    )).fetchone()

    if existing:
        st.error("❌ This participant has already submitted for this date.")
        st.stop()

    submission_id = str(uuid.uuid4())[:8]

    add_submission(
        submission_id,
        selected_participant_id,
        float(distance),
        activity_date.strftime("%Y-%m-%d")
    )

    st.success(f"✅ Submission recorded! ID: {submission_id}")
    st.rerun()

# =========================
# DISPLAY DATA
# =========================
st.header("📊 Progress Overview")

if not df.empty:
    total_km = df["distance"].astype(float).sum()

    st.metric("Total Distance Covered", f"{total_km:.2f} km")

    progress = min(total_km / GOAL_KM, 1.0)
    st.progress(progress)

    st.write(f"Progress: {total_km:.2f} / {GOAL_KM} km")

    # Leaderboard
    st.subheader("🏆 Leaderboard")

    leaderboard = (
        df.groupby(["name", "grad_year", "cca"])["distance"]
        .sum()
        .sort_values(ascending=False)
        .reset_index()
    )

    st.dataframe(leaderboard.head(10), use_container_width=True)

    # Recent submissions
    st.subheader("🕒 Recent Submissions")

    st.dataframe(
        df.sort_values(by="timestamp", ascending=False)[
            ["submission_id", "name", "grad_year", "cca", "distance", "activity_date"]
        ].head(10),
        use_container_width=True
    )

    # Daily trend
    st.subheader("📈 Daily Distance Trend")

    trend_df = df.copy()
    trend_df["activity_date"] = pd.to_datetime(trend_df["activity_date"])
    daily = trend_df.groupby("activity_date")["distance"].sum()

    st.line_chart(daily)
else:
    st.info("No submissions yet. Be the first!")

# =========================
# TIMELINE
# =========================
st.header("📅 Campaign Timeline")

today = date.today()

if today < START_DATE:
    st.info("Event has not started yet.")
elif today > END_DATE:
    st.success("🎉 Event completed!")
else:
    total_days = (END_DATE - START_DATE).days
    days_passed = (today - START_DATE).days
    st.progress(days_passed / total_days)
    st.write(f"Day {days_passed} of {total_days}")
