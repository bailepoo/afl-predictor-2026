import streamlit as st
import json
import math

# Import your engine
import engine

LEADERBOARD_FILE = "leaderboard.json"

# ---------------------------------------------------------
# Leaderboard helpers
# ---------------------------------------------------------
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
# Streamlit UI
# ---------------------------------------------------------
def main():

    # Title
    st.markdown(
        """
        <h1 style='text-align:center;'>🏉 AFL Prediction Engine</h1>
        <p style='text-align:center; font-size:18px; opacity:0.85;'>
            Balanced 9‑Metric Model • Last‑6‑Rounds Form • No Leakage
        </p>
        """,
        unsafe_allow_html=True
    )

    st.sidebar.header("Settings")

    # Year
    year = st.sidebar.number_input("Season year", min_value=2010, max_value=2100, value=2024, step=1)

    # Rounds‑back window
    rounds_back = st.sidebar.slider("Rounds of history to use", 1, 20, 6)

    # Metric toggles
    metric_options = list(engine.METRIC_FUNCS.keys())
    enabled_metrics = st.sidebar.multiselect(
        "Metrics to include",
        metric_options,
        default=metric_options
    )

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
                st.markdown(
                    f"### {p['home']} vs {p['away']} @ {p['venue']}"
                )
                st.write(f"**Winner:** {p['winner']} ({p['confidence']})")
                st.write(f"**Score:** {p['predicted_home_score']} – {p['predicted_away_score']}")
                st.write(f"**Margin:** {p['predicted_margin']} pts")
                st.write(f"**Raw Diff:** {p['raw_diff']}")
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
