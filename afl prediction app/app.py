import streamlit as st
import math
import engine
from engine import (
    predict_round,
    season_accuracy,
    projected_ladder,
    premiership_probabilities,
)

# ---------------------------------------------------------
# PAGE CONFIG + DARK THEME
# ---------------------------------------------------------
st.set_page_config(page_title="AFL Prediction Engine", layout="wide")

st.markdown("""
    <style>
        h1, h2, h3, h4, h5, h6, p, div, span {
            font-family: 'rockwell';
        }
        .team-logo {
            filter: drop-shadow(0px 0px 7px rgba(255,255,255,1));
        }
        .score-box {
            font-size: 40px;
            font-weight: 700;
            padding: 8px 0;
            backdrop-filter: blur(12px);
            -webkit-backdrop-filter: blur(12px);
            border-radius: 10px;
            background: rgba(175,175,175,0.2);
            border: 1px solid rgba(255,255,255,0.25);
            box-shadow: 0 0 12px rgba(255,255,255,0.15);
        }
    </style>
""", unsafe_allow_html=True)

st.markdown(
    """
    <h1 style='text-align:center; margin-bottom: -20px; '>AFL Prediction Engine</h1>
    <p style='text-align:center; margin-bottom: -5px; font-size:20px; opacity:0.85;'>(for demonstration purposes only)</p>
    """,
    unsafe_allow_html=True
)

