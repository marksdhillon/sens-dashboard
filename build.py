#!/usr/bin/env python3
"""
Ottawa Senators Dashboard Builder
Fetches live data from the NHL API + MoneyPuck analytics and generates a static dashboard.
"""

import csv
import io
import json
import os
import re
import unicodedata
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

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

def fetch_sens_news():
    """Fetch recent Ottawa Senators news/trade articles from Google News RSS."""
    queries = [
        "%22Ottawa+Senators%22+trade",
        "%22Ottawa+Senators%22+rumors+OR+rumours",
        "%22Ottawa+Senators%22+NHL+deadline",
    ]
    seen_titles = set()
    articles = []
    for q in queries:
        url = f"https://news.google.com/rss/search?q={q}&hl=en-CA&gl=CA&ceid=CA:en"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "SensDashboard/1.0"})
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = resp.read()
            root = ET.fromstring(data)
            for item in root.findall(".//item"):
                title_el = item.find("title")
                link_el = item.find("link")
                source_el = item.find("source")
                pub_el = item.find("pubDate")
                if title_el is None or link_el is None:
                    continue
                title = title_el.text or ""
                # Deduplicate by normalized title
                norm_title = re.sub(r"\s+", " ", title.lower().strip())
                if norm_title in seen_titles:
                    continue
                seen_titles.add(norm_title)
                source = source_el.text if source_el is not None else ""
                link = link_el.text or ""
                pub_str = pub_el.text if pub_el is not None else ""
                try:
                    pub_dt = parsedate_to_datetime(pub_str)
                except Exception:
                    pub_dt = datetime.now(timezone.utc)
                # Clean title: remove " - Source Name" suffix Google News appends
                clean_title = re.sub(r"\s*-\s*" + re.escape(source) + r"$", "", title) if source else title
                articles.append({
                    "title": clean_title,
                    "source": source,
                    "link": link,
                    "date": pub_dt,
                    "date_str": pub_dt.strftime("%b %-d"),
                    "time_str": pub_dt.strftime("%-I:%M %p"),
                })
        except Exception as e:
            print(f"  Warning: RSS fetch failed for query: {e}")
    articles.sort(key=lambda x: x["date"], reverse=True)
    return articles[:25]

def normalize_name(name):
    """Strip non-ASCII for cross-source name matching (e.g. Stützle/Sttzle -> Sttzle)."""
    return "".join(c for c in name if ord(c) < 128)

