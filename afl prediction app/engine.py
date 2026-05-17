import itertools
import requests
from collections import defaultdict

BASE_URL = "https://api.squiggle.com.au/"

# ---------------------------------------------------------
# API WRAPPER
# ---------------------------------------------------------
def api_get(params):
    headers = {
        "User-Agent": "afl-tipping-predictions/1.0",
        "Accept": "application/json"
    }
    r = requests.get(BASE_URL, params=params, headers=headers, timeout=30)
    r.raise_for_status()
    return r.json()

def get_teams():
    data = api_get({"q": "teams"})
    return {t["id"]: t["name"] for t in data["teams"]}

def get_games(year):
    return api_get({"q": "games", "year": year})["games"]

def get_ladder(year):
    return api_get({"q": "standings", "year": year}).get("standings", [])

# ---------------------------------------------------------
# FILTER: LAST 6 ROUNDS ONLY
# ---------------------------------------------------------
def filter_last_6_rounds(games, upto_round=None):
    completed = [g for g in games if g.get("complete") == 100]

    if upto_round is not None:
        completed = [g for g in completed if g["round"] < upto_round]

    if not completed:
        return []

    rounds = sorted({g["round"] for g in completed})
    last_6 = set(rounds[-6:])

    return [g for g in completed if g["round"] in last_6]

# ---------------------------------------------------------
# BUILD TEAM STATS FROM A SET OF GAMES
# ---------------------------------------------------------
def build_stats_from_games(games_subset, teams, ladder_rows=None):
    stats = {name: {
        "wins": 0,
        "games": 0,
        "margins": [],
        "recent_results": [],
        "scores_for": [],
        "scores_against": [],
        "opponents": []
    } for name in teams.values()}

    for g in games_subset:
        h = teams[g["hteamid"]]
        a = teams[g["ateamid"]]
        hs = g["hscore"]
        as_ = g["ascore"]

        if hs == as_:
            continue

        winner = h if hs > as_ else a
        margin = abs(hs - as_)

        stats[h]["games"] += 1
        stats[a]["games"] += 1

        stats[h]["scores_for"].append(hs)
        stats[h]["scores_against"].append(as_)
        stats[a]["scores_for"].append(as_)
        stats[a]["scores_against"].append(hs)

        stats[h]["opponents"].append(a)
        stats[a]["opponents"].append(h)

        stats[winner]["wins"] += 1
        stats[winner]["margins"].append(margin)

        stats[h]["recent_results"].append(1 if winner == h else 0)
        stats[a]["recent_results"].append(1 if winner == a else 0)

    for t, s in stats.items():
        s["last_5_wins"] = sum(s["recent_results"][-5:])
        s["season_win_pct"] = (s["wins"] / s["games"] * 100) if s["games"] else 0
        s["avg_winning_margin"] = (
            sum(s["margins"]) / len(s["margins"]) if s["margins"] else 0
        )
        s["form_margin"] = (
            sum(s["margins"][-5:]) / len(s["margins"][-5:]) if s["margins"] else 0
        )
        s["attack"] = sum(s["scores_for"]) / len(s["scores_for"]) if s["scores_for"] else 0
        s["defense"] = sum(s["scores_against"]) / len(s["scores_against"]) if s["scores_against"] else 0

    if ladder_rows:
        for row in ladder_rows:
            name = row["name"]
            if name in stats:
                stats[name]["ladder_position"] = row["rank"]

    return stats

# ---------------------------------------------------------
# METRICS
# ---------------------------------------------------------
def venue_record(team, venue, games, teams):
    wins = 0
    total = 0
    for g in games:
        if g.get("complete") != 100:
            continue
        if g["venue"] != venue:
            continue

        home = teams[g["hteamid"]]
        away = teams[g["ateamid"]]
        hs = g["hscore"]
        as_ = g["ascore"]

        if team not in (home, away):
            continue

        total += 1
        winner = home if hs > as_ else away
        if winner == team:
            wins += 1

    return wins / total if total else 0

def strength_of_schedule(team, stats):
    opps = stats[team]["opponents"]
    if not opps:
        return 0
    return sum(stats[o]["season_win_pct"] for o in opps) / len(opps)

def m_ladder(t1, t2, s): return 1 if s[t1].get("ladder_position", 99) < s[t2].get("ladder_position", 99) else 0
def m_last5(t1, t2, s): return 1 if s[t1]["last_5_wins"] > s[t2]["last_5_wins"] else 0
def m_avg_margin(t1, t2, s): return 1 if s[t1]["avg_winning_margin"] > s[t2]["avg_winning_margin"] else 0
def m_win_pct(t1, t2, s): return 1 if s[t1]["season_win_pct"] > s[t2]["season_win_pct"] else 0

