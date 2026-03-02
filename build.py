#!/usr/bin/env python3
"""
Ottawa Senators Dashboard Builder
Fetches live data from the NHL API + MoneyPuck analytics and generates a static dashboard.
"""

import csv
import io
import json
import os
import urllib.request
from datetime import datetime, timezone

TEAM = "OTT"
PREV_FILE = "previous.json"
SEASON = "20252026"
SEASON_SHORT = "2025"
NHL_API = "https://api-web.nhle.com/v1"
MONEYPUCK = "https://moneypuck.com/moneypuck"

# ── Fetchers ──────────────────────────────────────────────

def fetch_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": "SensDashboard/1.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read())

def fetch_csv_rows(url):
    req = urllib.request.Request(url, headers={"User-Agent": "SensDashboard/1.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        text = resp.read().decode("utf-8")
    reader = csv.DictReader(io.StringIO(text))
    return list(reader)

def fetch_standings():
    return fetch_json(f"{NHL_API}/standings/now")

def fetch_club_stats():
    return fetch_json(f"{NHL_API}/club-stats/{TEAM}/now")

def fetch_schedule():
    return fetch_json(f"{NHL_API}/club-schedule-season/{TEAM}/{SEASON}")

def fetch_moneypuck_odds():
    rows = fetch_csv_rows(f"{MONEYPUCK}/simulations/simulations_recent.csv")
    odds = {}
    for r in rows:
        team = r.get("teamCode", "")
        scenario = r.get("scenerio", "")
        entry = {
            "playoffPct": float(r.get("madePlayoffs", 0)),
            "projPts": float(r.get("points", 0)),
            "cupPct": float(r.get("wonCup", 0)),
            "divWinPct": float(r.get("wonDivision", 0)),
            "round2": float(r.get("round2", 0)),
            "round3": float(r.get("round3", 0)),
            "finals": float(r.get("round4", 0)),
            "div2": float(r.get("divisionPlace2Odds", 0)),
            "div3": float(r.get("divisionPlace3Odds", 0)),
            "wc1": float(r.get("wildcard1Odds", 0)),
            "wc2": float(r.get("wildcard2Odds", 0)),
            "firstPick": float(r.get("firstOverall", 0)),
            "draftLottery": float(r.get("draftLottery", 0)),
        }
        if scenario == "ALL":
            if team not in odds:
                odds[team] = {}
            odds[team]["ALL"] = entry
        elif scenario in ("WINREG", "WINOT", "LOSSOT", "LOSSREG"):
            if team not in odds:
                odds[team] = {}
            odds[team][scenario] = entry
    return odds

def fetch_moneypuck_team_stats():
    rows = fetch_csv_rows(f"{MONEYPUCK}/playerData/seasonSummary/{SEASON_SHORT}/regular/teams.csv")
    stats = {}
    for r in rows:
        team = r.get("team", "")
        situation = r.get("situation", "")
        if not team:
            continue
        if team not in stats:
            stats[team] = {}
        gp = int(float(r.get("games_played", 0) or 0))
        if situation == "all":
            gf = int(float(r.get("goalsFor", 0) or 0))
            ga = int(float(r.get("goalsAgainst", 0) or 0))
            stats[team]["all"] = {
                "xGFpct": float(r.get("xGoalsPercentage", 0) or 0),
                "CFpct": float(r.get("corsiPercentage", 0) or 0),
                "FFpct": float(r.get("fenwickPercentage", 0) or 0),
                "gf": gf, "ga": ga, "gp": gp,
                "gfpg": round(gf / gp, 2) if gp > 0 else 0,
                "gapg": round(ga / gp, 2) if gp > 0 else 0,
                "shotsFor": int(float(r.get("shotsOnGoalFor", 0) or 0)),
                "shotsAgainst": int(float(r.get("shotsOnGoalAgainst", 0) or 0)),
                "hd_gf": int(float(r.get("highDangerGoalsFor", 0) or 0)),
                "hd_ga": int(float(r.get("highDangerGoalsAgainst", 0) or 0)),
            }
        elif situation == "5on4":
            pp_gf = int(float(r.get("goalsFor", 0) or 0))
            pp_shots = int(float(r.get("shotsOnGoalFor", 0) or 0))
            stats[team]["pp"] = {"gf": pp_gf, "shots": pp_shots, "gp": gp}
        elif situation == "4on5":
            pk_ga = int(float(r.get("goalsAgainst", 0) or 0))
            pk_sa = int(float(r.get("shotsOnGoalAgainst", 0) or 0))
            stats[team]["pk"] = {"ga": pk_ga, "sa": pk_sa, "gp": gp}
        elif situation == "5on5":
            stats[team]["5v5"] = {
                "xGFpct": float(r.get("xGoalsPercentage", 0) or 0),
                "CFpct": float(r.get("corsiPercentage", 0) or 0),
            }
    return stats

def fetch_nhl_skater_summary():
    """Fetch full skater summary from NHL stats API (evGoals, evPoints, ppPoints, shPoints, etc.)."""
    url = (
        "https://api.nhle.com/stats/rest/en/skater/summary?"
        "isAggregate=false&isGame=false"
        "&sort=%5B%7B%22property%22:%22points%22,%22direction%22:%22DESC%22%7D%5D"
        "&start=0&limit=100"
        "&factCayenneExp=gamesPlayed%3E=1"
        f"&cayenneExp=franchiseId%3D30%20and%20seasonId%3C={SEASON}%20and%20seasonId%3E={SEASON}%20and%20gameTypeId=2"
    )
    data = fetch_json(url)
    return {p["playerId"]: p for p in data.get("data", [])}

def fetch_nhl_goalie_summary():
    """Fetch full goalie summary from NHL stats API (gamesStarted, timeOnIce, etc.)."""
    url = (
        "https://api.nhle.com/stats/rest/en/goalie/summary?"
        "isAggregate=false&isGame=false"
        "&sort=%5B%7B%22property%22:%22wins%22,%22direction%22:%22DESC%22%7D%5D"
        "&start=0&limit=20"
        "&factCayenneExp=gamesPlayed%3E=1"
        f"&cayenneExp=franchiseId%3D30%20and%20seasonId%3C={SEASON}%20and%20seasonId%3E={SEASON}%20and%20gameTypeId=2"
    )
    data = fetch_json(url)
    return {g["playerId"]: g for g in data.get("data", [])}

def fetch_moneypuck_player_stats():
    """Fetch individual player advanced stats from MoneyPuck for OTT."""
    rows = fetch_csv_rows(f"{MONEYPUCK}/playerData/seasonSummary/{SEASON_SHORT}/regular/skaters.csv")
    players = {}
    for r in rows:
        if r.get("team") != TEAM:
            continue
        name = r.get("name", "")
        sit = r.get("situation", "")
        if not name:
            continue
        if name not in players:
            players[name] = {}
        gp = int(float(r.get("games_played", 0) or 0))
        ice = float(r.get("icetime", 0) or 0)
        if sit == "5on5":
            players[name]["5v5"] = {
                "xGFpct": float(r.get("onIce_xGoalsPercentage", 0) or 0),
                "CFpct": float(r.get("onIce_corsiPercentage", 0) or 0),
                "xG": float(r.get("I_F_xGoals", 0) or 0),
                "hdShots": int(float(r.get("I_F_highDangerShots", 0) or 0)),
                "hdGoals": int(float(r.get("I_F_highDangerGoals", 0) or 0)),
                "hits": int(float(r.get("I_F_hits", 0) or 0)),
                "takeaways": int(float(r.get("I_F_takeaways", 0) or 0)),
                "giveaways": int(float(r.get("I_F_giveaways", 0) or 0)),
                "ozStarts": int(float(r.get("I_F_oZoneShiftStarts", 0) or 0)),
                "dzStarts": int(float(r.get("I_F_dZoneShiftStarts", 0) or 0)),
                "gp": gp,
                "ice": ice,
            }
        elif sit == "all":
            players[name]["all"] = {
                "xG": float(r.get("I_F_xGoals", 0) or 0),
                "goals": int(float(r.get("I_F_goals", 0) or 0)),
                "points": int(float(r.get("I_F_points", 0) or 0)),
                "shots": int(float(r.get("I_F_shotsOnGoal", 0) or 0)),
                "hdShots": int(float(r.get("I_F_highDangerShots", 0) or 0)),
                "hdGoals": int(float(r.get("I_F_highDangerGoals", 0) or 0)),
                "hits": int(float(r.get("I_F_hits", 0) or 0)),
                "takeaways": int(float(r.get("I_F_takeaways", 0) or 0)),
                "giveaways": int(float(r.get("I_F_giveaways", 0) or 0)),
                "gp": gp,
                "ice": ice,
                "gameScore": float(r.get("gameScore", 0) or 0),
            }
    return players

# ── Persistence (delta tracking) ──────────────────────────

def load_previous():
    if os.path.exists(PREV_FILE):
        try:
            with open(PREV_FILE) as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    return {}

def save_current(data):
    with open(PREV_FILE, "w") as f:
        json.dump(data, f, indent=2)

def fmt_delta(current, previous, fmt="num", invert=False):
    """Format a delta indicator. Returns HTML string or empty string if no previous data."""
    if previous is None:
        return ""
    diff = current - previous
    if abs(diff) < 0.001:
        return ""
    # For 'needed' and 'gap', going down is good. invert flips the arrow meaning.
    if invert:
        is_good = diff < 0
    else:
        is_good = diff > 0
    arrow = "&#9650;" if diff > 0 else "&#9660;"
    color = "#1a8a1a" if is_good else "#c43c3c"
    if fmt == "pct":
        label = f"{abs(diff)*100:.1f}%"
    elif fmt == "dec":
        label = f"{abs(diff):.1f}"
    else:
        label = f"{abs(diff):g}"
    return f'<span class="delta" style="color:{color}">{arrow} {label}</span>'

# ── Data Processors ───────────────────────────────────────

def get_team_data(standings):
    sens = None
    east_teams = []
    all_teams = []
    for team in standings.get("standings", []):
        abbrev = team.get("teamAbbrev", {})
        if isinstance(abbrev, dict):
            abbrev = abbrev.get("default", "")
        info = {
            "abbrev": abbrev,
            "name": team.get("teamName", {}).get("default", ""),
            "place": team.get("placeName", {}).get("default", ""),
            "gp": team.get("gamesPlayed", 0),
            "w": team.get("wins", 0),
            "l": team.get("losses", 0),
            "otl": team.get("otLosses", 0),
            "pts": team.get("points", 0),
            "ptsPct": team.get("pointPctg", 0),
            "gf": team.get("goalFor", 0),
            "ga": team.get("goalAgainst", 0),
            "conf": team.get("conferenceName", ""),
            "div": team.get("divisionName", ""),
            "divAbbrev": team.get("divisionAbbrev", ""),
            "streak": f"{team.get('streakCode', '')}{team.get('streakCount', '')}",
            "l10w": team.get("l10Wins", 0),
            "l10l": team.get("l10Losses", 0),
            "l10otl": team.get("l10OtLosses", 0),
            "homeW": team.get("homeWins", 0),
            "homeL": team.get("homeLosses", 0),
            "homeOtl": team.get("homeOtLosses", 0),
            "roadW": team.get("roadWins", 0),
            "roadL": team.get("roadLosses", 0),
            "roadOtl": team.get("roadOtLosses", 0),
        }
        all_teams.append(info)
        if info["conf"] == "Eastern":
            east_teams.append(info)
        if abbrev == TEAM:
            sens = info
    return sens, east_teams, all_teams

def get_above500_teams(all_teams):
    return {t["abbrev"] for t in all_teams if t["gp"] > 0 and t["w"] / t["gp"] > 0.5}

def get_team_records(all_teams):
    return {t["abbrev"]: t for t in all_teams}

def get_skaters(club_stats, nhl_summary):
    """Build skater list merging club-stats (headshots) + NHL stats API (full summary)."""
    skaters = []
    for s in club_stats.get("skaters", []):
        pid = s.get("playerId", 0)
        first = s.get("firstName", {})
        last = s.get("lastName", {})
        if isinstance(first, dict): first = first.get("default", "")
        if isinstance(last, dict): last = last.get("default", "")
        headshot = s.get("headshot", "")

        # Merge full stats from NHL stats API
        ns = nhl_summary.get(pid, {})
        gp = ns.get("gamesPlayed", s.get("gamesPlayed", 0))
        pts = ns.get("points", s.get("points", 0))
        goals = ns.get("goals", s.get("goals", 0))
        assists = ns.get("assists", s.get("assists", 0))
        toi_sec = ns.get("timeOnIcePerGame", s.get("avgTimeOnIcePerGame", 0))
        toi_min = int(toi_sec // 60)
        toi_s = int(toi_sec % 60)

        skaters.append({
            "name": f"{first} {last}",
            "pos": ns.get("positionCode", s.get("positionCode", "")),
            "headshot": headshot,
            "gp": gp,
            "g": goals,
            "a": assists,
            "pts": pts,
            "pm": ns.get("plusMinus", s.get("plusMinus", 0)),
            "pim": ns.get("penaltyMinutes", s.get("penaltyMinutes", 0)),
            "ppg": ns.get("pointsPerGame", round(pts / gp, 2) if gp > 0 else 0),
            "evg": ns.get("evGoals", 0),
            "evp": ns.get("evPoints", 0),
            "ppGoals": ns.get("ppGoals", s.get("powerPlayGoals", 0)),
            "ppPts": ns.get("ppPoints", 0),
            "shGoals": ns.get("shGoals", s.get("shorthandedGoals", 0)),
            "shPts": ns.get("shPoints", 0),
            "otg": ns.get("otGoals", s.get("overtimeGoals", 0)),
            "gwg": ns.get("gameWinningGoals", s.get("gameWinningGoals", 0)),
            "shots": ns.get("shots", s.get("shots", 0)),
            "shPct": round((ns.get("shootingPct") or s.get("shootingPctg") or 0) * 100, 1),
            "toi": f"{toi_min}:{toi_s:02d}",
            "foPct": round((ns.get("faceoffWinPct") or s.get("faceoffWinPctg") or 0) * 100, 1),
        })
    skaters.sort(key=lambda x: x["pts"], reverse=True)
    return skaters

def get_goalies(club_stats, nhl_goalie_summary):
    """Build goalie list merging club-stats (headshots) + NHL stats API (full summary)."""
    goalies = []
    for g in club_stats.get("goalies", []):
        pid = g.get("playerId", 0)
        first = g.get("firstName", {})
        last = g.get("lastName", {})
        if isinstance(first, dict): first = first.get("default", "")
        if isinstance(last, dict): last = last.get("default", "")

        ns = nhl_goalie_summary.get(pid, {})
        toi_total = ns.get("timeOnIce", 0)
        toi_h = int(toi_total // 3600)
        toi_m = int((toi_total % 3600) // 60)
        toi_str = f"{toi_h * 60 + toi_m}:{int(toi_total % 60):02d}" if toi_total else "0:00"

        goalies.append({
            "name": f"{first} {last}",
            "headshot": g.get("headshot", ""),
            "gp": ns.get("gamesPlayed", g.get("gamesPlayed", 0)),
            "gs": ns.get("gamesStarted", 0),
            "w": ns.get("wins", g.get("wins", 0)),
            "l": ns.get("losses", g.get("losses", 0)),
            "otl": ns.get("otLosses", g.get("overtimeLosses", 0)),
            "sa": ns.get("shotsAgainst", g.get("shotsAgainst", 0)),
            "ga": ns.get("goalsAgainst", g.get("goalsAgainst", 0)),
            "gaa": round(ns.get("goalsAgainstAverage", g.get("goalsAgainstAverage", 0)), 2),
            "sv": ns.get("saves", g.get("saves", 0)),
            "svPct": round(ns.get("savePct", g.get("savePercentage", 0)), 3),
            "so": ns.get("shutouts", g.get("shutouts", 0)),
            "toi": toi_str,
        })
    goalies.sort(key=lambda x: x["gp"], reverse=True)
    return goalies

def fetch_east_team_records(east_teams, above500):
    """Fetch schedules for all Eastern teams; compute vs OTT, vs above/below .500."""
    records = {}
    for t in east_teams:
        abbrev = t["abbrev"]
        try:
            data = fetch_json(f"{NHL_API}/club-schedule-season/{abbrev}/{SEASON}")
        except Exception:
            records[abbrev] = {"vsOTT": (0, 0, 0), "vsAbove": (0, 0, 0), "vsBelow": (0, 0, 0)}
            continue
        vs_ott = [0, 0, 0]  # w, l, otl
        vs_above = [0, 0, 0]
        vs_below = [0, 0, 0]
        for g in data.get("games", []):
            if g.get("gameType") != 2:
                continue
            if g.get("gameState") not in ("FINAL", "OFF"):
                continue
            home = g.get("homeTeam", {})
            away = g.get("awayTeam", {})
            is_home = home.get("abbrev") == abbrev
            opp = away.get("abbrev") if is_home else home.get("abbrev")
            my_score = home.get("score", 0) if is_home else away.get("score", 0)
            opp_score = away.get("score", 0) if is_home else home.get("score", 0)
            period = g.get("periodDescriptor", {}).get("periodType", "REG")
            # Determine result
            if my_score > opp_score:
                result = 0  # win
            elif period in ("OT", "SO"):
                result = 2  # otl
            else:
                result = 1  # loss
            if opp == TEAM:
                vs_ott[result] += 1
            if opp in above500:
                vs_above[result] += 1
            else:
                vs_below[result] += 1
        records[abbrev] = {
            "vsOTT": tuple(vs_ott),
            "vsAbove": tuple(vs_above),
            "vsBelow": tuple(vs_below),
        }
    return records

def get_remaining_schedule(schedule_data, above500):
    games = []
    for g in schedule_data.get("games", []):
        if g.get("gameType", 0) != 2:
            continue
        state = g.get("gameState", "")
        if state in ("FINAL", "OFF"):
            continue
        home_abbrev = g.get("homeTeam", {}).get("abbrev", "")
        away_abbrev = g.get("awayTeam", {}).get("abbrev", "")
        is_home = home_abbrev == TEAM
        opp_abbrev = away_abbrev if is_home else home_abbrev
        opp_name_obj = g.get("awayTeam" if is_home else "homeTeam", {}).get("placeName", {})
        if isinstance(opp_name_obj, dict):
            opp_name = opp_name_obj.get("default", opp_abbrev)
        else:
            opp_name = str(opp_name_obj) if opp_name_obj else opp_abbrev
        if not opp_name or opp_name == "None":
            opp_name = opp_abbrev
        game_date = g.get("gameDate", "")
        try:
            dt = datetime.strptime(game_date, "%Y-%m-%d")
            date_str = dt.strftime("%b %-d")
        except (ValueError, TypeError):
            date_str = game_date
        games.append({
            "date": date_str, "rawDate": game_date, "opp": opp_name,
            "oppAbbrev": opp_abbrev, "loc": "home" if is_home else "away",
            "above500": opp_abbrev in above500,
        })
    games.sort(key=lambda x: x["rawDate"])
    return games

def get_results(schedule_data):
    results = []
    for g in schedule_data.get("games", []):
        if g.get("gameType", 0) != 2: continue
        if g.get("gameState", "") not in ("FINAL", "OFF"): continue
        home = g.get("homeTeam", {})
        away = g.get("awayTeam", {})
        is_home = home.get("abbrev", "") == TEAM
        opp_abbrev = away.get("abbrev", "") if is_home else home.get("abbrev", "")
        sens_score = home.get("score", 0) if is_home else away.get("score", 0)
        opp_score = away.get("score", 0) if is_home else home.get("score", 0)
        period = g.get("periodDescriptor", {}).get("periodType", "REG")
        if sens_score > opp_score: result = "W"
        elif period in ("OT", "SO"): result = "OTL"
        else: result = "L"
        results.append({"oppAbbrev": opp_abbrev, "result": result})
    return results

def compute_vs_above500(results, above500):
    w, l, otl = 0, 0, 0
    for r in results:
        if r["oppAbbrev"] in above500:
            if r["result"] == "W": w += 1
            elif r["result"] == "L": l += 1
            else: otl += 1
    return w, l, otl

# ── HTML Builders ─────────────────────────────────────────


def build_roster_html(skaters, goalies, mp_players):
    rows = []
    ncols = 22  # total columns in skater table
    for i, s in enumerate(skaters):
        pm_val = s["pm"]
        pm_str = f"+{pm_val}" if pm_val > 0 else str(pm_val)
        alt = " alt" if i % 2 == 1 else ""
        fo_str = f'{s["foPct"]:.1f}' if s["foPct"] > 0 else "--"

        # MoneyPuck advanced stats
        mp = mp_players.get(s["name"], {})
        mp5 = mp.get("5v5", {})
        mp_all = mp.get("all", {})
        has_mp = bool(mp5)

        xg = mp_all.get("xG", 0)
        xg5 = mp5.get("xG", 0)
        xgf_pct = mp5.get("xGFpct", 0)
        cf_pct = mp5.get("CFpct", 0)
        hd_shots = mp5.get("hdShots", 0)
        hd_goals = mp5.get("hdGoals", 0)
        hits = mp5.get("hits", 0)
        tkwy = mp5.get("takeaways", 0)
        gvwy = mp5.get("giveaways", 0)
        oz = mp5.get("ozStarts", 0)
        dz = mp5.get("dzStarts", 0)
        oz_pct = round(oz / (oz + dz) * 100, 1) if (oz + dz) > 0 else 0
        game_score = mp_all.get("gameScore", 0)
        gs_pg = round(game_score / s["gp"], 2) if s["gp"] > 0 else 0
        g_minus_xg = s["g"] - xg

        expand_html = ""
        if has_mp:
            expand_html = f'''<tr class="expand-row"><td colspan="{ncols}"><div class="px-grid">
  <div class="px-section"><div class="px-title">Expected Goals</div>
    <div class="px-row"><span class="px-label">xG (All Sit.)</span><span class="px-val">{xg:.1f}</span></div>
    <div class="px-row"><span class="px-label">xG (5v5)</span><span class="px-val">{xg5:.1f}</span></div>
    <div class="px-row"><span class="px-label">Goals &minus; xG</span><span class="px-val" style="color:{"#1a8a1a" if g_minus_xg > 0.5 else "#c43c3c" if g_minus_xg < -0.5 else "inherit"}">{g_minus_xg:+.1f}</span></div>
    <div class="px-row"><span class="px-label">xGF% (5v5)</span><span class="px-val">{xgf_pct*100:.1f}%</span></div>
    <div class="px-row"><span class="px-label">GameScore/GP</span><span class="px-val">{gs_pg}</span></div>
  </div>
  <div class="px-section"><div class="px-title">Possession (5v5)</div>
    <div class="px-row"><span class="px-label">CF%</span><span class="px-val">{cf_pct*100:.1f}%</span></div>
    <div class="px-row"><span class="px-label">OZ Start %</span><span class="px-val">{oz_pct}%</span></div>
    <div class="px-row"><span class="px-label">HD Shots</span><span class="px-val">{hd_shots}</span></div>
    <div class="px-row"><span class="px-label">HD Goals</span><span class="px-val">{hd_goals}</span></div>
  </div>
  <div class="px-section"><div class="px-title">Physical (5v5)</div>
    <div class="px-row"><span class="px-label">Hits</span><span class="px-val">{hits}</span></div>
    <div class="px-row"><span class="px-label">Takeaways</span><span class="px-val">{tkwy}</span></div>
    <div class="px-row"><span class="px-label">Giveaways</span><span class="px-val">{gvwy}</span></div>
    {"<div class='px-row'><span class='px-label'>FO%</span><span class='px-val'>" + str(s["foPct"]) + "%</span></div>" if s["foPct"] > 0 else ""}
  </div>
</div></td></tr>'''

        img = f'<img src="{s["headshot"]}" class="hs" alt="">' if s["headshot"] else '<div class="hs hs-empty"></div>'

        rows.append(f'''<tbody class="player-group"><tr class="player-summary{alt}">
<td class="rank">{i+1}</td>
<td class="name-cell"><details class="pd"><summary class="pd-s">{img}<span class="pname">{s["name"]}</span></summary></details></td>
<td class="r pos-col">{s["pos"]}</td>
<td class="r">{s["gp"]}</td><td class="r">{s["g"]}</td><td class="r">{s["a"]}</td>
<td class="r pts-col">{s["pts"]}</td><td class="r">{pm_str}</td>
<td class="r">{s["pim"]}</td><td class="r">{s["ppg"]:.2f}</td>
<td class="r">{s["evg"]}</td><td class="r">{s["evp"]}</td>
<td class="r">{s["ppGoals"]}</td><td class="r">{s["ppPts"]}</td>
<td class="r">{s["shGoals"]}</td><td class="r">{s["shPts"]}</td>
<td class="r">{s["otg"]}</td><td class="r">{s["gwg"]}</td>
<td class="r">{s["shots"]}</td><td class="r">{s["shPct"]}</td>
<td class="r">{s["toi"]}</td><td class="r">{fo_str}</td>
</tr>{expand_html}</tbody>''')

    goalie_rows = []
    for i, g in enumerate(goalies):
        svp = f".{int(g['svPct']*1000):03d}" if 0 < g["svPct"] < 1 else f"{g['svPct']:.3f}"
        alt = " alt" if i % 2 == 1 else ""
        img = f'<img src="{g["headshot"]}" class="hs" alt="">' if g["headshot"] else '<div class="hs hs-empty"></div>'
        goalie_rows.append(f'''<tr class="goalie-row{alt}"><td class="rank">{i+1}</td>
<td class="name-cell"><div class="name-flex">{img}<span class="pname">{g["name"]}</span></div></td>
<td class="r">{g["gp"]}</td><td class="r">{g["gs"]}</td>
<td class="r">{g["w"]}</td><td class="r">{g["l"]}</td><td class="r">{g["otl"]}</td>
<td class="r">{g["sa"]}</td><td class="r">{g["ga"]}</td><td class="r">{g["gaa"]:.2f}</td>
<td class="r">{g["sv"]}</td><td class="r">{svp}</td>
<td class="r">{g["so"]}</td><td class="r">{g["toi"]}</td></tr>''')

    return f'''<p class="sub-note">Click any player to see MoneyPuck advanced analytics.</p>
<div class="scroll-x"><table class="nhl-tbl">
<thead><tr><th class="rank">#</th><th class="name-col">Player</th><th class="r">Pos</th><th class="r">GP</th><th class="r">G</th><th class="r">A</th><th class="r">P</th><th class="r">+/-</th><th class="r">PIM</th><th class="r">P/GP</th><th class="r">EVG</th><th class="r">EVP</th><th class="r">PPG</th><th class="r">PPP</th><th class="r">SHG</th><th class="r">SHP</th><th class="r">OTG</th><th class="r">GWG</th><th class="r">S</th><th class="r">S%</th><th class="r">TOI/GP</th><th class="r">FOW%</th></tr></thead>
{"".join(rows)}</table></div>

<h3 style="margin-top:32px">Goaltenders</h3>
<div class="scroll-x"><table class="nhl-tbl">
<thead><tr><th class="rank">#</th><th class="name-col">Player</th><th class="r">GP</th><th class="r">GS</th><th class="r">W</th><th class="r">L</th><th class="r">OT</th><th class="r">SA</th><th class="r">GA</th><th class="r">GAA</th><th class="r">SV</th><th class="r">SV%</th><th class="r">SO</th><th class="r">TOI</th></tr></thead>
<tbody>{"".join(goalie_rows)}</tbody></table></div>'''

def build_standings_section(east_teams, east_records):
    atlantic = sorted([t for t in east_teams if t["div"] == "Atlantic"], key=lambda x: -x["pts"])
    metro = sorted([t for t in east_teams if t["div"] == "Metropolitan"], key=lambda x: -x["pts"])

    def fmt_rec(w, l, otl):
        return f"{w}-{l}-{otl}"

    def team_row(t, rank, is_playoff=False, is_cutoff=False, is_sens=False):
        cls_list = []
        if is_sens: cls_list.append("sens-row")
        if is_cutoff: cls_list.append("cutoff")
        cls = f' class="{" ".join(cls_list)}"' if cls_list else ''
        pp = f".{int(t['ptsPct']*1000):03d}" if t['ptsPct'] < 1 else f"{t['ptsPct']:.3f}"
        rank_cls = "rank-in" if is_playoff else "rank-out"
        l10 = fmt_rec(t["l10w"], t["l10l"], t["l10otl"])
        home = fmt_rec(t["homeW"], t["homeL"], t["homeOtl"])
        road = fmt_rec(t["roadW"], t["roadL"], t["roadOtl"])
        er = east_records.get(t["abbrev"], {})
        vs_ott = fmt_rec(*er.get("vsOTT", (0, 0, 0)))
        vs_above = fmt_rec(*er.get("vsAbove", (0, 0, 0)))
        vs_below = fmt_rec(*er.get("vsBelow", (0, 0, 0)))
        diff = t["gf"] - t["ga"]
        diff_str = f"+{diff}" if diff > 0 else str(diff)
        return f'''<tr{cls}><td class="{rank_cls}">{rank}</td><td class="tcol">{t["name"]}</td><td class="r">{t["gp"]}</td><td class="r">{t["w"]}</td><td class="r">{t["l"]}</td><td class="r">{t["otl"]}</td><td class="r bpts">{t["pts"]}</td><td class="r">{pp}</td><td class="r">{t["gf"]}</td><td class="r">{t["ga"]}</td><td class="r">{diff_str}</td><td class="r">{home}</td><td class="r">{road}</td><td class="r">{l10}</td><td class="r">{t["streak"]}</td><td class="r">{vs_ott}</td><td class="r">{vs_above}</td><td class="r">{vs_below}</td></tr>'''

    def div_table(teams, name):
        rows = [team_row(t, i+1, i<3, i==2, t["abbrev"]==TEAM) for i, t in enumerate(teams)]
        return f'''<div class="div-label">{name}</div><div class="scroll-x"><table class="nhl-tbl stnd-tbl">
<thead><tr><th class="rank"></th><th class="name-col">Team</th><th class="r">GP</th><th class="r">W</th><th class="r">L</th><th class="r">OTL</th><th class="r">PTS</th><th class="r">P%</th><th class="r">GF</th><th class="r">GA</th><th class="r">DIFF</th><th class="r">Home</th><th class="r">Away</th><th class="r">L10</th><th class="r">STK</th><th class="r">vs OTT</th><th class="r">vs &gt;.500</th><th class="r">vs &lt;.500</th></tr></thead>
<tbody>{"".join(rows)}</tbody></table></div>'''

    wc_all = sorted(atlantic[3:] + metro[3:], key=lambda x: -x["pts"])
    wc_rows = []
    for i, t in enumerate(wc_all):
        is_sens = t["abbrev"] == TEAM
        label = f"WC{i+1}" if i < 2 else str(i+1)
        cls_list = []
        if is_sens: cls_list.append("sens-row")
        if i == 1: cls_list.append("cutoff")
        cls = f' class="{" ".join(cls_list)}"' if cls_list else ''
        rank_cls = "rank-in" if i < 2 else "rank-out"
        pp = f".{int(t['ptsPct']*1000):03d}" if t['ptsPct'] < 1 else f"{t['ptsPct']:.3f}"
        l10 = fmt_rec(t["l10w"], t["l10l"], t["l10otl"])
        home = fmt_rec(t["homeW"], t["homeL"], t["homeOtl"])
        road = fmt_rec(t["roadW"], t["roadL"], t["roadOtl"])
        er = east_records.get(t["abbrev"], {})
        vs_ott = fmt_rec(*er.get("vsOTT", (0, 0, 0)))
        vs_above = fmt_rec(*er.get("vsAbove", (0, 0, 0)))
        vs_below = fmt_rec(*er.get("vsBelow", (0, 0, 0)))
        diff = t["gf"] - t["ga"]
        diff_str = f"+{diff}" if diff > 0 else str(diff)
        wc_rows.append(f'''<tr{cls}><td class="{rank_cls}">{label}</td><td class="tcol">{t["name"]}</td><td>{t["divAbbrev"][:3].upper()}</td><td class="r">{t["gp"]}</td><td class="r">{t["w"]}</td><td class="r">{t["l"]}</td><td class="r">{t["otl"]}</td><td class="r bpts">{t["pts"]}</td><td class="r">{pp}</td><td class="r">{t["gf"]}</td><td class="r">{t["ga"]}</td><td class="r">{diff_str}</td><td class="r">{home}</td><td class="r">{road}</td><td class="r">{l10}</td><td class="r">{t["streak"]}</td><td class="r">{vs_ott}</td><td class="r">{vs_above}</td><td class="r">{vs_below}</td></tr>''')

    wc_html = f'''<div class="div-label">Wild Card Race</div>
<div class="scroll-x"><table class="nhl-tbl stnd-tbl">
<thead><tr><th class="rank"></th><th class="name-col">Team</th><th>Div</th><th class="r">GP</th><th class="r">W</th><th class="r">L</th><th class="r">OTL</th><th class="r">PTS</th><th class="r">P%</th><th class="r">GF</th><th class="r">GA</th><th class="r">DIFF</th><th class="r">Home</th><th class="r">Away</th><th class="r">L10</th><th class="r">STK</th><th class="r">vs OTT</th><th class="r">vs &gt;.500</th><th class="r">vs &lt;.500</th></tr></thead>
<tbody>{"".join(wc_rows)}</tbody></table></div>'''
    return wc_html + div_table(atlantic, "Atlantic Division") + div_table(metro, "Metropolitan Division")

def build_projections_html(sens, vs500, mp_odds, mp_stats, east_teams):
    pts = sens["pts"]
    gp = sens["gp"]
    remaining = 82 - gp
    pace = round(sens["ptsPct"] * 2 * 82, 1)
    ott_all = mp_odds.get(TEAM, {}).get("ALL", {})
    playoff_pct = ott_all.get("playoffPct", 0)
    proj_pts = ott_all.get("projPts", pace)
    target = 93
    needed = max(0, target - pts)
    deficit = round(proj_pts - target, 1)
    progress_pct = round(pts / 164 * 100, 1)
    target_pct = round(target / 164 * 100, 1)
    w500, l500, otl500 = vs500
    ppg_needed = round(needed / remaining, 2) if remaining > 0 else 0
    ppg_current = round(pts / gp, 2) if gp > 0 else 0

    s1_w = (needed + 1) // 2
    s1_otl = needed % 2
    s1_l = max(0, remaining - s1_w - s1_otl)

    ott_mp = mp_stats.get(TEAM, {})
    ott_all = ott_mp.get("all", {})
    ott_5v5 = ott_mp.get("5v5", {})

    deficit_str = f"+{deficit}" if deficit >= 0 else str(deficit)

    # Scenario impact (next game outcomes)
    scenarios = []
    for key, label in [("WINREG", "Win (REG)"), ("WINOT", "Win (OT)"), ("LOSSOT", "Loss (OT)"), ("LOSSREG", "Loss (REG)")]:
        sc = mp_odds.get(TEAM, {}).get(key, {})
        if sc:
            scenarios.append({
                "label": label,
                "playoff": sc.get("playoffPct", 0),
                "pts": sc.get("projPts", 0),
                "r2": sc.get("round2", 0),
                "cup": sc.get("cupPct", 0),
            })

    scenario_rows = ""
    for sc in scenarios:
        d_po = sc["playoff"] - playoff_pct
        po_cls = "sc-up" if d_po > 0 else "sc-down" if d_po < 0 else ""
        scenario_rows += f'''<tr><td class="sc-label">{sc["label"]}</td><td class="r">{sc["playoff"]*100:.1f}%</td><td class="r {po_cls}">{d_po*100:+.1f}%</td><td class="r">{sc["pts"]:.0f}</td><td class="r">{sc["r2"]*100:.1f}%</td><td class="r">{sc["cup"]*100:.1f}%</td></tr>'''

    # Eastern Conference predictions table
    east_abbrevs = {t["abbrev"] for t in east_teams}
    east_odds = []
    for abbrev in east_abbrevs:
        team_data = mp_odds.get(abbrev, {}).get("ALL", {})
        if team_data:
            east_odds.append({"team": abbrev, **team_data})
    east_odds.sort(key=lambda x: -x.get("playoffPct", 0))

    east_rows = ""
    for i, t in enumerate(east_odds):
        tc = t["team"]
        is_sens = "sens-row" if tc == TEAM else ""
        east_rows += f'''<tr class="{is_sens}"><td class="rank">{i+1}</td><td class="tcol">{tc}</td><td class="r">{t.get("playoffPct",0)*100:.1f}%</td><td class="r">{t.get("round2",0)*100:.1f}%</td><td class="r">{t.get("round3",0)*100:.1f}%</td><td class="r">{t.get("finals",0)*100:.1f}%</td><td class="r">{t.get("cupPct",0)*100:.1f}%</td><td class="r">{t.get("projPts",0):.0f}</td><td class="r">{t.get("divWinPct",0)*100:.1f}%</td></tr>'''

    ott_mp = mp_stats.get(TEAM, {})
    ott_mp_all = ott_mp.get("all", {})
    ott_mp_5v5 = ott_mp.get("5v5", {})

    return f'''<div class="kpi-row">
  <div class="kpi"><div class="kpi-val">{proj_pts:.0f}</div><div class="kpi-label">Projected Points</div></div>
  <div class="kpi"><div class="kpi-val">{pts}</div><div class="kpi-label">Current Points</div></div>
  <div class="kpi"><div class="kpi-val">{needed}</div><div class="kpi-label">Points Needed</div></div>
  <div class="kpi"><div class="kpi-val">{deficit_str}</div><div class="kpi-label">vs 93 Target</div></div>
</div>

<h3 style="margin-top:28px">Points Progress</h3>
<div class="progress-wrap">
  <div class="progress-bar"><div class="progress-fill" style="width:{progress_pct}%"></div><div class="progress-marker" style="left:{target_pct}%"><span>93</span></div></div>
  <div class="progress-labels"><span>{pts} earned</span><span>{needed} needed &middot; {remaining} games left</span></div>
</div>

<h3>Next Game Impact</h3>
<p class="sub-note">How each outcome changes Ottawa's odds</p>
<div class="scroll-x"><table class="nhl-tbl">
<thead><tr><th>Outcome</th><th class="r">Playoffs</th><th class="r">Change</th><th class="r">Proj Pts</th><th class="r">2nd Rd</th><th class="r">Cup</th></tr></thead>
<tbody>{scenario_rows}</tbody></table></div>

<h3 style="margin-top:28px">Eastern Conference Predictions</h3>
<p class="sub-note">All 16 Eastern teams &mdash; sorted by playoff probability</p>
<div class="scroll-x"><table class="nhl-tbl">
<thead><tr><th class="rank">#</th><th class="name-col">Team</th><th class="r">Playoffs</th><th class="r">2nd Rd</th><th class="r">Conf F.</th><th class="r">Cup F.</th><th class="r">Win Cup</th><th class="r">Proj Pts</th><th class="r">Win Div</th></tr></thead>
<tbody>{east_rows}</tbody></table></div>

<h3 style="margin-top:28px">Team Analytics</h3>
<p class="sub-note">Ottawa's underlying performance from MoneyPuck</p>
<div class="metric-grid">
  <div class="metric-card"><div class="metric-val">{ott_mp_5v5.get("xGFpct",0)*100:.1f}%</div><div class="metric-label">xGF% (5v5)</div><div class="metric-desc">Expected goals-for share at even strength</div></div>
  <div class="metric-card"><div class="metric-val">{ott_mp_5v5.get("CFpct",0)*100:.1f}%</div><div class="metric-label">CF% (5v5)</div><div class="metric-desc">Corsi (shot attempts) share</div></div>
  <div class="metric-card"><div class="metric-val">{ott_mp_all.get("xGFpct",0)*100:.1f}%</div><div class="metric-label">xGF% (All)</div><div class="metric-desc">Expected goals share, all situations</div></div>
  <div class="metric-card"><div class="metric-val">{ott_mp_all.get("gfpg",0)}</div><div class="metric-label">GF/GP</div><div class="metric-desc">Goals for per game</div></div>
  <div class="metric-card"><div class="metric-val">{ott_mp_all.get("gapg",0)}</div><div class="metric-label">GA/GP</div><div class="metric-desc">Goals against per game</div></div>
  <div class="metric-card"><div class="metric-val">{pace}</div><div class="metric-label">Pace</div><div class="metric-desc">Projected 82-game point total</div></div>
</div>

<div class="kpi-row" style="margin-top:12px;margin-bottom:28px">
  <div class="kpi"><div class="kpi-val">{ppg_current}</div><div class="kpi-label">Current P/GP</div></div>
  <div class="kpi"><div class="kpi-val">{ppg_needed}</div><div class="kpi-label">Needed P/GP</div></div>
  <div class="kpi"><div class="kpi-val">{w500}-{l500}-{otl500}</div><div class="kpi-label">vs Above .500</div></div>
</div>

<p class="footnote">All projections from <a href="https://moneypuck.com/predictions.htm">MoneyPuck</a>. Updated automatically after each game.</p>'''

def build_schedule_html(remaining, above500_count, home_count, away_count, team_records, mp_stats, mp_odds):
    ott = team_records.get(TEAM, {})
    fmt_r = lambda w, l, o: f"{w}-{l}-{o}"
    ott_record = fmt_r(ott.get("w",0), ott.get("l",0), ott.get("otl",0))
    ott_home = fmt_r(ott.get("homeW",0), ott.get("homeL",0), ott.get("homeOtl",0))
    ott_away = fmt_r(ott.get("roadW",0), ott.get("roadL",0), ott.get("roadOtl",0))
    ott_l10 = fmt_r(ott.get("l10w",0), ott.get("l10l",0), ott.get("l10otl",0))
    ott_gf = ott.get("gf", 0)
    ott_ga = ott.get("ga", 0)
    ott_pts = ott.get("pts", 0)

    cards = []
    for g in remaining:
        prefix = "@ " if g["loc"] == "away" else "vs "
        loc_text = "Away" if g["loc"] == "away" else "Home"
        tough_cls = " tough" if g["above500"] else ""

        opp = g["oppAbbrev"]
        o = team_records.get(opp, {})
        opp_record = fmt_r(o.get("w",0), o.get("l",0), o.get("otl",0))
        opp_home = fmt_r(o.get("homeW",0), o.get("homeL",0), o.get("homeOtl",0))
        opp_away = fmt_r(o.get("roadW",0), o.get("roadL",0), o.get("roadOtl",0))
        opp_l10 = fmt_r(o.get("l10w",0), o.get("l10l",0), o.get("l10otl",0))
        opp_gf = o.get("gf", 0)
        opp_ga = o.get("ga", 0)
        o_pts = o.get("pts", 0)

        def row(label, v_ott, v_opp):
            return f'<tr><td class="cmp-stat-l">{v_ott}</td><td class="cmp-stat-label">{label}</td><td class="cmp-stat-r">{v_opp}</td></tr>'

        rows = row("Record", ott_record, opp_record) + row("PTS", ott_pts, o_pts) + row("Home", ott_home, opp_home) + row("Away", ott_away, opp_away) + row("L10", ott_l10, opp_l10) + row("GF", ott_gf, opp_gf) + row("GA", ott_ga, opp_ga)

        cards.append(f'''<details class="game-detail{tough_cls}">
<summary class="game-summary"><div class="game-left"><span class="game-date">{g["date"]}</span><span class="game-opp">{prefix}{g["opp"]}</span></div><div class="game-right"><span class="game-meta">{opp_record} &middot; {o_pts}p</span><span class="game-loc loc-{g["loc"]}">{loc_text}</span></div></summary>
<div class="game-expand">
  <table class="cmp-tbl"><thead><tr><th>OTT</th><th></th><th>{opp}</th></tr></thead><tbody>{rows}</tbody></table>
</div></details>''')

    return f'''<div class="sched-meta">
  <span>{len(remaining)} games remaining</span>
  <span>{home_count} home &middot; {away_count} away</span>
  <span>{above500_count} vs above .500</span>
</div>
<p class="sub-note">Click any game to compare records.</p>
<div class="sched-list">{"".join(cards)}</div>'''

def generate_html(sens, roster_html, standings_html, projections_html, schedule_html, vs500, mp_odds, deltas):
    now = datetime.now(timezone.utc).strftime("%B %-d, %Y at %-I:%M %p UTC")
    record = f"{sens['w']}-{sens['l']}-{sens['otl']}"
    remaining = 82 - sens["gp"]
    pace = round(sens["ptsPct"] * 2 * 82, 1)
    home_rec = f"{sens['homeW']}-{sens['homeL']}-{sens['homeOtl']}"
    road_rec = f"{sens['roadW']}-{sens['roadL']}-{sens['roadOtl']}"
    l10 = f"{sens['l10w']}-{sens['l10l']}-{sens['l10otl']}"
    w500, l500, otl500 = vs500
    ott_odds = mp_odds.get(TEAM, {}).get("ALL", {})
    playoff_pct = ott_odds.get("playoffPct", 0)
    proj_pts = ott_odds.get("projPts", pace)
    target = 93
    needed = max(0, target - sens["pts"])
    gap = round(proj_pts - target, 1)
    gap_str = f"+{gap}" if gap >= 0 else str(gap)

    # Delta indicators
    d_pct = fmt_delta(playoff_pct, deltas.get("playoffPct"), fmt="pct")
    d_needed = fmt_delta(needed, deltas.get("needed"), invert=True)
    d_gap = fmt_delta(gap, deltas.get("gap"))
    d_pts = fmt_delta(sens["pts"], deltas.get("pts"))

    return f'''<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Ottawa Senators — 2025-26</title>
<style>
:root{{--bg:#ffffff;--bg-hover:#f7f6f3;--bg-tag:#f1f1ef;--border:#e3e3e0;--text:#37352f;--text-secondary:#787774;--text-muted:#b4b4b0;--black:#111;--accent:#37352f}}
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Helvetica,"Apple Color Emoji",Arial,sans-serif,"Segoe UI Emoji","Segoe UI Symbol";background:var(--bg);color:var(--text);line-height:1.5;-webkit-font-smoothing:antialiased}}
a{{color:var(--text);text-decoration:underline;text-underline-offset:2px}}
a:hover{{color:var(--black)}}

/* Top Bar */
.top-bar{{height:4px;background:#111}}

/* Header */
.header{{max-width:900px;margin:0 auto;padding:32px 24px 0}}
.hdr-top{{display:flex;justify-content:space-between;align-items:center;margin-bottom:20px}}
.hdr-left{{display:flex;align-items:center;gap:16px}}
.team-logo{{width:56px;height:56px;filter:grayscale(1) contrast(1.2)}}
.header h1{{font-size:26px;font-weight:700;letter-spacing:-0.5px;margin-bottom:1px}}
.header .subtitle{{font-size:13px;color:var(--text-secondary);font-variant-numeric:tabular-nums}}
.hdr-pct{{text-align:right}}
.pct-val{{font-size:36px;font-weight:700;letter-spacing:-1px;line-height:1}}
.pct-label{{display:block;font-size:11px;color:var(--text-muted);text-transform:uppercase;letter-spacing:0.5px;margin-top:4px}}
.delta{{display:inline-block;font-size:11px;font-weight:600;margin-left:4px;vertical-align:middle}}
@media(max-width:500px){{.team-logo{{width:40px;height:40px}}.header h1{{font-size:22px}}.pct-val{{font-size:28px}}}}

.stat-row{{display:flex;gap:6px;flex-wrap:wrap;padding-bottom:24px;margin-bottom:0;border-bottom:1px solid var(--border)}}
.stat-pill{{display:inline-flex;align-items:center;gap:5px;padding:4px 10px;border:1px solid var(--border);border-radius:6px;font-size:13px;white-space:nowrap}}
.stat-pill .sl{{color:var(--text-muted);font-size:10px;text-transform:uppercase;letter-spacing:0.5px}}
.stat-pill .sv{{font-weight:600}}

/* Tabs (CSS only) */
.container{{max-width:900px;margin:0 auto;padding:0 24px 60px}}
input[name="tab"]{{display:none}}
.tab-bar{{display:flex;gap:0;border-bottom:1px solid var(--border);margin-bottom:28px}}
.tab-bar label{{padding:8px 16px;font-size:14px;font-weight:500;color:var(--text-secondary);cursor:pointer;border-bottom:2px solid transparent;margin-bottom:-1px;transition:color 0.1s}}
.tab-bar label:hover{{color:var(--text)}}
.panel{{display:none}}
#tab-roster:checked~.tab-bar label[for="tab-roster"],
#tab-standings:checked~.tab-bar label[for="tab-standings"],
#tab-playoffs:checked~.tab-bar label[for="tab-playoffs"],
#tab-schedule:checked~.tab-bar label[for="tab-schedule"]{{color:var(--text);font-weight:600;border-bottom-color:var(--black)}}
#tab-roster:checked~#p-roster,
#tab-standings:checked~#p-standings,
#tab-playoffs:checked~#p-playoffs,
#tab-schedule:checked~#p-schedule{{display:block}}

/* Typography */
h3{{font-size:16px;font-weight:600;margin-bottom:12px;letter-spacing:-0.2px}}
.sub-note{{font-size:13px;color:var(--text-secondary);margin-bottom:16px}}

/* Tables */
.tbl{{width:100%;border-collapse:collapse;font-size:13px}}
.tbl th{{padding:6px 10px;font-weight:500;font-size:11px;text-transform:uppercase;letter-spacing:0.5px;color:var(--text-muted);text-align:left;border-bottom:1px solid var(--border)}}
.tbl th.r,.tbl td.r{{text-align:right}}
.tbl td{{padding:7px 10px;border-bottom:1px solid #f0f0ef;font-variant-numeric:tabular-nums}}
.tbl tbody tr:hover{{background:var(--bg-hover)}}
/* NHL.com Stats Table */
.nhl-tbl{{width:100%;border-collapse:collapse;font-size:12px;font-variant-numeric:tabular-nums}}
.nhl-tbl thead th{{background:#111;color:#fff;padding:8px 6px;font-weight:600;font-size:10px;text-transform:uppercase;letter-spacing:0.5px;text-align:left;white-space:nowrap;position:sticky;top:0}}
.nhl-tbl thead th.r{{text-align:right}}
.nhl-tbl thead th.rank{{width:30px;text-align:center}}
.nhl-tbl thead th.name-col{{min-width:160px}}
.nhl-tbl td{{padding:5px 6px;border:none;white-space:nowrap}}
.nhl-tbl td.r{{text-align:right}}
.nhl-tbl td.rank{{text-align:center;color:var(--text-muted);font-size:11px}}
.nhl-tbl td.pts-col{{font-weight:700}}
.nhl-tbl .player-summary:hover td{{background:#eef1f7}}
.nhl-tbl .player-summary.alt td{{background:#f7f7f8}}
.nhl-tbl .player-summary.alt:hover td{{background:#eaecf0}}
.nhl-tbl .goalie-row:hover td{{background:#eef1f7}}
.nhl-tbl .goalie-row.alt td{{background:#f7f7f8}}
.nhl-tbl .goalie-row.alt:hover td{{background:#eaecf0}}
/* Headshot */
.hs{{width:32px;height:32px;border-radius:50%;object-fit:cover;flex-shrink:0;background:#e8e8e8}}
.hs-empty{{display:inline-block}}
.name-cell{{padding-left:4px}}
.name-flex{{display:flex;align-items:center;gap:8px}}
.pname{{font-weight:600;white-space:nowrap;font-size:13px}}
.ppos{{font-size:10px;color:var(--text-muted);margin-left:4px}}
.name-wrap{{display:flex;align-items:baseline;gap:4px}}
/* Details toggle for player */
.pd{{display:inline}}.pd summary.pd-s{{display:flex;align-items:center;gap:8px;cursor:pointer;list-style:none}}
.pd summary.pd-s::-webkit-details-marker{{display:none}}
.pd summary.pd-s::marker{{display:none;content:""}}
.player-group{{border-bottom:1px solid #eee}}
/* Expand row */
.expand-row{{display:none}}
.pd[open]+td,.pd[open]~td{{}}
.player-group:has(.pd[open]) .expand-row{{display:table-row}}
.expand-row td{{padding:16px;background:#fafafa;border-top:1px solid #eee}}
.px-grid{{display:grid;grid-template-columns:repeat(3,1fr);gap:20px}}
@media(max-width:600px){{.px-grid{{grid-template-columns:1fr 1fr}}}}
.px-section{{}}
.px-title{{font-size:10px;font-weight:600;text-transform:uppercase;letter-spacing:0.8px;color:var(--text-muted);margin-bottom:8px;padding-bottom:4px;border-bottom:1px solid var(--border)}}
.px-row{{display:flex;justify-content:space-between;font-size:12px;padding:2px 0}}
.px-label{{color:var(--text-secondary)}}
.px-val{{font-weight:600;font-variant-numeric:tabular-nums}}
.sens-row td{{background:#f7f6f3}}.sens-row td:first-child{{font-weight:700}}
.cutoff td{{border-bottom:2px dashed var(--text-muted)}}
.rank-in{{font-weight:600;color:var(--text)}}.rank-out{{color:var(--text-muted)}}
.tcol{{font-weight:600;white-space:nowrap}}.bpts{{font-weight:700}}
.div-label{{margin:28px 0 8px;font-size:12px;font-weight:600;text-transform:uppercase;letter-spacing:0.8px;color:var(--text-muted)}}
.div-label:first-child{{margin-top:0}}
.stnd-tbl td{{padding:5px 5px;font-size:11px}}.stnd-tbl thead th{{padding:6px 5px;font-size:9px}}
.stnd-tbl .sens-row td{{background:#f7f6f3}}
.scroll-x{{overflow-x:auto;-webkit-overflow-scrolling:touch}}

/* KPI Row */
.kpi-row{{display:flex;gap:12px;flex-wrap:wrap;margin-bottom:12px}}
.kpi{{flex:1;min-width:100px;padding:16px;border:1px solid var(--border);border-radius:8px;text-align:center}}
.kpi-val{{font-size:28px;font-weight:700;letter-spacing:-1px;line-height:1.1}}
.kpi-label{{font-size:11px;color:var(--text-secondary);margin-top:4px;text-transform:uppercase;letter-spacing:0.5px}}
.kpi-sub{{font-size:10px;color:var(--text-muted);margin-top:2px}}

/* Progress bar */
.progress-wrap{{margin-bottom:32px}}
.progress-bar{{height:8px;background:var(--bg-tag);border-radius:4px;position:relative;overflow:visible;margin-bottom:8px}}
.progress-fill{{height:100%;border-radius:4px;background:var(--black)}}
.progress-marker{{position:absolute;top:-4px;width:2px;height:16px;background:var(--text-muted);border-radius:1px}}
.progress-marker span{{position:absolute;top:-18px;font-size:10px;color:var(--text-muted);font-weight:600;white-space:nowrap;transform:translateX(-50%);left:50%}}
.progress-labels{{display:flex;justify-content:space-between;font-size:12px;color:var(--text-secondary)}}

/* Metric grid */
.metric-grid{{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin-bottom:32px}}
@media(max-width:600px){{.metric-grid{{grid-template-columns:1fr 1fr}}}}
.metric-card{{padding:16px;border:1px solid var(--border);border-radius:8px}}
.metric-val{{font-size:24px;font-weight:700;letter-spacing:-0.5px}}
.metric-label{{font-size:12px;font-weight:600;color:var(--text);margin-top:2px}}
.metric-desc{{font-size:11px;color:var(--text-muted);margin-top:2px}}

/* Scenario impact */
.sc-label{{font-weight:600;white-space:nowrap}}
.sc-up{{color:#1a8a1a;font-weight:600}}
.sc-down{{color:#c43c3c;font-weight:600}}
/* Scenarios */
.scenario{{padding:12px 16px;border:1px solid var(--border);border-radius:8px;margin-bottom:8px;font-size:13px;line-height:1.6}}
.tag{{display:inline-block;font-size:11px;font-weight:600;padding:1px 7px;border-radius:4px;margin-right:4px;vertical-align:middle}}
.tag-dark{{background:var(--black);color:#fff}}
.tag-muted{{background:var(--bg-tag);color:var(--text-secondary)}}
.footnote{{margin-top:24px;font-size:12px;color:var(--text-muted);line-height:1.6}}

/* Schedule */
.sched-meta{{display:flex;gap:16px;flex-wrap:wrap;font-size:13px;color:var(--text-secondary);margin-bottom:8px}}
.sched-list{{display:flex;flex-direction:column;gap:4px}}
.game-detail{{border-radius:8px;overflow:hidden}}
.game-detail.tough{{border-left:3px solid var(--black)}}
.game-summary{{display:flex;justify-content:space-between;align-items:center;padding:10px 14px;cursor:pointer;list-style:none;border:1px solid var(--border);border-radius:8px;transition:background 0.1s}}
.game-summary:hover{{background:var(--bg-hover)}}
.game-summary::-webkit-details-marker{{display:none}}
.game-summary::marker{{display:none;content:""}}
.game-detail[open] .game-summary{{border-bottom-left-radius:0;border-bottom-right-radius:0;border-bottom-color:transparent}}
.game-left{{display:flex;align-items:center;gap:12px}}
.game-date{{font-size:12px;color:var(--text-muted);min-width:44px}}
.game-opp{{font-size:14px;font-weight:600}}
.game-right{{display:flex;align-items:center;gap:10px}}
.game-meta{{font-size:12px;color:var(--text-muted)}}
.game-loc{{font-size:11px;font-weight:600;padding:2px 6px;border-radius:4px}}
.loc-home{{background:#eef8ee;color:#3d8c40}}
.loc-away{{background:#f5f5f5;color:var(--text-secondary)}}
.game-expand{{border:1px solid var(--border);border-top:0;border-bottom-left-radius:8px;border-bottom-right-radius:8px;padding:16px}}
.cmp-tbl{{width:100%;border-collapse:collapse;font-size:13px}}
.cmp-tbl thead th{{font-size:12px;font-weight:700;padding:6px 8px;border-bottom:2px solid var(--border);text-align:center}}
.cmp-tbl thead th:first-child{{text-align:left}}
.cmp-tbl thead th:last-child{{text-align:right}}
.cmp-tbl td{{padding:5px 8px;border-bottom:1px solid var(--border)}}
.cmp-stat-l{{font-weight:600;text-align:left}}
.cmp-stat-label{{text-align:center;font-size:11px;color:var(--text-muted);text-transform:uppercase;letter-spacing:0.5px}}
.cmp-stat-r{{font-weight:600;text-align:right}}

/* Footer */
.footer{{text-align:center;padding:24px;font-size:12px;color:var(--text-muted);border-top:1px solid var(--border);max-width:900px;margin:0 auto}}
</style></head><body>

<div class="top-bar"></div>
<div class="header">
  <div class="hdr-top">
    <div class="hdr-left">
      <img src="https://assets.nhle.com/logos/nhl/svg/OTT_dark.svg" alt="Ottawa Senators" class="team-logo">
      <div>
        <h1>Ottawa Senators</h1>
        <div class="subtitle">{record} &middot; {sens["pts"]} pts &middot; {sens["gp"]} GP</div>
      </div>
    </div>
    <div class="hdr-pct"><span class="pct-val">{playoff_pct*100:.1f}%{d_pct}</span><span class="pct-label">Playoff Odds</span></div>
  </div>
  <div class="stat-row">
    <span class="stat-pill"><span class="sl">Home</span> <span class="sv">{home_rec}</span></span>
    <span class="stat-pill"><span class="sl">Away</span> <span class="sv">{road_rec}</span></span>
    <span class="stat-pill"><span class="sl">L10</span> <span class="sv">{l10}</span></span>
    <span class="stat-pill"><span class="sl">Streak</span> <span class="sv">{sens["streak"]}</span></span>
    <span class="stat-pill"><span class="sl">Pace</span> <span class="sv">{pace}</span></span>
  </div>
</div>

<div class="container">
  <input type="radio" name="tab" id="tab-playoffs" checked>
  <input type="radio" name="tab" id="tab-standings">
  <input type="radio" name="tab" id="tab-schedule">
  <input type="radio" name="tab" id="tab-roster">
  <div class="tab-bar">
    <label for="tab-playoffs">Playoff Odds</label>
    <label for="tab-standings">Standings</label>
    <label for="tab-schedule">Remaining Games</label>
    <label for="tab-roster">Player Stats</label>
  </div>
  <div class="panel" id="p-playoffs">{projections_html}</div>
  <div class="panel" id="p-standings">
    <h3>Eastern Conference Standings</h3>
    {standings_html}
  </div>
  <div class="panel" id="p-schedule">{schedule_html}</div>
  <div class="panel" id="p-roster">{roster_html}</div>
</div>
<div class="footer">NHL API + <a href="https://moneypuck.com">MoneyPuck</a> &middot; Auto-updated via GitHub Actions</div>
</body></html>'''

# ── Main ──────────────────────────────────────────────────

def main():
    print("Fetching NHL standings...")
    standings = fetch_standings()
    sens, east_teams, all_teams = get_team_data(standings)
    above500 = get_above500_teams(all_teams)
    team_records = get_team_records(all_teams)
    print(f"  Ottawa: {sens['w']}-{sens['l']}-{sens['otl']} ({sens['pts']} pts)")

    print("Fetching NHL club stats...")
    club_stats = fetch_club_stats()
    print("Fetching NHL stats API (skater + goalie summary)...")
    nhl_skater_summary = fetch_nhl_skater_summary()
    nhl_goalie_summary = fetch_nhl_goalie_summary()
    print(f"  Stats API: {len(nhl_skater_summary)} skaters, {len(nhl_goalie_summary)} goalies")
    skaters = get_skaters(club_stats, nhl_skater_summary)
    goalies = get_goalies(club_stats, nhl_goalie_summary)
    print(f"  {len(skaters)} skaters, {len(goalies)} goalies")

    print("Fetching NHL schedule...")
    schedule_data = fetch_schedule()
    remaining = get_remaining_schedule(schedule_data, above500)
    results = get_results(schedule_data)
    vs500 = compute_vs_above500(results, above500)
    print(f"  {len(remaining)} remaining, vs .500: {vs500[0]}-{vs500[1]}-{vs500[2]}")

    print("Fetching MoneyPuck playoff odds...")
    mp_odds = fetch_moneypuck_odds()
    ott_odds = mp_odds.get(TEAM, {}).get("ALL", {})
    print(f"  Playoff: {ott_odds.get('playoffPct',0)*100:.1f}%, Proj: {ott_odds.get('projPts',0):.0f} pts")

    print("Fetching MoneyPuck team stats...")
    mp_stats = fetch_moneypuck_team_stats()
    print(f"  {len(mp_stats)} teams loaded")

    print("Fetching MoneyPuck player stats...")
    mp_players = fetch_moneypuck_player_stats()
    print(f"  {len(mp_players)} OTT players loaded")

    above500_count = sum(1 for g in remaining if g["above500"])
    home_count = sum(1 for g in remaining if g["loc"] == "home")
    away_count = sum(1 for g in remaining if g["loc"] == "away")

    # Delta tracking
    prev = load_previous()
    target = 93
    needed = max(0, target - sens["pts"])
    proj_pts = ott_odds.get("projPts", 0)
    gap = round(proj_pts - target, 1)
    deltas = {
        "playoffPct": prev.get("playoffPct"),
        "pts": prev.get("pts"),
        "needed": prev.get("needed"),
        "gap": prev.get("gap"),
    }
    current = {
        "playoffPct": ott_odds.get("playoffPct", 0),
        "pts": sens["pts"],
        "needed": needed,
        "gap": gap,
    }
    # Only save if points changed (i.e., a game was actually played)
    if prev.get("pts") != sens["pts"]:
        save_current(current)
        print(f"  Saved snapshot (pts changed: {prev.get('pts')} -> {sens['pts']})")
    elif not prev:
        save_current(current)
        print("  Saved initial snapshot")
    else:
        print("  No game played since last update, skipping snapshot save")

    print("Fetching Eastern Conference team schedules...")
    east_records = fetch_east_team_records(east_teams, above500)
    print(f"  {len(east_records)} team records computed")

    print("Building HTML...")
    roster_html = build_roster_html(skaters, goalies, mp_players)
    standings_html = build_standings_section(east_teams, east_records)
    projections_html = build_projections_html(sens, vs500, mp_odds, mp_stats, east_teams)
    schedule_html = build_schedule_html(remaining, above500_count, home_count, away_count, team_records, mp_stats, mp_odds)
    html = generate_html(sens, roster_html, standings_html, projections_html, schedule_html, vs500, mp_odds, deltas)

    with open("index.html", "w") as f:
        f.write(html)
    print("Done! index.html generated.")

if __name__ == "__main__":
    main()