def fetch_moneypuck_player_stats():
    """Fetch individual player advanced stats from MoneyPuck for OTT."""
    rows = fetch_csv_rows(f"{MONEYPUCK}/playerData/seasonSummary/{SEASON_SHORT}/regular/skaters.csv")
    players = {}
    for r in rows:
        if r.get("team") != TEAM:
            continue
        name = normalize_name(r.get("name", ""))
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
    for i, s in enumerate(skaters):
        pm_val = s["pm"]
        pm_str = f"+{pm_val}" if pm_val > 0 else str(pm_val)
        alt = " alt" if i % 2 == 1 else ""
        fo_str = f'{s["foPct"]:.1f}' if s["foPct"] > 0 else "--"
        img = f'<img src="{s["headshot"]}" class="hs" alt="">' if s["headshot"] else '<div class="hs hs-empty"></div>'
        toi_sec = int(s["toi"].split(":")[0]) * 60 + int(s["toi"].split(":")[1])
        fo_sort = s["foPct"] if s["foPct"] > 0 else 0

        # MoneyPuck advanced stats (inline columns)
        mp = mp_players.get(normalize_name(s["name"]), {})
        mp_all = mp.get("all", {})
        mp5 = mp.get("5v5", {})
        xg = mp_all.get("xG", 0)
        g_minus_xg = round(s["g"] - xg, 1)
        gxg_str = f"{g_minus_xg:+.1f}" if xg > 0 else "--"
        gxg_sort = g_minus_xg if xg > 0 else 0
        gxg_cls = " adv-pos" if g_minus_xg > 0.5 else " adv-neg" if g_minus_xg < -0.5 else ""
        game_score = mp_all.get("gameScore", 0)
        gs_pg = round(game_score / s["gp"], 2) if s["gp"] > 0 and game_score else 0
        gs_str = f"{gs_pg:.2f}" if gs_pg else "--"
        gs_sort = gs_pg if gs_pg else 0
        xgf_pct = mp5.get("xGFpct", 0)
        xgf_str = f"{xgf_pct*100:.1f}" if xgf_pct > 0 else "--"
        xgf_sort = xgf_pct * 100 if xgf_pct > 0 else 0

        rows.append(f'''<tr class="player-summary{alt}">
<td class="rank" data-sort="{i+1}">{i+1}</td>
<td class="name-cell" data-sort="{s["name"]}"><div class="name-flex">{img}<span class="pname">{s["name"]}</span></div></td>
<td class="r pos-col" data-sort="{s["pos"]}">{s["pos"]}</td>
<td class="r" data-sort="{s["gp"]}">{s["gp"]}</td><td class="r" data-sort="{s["g"]}">{s["g"]}</td><td class="r" data-sort="{s["a"]}">{s["a"]}</td>
<td class="r pts-col" data-sort="{s["pts"]}">{s["pts"]}</td><td class="r" data-sort="{s["pm"]}">{pm_str}</td>
<td class="r" data-sort="{s["pim"]}">{s["pim"]}</td><td class="r" data-sort="{s["ppg"]:.2f}">{s["ppg"]:.2f}</td>
<td class="r" data-sort="{s["evg"]}">{s["evg"]}</td><td class="r" data-sort="{s["evp"]}">{s["evp"]}</td>
<td class="r" data-sort="{s["ppGoals"]}">{s["ppGoals"]}</td><td class="r" data-sort="{s["ppPts"]}">{s["ppPts"]}</td>
<td class="r" data-sort="{s["shGoals"]}">{s["shGoals"]}</td><td class="r" data-sort="{s["shPts"]}">{s["shPts"]}</td>
<td class="r" data-sort="{s["otg"]}">{s["otg"]}</td><td class="r" data-sort="{s["gwg"]}">{s["gwg"]}</td>
<td class="r" data-sort="{s["shots"]}">{s["shots"]}</td><td class="r" data-sort="{s["shPct"]}">{s["shPct"]}</td>
<td class="r" data-sort="{toi_sec}">{s["toi"]}</td><td class="r" data-sort="{fo_sort}">{fo_str}</td>
<td class="r adv{gxg_cls}" data-sort="{gxg_sort}">{gxg_str}</td>
<td class="r adv" data-sort="{xgf_sort}">{xgf_str}</td>
<td class="r adv" data-sort="{gs_sort}">{gs_str}</td>
</tr>''')

    goalie_rows = []
    for i, g in enumerate(goalies):
        svp = f".{int(g['svPct']*1000):03d}" if 0 < g["svPct"] < 1 else f"{g['svPct']:.3f}"
        alt = " alt" if i % 2 == 1 else ""
        img = f'<img src="{g["headshot"]}" class="hs" alt="">' if g["headshot"] else '<div class="hs hs-empty"></div>'
        toi_parts = g["toi"].split(":")
        g_toi_sec = int(toi_parts[0]) * 60 + int(toi_parts[1]) if len(toi_parts) == 2 else 0
        goalie_rows.append(f'''<tr class="goalie-row{alt}"><td class="rank" data-sort="{i+1}">{i+1}</td>
<td class="name-cell" data-sort="{g["name"]}"><div class="name-flex">{img}<span class="pname">{g["name"]}</span></div></td>
<td class="r" data-sort="{g["gp"]}">{g["gp"]}</td><td class="r" data-sort="{g["gs"]}">{g["gs"]}</td>
<td class="r" data-sort="{g["w"]}">{g["w"]}</td><td class="r" data-sort="{g["l"]}">{g["l"]}</td><td class="r" data-sort="{g["otl"]}">{g["otl"]}</td>
<td class="r" data-sort="{g["sa"]}">{g["sa"]}</td><td class="r" data-sort="{g["ga"]}">{g["ga"]}</td><td class="r" data-sort="{g["gaa"]:.2f}">{g["gaa"]:.2f}</td>
<td class="r" data-sort="{g["sv"]}">{g["sv"]}</td><td class="r" data-sort="{g["svPct"]:.4f}">{svp}</td>
<td class="r" data-sort="{g["so"]}">{g["so"]}</td><td class="r" data-sort="{g_toi_sec}">{g["toi"]}</td></tr>''')

    return f'''<div class="scroll-x"><table class="nhl-tbl sortable" id="skater-tbl">
<thead><tr><th class="rank sort-th" data-col="0" title="Rank by points">#</th><th class="name-col sort-th" data-col="1" title="Player name">Player</th><th class="r sort-th" data-col="2" title="Position (C, L, R, D)">Pos</th><th class="r sort-th" data-col="3" title="Games played this season">GP</th><th class="r sort-th" data-col="4" title="Goals scored">G</th><th class="r sort-th" data-col="5" title="Assists">A</th><th class="r sort-th" data-col="6" title="Points (goals + assists)">P</th><th class="r sort-th" data-col="7" title="Plus/minus: on-ice goal differential at even strength">+/-</th><th class="r sort-th" data-col="8" title="Penalty minutes">PIM</th><th class="r sort-th" data-col="9" title="Points per game played">P/GP</th><th class="r sort-th" data-col="10" title="Even-strength goals">EVG</th><th class="r sort-th" data-col="11" title="Even-strength points">EVP</th><th class="r sort-th" data-col="12" title="Power-play goals">PPG</th><th class="r sort-th" data-col="13" title="Power-play points">PPP</th><th class="r sort-th" data-col="14" title="Short-handed goals">SHG</th><th class="r sort-th" data-col="15" title="Short-handed points">SHP</th><th class="r sort-th" data-col="16" title="Overtime goals">OTG</th><th class="r sort-th" data-col="17" title="Game-winning goals">GWG</th><th class="r sort-th" data-col="18" title="Shots on goal">S</th><th class="r sort-th" data-col="19" title="Shooting %: goals ÷ shots on goal">S%</th><th class="r sort-th" data-col="20" title="Average time on ice per game">TOI</th><th class="r sort-th" data-col="21" title="Faceoff win %: faceoffs won ÷ total faceoffs">FO%</th><th class="r sort-th adv-hdr" data-col="22" title="Goals minus expected goals. Positive = scoring more than expected (MoneyPuck)">G-xG</th><th class="r sort-th adv-hdr" data-col="23" title="Expected goals for %: share of expected goals when on ice at 5v5 (MoneyPuck)">xGF%</th><th class="r sort-th adv-hdr" data-col="24" title="GameScore per game: composite rating combining goals, assists, shots, blocks, etc. (MoneyPuck)">GS/GP</th></tr></thead>
<tbody>{"".join(rows)}</tbody></table></div>

<h3 style="margin-top:32px">Goaltenders</h3>
<div class="scroll-x"><table class="nhl-tbl sortable" id="goalie-tbl">
<thead><tr><th class="rank sort-th" data-col="0" title="Rank by games played">#</th><th class="name-col sort-th" data-col="1" title="Player name">Player</th><th class="r sort-th" data-col="2" title="Games played">GP</th><th class="r sort-th" data-col="3" title="Games started">GS</th><th class="r sort-th" data-col="4" title="Wins">W</th><th class="r sort-th" data-col="5" title="Losses">L</th><th class="r sort-th" data-col="6" title="Overtime losses">OT</th><th class="r sort-th" data-col="7" title="Shots against">SA</th><th class="r sort-th" data-col="8" title="Goals against">GA</th><th class="r sort-th" data-col="9" title="Goals against average: goals allowed per 60 minutes">GAA</th><th class="r sort-th" data-col="10" title="Saves: shots faced minus goals allowed">SV</th><th class="r sort-th" data-col="11" title="Save %: saves ÷ shots against">SV%</th><th class="r sort-th" data-col="12" title="Shutouts: games with zero goals allowed">SO</th><th class="r sort-th" data-col="13" title="Total time on ice">TOI</th></tr></thead>
<tbody>{"".join(goalie_rows)}</tbody></table></div>'''

