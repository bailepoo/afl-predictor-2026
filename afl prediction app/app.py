import streamlit as st
from engine import (
    predict_round,
    season_accuracy,
    projected_ladder,
    premiership_probabilities,
)
import math

def margin_to_probability(margin):
    prob = 100 / (1 + math.exp(-margin / 10))
    return round(prob, 2)

# ---------------------------------------------------------
# PAGE CONFIG + THEME
# ---------------------------------------------------------
st.set_page_config(page_title="AFL Prediction Engine", layout="wide")

st.markdown("""
    <style>
        .stApp {
            background-color: #0A0A0A;
        }
        h1, h2, h3, h4, h5 {
            font-family: 'Segoe UI', sans-serif;
            font-weight: 600;
            color: #FFFFFF;
        }
        .block-container {
            padding-top: 2rem;
        }
    </style>
""", unsafe_allow_html=True)

st.markdown(
    """
    <h1 style='text-align:center;'>AFL Prediction Engine</h1>
    <p style='text-align:center; font-size:18px; opacity:0.85;'>
        (demonstration purposes only)
    </p>
    """,
    unsafe_allow_html=True
)


# ---------------------------------------------------------
# TEAM LOGOS (PNG)
# ---------------------------------------------------------
TEAM_LOGOS = {
    "Adelaide": "https://squiggle.com.au/wp-content/themes/squiggle/assets/images/Adelaide.png",
    "Brisbane Lions": "https://squiggle.com.au/wp-content/themes/squiggle/assets/images/Brisbane.png",
    "Carlton": "https://squiggle.com.au/wp-content/themes/squiggle/assets/images/Carlton.png",
    "Collingwood": "https://squiggle.com.au/wp-content/themes/squiggle/assets/images/Collingwood.png",
    "Essendon": "https://squiggle.com.au/wp-content/themes/squiggle/assets/images/Essendon.png",
    "Fremantle": "https://squiggle.com.au/wp-content/themes/squiggle/assets/images/Fremantle.png",
    "Geelong": "https://squiggle.com.au/wp-content/themes/squiggle/assets/images/Geelong.png",
    "Gold Coast": "https://squiggle.com.au/wp-content/themes/squiggle/assets/images/GoldCoast.png",
    "Greater Western Sydney": "https://squiggle.com.au//wp-content/themes/squiggle/assets/images/Giants.png",
    "Hawthorn": "https://squiggle.com.au/wp-content/themes/squiggle/assets/images/Hawthorn.png",
    "Melbourne": "https://squiggle.com.au/wp-content/themes/squiggle/assets/images/Melbourne.png",
    "North Melbourne": "https://squiggle.com.au/wp-content/themes/squiggle/assets/images/NorthMelbourne.png",
    "Port Adelaide": "https://squiggle.com.au/wp-content/themes/squiggle/assets/images/PortAdelaide.png",
    "Richmond": "https://squiggle.com.au/wp-content/themes/squiggle/assets/images/Richmond.png",
    "St Kilda": "https://squiggle.com.au/wp-content/themes/squiggle/assets/images/StKilda.png",
    "Sydney": "https://squiggle.com.au/wp-content/themes/squiggle/assets/images/Sydney.png",
    "West Coast": "https://squiggle.com.au/wp-content/themes/squiggle/assets/images/WestCoast.png",
    "Western Bulldogs": "https://squiggle.com.au/wp-content/themes/squiggle/assets/images/Bulldogs.png",
}

