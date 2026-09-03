import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, date
import uuid
from streamlit_gsheets import GSheetsConnection

# =========================
# CONFIG
# =========================
GOAL_KM = 70000
START_DATE = date(2026, 8, 29)
END_DATE = date(2027, 7, 2)
MAX_DISTANCE = 100

# =========================
# GOOGLE SHEETS SETUP
# =========================
gsheets_conn = st.connection(
    "gsheets",
    type=GSheetsConnection
)

PARTICIPANTS_SHEET_URL = st.secrets["connections"]["gsheets"][
    "participants_spreadsheet"
]

SUBMISSIONS_SHEET_URL = st.secrets["connections"]["gsheets"][
    "spreadsheet"
]

PARTICIPANTS_WORKSHEET = "Participants"
SUBMISSIONS_WORKSHEET = "Submissions"

# =========================
# HELPERS
# =========================
def clean_text(value):
    return " ".join(str(value).strip().split())


def key_text(value):
    return clean_text(value).lower()


def get_participants():
    try:
        participants = gsheets_conn.read(
            spreadsheet=PARTICIPANTS_SHEET_URL,
            worksheet=PARTICIPANTS_WORKSHEET,
            ttl=5
        )

        required_columns = [
            "participant_id",
            "name",
            "grad_year",
            "cca",
            "name_key",
            "cca_key"
        ]

        if participants.empty:
            return pd.DataFrame(columns=required_columns)

        participants = participants.dropna(how="all")

        for column in required_columns:
            if column not in participants.columns:
                participants[column] = ""

                
        participants = participants[required_columns].copy()
        
        for column in required_columns:
            participants[column] = (
                participants[column]
                .fillna("")
                .astype(str)
            )
        
        participants["grad_year"] = (
            participants["grad_year"]
            .str.replace(".0", "", regex=False)
        )
        
        return participants


        for column in required_columns:
            participants[column] = (
                participants[column]
                .fillna("")
                .astype(str)
            )

        return participants

    except Exception as error:
        st.error(f"Unable to read participant records: {error}")
        return pd.DataFrame(
            columns=[
                "participant_id",
                "name",
                "grad_year",
                "cca",
                "name_key",
                "cca_key"
            ]
        )


def save_participants(participants):
    participants = participants[
        [
            "participant_id",
            "name",
            "grad_year",
            "cca",
            "name_key",
            "cca_key"
        ]
    ].copy()

    gsheets_conn.update(
        spreadsheet=PARTICIPANTS_SHEET_URL,
        worksheet=PARTICIPANTS_WORKSHEET,
        data=participants
    )

def generate_participant_id():

    participants = get_participants()

    if participants.empty:
        return "CG70-0001"

    existing_ids = (
        participants["participant_id"]
        .fillna("")
        .astype(str)
    )

    numeric_ids = []

    for pid in existing_ids:

        if pid.startswith("CG70-"):

            try:
                numeric_ids.append(
                    int(pid.replace("CG70-", ""))
                )

            except ValueError:
                pass

    if not numeric_ids:
        return "CG70-0001"

    next_id = max(numeric_ids) + 1

    return f"CG70-{next_id:04d}"


def add_participant(name, grad_year, cca):

    name = clean_text(name)
    grad_year = clean_text(grad_year)
    cca = clean_text(cca)

    participants = get_participants()

    duplicate = participants[
        (participants["name_key"] == key_text(name)) &
        (participants["grad_year"] == grad_year) &
        (participants["cca_key"] == key_text(cca))
    ]

    if not duplicate.empty:
        return False, "Participant already exists."

    participant_id = generate_participant_id()

    new_participant = pd.DataFrame(
        [
            {
                "participant_id": participant_id,
                "name": name,
                "grad_year": grad_year,
                "cca": cca,
                "name_key": key_text(name),
                "cca_key": key_text(cca)
            }
        ]
    )

    updated_participants = pd.concat(
        [participants, new_participant],
        ignore_index=True
    )

    save_participants(updated_participants)

    return True, (
        f"Participant added successfully "
        f"({participant_id})"
    )


