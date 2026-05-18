import streamlit as st
import pandas as pd
from datetime import datetime, date
import uuid
from streamlit_gsheets import GSheetsConnection

# =========================
# CONFIG
# =========================
GOAL_KM = 70000
START_DATE = date(2026, 6, 1)
END_DATE = date(2027, 2, 1)
MAX_DISTANCE = 100

ADMIN_PASSWORD = st.secrets["ADMIN_PASSWORD"]

# =========================
# CONNECT TO GOOGLE SHEETS
# =========================
conn = st.connection("gsheets", type=GSheetsConnection)

# Submissions sheet
df = conn.read(
    spreadsheet=st.secrets["connections"]["gsheets"]["spreadsheet"],
    ttl=0
)

# Participants sheet
participants_df = conn.read(
    spreadsheet=st.secrets["connections"]["gsheets"]["participants_spreadsheet"],
    ttl=0
)

# Safeguards: ensure correct columns exist
if df.empty or "name" not in df.columns:
    df = pd.DataFrame(columns=["submission_id", "name", "distance", "activity_date", "timestamp"])

if participants_df.empty or "Name" not in participants_df.columns:
    participants_df = pd.DataFrame(columns=["Name", "Year of Grad", "CCA", "timestamp"])

# =========================
# UI HEADER
# =========================
st.image("cedar70000km3.png", width="stretch")
st.markdown("""
**🎯 Goal:** 70,000 km  
**📅 Period:** 1 June 2026 → 1 Feb 2027  
""")

# =========================
# PARTICIPANT CHECK
# =========================
st.header("👟 Participant Check")

is_new = st.radio(
    "Are you a new participant?",
    ["Select an option...", "No, I have registered", "Yes, I am new"],
    index=0
)

# Flag to track if a submission was made
submission_done = False

if is_new == "Yes, I am new":
    # Registration form
    st.subheader("📝 Register New Participant")
    new_name = st.text_input("Full Name")
    new_grad_year = st.text_input("Year of Graduation")
    new_cca = st.text_input("CCA")

    if st.button("Register"):
        if not new_name or not new_grad_year or not new_cca:
            st.warning("Please fill in all fields")
            st.stop()

        if not participants_df.empty:
            if new_name.lower() in participants_df["Name"].str.lower().tolist():
                st.error("This participant is already registered")
                st.stop()

        new_participant = pd.DataFrame([{
            "Name": new_name,
            "Year of Grad": new_grad_year,
            "CCA": new_cca,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }])

        # Append and update participants sheet
        updated_participants = pd.concat([participants_df, new_participant], ignore_index=True)
        conn.update(
            spreadsheet=st.secrets["connections"]["gsheets"]["participants_spreadsheet"],
            data=updated_participants
        )

        st.success(f"✅ {new_name} registered successfully!")

        # Reload participants immediately
        participants_df = conn.read(
            spreadsheet=st.secrets["connections"]["gsheets"]["participants_spreadsheet"],
            ttl=0
        )

        # Submission form immediately after registration
        name = new_name
        activity_date = st.date_input("Date of activity", min_value=START_DATE, max_value=END_DATE)
        distance = st.number_input("Distance (km)", min_value=0.1, step=0.1)

        if st.button("Submit Distance"):
            if distance > MAX_DISTANCE:
                st.warning(f"Max {MAX_DISTANCE} km allowed")
                st.stop()

            new_data = pd.DataFrame([{
                "submission_id": str(uuid.uuid4())[:8],
                "name": name,
                "distance": distance,
                "activity_date": activity_date.strftime("%Y-%m-%d"),
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }])

            updated_df = pd.concat([df, new_data], ignore_index=True)
            conn.update(
                spreadsheet=st.secrets["connections"]["gsheets"]["spreadsheet"],
                data=updated_df
            )

            st.success("✅ Submission added!")
            submission_done = True