def build_news_html(articles):
    if not articles:
        return '<p class="sub-note">No recent articles found.</p>'
    items = []
    for a in articles:
        items.append(f'''<a href="{a["link"]}" target="_blank" rel="noopener" class="news-item">
<div class="news-meta"><span class="news-source">{a["source"]}</span><span class="news-date">{a["date_str"]} &middot; {a["time_str"]}</span></div>
<div class="news-title">{a["title"]}</div></a>''')
    return f'<div class="news-list">{"".join(items)}</div>'

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
  <div class="kpi"><div class="kpi-val">{target}</div><div class="kpi-label">Pts to Make Playoffs</div></div>
  <div class="kpi"><div class="kpi-val">{pts}</div><div class="kpi-label">Current Pts</div></div>
  <div class="kpi"><div class="kpi-val">{needed}</div><div class="kpi-label">Pts Needed</div></div>
  <div class="kpi"><div class="kpi-val">{deficit_str}</div><div class="kpi-label">Projected vs Target</div></div>
</div>

<h3>Next Game Impact</h3>
<div class="scroll-x"><table class="nhl-tbl">
<thead><tr><th>Outcome</th><th class="r">Playoffs</th><th class="r">Change</th><th class="r">Proj Pts</th><th class="r">2nd Rd</th><th class="r">Cup</th></tr></thead>
<tbody>{scenario_rows}</tbody></table></div>