# ---------------------------------------------------------
# MATCH TILE COMPONENT
# ---------------------------------------------------------
def match_tile(p):
    home = p["home"]
    away = p["away"]
    winner = p["winner"]
    confidence = p["confidence"]

    # Compute win chances
    margin = p["predicted_home_score"] - p["predicted_away_score"]
    home_chance = round(margin_to_probability(margin), 2)
    away_chance = round(100 - home_chance, 2)

    # Emoji ticks/crosses
    home_icon = "✅" if winner == home else "❌"
    away_icon = "✅" if winner == away else "❌"

    # Layout: tick | logo | name+chance | score | name+chance | logo | tick
    col_tick_left, col_home_logo, col_home_info, col_score, col_away_info, col_away_logo, col_tick_right = st.columns(
        [1, 2, 3, 3, 3, 2, 1]
    )

    # LEFT TICK
    with col_tick_left:
        st.markdown(
            f"<div style='text-align:center; font-size:32px;'>{home_icon}</div>",
            unsafe_allow_html=True
        )

    # HOME LOGO (centred, fixed height)
    with col_home_logo:
        st.markdown(
            f"""
            <div style='text-align:center;'>
                <img src="{TEAM_LOGOS[home]}" height="70">
            </div>
            """,
            unsafe_allow_html=True
        )

    # HOME NAME + CHANCE
    with col_home_info:
        st.markdown(
            f"""
            <div style='text-align:center; color:white;'>
                <div style='font-size:18px;'><b>{home}</b></div>
                <div style='font-size:15px; opacity:0.9;'>Win Chance: <b>{home_chance:.2f}%</b></div>
            </div>
            """,
            unsafe_allow_html=True
        )

    # SCORE + CONFIDENCE
    with col_score:
        st.markdown(
            f"""
            <div style='text-align:center; color:white; line-height:1.2;'>
                <div style='font-size:40px; font-weight:700; margin-bottom:4px;'>
                    {p['predicted_home_score']} – {p['predicted_away_score']}
                </div>
                <div style='font-size:15px; opacity:0.9;'>
                    Confidence: <b>{confidence}</b>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

    # AWAY NAME + CHANCE
    with col_away_info:
        st.markdown(
            f"""
            <div style='text-align:center; color:white;'>
                <div style='font-size:18px;'><b>{away}</b></div>
                <div style='font-size:15px; opacity:0.9;'>Win Chance: <b>{away_chance:.2f}%</b></div>
            </div>
            """,
            unsafe_allow_html=True
        )

    # AWAY LOGO (centred, fixed height)
    with col_away_logo:
        st.markdown(
            f"""
            <div style='text-align:center;'>
                <img src="{TEAM_LOGOS[away]}" height="70">
            </div>
            """,
            unsafe_allow_html=True
        )

    # RIGHT TICK
    with col_tick_right:
        st.markdown(
            f"<div style='text-align:center; font-size:32px;'>{away_icon}</div>",
            unsafe_allow_html=True
        )

    st.markdown("---")

# ---------------------------------------------------------
# SIDEBAR
# ---------------------------------------------------------
st.sidebar.header("Settings")
year = st.sidebar.number_input("Season Year", min_value=2012, max_value=2030, value=2025)

menu = st.sidebar.radio(
    "Select Mode",
    [
        "Predict a Round",
        "Season Accuracy",
        "Projected Ladder",
        "Premiership Probabilities",
    ]
)

# ---------------------------------------------------------
# PREDICT A ROUND
# ---------------------------------------------------------
if menu == "Predict a Round":
    st.header("Round Predictions")

    round_number = st.number_input("Round Number", min_value=1, max_value=30, value=1)

    if st.button("Predict Round"):
        preds = predict_round(year, round_number)

        if not preds:
            st.warning("No games found for that round/year.")
        else:
            for p in preds:
                match_tile(p)

# ---------------------------------------------------------
# SEASON ACCURACY
# ---------------------------------------------------------
elif menu == "Season Accuracy":
    st.header("Season Accuracy")

    if st.button("Calculate Accuracy"):
        acc, correct, total = season_accuracy(year)
        st.metric("Accuracy", f"{acc:.2f}%")
        st.write(f"Correct: **{correct}** / {total}")

# ---------------------------------------------------------
# PROJECTED LADDER
# ---------------------------------------------------------
elif menu == "Projected Ladder":
    st.header("Projected Ladder")

    if st.button("Generate Ladder"):
        ladder = projected_ladder(year)

        if not ladder:
            st.warning("No ladder data available.")
        else:
            for i, (team, wins) in enumerate(ladder, start=1):
                col1, col2 = st.columns([1, 5])
                with col1:
                    logo = TEAM_LOGOS.get(team)
                    if logo:
                        st.image(logo, width=40)
                with col2:
                    st.write(f"{i}. **{team}** — {wins} wins")

# ---------------------------------------------------------
# PREMIERSHIP PROBABILITIES
# ---------------------------------------------------------
elif menu == "Premiership Probabilities":
    st.header("Premiership Probabilities")

    if st.button("Calculate Probabilities"):
        probs = premiership_probabilities(year)

        if not probs:
            st.warning("No probability data available.")
        else:
            for team, p in probs:
                col1, col2 = st.columns([1, 5])
                with col1:
                    logo = TEAM_LOGOS.get(team)
                    if logo:
                        st.image(logo, width=40)
                with col2:
                    st.write(f"**{team}:** {p}%")
