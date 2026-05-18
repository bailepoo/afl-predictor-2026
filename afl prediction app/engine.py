import requests
from collections import defaultdict

BASE_URL = "https://api.squiggle.com.au/"

# ---------------------------------------------------------
# API WRAPPER
# ---------------------------------------------------------
def api_get(params):
    headers = {
        "User-Agent": "afl-tipping-predictions/2.0",
        "Accept": "application/json"
    }
    r = requests.get(BASE_URL, params=params, headers=headers, timeout=30)
    r.raise_for_status()
    return r.json()

# ---------------------------------------------------------
# BASIC LOADERS
# ---------------------------------------------------------
def get_teams():
    data = api_get({"q": "teams"})
    return {t["id"]: t["name"] for t in data["teams"]}

def get_games(year):
    return api_get({"q": "games", "year": year}).get("games", [])

def get_ladder(year):
    return api_get({"q": "standings", "year": year}).get("standings", [])

# ---------------------------------------------------------
# GET LAST X HOME-AND-AWAY ROUNDS FROM PREVIOUS SEASON
# ---------------------------------------------------------
def get_last_ha_rounds(prev_year, needed):
    games = get_games(prev_year)
    ha_games = [g for g in games if g.get("is_final") != 1 and g.get("round")]

    if not ha_games:
        return []

    rounds = sorted({g["round"] for g in ha_games})
    last_rounds = rounds[-needed:]
    return [g for g in ha_games if g["round"] in last_rounds]

# ---------------------------------------------------------
# BUILD WINDOWED GAME SET
# ---------------------------------------------------------
def build_windowed_games(year, upto_round, rounds_back):
    this_year_games = get_games(year)
    ha_games = [g for g in this_year_games if g.get("is_final") != 1 and g.get("round")]

    # Completed rounds only
    completed = [g for g in ha_games if g.get("complete") == 100]

    # Filter to rounds < upto_round
    completed = [g for g in completed if g["round"] < upto_round]

    # Identify rounds
    rounds = sorted({g["round"] for g in completed})

    # If we have enough rounds in this season
    if len(rounds) >= rounds_back:
        last_rounds = rounds[-rounds_back:]
        return [g for g in completed if g["round"] in last_rounds]

    # Otherwise pull from previous season
    needed = rounds_back - len(rounds)
    prev_year = year - 1
    prev_games = get_last_ha_rounds(prev_year, needed)

    return prev_games + completed

# ---------------------------------------------------------
# TEAM STATS (HYBRID WINDOW MODEL)
# ---------------------------------------------------------
def team_stats(year, rounds_back=6):
    teams = get_teams()
    all_games = get_games(year)

    # Full-season stats (unchanged)
    full_stats = {name: {
        "wins": 0,
        "games": 0,
        "margins": [],
        "recent_results": [],
        "scores_for": [],
        "scores_against": [],
        "opponents": []
    } for name in teams.values()}

    # Build full-season stats
    for g in all_games:
        if g.get("complete") != 100:
            continue

        hid = g.get("hteamid")
        aid = g.get("ateamid")
        if hid not in teams or aid not in teams:
            continue

        h = teams[hid]
        a = teams[aid]
        hs = g["hscore"]
        as_ = g["ascore"]

        if hs == as_:
            continue

        winner = h if hs > as_ else a
        margin = abs(hs - as_)

        full_stats[h]["games"] += 1
        full_stats[a]["games"] += 1

        full_stats[h]["scores_for"].append(hs)
        full_stats[h]["scores_against"].append(as_)
        full_stats[a]["scores_for"].append(as_)
        full_stats[a]["scores_against"].append(hs)

        full_stats[h]["opponents"].append(a)
        full_stats[a]["opponents"].append(h)

        full_stats[winner]["wins"] += 1
        full_stats[winner]["margins"].append(margin)

        full_stats[h]["recent_results"].append(1 if winner == h else 0)
        full_stats[a]["recent_results"].append(1 if winner == a else 0)

    # Ladder positions
    ladder = get_ladder(year)
    for row in ladder:
        name = row["name"]
        if name in full_stats:
            full_stats[name]["ladder_position"] = row["rank"]

    # ---------------------------------------------------------
    # WINDOWED STATS (R2 Hybrid Model)
    # ---------------------------------------------------------
    # Determine current round
    completed = [g for g in all_games if g.get("complete") == 100 and g.get("round")]
    if completed:
        current_round = max(g["round"] for g in completed) + 1
    else:
        current_round = 1

    window_games = build_windowed_games(year, current_round, rounds_back)

    # Build windowed stats
    win_stats = {t: {
        "margins": [],
        "recent_results": [],
        "scores_for": [],
        "scores_against": []
    } for t in teams.values()}

    for g in window_games:
        hid = g.get("hteamid")
        aid = g.get("ateamid")
        if hid not in teams or aid not in teams:
            continue

        h = teams[hid]
        a = teams[aid]
        hs = g["hscore"]
        as_ = g["ascore"]

        if hs == as_:
            continue

        winner = h if hs > as_ else a
        margin = abs(hs - as_)

        win_stats[h]["scores_for"].append(hs)
        win_stats[h]["scores_against"].append(as_)
        win_stats[a]["scores_for"].append(as_)
        win_stats[a]["scores_against"].append(hs)

        win_stats[winner]["margins"].append(margin)

        win_stats[h]["recent_results"].append(1 if winner == h else 0)
        win_stats[a]["recent_results"].append(1 if winner == a else 0)

    # Merge windowed stats into full stats
    for t in full_stats:
        ws = win_stats[t]

        # Windowed metrics
        full_stats[t]["last_5_wins"] = sum(ws["recent_results"][-5:])
        full_stats[t]["avg_winning_margin"] = (
            sum(ws["margins"]) / len(ws["margins"]) if ws["margins"] else 0
        )
        full_stats[t]["form_margin"] = (
            sum(ws["margins"][-5:]) / len(ws["margins"][-5:]) if ws["margins"] else 0
        )
        full_stats[t]["attack"] = (
            sum(ws["scores_for"]) / len(ws["scores_for"]) if ws["scores_for"] else 0
        )
        full_stats[t]["defense"] = (
            sum(ws["scores_against"]) / len(ws["scores_against"]) if ws["scores_against"] else 0
        )

        # SAFETY FIXES
        if "season_win_pct" not in full_stats[t]:
            full_stats[t]["season_win_pct"] = 0

        if "ladder_position" not in full_stats[t]:
            full_stats[t]["ladder_position"] = 18

        # Season-long metrics remain unchanged:
        # season_win_pct, ladder_position, strength_of_schedule, venue_record

    return full_stats, all_games, teams