<h3 style="margin-top:28px">Eastern Conference</h3>
<div class="scroll-x"><table class="nhl-tbl">
<thead><tr><th class="rank">#</th><th class="name-col">Team</th><th class="r">Playoffs</th><th class="r">2nd Rd</th><th class="r">Conf F.</th><th class="r">Cup F.</th><th class="r">Win Cup</th><th class="r">Proj Pts</th><th class="r">Win Div</th></tr></thead>
<tbody>{east_rows}</tbody></table></div>

<p class="footnote">Data from <a href="https://moneypuck.com/predictions.htm">MoneyPuck</a></p>'''

def build_schedule_html(remaining, above500_count, home_count, away_count, team_records, mp_stats, mp_odds, results):
    ott = team_records.get(TEAM, {})
    fmt_r = lambda w, l, o: f"{w}-{l}-{o}"
    ott_record = fmt_r(ott.get("w",0), ott.get("l",0), ott.get("otl",0))
    ott_home = fmt_r(ott.get("homeW",0), ott.get("homeL",0), ott.get("homeOtl",0))
    ott_away = fmt_r(ott.get("roadW",0), ott.get("roadL",0), ott.get("roadOtl",0))
    ott_l10 = fmt_r(ott.get("l10w",0), ott.get("l10l",0), ott.get("l10otl",0))
    ott_gf = ott.get("gf", 0)
    ott_ga = ott.get("ga", 0)
    ott_pts = ott.get("pts", 0)
    ott_gp = ott.get("gp", 1)
    ott_mp = mp_stats.get(TEAM, {})
    ott_odds_all = mp_odds.get(TEAM, {}).get("ALL", {})

    # Season series: count W/L/OTL vs each opponent
    series = {}
    for r in results:
        a = r["oppAbbrev"]
        if a not in series:
            series[a] = {"W": 0, "L": 0, "OTL": 0}
        series[a][r["result"]] += 1

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
        opp_gp = o.get("gp", 1)

        def row(label, v_ott, v_opp):
            return f'<tr><td class="cmp-stat-l">{v_ott}</td><td class="cmp-stat-label">{label}</td><td class="cmp-stat-r">{v_opp}</td></tr>'

        rows = row("Record", ott_record, opp_record) + row("PTS", ott_pts, o_pts) + row("Home", ott_home, opp_home) + row("Away", ott_away, opp_away) + row("L10", ott_l10, opp_l10) + row("GF", ott_gf, opp_gf) + row("GA", ott_ga, opp_ga)

        # ── Build matchup insights ──
        notes = []

        # 1. Season series
        s = series.get(opp)
        if s:
            sw, sl, so = s["W"], s["L"], s["OTL"]
            series_str = f"{sw}-{sl}-{so}"
            if sw > sl + so:
                notes.append(f"OTT leads season series {series_str}")
            elif sl > sw:
                notes.append(f"OTT trails season series {series_str}")
            elif sw == sl and so == 0:
                notes.append(f"Season series tied {series_str}")
            else:
                notes.append(f"Season series: {series_str}")
        else:
            notes.append("First meeting of the season")

        # 2. Points gap context
        gap = ott_pts - o_pts
        if abs(gap) <= 3:
            notes.append(f"Separated by only {abs(gap)} pts — a direct rival")
        elif gap > 0:
            notes.append(f"OTT holds a {gap}-pt lead over {opp}")
        else:
            notes.append(f"{opp} holds a {abs(gap)}-pt lead over OTT")

        # 3. Opponent playoff odds (if available)
        opp_odds = mp_odds.get(opp, {}).get("ALL", {})
        opp_playoff_pct = opp_odds.get("playoffPct", 0)
        if opp_playoff_pct >= 0.95:
            notes.append(f"{opp} is a virtual lock for playoffs ({opp_playoff_pct*100:.0f}%)")
        elif opp_playoff_pct >= 0.6:
            notes.append(f"{opp} projected to make playoffs ({opp_playoff_pct*100:.0f}% odds)")
        elif opp_playoff_pct >= 0.2:
            notes.append(f"{opp} is on the bubble ({opp_playoff_pct*100:.0f}% playoff odds)")
        elif opp_playoff_pct > 0:
            notes.append(f"{opp} is fading — only {opp_playoff_pct*100:.0f}% playoff odds")
        else:
            notes.append(f"{opp} is out of the playoff picture")

        # 4. Scoring rate comparison
        ott_gfpg = round(ott_gf / ott_gp, 1) if ott_gp else 0
        opp_gfpg = round(opp_gf / opp_gp, 1) if opp_gp else 0
        combined = round(ott_gfpg + opp_gfpg, 1)
        if combined >= 6.6:
            notes.append(f"High-scoring matchup — combined {combined} goals/game avg")
        elif combined <= 5.2:
            notes.append(f"Low-scoring matchup — combined {combined} goals/game avg")

        # 5. L10 hot/cold
        opp_l10w = o.get("l10w", 0)
        opp_l10l = o.get("l10l", 0)
        if opp_l10w >= 7:
            notes.append(f"{opp} is hot — {opp_l10} in last 10")
        elif opp_l10w <= 3:
            notes.append(f"{opp} is cold — {opp_l10} in last 10")

        notes_html = "".join(f'<li>{n}</li>' for n in notes[:4])

        cards.append(f'''<details class="game-detail{tough_cls}">