# ---------------------------------------------------------
# TEAM LOGOS
# ---------------------------------------------------------
TEAM_LOGOS = {
    "Adelaide": "https://squiggle.com.au/wp-content/themes/squiggle/assets/images/Adelaide.png",
    "Brisbane": "https://squiggle.com.au/wp-content/themes/squiggle/assets/images/Brisbane.png",
    "Brisbane Lions": "https://squiggle.com.au/wp-content/themes/squiggle/assets/images/Brisbane.png",

    "Carlton": "https://squiggle.com.au/wp-content/themes/squiggle/assets/images/Carlton.png",
    "Collingwood": "https://squiggle.com.au/wp-content/themes/squiggle/assets/images/Collingwood.png",
    "Essendon": "https://squiggle.com.au/wp-content/themes/squiggle/assets/images/Essendon.png",

    "Fremantle": "https://squiggle.com.au/wp-content/themes/squiggle/assets/images/Fremantle.png",
    "Geelong": "https://squiggle.com.au/wp-content/themes/squiggle/assets/images/Geelong.png",

    "Gold Coast": "https://squiggle.com.au/wp-content/themes/squiggle/assets/images/GoldCoast.png",
    "Gold Coast Suns": "https://squiggle.com.au/wp-content/themes/squiggle/assets/images/GoldCoast.png",

    "GWS": "https://squiggle.com.au/wp-content/themes/squiggle/assets/images/Giants.png",
    "Giants": "https://squiggle.com.au/wp-content/themes/squiggle/assets/images/Giants.png",
    "Greater Western Sydney": "https://squiggle.com.au/wp-content/themes/squiggle/assets/images/Giants.png",

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
# UTILS
# ---------------------------------------------------------
def margin_to_probability(margin):
    return round(100 / (1 + math.exp(-margin / 6)), 2)

# ---------------------------------------------------------
# UNIVERSAL MATCHUP TILE (Used by Team vs League + Others)
# ---------------------------------------------------------
def matchup_tile(team1, team2, score1, score2, chance1, chance2, label):
    # Tick logic
    def tick(c):
        if c > 55:
            return "✔️"
        elif c < 45:
            return "❌"
        else:
            return "❓"

    tick1 = tick(chance1)
    tick2 = tick(chance2)

    st.markdown("<div class='glass-tile'>", unsafe_allow_html=True)

    col1, col2, col3, col4, col5, col6, col7 = st.columns([1,1,2,3,2,1,1])

    # LEFT TICK
    with col1:
        st.markdown(f"<h2 style='text-align:center;'>{tick1}</h2>", unsafe_allow_html=True)

    # LEFT LOGO
    with col2:
        st.markdown(
            f"<div style='text-align:center;'><img class='team-logo' src='{TEAM_LOGOS.get(team1, '')}' height='70'></div>",
            unsafe_allow_html=True
        )

    # LEFT TEAM + WIN %
    with col3:
        st.markdown(
            f"<div style='text-align:center;'><b>{team1}</b><br>"
            f"<span style='opacity:0.85;'>Win Chance: {chance1:.1f}%</span></div>",
            unsafe_allow_html=True
        )

    # SCORE + CONFIDENCE LABEL
    with col4:
        st.markdown(
            f"<div class='score-box' style='text-align:center;'>{score1} – {score2}</div>",
            unsafe_allow_html=True
        )
        st.markdown(
            f"<div style='text-align:center; opacity:0.85;'>{label}</div>",
            unsafe_allow_html=True
        )

    # RIGHT TEAM + WIN %
    with col5:
        st.markdown(
            f"<div style='text-align:center;'><b>{team2}</b><br>"
            f"<span style='opacity:0.85;'>Win Chance: {chance2:.1f}%</span></div>",
            unsafe_allow_html=True
        )

    # RIGHT LOGO
    with col6:
        st.markdown(
            f"<div style='text-align:center;'><img class='team-logo' src='{TEAM_LOGOS.get(team2, '')}' height='70'></div>",
            unsafe_allow_html=True
        )

    # RIGHT TICK
    with col7:
        st.markdown(f"<h2 style='text-align:center;'>{tick2}</h2>", unsafe_allow_html=True)

    # Divider
    st.markdown(
        "<div style='height:2px; background:rgba(175,175,175,0.3); margin-top:0px;'></div>",
        unsafe_allow_html=True
    )

    st.markdown("</div>", unsafe_allow_html=True)

# ---------------------------------------------------------
# SIDEBAR
# ---------------------------------------------------------
st.sidebar.header("Settings")
year = st.sidebar.number_input("Season Year", min_value=2012, max_value=2030, value=2026)
rounds_back = st.sidebar.slider("Past Rounds to Use", 1, 20, 5)

menu = st.sidebar.radio(
    "Select Mode",
    [
        "Predict a Round",
        "Season Accuracy",
        "Projected Ladder",
        "Team vs League",
    ]
)

# ---------------------------------------------------------
# PREDICT A ROUND
# ---------------------------------------------------------
if menu == "Predict a Round":
    st.header("Round Predictions")

    round_number = st.number_input("Round Number", min_value=0, max_value=30, value=1)

    if st.button("Predict Round"):
        preds = predict_round(year, round_number, rounds_back=rounds_back)

        if not preds:
            st.warning("No games found for that round/year.")
        else:
            for p in preds:
                home = p["home"]
                away = p["away"]

                score_home = p["predicted_home_score"]
                score_away = p["predicted_away_score"]

                margin = score_home - score_away
                home_chance = margin_to_probability(margin)
                away_chance = 100 - home_chance

                # Confidence label (same as match_tile)
                max_chance = max(home_chance, away_chance)
                if max_chance >= 55:
                    label = "Anyones Game"
                elif max_chance >= 90:
                    label = "Lock in"
                elif max_chance >= 75:
                    label = "Could be"
                elif max_chance >= 55:
                    label = "Be Careful"
                else:
                    label = "IDK Dude"

                # Use the universal tile
                matchup_tile(
                    home, away,
                    score1=score_home,
                    score2=score_away,
                    chance1=home_chance,
                    chance2=away_chance,
                    label=label
                )


# ---------------------------------------------------------
# SEASON ACCURACY
# ---------------------------------------------------------
elif menu == "Season Accuracy":
    st.header("Season Accuracy")

    if st.button("Calculate Accuracy"):

        # Load real games data
        stats, games, teams = engine.team_stats(year, rounds_back=rounds_back)

        # Filter only completed games
        completed_games = [g for g in games if g.get("complete", 0) == 100]

        # Build lookup: (round, home, away) → actual scores
        actual_results = {}
        for g in completed_games:
            key = (g["round"], g["hteam"], g["ateam"])
            actual_results[key] = (g["hscore"], g["ascore"])

        # ---------------------------------------------------------
        # FAST MODE: Precompute predictions only for completed games
        # ---------------------------------------------------------
        season_predictions = {}

        for g in completed_games:
            rnd = g["round"]
            home = g["hteam"]
            away = g["ateam"]
            venue = g["venue"]

            # Skip invalid teams
            if home not in stats or away not in stats:
                continue
            p = engine.compare_teams(home, away, venue, stats, games, teams)
            if p is None:
                continue

            predicted_winner = home if p["score_home"] > p["score_away"] else away
            season_predictions[(rnd, home, away)] = predicted_winner

        # ---------------------------------------------------------
        # Compute accuracy ONLY for completed rounds
        # ---------------------------------------------------------
        round_numbers = []
        round_percentages = []

        correct_total = 0
        total_games = 0

        # Identify completed rounds
        rounds = sorted(set(g["round"] for g in completed_games))

        for rnd in rounds:
            games_in_round = [g for g in completed_games if g["round"] == rnd]

            # Skip rounds with missing or incomplete data
            if len(games_in_round) == 0:
                continue

            correct_r = 0
            total_r = len(games_in_round)

            for g in games_in_round:
                home = g["hteam"]
                away = g["ateam"]

                actual_home = g["hscore"]
                actual_away = g["ascore"]

                # Determine actual winner
                if actual_home > actual_away:
                    actual_winner = home
                elif actual_home < actual_away:
                    actual_winner = away
                else:
                    actual_winner = "Tie"

                predicted_winner = season_predictions.get((rnd, home, away), None)

                if predicted_winner == actual_winner:
                    correct_r += 1

            percent_r = (correct_r / total_r) * 100

            round_numbers.append(rnd)
            round_percentages.append(percent_r)

            correct_total += correct_r
            total_games += total_r

        overall_accuracy = (correct_total / total_games) * 100 if total_games > 0 else 0

        # ---------------------------------------------------------
        # UI
        # ---------------------------------------------------------
        col_left, col_right = st.columns([1.2, 1])

        with col_left:
            st.metric("Overall Accuracy (Completed Rounds)", f"{overall_accuracy:.2f}%")
            st.write(f"Correct: **{correct_total}** / {total_games}")

            st.markdown("---")
            st.subheader("Round-by-Round Accuracy")

            for rnd, pct in zip(round_numbers, round_percentages):
                games_in_round = [g for g in completed_games if g["round"] == rnd]
                total_r = len(games_in_round)
                correct_r = int((pct / 100) * total_r)

                st.write(
                    f"**Round {rnd}:** {correct_r}/{total_r} correct "
                    f"(**{pct:.1f}%**)"
                )

        with col_right:
            st.subheader("Accuracy Graph")
            chart_data = {
                "Round": round_numbers,
                "Accuracy (%)": round_percentages
            }
            st.line_chart(chart_data, x="Round", y="Accuracy (%)")


# ---------------------------------------------------------
# PROJECTED LADDER
# ---------------------------------------------------------
elif menu == "Projected Ladder":
    st.header("Projected Ladder")

    if st.button("Generate Ladder"):
        ladder = projected_ladder(year, rounds_back=rounds_back)
        probs = premiership_probabilities(year, rounds_back=rounds_back)

        if not ladder:
            st.warning("No ladder data available.")
        elif not probs:
            st.warning("No probability data available.")
        else:
            # Convert probs list → dict for fast lookup
            prob_dict = {team: p for team, p in probs}

            for i, (team, wins) in enumerate(ladder, start=1):
                col1, col2, col3 = st.columns([1,1,1])

                with col1:
                    st.markdown("<div style='text-align:right;'>projected wins</div>", unsafe_allow_html=True)
                    st.markdown(f"<div style='text-align:right;'>{i}. {team} - {wins} wins</div>", unsafe_allow_html=True)

                with col2:
                    st.markdown(
                        f"<div style='text-align:center;'><img class='team-logo' src='{TEAM_LOGOS.get(team, '')}' height='70'></div>",
                        unsafe_allow_html=True
                    )

                with col3:
                    st.markdown("<div style='text-align:left;'>chance of premiership</div>", unsafe_allow_html=True)
                    st.markdown(
                        f"<div style='text-align:left;'>{prob_dict.get(team, 0)}%</div>",
                        unsafe_allow_html=True
                    )

                st.markdown(
                    "<div style='height:0px; background:rgba(175,175,175,0.3); margin-top:2px;'></div>",
                    unsafe_allow_html=True
                )
# ---------------------------------------------------------
# TEAM VS LEAGUE
# ---------------------------------------------------------
elif menu == "Team vs League":
    st.header("Team vs Entire League")

    stats, games, teams = engine.team_stats(year, rounds_back=rounds_back)

    col1, col2 = st.columns([1,2])
    with col1:
        team_list = sorted(list(teams.values()))
        selected = st.selectbox("Select a team", team_list)
    with col2:
        filter_option = st.radio(
            "Show:",
            ["All", "Wins Only", "Losses Only", "Ties Only"],
            horizontal=True
        )

    if st.button("Run Matchups"):
        def classify(c):
            if c > 55: return "win"
            if c < 45: return "loss"
            return "tie"

        def label_for(c):
            if 45 <= c <= 55: return "ANYONES GAME"
            if c >= 90: return "LOCK IN"
            if c >= 75: return "LOOKING GOOD"
            if c >= 55: return "COULD BE"
            return "NOT LOOKING GOOD"

        home_results = []
        away_results = []

        for opp in team_list:
            if opp == selected:
                continue

            # HOME
            h = engine.compare_teams(selected, opp, "Generic", stats, games, teams)
            margin_h = h["score_home"] - h["score_away"]
            chance_h = margin_to_probability(margin_h)

            # AWAY
            a = engine.compare_teams(opp, selected, "Generic", stats, games, teams)
            margin_a = a["score_away"] - a["score_home"]
            chance_a = margin_to_probability(margin_a)

            home_results.append((opp, chance_h, margin_h, classify(chance_h)))
            away_results.append((opp, chance_a, margin_a, classify(chance_a)))

        # Filtering
        def apply_filter(lst):
            if filter_option == "All": return lst
            return [x for x in lst if x[3] == filter_option.lower().split()[0]]

        home_results = apply_filter(home_results)
        away_results = apply_filter(away_results)

        # Sorting
        home_results.sort(key=lambda x: x[1], reverse=True)
        away_results.sort(key=lambda x: x[1], reverse=True)

        # HOME SECTION
        st.subheader(f"Home Matchups for {selected}")
        for opp, chance, margin, _ in home_results:
            h = engine.compare_teams(selected, opp, "Generic", stats, games, teams)
            matchup_tile(
                selected, opp,
                score1=h["score_home"],
                score2=h["score_away"],
                chance1=chance,
                chance2=100 - chance,
                label=label_for(chance)
            )

        # AWAY SECTION
        st.subheader(f"Away Matchups for {selected}")
        for opp, chance, margin, _ in away_results:
            a = engine.compare_teams(selected, opp, "Generic", stats, games, teams)
            matchup_tile(
                opp, selected,
                score1=a["score_home"],
                score2=a["score_away"],
                chance1=chance,
                chance2=100 - chance,
                label=label_for(chance)
            )