import streamlit as st
import pandas as pd
from datetime import datetime, date
import uuid
import plotly
from streamlit_gsheets import GSheetsConnection

# =========================
# CONFIG
# =========================
GOAL_KM = 70000
START_DATE = date(2026, 6, 1)
END_DATE = date(2027, 2, 1)
MAX_DISTANCE = 100

ADMIN_PASSWORD = st.secrets["ADMIN_PASSWORD"

# =========================
# CONNECT TO GOOGLE SHEETS
# =========================
conn = st.connection("gsheets", type=GSheetsConnection)

# Always fresh read (no caching)
df = conn.read(
    spreadsheet=st.secrets["connections"]["gsheets"]["spreadsheet"],
    ttl=0
)

# =========================
# UI HEADER
# =========================
st.image("cedar70000km2.png", use_container_width=True)
# st.title("🏃‍♀️ Cedar Girls 70th Anniversary Distance Challenge") #
st.markdown("""
**🎯 Goal:** 70,000 km  
**📅 Period:** 1 June 2026 → 1 Feb 2027  
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

distance = st.number_input("Distance (km)", min_value=0.1, step=0.1)

if st.button("Submit"):

    if not name:
        st.warning("Enter your name")
        st.stop()

    if distance > MAX_DISTANCE:
        st.warning(f"Max {MAX_DISTANCE} km allowed")
        st.stop()

    # ✅ Prevent duplicate
    if not df.empty:
        duplicate = df[
            (df["name"].str.lower() == name.lower()) &
            (df["activity_date"] == activity_date.strftime("%Y-%m-%d"))
        ]

        if not duplicate.empty:
            st.error("Already submitted for this date")
            st.stop()

    # ✅ Create new row
    new_data = pd.DataFrame([{
        "submission_id": str(uuid.uuid4())[:8],
        "name": name,
        "distance": distance,
        "activity_date": activity_date.strftime("%Y-%m-%d"),
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }])

    # ✅ Append + write back
    updated_df = pd.concat([df, new_data], ignore_index=True)
    conn.update(data=updated_df)

    st.success("✅ Submission added!")
    st.rerun()

# =========================
# DISPLAY DATA
# =========================
st.header("📊 Progress")

# ✅ Default value (prevents crash)
total_km = 0

if not df.empty:
    total_km = df["distance"].astype(float).sum()

# ✅ Progress calculations
remaining_km = max(GOAL_KM - total_km, 0)
percent = total_km / GOAL_KM if GOAL_KM > 0 else 0

# ✅ FUN PROGRESS DISPLAY
st.subheader("🏁 Let’s Reach 70,000 km together!")

st.progress(min(percent, 1.0))

st.markdown(f"""
### 🌟 {total_km:.0f} km completed!
💪 Only **{remaining_km:.0f} km** more to go!
""")

# =========================
# DONUT CHART (FUN VISUAL)
# =========================
import plotly.graph_objects as go

fig = go.Figure(data=[go.Pie(
    labels=["Completed 🎉", "Remaining 💪"],
    values=[total_km, remaining_km],
    hole=0.65,
    marker=dict(colors=["#FF4B4B", "#E0E0E0"])
)])

fig.update_layout(
    showlegend=True,
    annotations=[dict(
        text=f"{percent*100:.1f}%<br>Done!",
        x=0.5, y=0.5,
        font_size=22,
        showarrow=False
    )]
)

st.plotly_chart(fig)

# =========================
# EXTRA: MILESTONES 🎉
# =========================
milestones = [100, 500, 1000, 5000, 10000, 15000, 20000, 25000, 30000, 35000, 40000, 45000, 50000, 55000, 60000, 65000, 70000]

for m in milestones:
    if total_km >= m:
        st.success(f"🎉 WE HIT {m:,} KM!")

if total_km >= GOAL_KM:
    st.balloons()
    st.success("🏆 AMAZING! 70,000 KM GOAL ACHIEVED!")

# =========================
# LEADERBOARD + RECENT
# =========================
if not df.empty:
    # Leaderboard
    leaderboard = df.groupby("name")["distance"].sum().sort_values(ascending=False)
    st.subheader("🏆 Leaderboard")
    st.dataframe(leaderboard.reset_index().head(10))

    # Recent
    st.subheader("🕒 Recent Submissions")
    st.dataframe(
        df.sort_values(by="timestamp", ascending=False)
        [["submission_id", "name", "distance", "activity_date"]]
        .head(10)
    )
# =========================
# ADMIN PANEL
# =========================
st.markdown("---")
st.header("🔐 Admin Panel")

password = st.text_input("Enter admin password", type="password")

if password == ADMIN_PASSWORD:

    st.success("Admin access granted")

    if not df.empty:
        st.subheader("🧾 All Entries")

        st.dataframe(df)

        # ✅ Delete specific entry
        delete_id = st.text_input("Enter submission_id to delete")

        if st.button("Delete Entry"):
            new_df = df[df["submission_id"] != delete_id]
            conn.update(data=new_df)
            st.success("Entry deleted")
            st.rerun()

        # ✅ Reset ALL data
        if st.button("⚠️ Delete ALL entries"):
            empty_df = pd.DataFrame(columns=df.columns)
            conn.update(data=empty_df)
            st.success("All entries deleted")
            st.rerun()

else:
    st.info("Enter password to access admin panel")
