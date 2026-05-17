import streamlit as st
import json
import engine

# ---------------------------------------------------------
# TEAM LOGOS
# ---------------------------------------------------------
TEAM_LOGOS = {
    "Adelaide": "https://squiggle.com.au/wp-content/themes/squiggle/assets/images/Adelaide.png",
    "Brisbane": "https://squiggle.com.au/wp-content/themes/squiggle/assets/images/Lions.png",
    "Carlton": "https://squiggle.com.au/wp-content/themes/squiggle/assets/images/Carlton.png",
    "Collingwood": "https://squiggle.com.au/wp-content/themes/squiggle/assets/images/Collingwood.png",
    "Essendon": "https://squiggle.com.au/wp-content/themes/squiggle/assets/images/Essendon.png",
    "Fremantle": "https://squiggle.com.au/wp-content/themes/squiggle/assets/images/Fremantle.png",
    "Geelong": "https://squiggle.com.au/wp-content/themes/squiggle/assets/images/Geelong.png",
    "Gold Coast": "https://squiggle.com.au/wp-content/themes/squiggle/assets/images/GoldCoast.png",
    "GWS": "https://squiggle.com.au/wp-content/themes/squiggle/assets/images/Giants.png",
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
# LEADERBOARD STORAGE
# ---------------------------------------------------------
LEADERBOARD_FILE = "leaderboard.json"

def load_leaderboard():
    try:
        with open(LEADERBOARD_FILE, "r") as f:
            return json.load(f)
    except:
        return []

def save_leaderboard(data):
    with open(LEADERBOARD_FILE, "w") as f:
        json.dump(data, f, indent=4)

def update_leaderboard(entry):
    data = load_leaderboard()
    data.append(entry)
    save_leaderboard(data)

# ---------------------------------------------------------
# STREAMLIT APP
# ---------------------------------------------------------
def main():

    st.markdown(
        """
        <h1 style='text-align:center;'>🏉 AFL Prediction Engine</h1>
        <p style='text-align:center; font-size:18px; opacity:0.85;'>
            Balanced Model • Last‑6‑Rounds Form • Score + Confidence Predictions
        </p>
        """,
        unsafe_allow_html=True
    )

    st.sidebar.header("Settings")

    year = st.sidebar.number_input("Season year", min_value=2010, max_value=2100, value=2024, step=1)

    st.sidebar.markdown("---")
    st.sidebar.subheader("Actions")

    run_round = st.sidebar.button("Predict a round")
    run_accuracy = st.sidebar.button("Run accuracy test")
    run_ladder = st.sidebar.button("Projected ladder")
    run_prem = st.sidebar.button("Premiership probabilities")

    st.markdown("---")

    # ---------------------------------------------------------
    # ROUND PREDICTION
    # ---------------------------------------------------------
    if run_round:
        games = engine.get_games(year)
        rounds = sorted({g["round"] for g in games})

        if not rounds:
            st.error("No games found for this year.")
        else:
            round_number = st.number_input(
                "Round to predict",
                min_value=min(rounds),
                max_value=max(rounds),
                value=max(rounds),
                step=1
            )

            preds = engine.predict_round(year, round_number)

            st.subheader(f"Round {round_number} Predictions")

            for p in preds:

                # LEFT → RIGHT LAYOUT
                col_tick_left, col_logo_home, col_home, col_score, col_away, col_logo_away, col_tick_right = st.columns([1,2,3,3,3,2,1])

                # LEFT TICK
                with col_tick_left:
                    if p["winner"] == p["home"]:
                        st.markdown("<h1 style='text-align:center;'>✔️</h1>", unsafe_allow_html=True)
                    else:
                        st.markdown("<h1 style='text-align:center; opacity:0.3;'>✔️</h1>", unsafe_allow_html=True)

                # HOME LOGO
                with col_logo_home:
                    st.markdown(
                        f"""
                        <div style='text-align:center;'>
                            <img src="{TEAM_LOGOS[p['home']]}" height="70">
                        </div>
                        """,
                        unsafe_allow_html=True
                    )

                # HOME NAME + ACCURACY
                with col_home:
                    st.markdown(
                        f"""
                        <div style='text-align:center; font-size:20px; font-weight:600;'>
                            {p['home']}
                        </div>
                        <div style='text-align:center; font-size:14px; opacity:0.7;'>
                            Win Chance: {round(50 + p['raw_diff']*5, 2)}%
                        </div>
                        """,
                        unsafe_allow_html=True
                    )

                # SCORE + CONFIDENCE
                with col_score:
                    st.markdown(
                        f"""
                        <div style='text-align:center; font-size:26px; font-weight:700;'>
                            {p['predicted_home_score']} – {p['predicted_away_score']}
                        </div>
                        <div style='text-align:center; font-size:16px; opacity:0.8;'>
                            Confidence: {p['confidence']}
                        </div>
                        """,
                        unsafe_allow_html=True
                    )

                # AWAY NAME + ACCURACY
                with col_away:
                    st.markdown(
                        f"""
                        <div style='text-align:center; font-size:20px; font-weight:600;'>
                            {p['away']}
                        </div>
                        <div style='text-align:center; font-size:14px; opacity:0.7;'>
                            Win Chance: {round(50 - p['raw_diff']*5, 2)}%
                        </div>
                        """,
                        unsafe_allow_html=True
                    )

                # AWAY LOGO
                with col_logo_away:
                    st.markdown(
                        f"""
                        <div style='text-align:center;'>
                            <img src="{TEAM_LOGOS[p['away']]}" height="70">
                        </div>
                        """,
                        unsafe_allow_html=True
                    )

                # RIGHT TICK
                with col_tick_right:
                    if p["winner"] == p["away"]:
                        st.markdown("<h1 style='text-align:center;'>✔️</h1>", unsafe_allow_html=True)
                    else:
                        st.markdown("<h1 style='text-align:center; opacity:0.3;'>✔️</h1>", unsafe_allow_html=True)

                st.markdown("---")

    # ---------------------------------------------------------
    # ACCURACY TEST
    # ---------------------------------------------------------
    if run_accuracy:
        st.subheader("Accuracy Test")

        acc, correct, total = engine.season_accuracy(year)

        st.markdown(f"### Accuracy: **{acc:.2f}%** ({correct}/{total})")

        name = st.text_input("Name for leaderboard (optional)", value="Anonymous")

        if st.button("Save result to leaderboard"):
            entry = {
                "year": year,
                "accuracy": acc,
                "correct": correct,
                "total": total,
                "rounds_back": 6,
                "metrics": list(engine.METRIC_FUNCS.keys()),
                "user": name
            }
            update_leaderboard(entry)
            st.success("Saved to leaderboard!")

    # ---------------------------------------------------------
    # PROJECTED LADDER
    # ---------------------------------------------------------
    if run_ladder:
        st.subheader("Projected Ladder")

        ladder = engine.projected_ladder(year)

        for i, (team, wins) in enumerate(ladder, start=1):
            st.markdown(f"**{i}. {team} — {wins} wins**")

    # ---------------------------------------------------------
    # PREMIERSHIP PROBABILITIES
    # ---------------------------------------------------------
    if run_prem:
        st.subheader("Premiership Probabilities")

        probs = engine.premiership_probabilities(year)

        for team, p in probs:
            st.markdown(f"**{team}: {p}%**")

    # ---------------------------------------------------------
    # LEADERBOARD
    # ---------------------------------------------------------
    st.markdown("---")
    st.subheader("🏆 Accuracy Leaderboard")

    lb = load_leaderboard()

    if not lb:
        st.info("No leaderboard entries yet. Run an accuracy test and save a result.")
    else:
        lb_sorted = sorted(lb, key=lambda x: x["accuracy"], reverse=True)

        for row in lb_sorted[:20]:
            st.markdown(
                f"**{row['accuracy']:.2f}%** ({row['correct']}/{row['total']}) — "
                f"Year: {row['year']} — Rounds: {row['rounds_back']} — "
                f"Metrics: {', '.join(row['metrics'])} — User: {row['user']}"
            )

if __name__ == "__main__":
    main()