<summary class="game-summary"><div class="game-left"><span class="game-date">{g["date"]}</span><span class="game-opp">{prefix}{g["opp"]}</span></div><div class="game-right"><span class="game-meta">{opp_record} &middot; {o_pts}p</span><span class="game-loc loc-{g["loc"]}">{loc_text}</span></div></summary>
<div class="game-expand">
  <table class="cmp-tbl"><thead><tr><th>OTT</th><th></th><th>{opp}</th></tr></thead><tbody>{rows}</tbody></table>
  <ul class="matchup-notes">{notes_html}</ul>
</div></details>''')

    return f'''<div class="sched-meta">
  <span>{len(remaining)} games remaining</span>
  <span>{home_count} home &middot; {away_count} away</span>
  <span>{above500_count} vs above .500</span>
</div>
<div class="sched-list">{"".join(cards)}</div>'''

def generate_html(sens, roster_html, standings_html, projections_html, schedule_html, news_html, vs500, mp_odds, deltas):
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
.container{{max-width:900px;margin:0 auto;padding:0 24px 48px}}
input[name="tab"]{{display:none}}
.tab-bar{{display:flex;gap:0;border-bottom:1px solid var(--border);margin-bottom:24px}}
.tab-bar label{{padding:8px 16px;font-size:14px;font-weight:500;color:var(--text-secondary);cursor:pointer;border-bottom:2px solid transparent;margin-bottom:-1px;transition:color 0.1s}}
.tab-bar label:hover{{color:var(--text)}}
.panel{{display:none}}
#tab-roster:checked~.tab-bar label[for="tab-roster"],
#tab-standings:checked~.tab-bar label[for="tab-standings"],
#tab-playoffs:checked~.tab-bar label[for="tab-playoffs"],
#tab-schedule:checked~.tab-bar label[for="tab-schedule"],
#tab-news:checked~.tab-bar label[for="tab-news"],
#tab-community:checked~.tab-bar label[for="tab-community"]{{color:var(--text);font-weight:600;border-bottom-color:var(--black)}}
#tab-roster:checked~#p-roster,
#tab-standings:checked~#p-standings,
#tab-playoffs:checked~#p-playoffs,
#tab-schedule:checked~#p-schedule,
#tab-news:checked~#p-news,
#tab-community:checked~#p-community{{display:block}}

/* Typography */
h3{{font-size:16px;font-weight:600;margin-bottom:12px;letter-spacing:-0.2px}}
.sub-note{{font-size:13px;color:var(--text-secondary);margin-bottom:16px}}

/* Tables */
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
/* Advanced stat columns */
.adv{{color:var(--text-secondary)}}
.adv-pos{{color:#1a8a1a;font-weight:600}}
.adv-neg{{color:#c43c3c;font-weight:600}}
.adv-hdr{{background:#1a1a2e !important}}
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
.kpi-row{{display:flex;gap:10px;flex-wrap:wrap;margin-bottom:24px}}
.kpi{{flex:1;min-width:90px;padding:14px;border:1px solid var(--border);border-radius:8px;text-align:center}}
.kpi-val{{font-size:26px;font-weight:700;letter-spacing:-1px;line-height:1.1}}
.kpi-label{{font-size:11px;color:var(--text-secondary);margin-top:4px;text-transform:uppercase;letter-spacing:0.5px}}

/* Scenario impact */
.sc-label{{font-weight:600;white-space:nowrap}}
.sc-up{{color:#1a8a1a;font-weight:600}}
.sc-down{{color:#c43c3c;font-weight:600}}
.footnote{{margin-top:24px;font-size:12px;color:var(--text-muted)}}

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
.matchup-notes{{margin:12px 0 0;padding:0 0 0 18px;font-size:12px;color:var(--text-muted);line-height:1.6}}
.matchup-notes li{{margin-bottom:2px}}

/* News / Trade Rumors */
.news-list{{display:flex;flex-direction:column;gap:2px}}
.news-item{{display:block;padding:12px 14px;border-radius:8px;text-decoration:none;transition:background 0.1s}}
.news-item:hover{{background:var(--bg-hover);text-decoration:none}}
.news-meta{{display:flex;justify-content:space-between;align-items:center;margin-bottom:4px}}
.news-source{{font-size:11px;font-weight:600;text-transform:uppercase;letter-spacing:0.5px;color:var(--text-muted)}}
.news-date{{font-size:11px;color:var(--text-muted)}}
.news-title{{font-size:14px;font-weight:500;color:var(--text);line-height:1.4}}

/* Community */
.community-list{{display:grid;grid-template-columns:1fr 1fr;gap:10px}}
@media(max-width:560px){{.community-list{{grid-template-columns:1fr}}}}
.community-card{{display:block;padding:16px;border:1px solid var(--border);border-radius:8px;text-decoration:none;transition:background 0.1s,border-color 0.1s}}
.community-card:hover{{background:var(--bg-hover);border-color:var(--text-muted);text-decoration:none}}
.cc-name{{font-size:14px;font-weight:600;color:var(--text);margin-bottom:4px}}
.cc-desc{{font-size:12px;color:var(--text-secondary);line-height:1.4}}

/* Sortable columns */
.sort-th{{cursor:pointer;user-select:none;position:relative}}
.sort-th:hover{{background:#222}}
.sort-th::after{{content:"";display:inline-block;margin-left:3px;opacity:0.3;font-size:8px;vertical-align:middle}}
.sort-th.asc::after{{content:"\\25B2";opacity:0.9}}
.sort-th.desc::after{{content:"\\25BC";opacity:0.9}}

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
      </div>
    </div>
    <div class="hdr-pct"><span class="pct-val">{playoff_pct*100:.1f}%{d_pct}</span><span class="pct-label">Playoff Odds</span></div>
  </div>
  <div class="stat-row">
    <span class="stat-pill"><span class="sl">Record</span> <span class="sv">{record}</span></span>
    <span class="stat-pill"><span class="sl">Home</span> <span class="sv">{home_rec}</span></span>
    <span class="stat-pill"><span class="sl">Away</span> <span class="sv">{road_rec}</span></span>
    <span class="stat-pill"><span class="sl">PTS</span> <span class="sv">{sens["pts"]}</span></span>
    <span class="stat-pill"><span class="sl">GP</span> <span class="sv">{sens["gp"]}</span></span>
    <span class="stat-pill"><span class="sl">L10</span> <span class="sv">{l10}</span></span>
    <span class="stat-pill"><span class="sl">Streak</span> <span class="sv">{sens["streak"]}</span></span>
  </div>
</div>

<div class="container">
  <input type="radio" name="tab" id="tab-standings" checked>
  <input type="radio" name="tab" id="tab-schedule">
  <input type="radio" name="tab" id="tab-roster">
  <input type="radio" name="tab" id="tab-playoffs">
  <input type="radio" name="tab" id="tab-news">
  <input type="radio" name="tab" id="tab-community">
  <div class="tab-bar">
    <label for="tab-standings">Standings</label>
    <label for="tab-schedule">Remaining Games</label>
    <label for="tab-roster">Player Stats</label>
    <label for="tab-playoffs">Playoff Odds</label>
    <label for="tab-news">Trade Rumors</label>
    <label for="tab-community">Community</label>
  </div>
  <div class="panel" id="p-standings">{standings_html}</div>
  <div class="panel" id="p-schedule">{schedule_html}</div>
  <div class="panel" id="p-roster">{roster_html}</div>
  <div class="panel" id="p-playoffs">{projections_html}</div>
  <div class="panel" id="p-news">{news_html}</div>
  <div class="panel" id="p-community">
    <div class="community-list">
      <a href="https://forums.hfboards.com/forums/ottawa-senators.98/" target="_blank" rel="noopener" class="community-card"><div class="cc-name">HFBoards</div><div class="cc-desc">The longest-running hockey forum. Trade talk, game threads, prospect discussions.</div></a>
      <a href="https://www.reddit.com/r/OttawaSenators/" target="_blank" rel="noopener" class="community-card"><div class="cc-name">r/OttawaSenators</div><div class="cc-desc">Reddit community. Memes, highlights, post-game threads, and fan takes.</div></a>
      <a href="https://x.com/search?q=%22Ottawa%20Senators%22&src=typed_query&f=live" target="_blank" rel="noopener" class="community-card"><div class="cc-name">X / Twitter</div><div class="cc-desc">Live feed of Senators mentions. Breaking news, insider tweets, fan reactions.</div></a>
      <a href="https://www.reddit.com/r/hockey/" target="_blank" rel="noopener" class="community-card"><div class="cc-name">r/hockey</div><div class="cc-desc">The main NHL subreddit. League-wide discussion, trades, and highlights.</div></a>
    </div>
  </div>
</div>
<div class="footer">Data from NHL API &amp; <a href="https://moneypuck.com">MoneyPuck</a></div>
<script>
document.querySelectorAll(".sortable").forEach(function(tbl){{
  tbl.querySelectorAll(".sort-th").forEach(function(th){{
    th.addEventListener("click",function(){{
      var col=parseInt(th.dataset.col),asc=th.classList.contains("asc");
      tbl.querySelectorAll(".sort-th").forEach(function(h){{h.classList.remove("asc","desc")}});
      var dir=asc?"desc":"asc";
      th.classList.add(dir);
      var tbody=tbl.querySelector("tbody");
      var rows=Array.from(tbody.querySelectorAll("tr"));
      rows.sort(function(a,b){{
        var ca=a.children[col],cb=b.children[col];
        var va=ca?ca.dataset.sort:"",vb=cb?cb.dataset.sort:"";
        var na=parseFloat(va),nb=parseFloat(vb);
        if(!isNaN(na)&&!isNaN(nb))return dir==="asc"?na-nb:nb-na;
        return dir==="asc"?va.localeCompare(vb):vb.localeCompare(va);
      }});
      rows.forEach(function(r){{tbody.appendChild(r)}});
    }});
  }});
}});
</script>
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

    print("Fetching trade rumors / news...")
    news_articles = fetch_sens_news()
    print(f"  {len(news_articles)} articles found")

    print("Building HTML...")
    roster_html = build_roster_html(skaters, goalies, mp_players)
    standings_html = build_standings_section(east_teams, east_records)
    projections_html = build_projections_html(sens, vs500, mp_odds, mp_stats, east_teams)
    schedule_html = build_schedule_html(remaining, above500_count, home_count, away_count, team_records, mp_stats, mp_odds, results)
    news_html = build_news_html(news_articles)
    html = generate_html(sens, roster_html, standings_html, projections_html, schedule_html, news_html, vs500, mp_odds, deltas)

    with open("index.html", "w") as f:
        f.write(html)
    print("Done! index.html generated.")

if __name__ == "__main__":
    main()