# ---------------------------------------------------------
# VENUE RECORD
# ---------------------------------------------------------
def venue_record(team, venue, games, teams):
    wins = 0
    total = 0
    for g in games:
        if g.get("complete") != 100:
            continue
        if g.get("venue") != venue:
            continue

        hid = g.get("hteamid")
        aid = g.get("ateamid")
        if hid not in teams or aid not in teams:
            continue

        home = teams[hid]
        away = teams[aid]
        hs = g["hscore"]
        as_ = g["ascore"]

        if team not in (home, away):
            continue

        total += 1
        winner = home if hs > as_ else away
        if winner == team:
            wins += 1

    return wins / total if total else 0

# ---------------------------------------------------------
# STRENGTH OF SCHEDULE
# ---------------------------------------------------------
def strength_of_schedule(team, stats):
    opps = stats[team]["opponents"]
    if not opps:
        return 0
    return sum(stats[o]["season_win_pct"] for o in opps) / len(opps)

# ---------------------------------------------------------
# METRICS
# ---------------------------------------------------------
def m_ladder(t1, t2, s): return 1 if s[t1]["ladder_position"] < s[t2]["ladder_position"] else 0
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

# ---------------------------------------------------------
# WEIGHTS
# ---------------------------------------------------------
WEIGHTS = {"ladder":2,
            "last5":4,
            "avg_margin":4,
            "win_pct":3,
            "home_adv":8,
            "venue_record":8,
            "form_margin":1,
            "sos":2,
            "attack_defense":1
            }

# ---------------------------------------------------------
# TEAM COMPARISON
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

# ---------------------------------------------------------
# PREDICT A SINGLE GAME
# ---------------------------------------------------------
def predict_game(game, stats, games, teams):
    hid = game.get("hteamid")
    aid = game.get("ateamid")

    if hid not in teams or aid not in teams:
        return None

    home = teams[hid]
    away = teams[aid]
    venue = game.get("venue")

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
# PREDICT A ROUND
# ---------------------------------------------------------
def predict_round(year, round_number, rounds_back=6):
    stats, games, teams = team_stats(year, rounds_back=rounds_back)
    round_games = [g for g in games if g.get("round") == round_number]
    return [predict_game(g, stats, games, teams) for g in round_games]

# ---------------------------------------------------------
# SEASON ACCURACY
# ---------------------------------------------------------
def season_accuracy(year, rounds_back=6):
    stats, games, teams = team_stats(year, rounds_back=rounds_back)

    correct = 0
    total = 0

    for g in games:
        if g.get("complete") != 100:
            continue

        pred = predict_game(g, stats, games, teams)
        if pred is None:
            continue

        actual = teams[g["hteamid"]] if g["hscore"] > g["ascore"] else teams[g["ateamid"]]

        if pred["winner"] == actual:
            correct += 1

        total += 1

    accuracy = (correct / total * 100) if total else 0
    return accuracy, correct, total

# ---------------------------------------------------------
# PROJECTED LADDER
# ---------------------------------------------------------
def projected_ladder(year, rounds_back=6):
    stats, games, teams = team_stats(year, rounds_back=rounds_back)
    ladder = defaultdict(int)

    for g in games:
        if g.get("complete") == 100:
            winner = teams[g["hteamid"]] if g["hscore"] > g["ascore"] else teams[g["ateamid"]]
            ladder[winner] += 1
        else:
            pred = predict_game(g, stats, games, teams)
            if pred and pred.get("winner"):
                ladder[pred["winner"]] += 1

    return sorted(ladder.items(), key=lambda x: x[1], reverse=True)

# ---------------------------------------------------------
# PREMIERSHIP PROBABILITIES
# ---------------------------------------------------------
def premiership_probabilities(year, rounds_back=6):
    ladder = projected_ladder(year, rounds_back=rounds_back)
    total_wins = sum(w for _, w in ladder)
    if total_wins == 0:
        return []
    return [(team, round(w / total_wins * 100, 2)) for team, w in ladder]