def get_submissions():
    required_columns = [
        "submission_id",
        "participant_id",
        "distance",
        "activity_date",
        "timestamp"
    ]

    try:
        submissions = gsheets_conn.read(
            spreadsheet=SUBMISSIONS_SHEET_URL,
            worksheet=SUBMISSIONS_WORKSHEET,
            ttl=5
        )

        if submissions.empty:
            return pd.DataFrame(columns=required_columns)

        submissions = submissions.dropna(how="all")

        for column in required_columns:
            if column not in submissions.columns:
                submissions[column] = ""

        submissions = submissions[required_columns].copy()

        submissions["submission_id"] = (
            submissions["submission_id"].fillna("").astype(str)
        )

        submissions["participant_id"] = (
            submissions["participant_id"].fillna("").astype(str)
        )

        submissions["activity_date"] = (
            submissions["activity_date"].fillna("").astype(str)
        )

        submissions["timestamp"] = (
            submissions["timestamp"].fillna("").astype(str)
        )

        submissions["distance"] = pd.to_numeric(
            submissions["distance"],
            errors="coerce"
        ).fillna(0.0)

        return submissions

    except Exception as error:
        st.error(f"Unable to read submission records: {error}")
        return pd.DataFrame(columns=required_columns)


def save_submissions(submissions):
    submissions = submissions[
        [
            "submission_id",
            "participant_id",
            "distance",
            "activity_date",
            "timestamp"
        ]
    ].copy()

    gsheets_conn.update(
        spreadsheet=SUBMISSIONS_SHEET_URL,
        worksheet=SUBMISSIONS_WORKSHEET,
        data=submissions
    )




def add_submission(
    submission_id,
    participant_id,
    distance,
    activity_date
):
    submissions = get_submissions()

    new_submission = pd.DataFrame(
        [
            {
                "submission_id": submission_id,
                "participant_id": participant_id,
                "distance": float(distance),
                "activity_date": activity_date,
                "timestamp": datetime.now().strftime(
                    "%Y-%m-%d %H:%M:%S"
                )
            }
        ]
    )

    updated_submissions = pd.concat(
        [submissions, new_submission],
        ignore_index=True
    )

    save_submissions(updated_submissions)


def get_data():
    submissions = get_submissions()
    participants = get_participants()

    if submissions.empty or participants.empty:
        return pd.DataFrame(
            columns=[
                "submission_id",
                "participant_id",
                "distance",
                "activity_date",
                "timestamp",
                "name",
                "grad_year",
                "cca"
            ]
        )

    return submissions.merge(
        participants[
            [
                "participant_id",
                "name",
                "grad_year",
                "cca"
            ]
        ],
        on="participant_id",
        how="left"
    )

# =========================
# HEADER
# =========================
st.image("cedar70000km4.png", use_container_width=True)

st.title("🏃‍♀️‍➡️ Cedar Girls 70th Anniversary Distance Challenge")