elif is_new == "No, I have registered":
    # Submission form
    st.header("📥 Submit Your Distance")
    name = st.text_input("Enter your name")
    activity_date = st.date_input("Date of activity", min_value=START_DATE, max_value=END_DATE)
    distance = st.number_input("Distance (km)", min_value=0.1, step=0.1)

    if st.button("Submit"):
        if not name:
            st.warning("Enter your name")
            st.stop()

        if distance > MAX_DISTANCE:
            st.warning(f"Max {MAX_DISTANCE} km allowed")
            st.stop()

        if not participants_df.empty:
            valid_names = participants_df["Name"].str.lower().tolist()
            if name.lower() not in valid_names:
                st.error("Name not found in participants list")
                st.stop()

        if not df.empty:
            duplicate = df[
                (df["name"].str.lower() == name.lower()) &
                (df["activity_date"] == activity_date.strftime("%Y-%m-%d"))
            ]
            if not duplicate.empty:
                st.error("Already submitted for this date")
                st.stop()

        new_data = pd.DataFrame([{
            "submission_id": str(uuid.uuid4())[:8],
            "name": name,
            "distance": distance,
            "activity_date": activity_date.strftime("%Y-%m-%d"),
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }])

        updated_df = pd.concat([df, new_data], ignore_index=True)
        conn.update(
            spreadsheet=st.secrets["connections"]["gsheets"]["spreadsheet"],
            data=updated_df
        )

        st.success("✅ Submission added!")
        submission_done = True

# =========================
# SHOW PROGRESS + LEADERBOARD ONLY AFTER SUBMISSION
# =========================
if submission_done:
    st.header("📊 Progress & Leaderboard")

    # Reload submissions to ensure fresh data
    df = conn.read(
        spreadsheet=st.secrets["connections"]["gsheets"]["spreadsheet"],
        ttl=0
    )

    merged_df = df.merge(
        participants_df[["Name", "Year of Grad", "CCA"]],
        left_on="name",
        right_on="Name",
        how="left"
    )

    # Leaderboard
    leaderboard = merged_df.groupby(["Name", "Year of Grad", "CCA"])["distance"].sum().sort_values(ascending=False)
    leaderboard_df = leaderboard.reset_index().rename(columns={"distance": "distance in km"}).head(10)
    st.subheader("🏆 Leaderboard")
    st.dataframe(leaderboard_df)

    # Recent submissions
    recent_df = merged_df.sort_values(by="timestamp", ascending=False)[
        ["submission_id", "Name", "Year of Grad", "CCA", "distance", "activity_date"]
    ].rename(columns={"distance": "distance in km"}).head(10)
    st.subheader("🕒 Recent Submissions")
    st.dataframe(recent_df)

# =========================
# ADMIN PANEL
# =========================
st.header("🔐 Admin Panel")
admin_pw = st.text_input("Enter admin password", type="password")

if admin_pw == ADMIN_PASSWORD:
    st.success("Admin access granted")

    # Delete submissions
    st.subheader("🗑️ Delete Submission")
    if not df.empty:
        submission_id_to_delete = st.selectbox("Select submission ID to delete", df["submission_id"].tolist())
        if st.button("Delete Submission"):
            df = df[df["submission_id"] != submission_id_to_delete]
            conn.update(
                spreadsheet=st.secrets["connections"]["gsheets"]["spreadsheet"],
                data=df
            )
            st.success(f"Submission {submission_id_to_delete} deleted!")
            st.rerun()

    # Delete participants
    st.subheader("🗑️ Delete Participant")
    if not participants_df.empty:
        participant_to_delete = st.selectbox("Select participant to delete", participants_df["Name"].tolist())
        if st.button("Delete Participant"):
            participants_df = participants_df[participants_df["Name"] != participant_to_delete]
            conn.update(
                spreadsheet=st.secrets["connections"]["gsheets"]["participants_spreadsheet"],
                data=participants_df
            )
            st.success(f"Participant {participant_to_delete} deleted!")
            st.rerun()