def m_home_adv(t1, t2, venue):
    interstate = {
        "Adelaide Oval": ["Adelaide", "Port Adelaide"],
        "Optus Stadium": ["West Coast", "Fremantle"],
        "Gabba": ["Brisbane"],
        "SCG": ["Sydney"],
        "Manuka Oval": ["GWS"],
    }
    for v, teams in interstate.items():
        if venue == v and t1 in teams:
            return 1
    return 0

def m_venue_record(t1, t2, s, games, teams, venue):
    return 1 if venue_record(t1, venue, games, teams) > venue_record(t2, venue, games, teams) else 0

def m_form_margin(t1, t2, s): return 1 if s[t1]["form_margin"] > s[t2]["form_margin"] else 0
def m_sos(t1, t2, s): return 1 if strength_of_schedule(t1, s) > strength_of_schedule(t2, s) else 0

def m_attack_defense(t1, t2, s):
    t1_power = s[t1]["attack"] - s[t1]["defense"]
    t2_power = s[t2]["attack"] - s[t2]["defense"]
    return 1 if t1_power > t2_power else 0

METRIC_FUNCS = {
    "ladder": m_ladder,
    "last5": m_last5,
    "avg_margin": m_avg_margin,
    "win_pct": m_win_pct,
    "home_adv": m_home_adv,
    "venue_record": m_venue_record,
    "form_margin": m_form_margin,
    "sos": m_sos,
    "attack_defense": m_attack_defense,
}

WEIGHTS = {
    "venue_record": 3,
    "home_adv": 2,
    "win_pct": 2,
    "ladder": 1,
    "last5": 1,
    "avg_margin": 1,
    "form_margin": 1,
    "sos": 1,
    "attack_defense": 1,
}

# ---------------------------------------------------------
# TEAM STATS WINDOW (LAST 6 ROUNDS)
# ---------------------------------------------------------
def team_stats_window(year, upto_round=None):
    games = get_games(year)
    teams = get_teams()
    ladder = get_ladder(year)

    recent_games = filter_last_6_rounds(games, upto_round=upto_round)
    stats = build_stats_from_games(recent_games, teams, ladder_rows=ladder)

    return stats, games, teams

# ---------------------------------------------------------
# PREDICTION ENGINE
# ---------------------------------------------------------
def compare_teams(home, away, venue, stats, games, teams):
    score_home = 0
    score_away = 0

    for metric, fn in METRIC_FUNCS.items():
        w = WEIGHTS[metric]

        if metric == "venue_record":
            h = fn(home, away, stats, games, teams, venue)
            a = fn(away, home, stats, games, teams, venue)
        elif metric == "home_adv":
            h = fn(home, away, venue)
            a = fn(away, home, venue)
        else:
            h = fn(home, away, stats)
            a = fn(away, home, stats)

        score_home += h * w
        score_away += a * w

    diff = score_home - score_away

    if diff >= 6:
        confidence = "LOCK"
    elif diff >= 3:
        confidence = "LEAN"
    else:
        confidence = "TOSS-UP"

    margin = (
        diff * 3
        + (stats[home]["attack"] - stats[away]["defense"]) * 0.5
        + (stats[home]["form_margin"] - stats[away]["form_margin"]) * 0.3
    )

    margin = max(min(margin, 80), -80)

    predicted_home_score = int(80 + margin / 2)
    predicted_away_score = int(80 - margin / 2)

    winner = home if diff >= 0 else away

    return {
        "winner": winner,
        "confidence": confidence,
        "score_home": predicted_home_score,
        "score_away": predicted_away_score,
        "margin": abs(int(margin)),
        "raw_diff": diff
    }

def predict_game(game, stats, games, teams):
    hid = game.get("hteamid")
    aid = game.get("ateamid")

    if hid not in teams or aid not in teams:
        return None

    home = teams[hid]
    away = teams[aid]
    venue = game["venue"]

    result = compare_teams(home, away, venue, stats, games, teams)

    return {
        "home": home,
        "away": away,
        "venue": venue,
        "winner": result["winner"],
        "confidence": result["confidence"],
        "predicted_home_score": result["score_home"],
        "predicted_away_score": result["score_away"],
        "predicted_margin": result["margin"],
        "raw_diff": result["raw_diff"]
    }

