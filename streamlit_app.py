import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, date
import os
import uuid

# =========================
# CONFIG
# =========================
GOAL_KM = 70000
START_DATE = date(2026, 6, 1)
END_DATE = date(2027, 2, 1)

MAX_DISTANCE = 100  # Prevent unrealistic entries

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# =========================
# DATABASE SETUP
# =========================
conn = sqlite3.connect("data.db", check_same_thread=False)
c = conn.cursor()

c.execute('''
CREATE TABLE IF NOT EXISTS submissions (
    submission_id TEXT PRIMARY KEY,
    name TEXT,
    distance REAL,
    activity_date TEXT,
    image TEXT,
    timestamp TEXT
)
''')
conn.commit()

# =========================
# FUNCTIONS
# =========================
def add_submission(submission_id, name, distance, activity_date, image_path):
    c.execute("""
        INSERT INTO submissions
        (submission_id, name, distance, activity_date, image, timestamp)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        submission_id,
        name,
        distance,
        activity_date,
        image_path,
        datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ))
    conn.commit()

def get_data():
    return pd.read_sql("SELECT * FROM submissions", conn)

# =========================
# UI
# =========================
st.title("🏃‍♀️ Cedar Girls 70th Anniversary Distance Challenge")

st.markdown("""
**🎯 Goal:** 70,000 km  
**📅 Period:** 1 June 2026 → 1 Feb 2027  

Let’s achieve this together 💜
""")

# =========================
# SUBMISSION FORM
# =========================
st.header("📥 Submit Your Distance")

name = st.text_input("Enter your name")

activity_date = st.date_input(
    "Date of activity",
    min_value=START_DATE,
    max_value=END_DATE
)

distance = st.number_input("Distance covered (km)", min_value=0.1, step=0.1)

uploaded_file = st.file_uploader(
    "Upload screenshot (Strava or tracker)",
    type=["jpg", "png", "jpeg"]
)

if st.button("Submit"):

    # =========================
    # VALIDATION
    # =========================
    if not name:
        st.warning("Please enter your name.")
        st.stop()

    if distance <= 0:
        st.warning("Distance must be greater than 0.")
        st.stop()

    if distance > MAX_DISTANCE:
        st.warning(f"Distance too large (> {MAX_DISTANCE} km). Please verify.")
        st.stop()

    # ✅ Prevent duplicate submission (same name + same date)
    existing = c.execute("""
        SELECT * FROM submissions
        WHERE name=? AND activity_date=?
    """, (name.strip().lower(), activity_date.strftime("%Y-%m-%d"))).fetchone()

    if existing:
        st.error("❌ You have already submitted for this date.")
        st.stop()

    # =========================
    # GENERATE UNIQUE ID
    # =========================
    submission_id = str(uuid.uuid4())[:8]

    # =========================
    # SAVE IMAGE SAFELY
    # =========================
    image_path = None

    if uploaded_file:
        file_ext = uploaded_file.name.split(".")[-1]
        filename = f"{submission_id}.{file_ext}"
        image_path = os.path.join(UPLOAD_FOLDER, filename)

        with open(image_path, "wb") as f:
            f.write(uploaded_file.getbuffer())

    # =========================
    # SAVE TO DATABASE
    # =========================
    add_submission(
        submission_id,
        name.strip(),
        float(distance),
        activity_date.strftime("%Y-%m-%d"),
        image_path
    )

    st.success(f"✅ Submission recorded! ID: {submission_id}")

# =========================
# DISPLAY DATA
# =========================
st.header("📊 Progress Overview")

df = get_data()

if not df.empty:

    total_km = df["distance"].sum()

    st.metric("Total Distance Covered", f"{total_km:.2f} km")

    progress = min(total_km / GOAL_KM, 1.0)
    st.progress(progress)

    st.write(f"Progress: {total_km:.2f} / {GOAL_KM} km")

    # =========================
    # LEADERBOARD
    # =========================
    st.subheader("🏆 Leaderboard")

    leaderboard = (
        df.groupby("name")["distance"]
        .sum()
        .sort_values(ascending=False)
        .reset_index()
    )

    st.dataframe(leaderboard.head(10))

    # =========================
    # RECENT SUBMISSIONS
    # =========================
    st.subheader("🕒 Recent Submissions")

    st.dataframe(
        df.sort_values(by="timestamp", ascending=False)[
            ["submission_id", "name", "distance", "activity_date"]
        ].head(10)
    )

    # =========================
    # DAILY TREND
    # =========================
    st.subheader("📈 Daily Distance Trend")

    df["activity_date"] = pd.to_datetime(df["activity_date"])
    daily = df.groupby("activity_date")["distance"].sum()

    st.line_chart(daily)

    # =========================
    # SHOW SOME IMAGES
    # =========================
    st.subheader("📸 Latest Activity Screenshots")

    recent_images = df[df["image"].notnull()].tail(5)

    for _, row in recent_images.iterrows():
        st.image(row["image"], caption=f"{row['name']} - {row['distance']} km", width=300)

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