st.markdown("""
**🎯 Goal:** 70,000 km  
**📅 Period:** 29 August 2026 → 02 July 2027  
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

    activity_date_text = activity_date.strftime("%Y-%m-%d")
    existing_submissions = get_submissions()
    
    existing = existing_submissions[
        (
            existing_submissions["participant_id"] ==
            str(selected_participant_id)
        ) &
        (
            existing_submissions["activity_date"] ==
            activity_date_text
        )
    ]
    
    if not existing.empty:
        st.error("❌ Already submitted for this activity date.")
        st.stop()

    submission_id = str(uuid.uuid4())[:8]
    
    add_submission(
        submission_id,
        selected_participant_id,
        distance,
        activity_date_text
    )
    
    st.success(
        f"✅ Submitted! Your Submission ID is {submission_id}"
    )
    
    st.rerun()


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
    st.success("✅ Event completed!")

else:
    progress_days = (
        (today - START_DATE).days /
        (END_DATE - START_DATE).days
    )

    pct = progress_days * 100

    st.write(f"**Challenge Duration Progress:** {pct:.1f}%")
    st.progress(progress_days)

    # Milestone achievements
    milestones = []

    for milestone in [25, 50, 75, 100]:
        if pct >= milestone:
            milestones.append(f"✅ {milestone}%")
        else:
            milestones.append(f"⬜ {milestone}%")

    st.write(" | ".join(milestones))

# =========================
# FAQ
# =========================
st.markdown("---")
 
st.header("❓ FAQ & Challenge Guidelines")
 
st.write(
"Have a question? Check our FAQ below! "
"If you don't see your question here, feel free to reach out to @Soffiah."
)
 
with st.expander("1. Can I make multiple entries per day?"):
    st.write("""
    No, only one entry is allowed per day. If you've walked, jogged, or run multiple times in a day,
    simply add up all the distances and submit the total distance for that day.
    """)
 
with st.expander("2. What should I do if I made an erroneous entry?"):
    st.write("""
    No worries! Just let @Soffiah know and provide your Submission ID (if available).
    The entry can be edited or deleted, and you can then submit the correct distance.
    """)
 
with st.expander("3. What happens if I ran yesterday but forgot to log it?"):
    st.write("""
    That's perfectly fine! You can backdate your entry. Simply select the date you missed
    and submit the distance you covered on that day.
    """)
 
with st.expander("4. I did a Zumba / Pilates / Badminton / Pickleball / Tennis session. Can I add that in?"):
    st.write("""
    Sorry, not for this challenge. We're currently tracking only walking, jogging,
    and running distances so that everyone is measured using the same criteria.
    """)
 
with st.expander("5. I went for a hike. Can I add that in?"):
    st.write("""
    Yes! Hiking counts as walking, so feel free to log the distance covered during your hike.
    """)
 
with st.expander("6. I only walk or run on a treadmill. Does that count?"):
    st.write("""
    Absolutely! Both indoor treadmill and outdoor walking, jogging and running distances are accepted.
     
    Simply log the distance shown on your treadmill or fitness device as you would for any other walk or run.
    """)
 
with st.expander("7. I completed a triathlon. Can I include my running, cycling and swimming distances?"):
    st.write("""
    First of all, wow, that's impressive! 💪
     
    For this challenge, we're only tracking walking, jogging and running distances.
    Please log only your running distance from the triathlon.
    """)
 
with st.expander("8. I have an Apple Watch or Garmin. Can I sync my data directly?"):
    st.write("""
    Unfortunately not. As this is a community initiative run on a $0 budget,
    we're unable to support direct syncing from fitness devices at the moment.
    """)
 
with st.expander("9. I use Strava, Runkeeper or another fitness app. Can the site read my activity automatically?"):
    st.write("""
    Not at the moment. As this is a community initiative run on a $0 budget,
    you'll need to enter your distances manually.
    """)
 
with st.expander("10. Should I upload screenshots or records from my fitness device to substantiate my entry?"):
    st.write("""
    No need! We're operating on trust and honesty because Cedarians are 🎼 courteous, honest every day. 🎶🎵
     
    That said, we'd love for you to share your screenshots, routes, photos and achievements
    in the WhatsApp group to motivate and inspire fellow participants!
    """)
 
with st.expander("11. I can't see my name in the participant list. What should I do?"):
    st.write("""
    Please complete the registration form using the link below:
     
    🔗 https://docs.google.com/spreadsheets/d/14n5bPduKfCls8ObaRoyX-IbYBoA9fCmXvw-RlN_Mk_g/edit?gid=1986767549#gid=1986767549
    
    Please allow approximately 5–7 days for your name to be added to the participant list.
     
    In the meantime, continue tracking your distances. Once your name has been added,
    you'll be able to backdate your entries and log any walks, jogs or runs you've already completed.
    """)
 
with st.expander("12. How accurate do my distances need to be?"):
    st.write("""
    Please provide your best and most honest estimate based on your fitness tracker,
    fitness app, treadmill reading or route distance. Every kilometre contributes
    towards our shared goal of 70,000 km! 🎉
    """)
 
st.info(
"❤️ Thank you for being part of the Cedar Girls 70th Anniversary Distance Challenge. "
"Every kilometre counts towards our shared goal of 70,000 km!"
)


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
            if not name or not year or not cca:
                st.warning("Please complete all participant fields.")
            else:
                added, message = add_participant(
                    name,
                    year,
                    cca
                )

                if added:
                    st.success(f"✅ {message}")
                    st.rerun()
                else:
                    st.warning(message)


    # Participant list
    st.subheader("📋 Participant List")
    if not participants_df.empty:
        st.dataframe(participants_df[["name", "grad_year", "cca"]])
        
    # Edit participants
    st.subheader("✏️ Edit Participant")
    
    if not participants_df.empty:
    
        selected_edit = st.selectbox(
            "Select participant",
            participants_df["display"],
            key="edit"
        )
    
        row = participants_df[
            participants_df["display"] == selected_edit
        ].iloc[0]
    
        edit_name = st.text_input(
            "Name",
            value=row["name"]
        )
    
        edit_year = st.text_input(
            "Year",
            value=row["grad_year"]
        )
    
        edit_cca = st.text_input(
            "CCA",
            value=row["cca"]
        )
    
        if st.button("Update"):
    
            updated_participants = get_participants()
    
            selected_id = str(row["participant_id"])
    
            updated_participants.loc[
                updated_participants["participant_id"] == selected_id,
                "name"
            ] = clean_text(edit_name)
    
            updated_participants.loc[
                updated_participants["participant_id"] == selected_id,
                "grad_year"
            ] = clean_text(edit_year)
    
            updated_participants.loc[
                updated_participants["participant_id"] == selected_id,
                "cca"
            ] = clean_text(edit_cca)
    
            updated_participants.loc[
                updated_participants["participant_id"] == selected_id,
                "name_key"
            ] = key_text(edit_name)
    
            updated_participants.loc[
                updated_participants["participant_id"] == selected_id,
                "cca_key"
            ] = key_text(edit_cca)
    
            save_participants(updated_participants)
    
            st.success("✅ Updated")
            st.rerun()
    
    else:
        st.info("No participants available.")

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
            
            participant_id = str(delete_row["participant_id"]).strip()
            
            updated_submissions = get_submissions()
            updated_submissions = updated_submissions[
                updated_submissions["participant_id"] != participant_id
            ].reset_index(drop=True)
            
            updated_participants = get_participants()
            updated_participants = updated_participants[
                updated_participants["participant_id"] != participant_id
            ].reset_index(drop=True)
            
            save_submissions(updated_submissions)
            save_participants(updated_participants)
            
            st.success("✅ Participant and all related entries deleted")
            st.rerun()


    
    # Delete entries
    if not df.empty:
        delete_id = st.text_input("Delete submission ID")

        if st.button("Delete Entry"):
        
            updated_submissions = get_submissions()
        
            updated_submissions = updated_submissions[
                updated_submissions["submission_id"] !=
                clean_text(delete_id)
            ].reset_index(drop=True)
        
            save_submissions(updated_submissions)
        
            st.success("✅ Deleted")
            st.rerun()
        
        if st.button("⚠️ Delete ALL"):
        
            empty_submissions = pd.DataFrame(
                columns=[
                    "submission_id",
                    "participant_id",
                    "distance",
                    "activity_date",
                    "timestamp"
                ]
            )
        
            save_submissions(empty_submissions)
        
            st.success("✅ Cleared all submissions")
            st.rerun()