# ---------------------------------------------------------
# ROUND PREDICTION (NO LEAKAGE)
# ---------------------------------------------------------
def predict_round(year, round_number):
    stats, games, teams = team_stats_window(year, upto_round=round_number)
    round_games = [g for g in games if g.get("round") == round_number]

    return [predict_game(g, stats, games, teams) for g in round_games]

# ---------------------------------------------------------
# ACCURACY (NO SAME-WEEK LEAKAGE)
# ---------------------------------------------------------
def season_accuracy(year):
    games = get_games(year)
    teams = get_teams()

    correct = 0
    total = 0

    for g in games:
        if g.get("complete") != 100:
            continue

        stats, all_games, all_teams = team_stats_window(year, upto_round=g["round"])
        pred = predict_game(g, stats, all_games, all_teams)

        actual = teams[g["hteamid"]] if g["hscore"] > g["ascore"] else teams[g["ateamid"]]

        if pred["winner"] == actual:
            correct += 1

        total += 1

    accuracy = (correct / total * 100) if total else 0
    return accuracy, correct, total
# ---------------------------------------------------------
# PROJECTED LADDER (NO LEAKAGE)
# ---------------------------------------------------------
def projected_ladder(year):
    stats, games, teams = team_stats_window(year, upto_round=None)
    ladder = defaultdict(int)

    for g in games:
        if g.get("complete") == 100:
            # Use actual result
            winner = teams[g["hteamid"]] if g["hscore"] > g["ascore"] else teams[g["ateamid"]]
            ladder[winner] += 1
        else:
            # Predict future games using last 6 rounds only
            pred = predict_game(g, stats, games, teams)
            if pred and pred.get("winner"):
                ladder[pred["winner"]] += 1

    return sorted(ladder.items(), key=lambda x: x[1], reverse=True)


# ---------------------------------------------------------
# PREMIERSHIP PROBABILITIES
# ---------------------------------------------------------
def premiership_probabilities(year):
    ladder = projected_ladder(year)

    total_wins = sum(w for _, w in ladder)
    if total_wins == 0:
        return []

    probs = [(team, round(w / total_wins * 100, 2)) for team, w in ladder]
    return probs


# ---------------------------------------------------------
# TIPPING SHEET
# ---------------------------------------------------------
def tipping_sheet(year, round_number):
    preds = predict_round(year, round_number)
    sheet = []

    for p in preds:
        sheet.append(f"{p['home']} vs {p['away']} → {p['winner']} ({p['confidence']})")

    return sheet


# ---------------------------------------------------------
# PRINT PREDICTIONS (CLI OUTPUT)
# ---------------------------------------------------------
def print_predictions(preds):
    print("\n================ AFL PREDICTIONS ================\n")

    for p in preds:
        print(f"{p['home']} vs {p['away']} @ {p['venue']}")
        print(f"→ Winner: {p['winner']} ({p['confidence']})")
        print(f"→ Predicted Score: {p['predicted_home_score']} - {p['predicted_away_score']}")
        print(f"→ Margin: {p['predicted_margin']} pts")
        print(f"→ Raw Metric Diff: {p['raw_diff']}")
        print("--------------------------------------------------")


# ---------------------------------------------------------
# MAIN MENU (CLI VERSION)
# ---------------------------------------------------------
def main():
    while True:
        print("\n=== AFL PREDICTION ENGINE (Last 6 Rounds Model) ===")
        print("1) Predict a round")
        print("2) Tipping sheet for a round")
        print("3) Season accuracy so far")
        print("4) Projected ladder")
        print("5) Premiership probabilities")
        print("Enter to quit")

        choice = input("Select option: ").strip()
        if choice == "":
            break

        year = int(input("Enter season year: ").strip())

        if choice == "1":
            rnd = int(input("Round number: ").strip())
            preds = predict_round(year, rnd)
            print_predictions(preds)

        elif choice == "2":
            rnd = int(input("Round number: ").strip())
            sheet = tipping_sheet(year, rnd)
            print("\n=== TIPPING SHEET ===\n")
            for line in sheet:
                print(line)

        elif choice == "3":
            acc, correct, total = season_accuracy(year)
            print(f"\nSeason accuracy: {acc:.2f}% ({correct}/{total})")

        elif choice == "4":
            ladder = projected_ladder(year)
            print("\n=== PROJECTED LADDER ===\n")
            for i, (team, wins) in enumerate(ladder, start=1):
                print(f"{i}. {team} — {wins} wins")

        elif choice == "5":
            probs = premiership_probabilities(year)
            print("\n=== PREMIERSHIP PROBABILITIES ===\n")
            for team, p in probs:
                print(f"{team}: {p}%")

        else:
            print("Invalid option.")


if __name__ == "__main__":
    main()
