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
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime

TEAM = "OTT"  # Global — set per iteration in main()
DEFAULT_TEAM = "OTT"
SEASON = "20252026"
SEASON_SHORT = "2025"
NHL_API = "https://api-web.nhle.com/v1"
MONEYPUCK = "https://moneypuck.com/moneypuck"

# All 32 NHL team configs
TEAM_INFO = {
    # --- Eastern Conference ---
    # Atlantic
    "BOS": {"name": "Boston Bruins", "franchise_id": 6, "accent": "#e8b230", "subreddit": "BostonBruins", "div": "Atlantic"},
    "BUF": {"name": "Buffalo Sabres", "franchise_id": 19, "accent": "#6b9fff", "subreddit": "sabres", "div": "Atlantic"},
    "DET": {"name": "Detroit Red Wings", "franchise_id": 12, "accent": "#e8384f", "subreddit": "DetroitRedWings", "div": "Atlantic"},
    "FLA": {"name": "Florida Panthers", "franchise_id": 33, "accent": "#c8102e", "subreddit": "FloridaPanthers", "div": "Atlantic"},
    "MTL": {"name": "Montreal Canadiens", "franchise_id": 1, "accent": "#d42e42", "subreddit": "Habs", "div": "Atlantic"},
    "OTT": {"name": "Ottawa Senators", "franchise_id": 30, "accent": "#e8384f", "subreddit": "OttawaSenators", "div": "Atlantic"},
    "TBL": {"name": "Tampa Bay Lightning", "franchise_id": 31, "accent": "#6b9fff", "subreddit": "TampaBayLightning", "div": "Atlantic"},
    "TOR": {"name": "Toronto Maple Leafs", "franchise_id": 5, "accent": "#6b9fff", "subreddit": "leafs", "div": "Atlantic"},
    # Metropolitan
    "CAR": {"name": "Carolina Hurricanes", "franchise_id": 26, "accent": "#e8384f", "subreddit": "canes", "div": "Metropolitan"},
    "CBJ": {"name": "Columbus Blue Jackets", "franchise_id": 36, "accent": "#6b9fff", "subreddit": "BlueJackets", "div": "Metropolitan"},
    "NJD": {"name": "New Jersey Devils", "franchise_id": 23, "accent": "#e8384f", "subreddit": "devils", "div": "Metropolitan"},
    "NYI": {"name": "New York Islanders", "franchise_id": 22, "accent": "#f47d30", "subreddit": "NewYorkIslanders", "div": "Metropolitan"},
    "NYR": {"name": "New York Rangers", "franchise_id": 10, "accent": "#6b9fff", "subreddit": "rangers", "div": "Metropolitan"},
    "PHI": {"name": "Philadelphia Flyers", "franchise_id": 16, "accent": "#f47d30", "subreddit": "Flyers", "div": "Metropolitan"},
    "PIT": {"name": "Pittsburgh Penguins", "franchise_id": 17, "accent": "#e8b230", "subreddit": "penguins", "div": "Metropolitan"},
    "WSH": {"name": "Washington Capitals", "franchise_id": 24, "accent": "#c8102e", "subreddit": "caps", "div": "Metropolitan"},
    # --- Western Conference ---
    # Central
    "CHI": {"name": "Chicago Blackhawks", "franchise_id": 11, "accent": "#e8384f", "subreddit": "hawks", "div": "Central"},
    "COL": {"name": "Colorado Avalanche", "franchise_id": 27, "accent": "#c84060", "subreddit": "ColoradoAvalanche", "div": "Central"},
    "DAL": {"name": "Dallas Stars", "franchise_id": 15, "accent": "#00a651", "subreddit": "DallasStars", "div": "Central"},
    "MIN": {"name": "Minnesota Wild", "franchise_id": 37, "accent": "#2e8540", "subreddit": "wildhockey", "div": "Central"},
    "NSH": {"name": "Nashville Predators", "franchise_id": 34, "accent": "#ffb81c", "subreddit": "Predators", "div": "Central"},
    "STL": {"name": "St. Louis Blues", "franchise_id": 18, "accent": "#4477ce", "subreddit": "stlouisblues", "div": "Central"},
    "UTA": {"name": "Utah Hockey Club", "franchise_id": 28, "accent": "#69b3e7", "subreddit": "UtahHC", "div": "Central"},
    "WPG": {"name": "Winnipeg Jets", "franchise_id": 35, "accent": "#6888b0", "subreddit": "winnipegjets", "div": "Central"},
    # Pacific
    "ANA": {"name": "Anaheim Ducks", "franchise_id": 32, "accent": "#f47d30", "subreddit": "AnaheimDucks", "div": "Pacific"},
    "CGY": {"name": "Calgary Flames", "franchise_id": 21, "accent": "#d2001c", "subreddit": "CalgaryFlames", "div": "Pacific"},
    "EDM": {"name": "Edmonton Oilers", "franchise_id": 25, "accent": "#ff6b2b", "subreddit": "EdmontonOilers", "div": "Pacific"},
    "LAK": {"name": "Los Angeles Kings", "franchise_id": 14, "accent": "#a2aaad", "subreddit": "losangeleskings", "div": "Pacific"},
    "SEA": {"name": "Seattle Kraken", "franchise_id": 39, "accent": "#68cfd1", "subreddit": "SeattleKraken", "div": "Pacific"},
    "SJS": {"name": "San Jose Sharks", "franchise_id": 29, "accent": "#009aa6", "subreddit": "SanJoseSharks", "div": "Pacific"},
    "VAN": {"name": "Vancouver Canucks", "franchise_id": 20, "accent": "#4080c4", "subreddit": "canucks", "div": "Pacific"},
    "VGK": {"name": "Vegas Golden Knights", "franchise_id": 38, "accent": "#b4975a", "subreddit": "goldenknights", "div": "Pacific"},
}

def accent_rgba(hex_color, alpha):
    h = hex_color.lstrip('#')
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r},{g},{b},{alpha})"

def darken_hex(hex_color, factor=0.85):
    h = hex_color.lstrip('#')
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    r, g, b = min(255, int(r * factor)), min(255, int(g * factor)), min(255, int(b * factor))
    return f"#{r:02x}{g:02x}{b:02x}"

# ── Fetchers ──────────────────────────────────────────────

def fetch_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": "SensDashboard/1.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read())

def fetch_scores():
    """Fetch today's NHL scores from the API."""
    try:
        data = fetch_json(f"{NHL_API}/score/now")
        return data
    except Exception as e:
        print(f"  WARNING: scores fetch failed: {e}")
        return {"currentDate": "", "prevDate": {"default": ""}, "nextDate": {"default": ""}, "games": []}

def fetch_game_details(game_id):
    """Fetch boxscore and scoring summary for a game."""
    details = {"boxscore": None, "scoring": None}
    try:
        landing = fetch_json(f"{NHL_API}/gamecenter/{game_id}/landing")
        details["scoring"] = landing.get("summary", {}).get("scoring", [])
    except Exception:
        pass
    try:
        box = fetch_json(f"{NHL_API}/gamecenter/{game_id}/boxscore")
        pstats = box.get("playerByGameStats", {})
        details["boxscore"] = pstats
    except Exception:
        pass
    return details

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
    fid = TEAM_INFO.get(TEAM, {}).get("franchise_id", 30)
    url = (
        "https://api.nhle.com/stats/rest/en/skater/summary?"
        "isAggregate=false&isGame=false"
        "&sort=%5B%7B%22property%22:%22points%22,%22direction%22:%22DESC%22%7D%5D"
        "&start=0&limit=100"
        "&factCayenneExp=gamesPlayed%3E=1"
        f"&cayenneExp=franchiseId%3D{fid}%20and%20seasonId%3C={SEASON}%20and%20seasonId%3E={SEASON}%20and%20gameTypeId=2"
    )
    data = fetch_json(url)
    return {p["playerId"]: p for p in data.get("data", [])}

def fetch_nhl_goalie_summary():
    """Fetch full goalie summary from NHL stats API (gamesStarted, timeOnIce, etc.)."""
    fid = TEAM_INFO.get(TEAM, {}).get("franchise_id", 30)
    url = (
        "https://api.nhle.com/stats/rest/en/goalie/summary?"
        "isAggregate=false&isGame=false"
        "&sort=%5B%7B%22property%22:%22wins%22,%22direction%22:%22DESC%22%7D%5D"
        "&start=0&limit=20"
        "&factCayenneExp=gamesPlayed%3E=1"
        f"&cayenneExp=franchiseId%3D{fid}%20and%20seasonId%3C={SEASON}%20and%20seasonId%3E={SEASON}%20and%20gameTypeId=2"
    )
    data = fetch_json(url)
    return {g["playerId"]: g for g in data.get("data", [])}

def fetch_team_news():
    """Fetch recent team news/trade articles from Google News RSS."""
    team_name = TEAM_INFO.get(TEAM, {}).get("name", "Ottawa Senators")
    encoded = team_name.replace(" ", "+")
    queries = [
        f"%22{encoded}%22+trade",
        f"%22{encoded}%22+rumors+OR+rumours",
        f"%22{encoded}%22+NHL",
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

def fetch_all_moneypuck_players():
    """Fetch individual player advanced stats from MoneyPuck for all teams."""
    rows = fetch_csv_rows(f"{MONEYPUCK}/playerData/seasonSummary/{SEASON_SHORT}/regular/skaters.csv")
    all_players = {}
    for r in rows:
        team = r.get("team", "")
        if not team:
            continue
        name = normalize_name(r.get("name", ""))
        sit = r.get("situation", "")
        if not name:
            continue
        if team not in all_players:
            all_players[team] = {}
        if name not in all_players[team]:
            all_players[team][name] = {}
        gp = int(float(r.get("games_played", 0) or 0))
        ice = float(r.get("icetime", 0) or 0)
        if sit == "5on5":
            all_players[team][name]["5v5"] = {
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
            all_players[team][name]["all"] = {
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
    return all_players

# ── Persistence (delta tracking) ──────────────────────────

def load_previous():
    prev_file = f"previous_{TEAM}.json"
    if os.path.exists(prev_file):
        try:
            with open(prev_file) as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    return {}

def save_current(data):
    prev_file = f"previous_{TEAM}.json"
    with open(prev_file, "w") as f:
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
    color = "var(--green)" if is_good else "var(--red)"
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
    west_teams = []
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
        elif info["conf"] == "Western":
            west_teams.append(info)
        if abbrev == TEAM:
            sens = info
    return sens, east_teams, west_teams, all_teams

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
            "gaa": round(ns.get("goalsAgainstAverage") or g.get("goalsAgainstAverage") or 0, 2),
            "sv": ns.get("saves", g.get("saves", 0)),
            "svPct": round(ns.get("savePct") or g.get("savePercentage") or 0, 3),
            "so": ns.get("shutouts", g.get("shutouts", 0)),
            "toi": toi_str,
        })
    goalies.sort(key=lambda x: x["gp"], reverse=True)
    return goalies

def fetch_all_schedules(all_teams):
    """Fetch schedules for all teams once. Returns dict of abbrev -> schedule data."""
    schedules = {}
    for t in all_teams:
        abbrev = t["abbrev"]
        try:
            schedules[abbrev] = fetch_json(f"{NHL_API}/club-schedule-season/{abbrev}/{SEASON}")
        except Exception:
            schedules[abbrev] = {"games": []}
    return schedules

def compute_conf_records(all_schedules, focus_team, conf_teams, above500):
    """Compute standings records from cached schedules for a given focus team."""
    records = {}
    for t in conf_teams:
        abbrev = t["abbrev"]
        data = all_schedules.get(abbrev, {"games": []})
        vs_focus = [0, 0, 0]
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
            if my_score > opp_score:
                result = 0
            elif period in ("OT", "SO"):
                result = 2
            else:
                result = 1
            if opp == focus_team:
                vs_focus[result] += 1
            if opp in above500:
                vs_above[result] += 1
            else:
                vs_below[result] += 1
        records[abbrev] = {
            "vsFocus": tuple(vs_focus),
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
    if not skaters and not goalies:
        return '<div class="empty-state"><span>&#127917;</span>Player stats unavailable. Data will refresh shortly.</div>'
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
<td class="name-cell" data-sort="{s["name"]}"><div class="name-flex">{img}<a href="https://www.hockeydb.com/ihdb/stats/find_player.php?full_name={s["name"].replace(" ", "+")}" target="_blank" rel="noopener" class="pname">{s["name"]}</a></div></td>
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
<td class="name-cell" data-sort="{g["name"]}"><div class="name-flex">{img}<a href="https://www.hockeydb.com/ihdb/stats/find_player.php?full_name={g["name"].replace(" ", "+")}" target="_blank" rel="noopener" class="pname">{g["name"]}</a></div></td>
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
        return '<div class="empty-state"><span>&#128240;</span>No recent trade rumors found. Check back later.</div>'
    items = []
    for a in articles:
        items.append(f'''<a href="{a["link"]}" target="_blank" rel="noopener" class="news-item">
<div class="news-meta"><span class="news-source">{a["source"]}</span><span class="news-date">{a["date_str"]} &middot; {a["time_str"]}</span></div>
<div class="news-title">{a["title"]}</div></a>''')
    return f'<div class="news-list">{"".join(items)}</div>'

ESPN_SLUGS = {
    "BOS": ("bos", "boston-bruins"), "BUF": ("buf", "buffalo-sabres"),
    "DET": ("det", "detroit-red-wings"), "FLA": ("fla", "florida-panthers"),
    "MTL": ("mtl", "montreal-canadiens"), "OTT": ("ott", "ottawa-senators"),
    "TBL": ("tb", "tampa-bay-lightning"), "TOR": ("tor", "toronto-maple-leafs"),
    "CAR": ("car", "carolina-hurricanes"), "CBJ": ("cbj", "columbus-blue-jackets"),
    "NJD": ("nj", "new-jersey-devils"), "NYI": ("nyi", "new-york-islanders"),
    "NYR": ("nyr", "new-york-rangers"), "PHI": ("phi", "philadelphia-flyers"),
    "PIT": ("pit", "pittsburgh-penguins"), "WSH": ("wsh", "washington-capitals"),
    "ANA": ("ana", "anaheim-ducks"), "CGY": ("cgy", "calgary-flames"),
    "EDM": ("edm", "edmonton-oilers"), "LAK": ("la", "los-angeles-kings"),
    "SEA": ("sea", "seattle-kraken"), "SJS": ("sj", "san-jose-sharks"),
    "VAN": ("van", "vancouver-canucks"), "VGK": ("vgs", "vegas-golden-knights"),
    "CHI": ("chi", "chicago-blackhawks"), "COL": ("col", "colorado-avalanche"),
    "DAL": ("dal", "dallas-stars"), "MIN": ("min", "minnesota-wild"),
    "NSH": ("nsh", "nashville-predators"), "STL": ("stl", "st-louis-blues"),
    "WPG": ("wpg", "winnipeg-jets"), "UTA": ("utah", "utah-hockey-club"),
}

def espn_link(abbrev, display):
    slug = ESPN_SLUGS.get(abbrev)
    if slug:
        return f'<a href="https://www.espn.com/nhl/team/_/name/{slug[0]}/{slug[1]}" target="_blank" rel="noopener" class="tcol-link">{display}</a>'
    return display

def build_standings_section(conf_teams, conf_records, conf_name):
    if conf_name == "Eastern":
        div1_name, div2_name = "Atlantic", "Metropolitan"
    else:
        div1_name, div2_name = "Central", "Pacific"

    div1 = sorted([t for t in conf_teams if t["div"] == div1_name], key=lambda x: -x["pts"])
    div2 = sorted([t for t in conf_teams if t["div"] == div2_name], key=lambda x: -x["pts"])

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
        er = conf_records.get(t["abbrev"], {})
        vs_focus = fmt_rec(*er.get("vsFocus", (0, 0, 0)))
        vs_above = fmt_rec(*er.get("vsAbove", (0, 0, 0)))
        vs_below = fmt_rec(*er.get("vsBelow", (0, 0, 0)))
        diff = t["gf"] - t["ga"]
        diff_str = f"+{diff}" if diff > 0 else str(diff)
        return f'''<tr{cls}><td class="{rank_cls}">{rank}</td><td class="tcol">{espn_link(t["abbrev"], t["name"])}</td><td class="r">{t["gp"]}</td><td class="r">{t["w"]}</td><td class="r">{t["l"]}</td><td class="r">{t["otl"]}</td><td class="r bpts">{t["pts"]}</td><td class="r">{pp}</td><td class="r">{t["gf"]}</td><td class="r">{t["ga"]}</td><td class="r">{diff_str}</td><td class="r">{home}</td><td class="r">{road}</td><td class="r">{l10}</td><td class="r">{t["streak"]}</td><td class="r">{vs_focus}</td><td class="r">{vs_above}</td><td class="r">{vs_below}</td></tr>'''

    def div_table(teams, name):
        rows = [team_row(t, i+1, i<3, i==2, t["abbrev"]==TEAM) for i, t in enumerate(teams)]
        return f'''<div class="div-label">{name}</div><div class="stnd-card"><div class="scroll-x"><table class="nhl-tbl stnd-tbl">
<thead><tr><th class="rank"></th><th class="name-col">Team</th><th class="r">GP</th><th class="r">W</th><th class="r">L</th><th class="r">OTL</th><th class="r">PTS</th><th class="r">P%</th><th class="r">GF</th><th class="r">GA</th><th class="r">DIFF</th><th class="r">Home</th><th class="r">Away</th><th class="r">L10</th><th class="r">STK</th><th class="r">vs {TEAM}</th><th class="r">vs &gt;.500</th><th class="r">vs &lt;.500</th></tr></thead>
<tbody>{"".join(rows)}</tbody></table></div></div>'''

    # Wild Card view
    wc_all = sorted(div1[3:] + div2[3:], key=lambda x: -x["pts"])
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
        er = conf_records.get(t["abbrev"], {})
        vs_focus = fmt_rec(*er.get("vsFocus", (0, 0, 0)))
        vs_above = fmt_rec(*er.get("vsAbove", (0, 0, 0)))
        vs_below = fmt_rec(*er.get("vsBelow", (0, 0, 0)))
        diff = t["gf"] - t["ga"]
        diff_str = f"+{diff}" if diff > 0 else str(diff)
        wc_rows.append(f'''<tr{cls}><td class="{rank_cls}">{label}</td><td class="tcol">{espn_link(t["abbrev"], t["name"])}</td><td>{t["divAbbrev"][:3].upper()}</td><td class="r">{t["gp"]}</td><td class="r">{t["w"]}</td><td class="r">{t["l"]}</td><td class="r">{t["otl"]}</td><td class="r bpts">{t["pts"]}</td><td class="r">{pp}</td><td class="r">{t["gf"]}</td><td class="r">{t["ga"]}</td><td class="r">{diff_str}</td><td class="r">{home}</td><td class="r">{road}</td><td class="r">{l10}</td><td class="r">{t["streak"]}</td><td class="r">{vs_focus}</td><td class="r">{vs_above}</td><td class="r">{vs_below}</td></tr>''')

    wc_html = f'''<div class="div-label">Wild Card Race</div>
<div class="stnd-card"><div class="scroll-x"><table class="nhl-tbl stnd-tbl">
<thead><tr><th class="rank"></th><th class="name-col">Team</th><th>Div</th><th class="r">GP</th><th class="r">W</th><th class="r">L</th><th class="r">OTL</th><th class="r">PTS</th><th class="r">P%</th><th class="r">GF</th><th class="r">GA</th><th class="r">DIFF</th><th class="r">Home</th><th class="r">Away</th><th class="r">L10</th><th class="r">STK</th><th class="r">vs {TEAM}</th><th class="r">vs &gt;.500</th><th class="r">vs &lt;.500</th></tr></thead>
<tbody>{"".join(wc_rows)}</tbody></table></div></div>'''

    conf_view = div_table(div1, f"{div1_name} Division") + div_table(div2, f"{div2_name} Division")

    return f'''<div class="stnd-toggle">
<input type="radio" id="sv-conf" name="stnd-view" checked>
<input type="radio" id="sv-wc" name="stnd-view">
<div class="stnd-toggle-bar"><label for="sv-conf">Conference</label><label for="sv-wc">Wild Card</label></div>
<div class="sv-conf">{conf_view}</div>
<div class="sv-wc">{wc_html}</div>
</div>'''

def build_projections_html(sens, vs500, mp_odds, mp_stats, conf_teams):
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

    # Conference predictions table
    conf_abbrevs = {t["abbrev"] for t in conf_teams}
    conf_name = conf_teams[0]["conf"] if conf_teams else "Eastern"
    conf_odds = []
    for abbrev in conf_abbrevs:
        team_data = mp_odds.get(abbrev, {}).get("ALL", {})
        if team_data:
            conf_odds.append({"team": abbrev, **team_data})
    conf_odds.sort(key=lambda x: -x.get("playoffPct", 0))

    conf_rows = ""
    for i, t in enumerate(conf_odds):
        tc = t["team"]
        is_sens = "sens-row" if tc == TEAM else ""
        conf_rows += f'''<tr class="{is_sens}"><td class="rank">{i+1}</td><td class="tcol">{espn_link(tc, tc)}</td><td class="r">{t.get("playoffPct",0)*100:.1f}%</td><td class="r">{t.get("round2",0)*100:.1f}%</td><td class="r">{t.get("round3",0)*100:.1f}%</td><td class="r">{t.get("finals",0)*100:.1f}%</td><td class="r">{t.get("cupPct",0)*100:.1f}%</td><td class="r">{t.get("projPts",0):.0f}</td><td class="r">{t.get("divWinPct",0)*100:.1f}%</td></tr>'''

    ott_mp = mp_stats.get(TEAM, {})
    ott_mp_all = ott_mp.get("all", {})
    ott_mp_5v5 = ott_mp.get("5v5", {})

    proj_diff = proj_pts - target
    diff_sign = "+" if proj_diff >= 0 else ""
    diff_color = "var(--green)" if proj_diff >= 0 else "var(--red)"
    return f'''<div class="kpi-row">
  <div class="kpi"><div class="kpi-val">{target}</div><div class="kpi-label">Playoff Target</div></div>
  <div class="kpi"><div class="kpi-val">{proj_pts:.0f} <span style="font-size:16px;color:{diff_color}">({diff_sign}{proj_diff:.0f})</span></div><div class="kpi-label">Projected Pts</div></div>
  <div class="kpi"><div class="kpi-val">{pts}</div><div class="kpi-label">Current Pts</div></div>
  <div class="kpi"><div class="kpi-val">{needed}</div><div class="kpi-label">Pts Still Needed</div></div>
</div>

<h3>Next Game Impact</h3>
<div class="scroll-x"><table class="nhl-tbl">
<thead><tr><th>Outcome</th><th class="r">Playoffs</th><th class="r">Change</th><th class="r">Proj Pts</th><th class="r">2nd Rd</th><th class="r">Cup</th></tr></thead>
<tbody>{scenario_rows}</tbody></table></div>

<h3 style="margin-top:28px">{conf_name} Conference</h3>
<div class="scroll-x"><table class="nhl-tbl">
<thead><tr><th class="rank">#</th><th class="name-col">Team</th><th class="r">Playoffs</th><th class="r">2nd Rd</th><th class="r">Conf F.</th><th class="r">Cup F.</th><th class="r">Win Cup</th><th class="r">Proj Pts</th><th class="r">Win Div</th></tr></thead>
<tbody>{conf_rows}</tbody></table></div>

<p class="footnote">Data from <a href="https://moneypuck.com/predictions.htm">MoneyPuck</a></p>'''

def build_schedule_html(remaining, above500_count, home_count, away_count, team_records, mp_stats, mp_odds, results):
    if not remaining:
        return '<div class="empty-state"><span>&#127944;</span>Season complete! No remaining games.</div>'
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

    # Determine which teams are in a playoff position (top 3 per div + 2 WC per conf)
    playoff_teams = set()
    for conf_name in ("Eastern", "Western"):
        conf_teams = [t for t in team_records.values() if t.get("conf") == conf_name]
        divs = {}
        for t in conf_teams:
            divs.setdefault(t.get("div", ""), []).append(t)
        wc_pool = []
        for div_name, div_teams in divs.items():
            div_sorted = sorted(div_teams, key=lambda x: -x["pts"])
            for t in div_sorted[:3]:
                playoff_teams.add(t["abbrev"])
            wc_pool.extend(div_sorted[3:])
        wc_sorted = sorted(wc_pool, key=lambda x: -x["pts"])
        for t in wc_sorted[:2]:
            playoff_teams.add(t["abbrev"])

    cards = []
    for g in remaining:
        prefix = "@ " if g["loc"] == "away" else "vs "
        loc_text = "Away" if g["loc"] == "away" else "Home"

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
                notes.append(f"{TEAM} leads season series {series_str}")
            elif sl > sw:
                notes.append(f"{TEAM} trails season series {series_str}")
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
            notes.append(f"{TEAM} holds a {gap}-pt lead over {opp}")
        else:
            notes.append(f"{opp} holds a {abs(gap)}-pt lead over {TEAM}")

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

        # Tags based on playoff picture + hot streak
        tags = ""
        opp_streak = o.get("streak", "")
        opp_po = mp_odds.get(opp, {}).get("ALL", {}).get("playoffPct", 0)
        if opp_po >= 0.60:
            tags += '<span class="game-tag tag-playoff">Playoff Team</span>'
        elif opp_po >= 0.15:
            tags += '<span class="game-tag tag-desperate">Desperate</span>'
        else:
            tags += '<span class="game-tag tag-sellers">Sellers</span>'
        # Hot = win streak of 3+
        if opp_streak.startswith("W") and len(opp_streak) > 1:
            try:
                streak_n = int(opp_streak[1:])
                if streak_n >= 3:
                    tags += f'<span class="game-tag tag-hot">W{streak_n}</span>'
            except ValueError:
                pass
        cards.append(f'''<details class="game-detail">
<summary class="game-summary"><div class="game-left"><span class="game-date">{g["date"]}</span><span class="game-opp">{prefix}{g["opp"]}</span>{tags}</div><div class="game-right"><span class="game-meta">{opp_record} &middot; {o_pts}p</span><span class="game-loc loc-{g["loc"]}">{loc_text}</span></div></summary>
<div class="game-expand">
  <ul class="matchup-notes">{notes_html}</ul>
  <table class="cmp-tbl"><thead><tr><th>{TEAM}</th><th></th><th>{opp}</th></tr></thead><tbody>{rows}</tbody></table>
</div></details>''')

    return f'''<div class="sched-meta">
  <div class="sm-card"><div class="sm-val">{len(remaining)}</div><div class="sm-label">Games Left</div></div>
  <div class="sm-card"><div class="sm-val">{home_count}</div><div class="sm-label">Home</div></div>
  <div class="sm-card"><div class="sm-val">{away_count}</div><div class="sm-label">Away</div></div>
  <div class="sm-card"><div class="sm-val">{above500_count}</div><div class="sm-label">vs .500+</div></div>
</div>
<div class="sched-list">{"".join(cards)}</div>'''

def generate_html(sens, roster_html, standings_html, projections_html, schedule_html, news_html, vs500, mp_odds, deltas, mp_stats, all_teams):
    team_info = TEAM_INFO.get(TEAM, TEAM_INFO["OTT"])
    team_name = team_info["name"]
    accent = team_info["accent"]
    accent_soft_dark = accent_rgba(accent, 0.12)
    accent_light = darken_hex(accent, 0.85)
    accent_soft_light = accent_rgba(accent, 0.08)
    subreddit = team_info["subreddit"]

    # Build team switcher dropdown (all 4 divisions)
    div_groups = [("Atlantic", []), ("Metropolitan", []), ("Central", []), ("Pacific", [])]
    for t in all_teams:
        for dname, dlist in div_groups:
            if t["div"] == dname:
                dlist.append(t)
                break
    switcher_opts = ''
    for dname, dlist in div_groups:
        dlist.sort(key=lambda x: x["name"])
        switcher_opts += f'<optgroup label="{dname}">'
        for t in dlist:
            a = t["abbrev"]
            fn = "index.html" if a == DEFAULT_TEAM else f"{a}.html"
            sel = " selected" if a == TEAM else ""
            switcher_opts += f'<option value="{fn}"{sel}>{t["name"]}</option>'
        switcher_opts += '</optgroup>'

    eastern = timezone(timedelta(hours=-5))
    now = datetime.now(eastern).strftime("%B %-d, %Y at %-I:%M %p ET")
    record = f"{sens['w']}-{sens['l']}-{sens['otl']}"
    remaining = 82 - sens["gp"]
    pace = round(sens["ptsPct"] * 2 * 82, 1)
    l10 = f"{sens['l10w']}-{sens['l10l']}-{sens['l10otl']}"
    w500, l500, otl500 = vs500
    ott_odds = mp_odds.get(TEAM, {}).get("ALL", {})
    playoff_pct = ott_odds.get("playoffPct", 0)
    proj_pts = ott_odds.get("projPts", pace)
    target = 93
    needed = max(0, target - sens["pts"])
    gap = round(proj_pts - target, 1)

    # Compute unique header stats
    gp = sens["gp"] or 1
    goal_diff = sens["gf"] - sens["ga"]
    goal_diff_str = f"+{goal_diff}" if goal_diff >= 0 else str(goal_diff)
    ott_mp = mp_stats.get(TEAM, {})
    def ordinal(n):
        if 11 <= n % 100 <= 13: return f"{n}th"
        return f"{n}" + {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")

    # PP% and PK% with league rankings (from MoneyPuck, all 32 teams)
    def calc_pp_pct(team_mp):
        d = team_mp.get("pp", {})
        shots = d.get("shots", 0)
        return round(d.get("gf", 0) / max(shots, 1) * 100, 1) if shots else 0
    def calc_pk_pct(team_mp):
        d = team_mp.get("pk", {})
        sa = d.get("sa", 0)
        return round((1 - d.get("ga", 0) / max(sa, 1)) * 100, 1) if sa else 0

    all_pp = sorted([(t, calc_pp_pct(mp_stats.get(t, {}))) for t in mp_stats], key=lambda x: -x[1])
    all_pk = sorted([(t, calc_pk_pct(mp_stats.get(t, {}))) for t in mp_stats], key=lambda x: -x[1])
    pp_pct = calc_pp_pct(ott_mp)
    pk_pct = calc_pk_pct(ott_mp)
    pp_rank = next((i+1 for i, (t, _) in enumerate(all_pp) if t == TEAM), 0)
    pk_rank = next((i+1 for i, (t, _) in enumerate(all_pk) if t == TEAM), 0)

    # Points pace (projected 82-game total from pts%)
    pts_pace = round(sens["ptsPct"] * 2 * 82)

    # 1-goal games record (clutch factor) — count from results
    # Not available directly; use goal diff per game as proxy
    gf_pg = round(sens["gf"] / gp, 1)
    ga_pg = round(sens["ga"] / gp, 1)

    # vs .500 record
    vs500_str = f"{w500}-{l500}-{otl500}"
    gap_str = f"+{gap}" if gap >= 0 else str(gap)

    # Delta indicators
    d_pct = fmt_delta(playoff_pct, deltas.get("playoffPct"), fmt="pct")
    d_needed = fmt_delta(needed, deltas.get("needed"), invert=True)
    d_gap = fmt_delta(gap, deltas.get("gap"))
    d_pts = fmt_delta(sens["pts"], deltas.get("pts"))

    return f'''<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>{team_name} — 2025-26</title>
<script>document.documentElement.setAttribute('data-theme',localStorage.getItem('theme')||'dark')</script>
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin><link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>
:root,:root[data-theme="dark"]{{--bg:#101012;--bg-surface:rgba(255,255,255,0.03);--bg-elevated:rgba(255,255,255,0.05);--bg-hover:rgba(255,255,255,0.07);--border:rgba(255,255,255,0.06);--border-subtle:rgba(255,255,255,0.04);--text:#e8e8ec;--text-secondary:#9898a0;--text-muted:#56565e;--accent:{accent};--accent-soft:{accent_soft_dark};--green:#34d399;--red:#fb7185;--card-shadow:0 1px 2px rgba(0,0,0,0.4),0 0 0 1px rgba(255,255,255,0.04);--card-shadow-hover:0 4px 12px rgba(0,0,0,0.5),0 0 0 1px rgba(255,255,255,0.08);--text-strong:#fff;--ring-bg:rgba(255,255,255,0.06);--alt-row:rgba(255,255,255,0.015);--matchup-bg:rgba(255,255,255,0.02);--tag-bg:rgba(255,255,255,0.04);--tag-dash:rgba(255,255,255,0.08);--amber:#fbbf24;--amber-bg:rgba(251,191,36,0.08);--loc-home-bg:rgba(52,211,153,0.1);--loc-away-bg:rgba(255,255,255,0.03);--tab-active-shadow:0 1px 3px rgba(0,0,0,0.3),inset 0 1px 0 rgba(255,255,255,0.06);--tab-hover-bg:rgba(255,255,255,0.03);--hs-bg:rgba(255,255,255,0.06);--footer-link-deco:rgba(255,255,255,0.1)}}
:root[data-theme="light"]{{--bg:#f8f8fa;--bg-surface:rgba(0,0,0,0.025);--bg-elevated:rgba(0,0,0,0.04);--bg-hover:rgba(0,0,0,0.05);--border:rgba(0,0,0,0.08);--border-subtle:rgba(0,0,0,0.05);--text:#1a1a1e;--text-secondary:#6b6b73;--text-muted:#a0a0a8;--accent:{accent_light};--accent-soft:{accent_soft_light};--green:#059669;--red:#e11d48;--card-shadow:0 1px 3px rgba(0,0,0,0.06),0 0 0 1px rgba(0,0,0,0.04);--card-shadow-hover:0 4px 12px rgba(0,0,0,0.1),0 0 0 1px rgba(0,0,0,0.06);--text-strong:#000;--ring-bg:rgba(0,0,0,0.06);--alt-row:rgba(0,0,0,0.02);--matchup-bg:rgba(0,0,0,0.025);--tag-bg:rgba(0,0,0,0.04);--tag-dash:rgba(0,0,0,0.12);--amber:#92400e;--amber-bg:rgba(251,191,36,0.12);--loc-home-bg:rgba(5,150,105,0.08);--loc-away-bg:rgba(0,0,0,0.03);--tab-active-shadow:0 1px 3px rgba(0,0,0,0.06),inset 0 1px 0 rgba(255,255,255,0.8);--tab-hover-bg:rgba(0,0,0,0.03);--hs-bg:rgba(0,0,0,0.06);--footer-link-deco:rgba(0,0,0,0.12)}}
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:'Inter',system-ui,-apple-system,sans-serif;background:var(--bg);color:var(--text);line-height:1.55;-webkit-font-smoothing:antialiased;font-feature-settings:'cv02','cv03','cv04','cv11'}}
a{{color:var(--text);text-decoration:none}}
a:hover{{color:var(--text-strong)}}

/* Header */
.header{{max-width:880px;margin:0 auto;padding:40px 28px 0}}
.hdr-top{{display:flex;justify-content:space-between;align-items:center;margin-bottom:28px}}
.hdr-left{{display:flex;align-items:center;gap:16px}}
.team-logo{{width:44px;height:44px;opacity:0.95}}
.header h1{{font-size:20px;font-weight:600;letter-spacing:-0.4px;margin-bottom:0;color:var(--text-strong)}}
.header .subtitle{{font-size:13px;color:var(--text-secondary);font-variant-numeric:tabular-nums}}
.hdr-pct{{text-align:right}}
.pct-val{{font-size:32px;font-weight:700;letter-spacing:-1.5px;line-height:1;color:var(--text)}}
.pct-label{{display:block;font-size:10px;color:var(--text-muted);text-transform:uppercase;letter-spacing:1px;margin-top:8px;font-weight:500}}
.delta{{display:inline-block;font-size:11px;font-weight:600;margin-left:4px;vertical-align:middle}}
@media(max-width:500px){{.team-logo{{width:36px;height:36px}}.header h1{{font-size:17px}}.pct-val{{font-size:26px}}}}

.stat-row{{display:flex;gap:6px;flex-wrap:wrap;padding-bottom:28px;margin-bottom:0}}
.stat-pill{{display:inline-flex;align-items:center;gap:5px;padding:6px 12px;background:var(--bg-surface);border-radius:8px;font-size:12px;white-space:nowrap;transition:background 0.2s ease}}
.stat-pill:hover{{background:var(--bg-elevated)}}
.stat-pill .sl{{color:var(--text-muted);font-size:9px;text-transform:uppercase;letter-spacing:0.6px;font-weight:500}}
.stat-pill .sv{{font-weight:600;color:var(--text)}}
.pill-accent{{background:var(--accent-soft)}}.pill-accent .sv{{color:var(--accent);font-weight:700}}

/* Tabs */
.container{{max-width:880px;margin:0 auto;padding:0 28px 60px}}
input[name="tab"]{{display:none}}
.tab-bar{{display:flex;gap:2px;margin-bottom:36px;padding:3px;background:var(--bg-surface);border-radius:10px;width:fit-content}}
.tab-bar label{{padding:7px 16px;font-size:12px;font-weight:500;color:var(--text-muted);cursor:pointer;border-radius:7px;transition:all 0.2s ease;white-space:nowrap}}
.tab-bar label:hover{{color:var(--text-secondary);background:var(--tab-hover-bg)}}
.panel{{display:none}}
#tab-roster:checked~.tab-bar label[for="tab-roster"],
#tab-standings:checked~.tab-bar label[for="tab-standings"],
#tab-playoffs:checked~.tab-bar label[for="tab-playoffs"],
#tab-schedule:checked~.tab-bar label[for="tab-schedule"],
#tab-news:checked~.tab-bar label[for="tab-news"],
#tab-community:checked~.tab-bar label[for="tab-community"]{{color:var(--text-strong);font-weight:600;background:var(--bg-elevated);box-shadow:var(--tab-active-shadow)}}
#tab-roster:checked~#p-roster,
#tab-standings:checked~#p-standings,
#tab-playoffs:checked~#p-playoffs,
#tab-schedule:checked~#p-schedule,
#tab-news:checked~#p-news,
#tab-community:checked~#p-community{{display:block}}

/* Typography */
h3{{font-size:14px;font-weight:600;margin-bottom:18px;letter-spacing:-0.1px;color:var(--text-secondary)}}
.sub-note{{font-size:12px;color:var(--text-muted);margin-bottom:20px}}

/* Tables */
.nhl-tbl{{width:100%;border-collapse:collapse;font-size:12px;font-variant-numeric:tabular-nums}}
.nhl-tbl thead th{{background:var(--bg);color:var(--text-muted);padding:10px 8px;font-weight:500;font-size:10px;text-transform:uppercase;letter-spacing:0.5px;text-align:left;white-space:nowrap;position:sticky;top:0;border-bottom:1px solid var(--border)}}
.nhl-tbl thead th.r{{text-align:right}}
.nhl-tbl thead th.rank{{width:30px;text-align:center}}
.nhl-tbl thead th.name-col{{min-width:160px}}
/* Frozen rank + player columns on horizontal scroll */
#skater-tbl,#goalie-tbl{{border-collapse:separate;border-spacing:0}}
#skater-tbl th.rank,#skater-tbl td.rank,#goalie-tbl th.rank,#goalie-tbl td.rank{{position:sticky;left:0;z-index:2;background:var(--bg) !important}}
#skater-tbl th.name-col,#skater-tbl td.name-cell,#goalie-tbl th.name-col,#goalie-tbl td.name-cell{{position:sticky;left:30px;z-index:2;background:var(--bg) !important;box-shadow:2px 0 4px rgba(0,0,0,0.15)}}
#skater-tbl thead th.rank,#skater-tbl thead th.name-col,#goalie-tbl thead th.rank,#goalie-tbl thead th.name-col{{z-index:3}}
.nhl-tbl td{{padding:8px 8px;border:none;border-bottom:1px solid var(--border-subtle);white-space:nowrap;color:var(--text-secondary)}}
.nhl-tbl td.r{{text-align:right}}
.nhl-tbl td.rank{{text-align:center;color:var(--text-muted);font-size:11px}}
.nhl-tbl td.pts-col{{font-weight:700;color:var(--text)}}
.nhl-tbl .player-summary:hover td{{background:var(--bg-hover)}}
.nhl-tbl .player-summary.alt td{{background:var(--alt-row)}}
.nhl-tbl .player-summary.alt:hover td{{background:var(--bg-hover)}}
.nhl-tbl .goalie-row:hover td{{background:var(--bg-hover)}}
.nhl-tbl .goalie-row.alt td{{background:var(--alt-row)}}
.nhl-tbl .goalie-row.alt:hover td{{background:var(--bg-hover)}}
/* Headshot */
.hs{{width:30px;height:30px;border-radius:50%;object-fit:cover;flex-shrink:0;background:var(--hs-bg)}}
.hs-empty{{display:inline-block}}
.name-cell{{padding-left:4px}}
.name-flex{{display:flex;align-items:center;gap:8px}}
a.pname{{font-weight:600;white-space:nowrap;font-size:12.5px;color:var(--text);text-decoration:none;transition:color 0.15s}}
a.pname:hover{{color:var(--text-strong)}}
/* Advanced stat columns */
.adv{{color:var(--text-muted)}}
.adv-pos{{color:var(--green);font-weight:600}}
.adv-neg{{color:var(--red);font-weight:600}}
.adv-hdr{{background:var(--bg) !important}}
.sens-row td{{background:var(--accent-soft)}}.sens-row td:first-child{{font-weight:700;color:var(--accent)}}
.cutoff td{{border-bottom:2px dashed var(--text-muted)}}
.rank-in{{font-weight:600;color:var(--text)}}.rank-out{{color:var(--text-muted)}}
.tcol{{font-weight:600;white-space:nowrap}}.tcol-link{{color:var(--text);text-decoration:none;transition:color 0.15s}}.tcol-link:hover{{color:var(--text-strong)}}.bpts{{font-weight:700;color:var(--text)}}
.div-label{{margin:36px 0 14px;font-size:11px;font-weight:500;text-transform:uppercase;letter-spacing:1.2px;color:var(--text-muted)}}
.div-label:first-child{{margin-top:0}}
.stnd-tbl td{{padding:7px 6px;font-size:11px}}.stnd-tbl thead th{{padding:8px 6px;font-size:9px}}
.stnd-tbl .sens-row td{{background:var(--accent-soft)}}
.scroll-x{{overflow-x:auto;-webkit-overflow-scrolling:touch}}

/* KPI Row */
.kpi-row{{display:flex;gap:10px;flex-wrap:wrap;margin-bottom:32px}}
.kpi{{flex:1;min-width:90px;padding:20px 16px;background:var(--bg-surface);border-radius:12px;text-align:center;box-shadow:var(--card-shadow);transition:box-shadow 0.25s ease}}
.kpi:hover{{box-shadow:var(--card-shadow-hover)}}
.kpi-val{{font-size:28px;font-weight:700;letter-spacing:-1.5px;line-height:1;color:var(--text-strong)}}
.kpi-label{{font-size:10px;color:var(--text-muted);margin-top:8px;text-transform:uppercase;letter-spacing:0.8px;font-weight:500}}

/* Scenario impact */
.sc-label{{font-weight:600;white-space:nowrap;color:var(--text)}}
.sc-up{{color:var(--green);font-weight:600}}
.sc-down{{color:var(--red);font-weight:600}}
.footnote{{margin-top:36px;font-size:11px;color:var(--text-muted)}}

/* Schedule */
.sched-meta{{display:flex;gap:10px;flex-wrap:wrap;margin-bottom:28px}}
.sm-card{{flex:1;min-width:70px;text-align:center;padding:18px 10px;background:var(--bg-surface);border-radius:12px;box-shadow:var(--card-shadow)}}
.sm-val{{font-size:24px;font-weight:700;line-height:1;color:var(--text-strong);letter-spacing:-0.5px}}
.sm-label{{font-size:10px;color:var(--text-muted);text-transform:uppercase;letter-spacing:0.8px;margin-top:8px;font-weight:500}}
.sched-list{{display:flex;flex-direction:column;gap:4px}}
.game-detail{{border-radius:12px;overflow:hidden}}
.game-tag{{font-size:9px;font-weight:600;padding:3px 8px;border-radius:20px;margin-left:6px;letter-spacing:0.3px;vertical-align:middle}}
.tag-playoff{{color:var(--text-muted);background:var(--tag-bg)}}
.tag-desperate{{color:var(--amber);background:var(--amber-bg)}}
.tag-sellers{{color:var(--text-muted);background:transparent;border:1px dashed var(--tag-dash)}}
.tag-hot{{color:var(--text-strong);background:var(--accent);box-shadow:0 0 8px rgba(232,56,79,0.3)}}
.game-summary{{display:flex;justify-content:space-between;align-items:center;padding:12px 16px;cursor:pointer;list-style:none;background:var(--bg-surface);border-radius:12px;box-shadow:var(--card-shadow);transition:all 0.2s ease}}
.game-summary:hover{{background:var(--bg-elevated);box-shadow:var(--card-shadow-hover)}}
.game-summary::-webkit-details-marker{{display:none}}
.game-summary::marker{{display:none;content:""}}
.game-detail[open] .game-summary{{border-bottom-left-radius:0;border-bottom-right-radius:0}}
.game-left{{display:flex;align-items:center;gap:12px}}
.game-date{{font-size:11px;color:var(--text-muted);min-width:44px;font-weight:500;font-variant-numeric:tabular-nums}}
.game-opp{{font-size:13px;font-weight:600;color:var(--text)}}
.game-right{{display:flex;align-items:center;gap:10px}}
.game-meta{{font-size:11px;color:var(--text-muted)}}
.game-loc{{font-size:9px;font-weight:600;padding:3px 8px;border-radius:20px;letter-spacing:0.3px}}
.loc-home{{background:var(--loc-home-bg);color:var(--green)}}
.loc-away{{background:var(--loc-away-bg);color:var(--text-muted)}}
.game-expand{{background:var(--matchup-bg);border:1px solid var(--border);border-top:0;border-bottom-left-radius:12px;border-bottom-right-radius:12px;padding:20px}}
.cmp-tbl{{width:100%;border-collapse:collapse;font-size:12px}}
.cmp-tbl thead th{{font-size:10px;font-weight:500;padding:8px 8px;border-bottom:1px solid var(--border);text-align:center;color:var(--text-muted);text-transform:uppercase;letter-spacing:0.5px}}
.cmp-tbl thead th:first-child{{text-align:left}}
.cmp-tbl thead th:last-child{{text-align:right}}
.cmp-tbl td{{padding:6px 8px;border-bottom:1px solid var(--border-subtle);color:var(--text-secondary)}}
.cmp-stat-l{{font-weight:600;text-align:left;color:var(--text)}}
.cmp-stat-label{{text-align:center;font-size:10px;color:var(--text-muted);text-transform:uppercase;letter-spacing:0.5px;font-weight:500}}
.cmp-stat-r{{font-weight:600;text-align:right;color:var(--text)}}
.matchup-notes{{margin:0 0 16px;padding:0;list-style:none;font-size:11px;color:var(--text-secondary);line-height:1.5}}
.matchup-notes li{{padding:6px 12px;background:var(--matchup-bg);border-radius:8px;margin-bottom:4px;font-weight:500}}

/* News / Trade Rumors */
.news-list{{display:flex;flex-direction:column;gap:1px}}
.news-item{{display:block;padding:14px 16px;border-radius:10px;text-decoration:none;transition:background 0.2s ease}}
.news-item:hover{{background:var(--bg-hover);text-decoration:none}}
.news-meta{{display:flex;justify-content:space-between;align-items:center;margin-bottom:5px}}
.news-source{{font-size:9px;font-weight:600;text-transform:uppercase;letter-spacing:0.8px;color:var(--text-muted)}}
.news-date{{font-size:10px;color:var(--text-muted)}}
.news-title{{font-size:13px;font-weight:500;color:var(--text);line-height:1.45}}

/* Community */
.community-list{{display:grid;grid-template-columns:1fr 1fr;gap:10px}}
@media(max-width:560px){{.community-list{{grid-template-columns:1fr}}}}
.community-card{{display:block;padding:20px;background:var(--bg-surface);border-radius:12px;text-decoration:none;box-shadow:var(--card-shadow);transition:all 0.2s ease}}
.community-card:hover{{background:var(--bg-elevated);box-shadow:var(--card-shadow-hover);text-decoration:none}}
.cc-name{{font-size:13px;font-weight:600;color:var(--text);margin-bottom:6px}}
.cc-desc{{font-size:11px;color:var(--text-muted);line-height:1.5}}

/* Sortable columns */
.sort-th{{cursor:pointer;user-select:none;position:relative;transition:color 0.15s}}
.sort-th:hover{{color:var(--text-secondary)}}
.sort-th::after{{content:"";display:inline-block;margin-left:3px;opacity:0.3;font-size:8px;vertical-align:middle}}
.sort-th.asc::after{{content:"\\25B2";opacity:0.8}}
.sort-th.desc::after{{content:"\\25BC";opacity:0.8}}

/* Progress ring */
.odds-ring{{position:relative;width:72px;height:72px;flex-shrink:0}}
.odds-ring svg{{transform:rotate(-90deg);width:72px;height:72px}}
.odds-ring .ring-bg{{fill:none;stroke:var(--ring-bg);stroke-width:5}}
.odds-ring .ring-fg{{fill:none;stroke:var(--accent);stroke-width:5;stroke-linecap:round;transition:stroke-dashoffset 0.5s ease}}
.odds-ring .ring-text{{position:absolute;inset:0;display:flex;flex-direction:column;align-items:center;justify-content:center}}
.odds-ring .ring-val{{font-size:16px;font-weight:700;color:var(--text);letter-spacing:-0.5px;line-height:1}}
.odds-ring .ring-label{{font-size:8px;color:var(--text-muted);text-transform:uppercase;letter-spacing:0.8px;margin-top:3px;font-weight:500}}

/* Standings card wrap */
.stnd-card{{background:var(--bg-surface);border-radius:12px;box-shadow:var(--card-shadow);padding:4px 0;margin-bottom:8px;overflow:hidden}}
.stnd-card .scroll-x{{padding:0}}
.stnd-card .nhl-tbl thead th{{background:transparent}}

/* Community icons */
.cc-icon{{width:20px;height:20px;border-radius:4px;flex-shrink:0;opacity:0.85}}
.cc-head{{display:flex;align-items:center;gap:8px;margin-bottom:6px}}

/* Mobile tabs */
@media(max-width:680px){{.tab-bar{{overflow-x:auto;-webkit-overflow-scrolling:touch;scrollbar-width:none;width:auto}}.tab-bar::-webkit-scrollbar{{display:none}}}}

/* Standings sub-toggle */
.stnd-toggle input[type="radio"]{{display:none}}
.stnd-toggle-bar{{display:flex;gap:2px;margin-bottom:24px;padding:3px;background:var(--bg-surface);border-radius:10px;width:fit-content}}
.stnd-toggle-bar label{{padding:6px 14px;font-size:11px;font-weight:500;color:var(--text-muted);cursor:pointer;border-radius:7px;transition:all 0.2s ease;white-space:nowrap}}
.stnd-toggle-bar label:hover{{color:var(--text-secondary);background:var(--tab-hover-bg)}}
.sv-conf,.sv-wc{{display:none}}
#sv-conf:checked~.sv-conf{{display:block}}
#sv-wc:checked~.sv-wc{{display:block}}
#sv-conf:checked~.stnd-toggle-bar label[for="sv-conf"],#sv-wc:checked~.stnd-toggle-bar label[for="sv-wc"]{{color:var(--text-strong);font-weight:600;background:var(--bg-elevated);box-shadow:var(--tab-active-shadow)}}

/* Empty state */
.empty-state{{text-align:center;padding:48px 20px;color:var(--text-muted);font-size:13px}}
.empty-state span{{display:block;font-size:28px;margin-bottom:12px;opacity:0.4}}

/* Footer */
.footer{{text-align:center;padding:36px 28px;font-size:11px;color:var(--text-muted);max-width:880px;margin:0 auto}}
.footer a{{color:var(--text-muted);text-decoration:underline;text-decoration-color:var(--footer-link-deco);text-underline-offset:2px}}.footer a:hover{{color:var(--text-secondary)}}
.footer-ts{{display:block;margin-top:6px;font-size:10px;color:var(--text-muted);opacity:0.7}}

/* Team selector */
.team-select{{appearance:none;-webkit-appearance:none;background:var(--bg-surface);color:var(--text);border:1px solid var(--border);border-radius:8px;padding:6px 28px 6px 10px;font-size:12px;font-family:inherit;font-weight:500;cursor:pointer;transition:all 0.2s ease;background-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='10' height='6'%3E%3Cpath d='M0 0l5 6 5-6z' fill='%239898a0'/%3E%3C/svg%3E");background-repeat:no-repeat;background-position:right 8px center}}
.team-select:hover{{background-color:var(--bg-elevated);border-color:var(--border)}}
.team-select:focus{{outline:none;box-shadow:0 0 0 2px var(--accent)}}
.team-select optgroup{{font-weight:600;color:var(--text-muted)}}
.team-select option{{background:var(--bg);color:var(--text)}}
.scores-link{{font-size:12px;font-weight:500;color:var(--text-muted);padding:6px 12px;background:var(--bg-surface);border-radius:8px;transition:all 0.2s ease;white-space:nowrap;text-decoration:none}}.scores-link:hover{{color:var(--text);background:var(--bg-elevated)}}
.hdr-controls{{display:flex;align-items:center;gap:8px}}

/* Theme toggle */
.theme-toggle{{display:flex;gap:2px;padding:2px;background:var(--bg-surface);border-radius:8px}}
.theme-btn{{display:flex;align-items:center;justify-content:center;width:28px;height:26px;border:none;background:transparent;color:var(--text-muted);cursor:pointer;border-radius:6px;transition:all 0.2s ease;padding:0}}.theme-btn:hover{{color:var(--text-secondary);background:var(--bg-hover)}}
.theme-btn.active{{color:var(--text-strong);background:var(--bg-elevated);box-shadow:var(--tab-active-shadow)}}
</style></head><body>

<div class="header">
  <div class="hdr-top">
    <div class="hdr-left">
      <img src="https://assets.nhle.com/logos/nhl/svg/{TEAM}_dark.svg" alt="{team_name}" class="team-logo">
      <div>
        <h1>{team_name}</h1>
        <div class="subtitle">Updated {now}</div>
      </div>
    </div>
    <div class="hdr-controls">
      <a href="scores.html" class="scores-link">Scores</a>
      <select class="team-select" onchange="if(this.value)window.location.href=this.value">{switcher_opts}</select>
      <div class="theme-toggle">
        <button class="theme-btn" data-theme="light" title="Light" aria-label="Light theme"><svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5"><circle cx="8" cy="8" r="3"/><path d="M8 1.5v2M8 12.5v2M1.5 8h2M12.5 8h2M3.4 3.4l1.4 1.4M11.2 11.2l1.4 1.4M3.4 12.6l1.4-1.4M11.2 4.8l1.4-1.4" stroke-linecap="round"/></svg></button>
        <button class="theme-btn" data-theme="dark" title="Dark" aria-label="Dark theme"><svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M13 8.5A5.5 5.5 0 017 3a6 6 0 00.2-1.5A6 6 0 1013.5 9a5 5 0 01-.5-.5z" stroke-linecap="round" stroke-linejoin="round"/></svg></button>
      </div>
    </div>
  </div>
  <div class="stat-row">
    <span class="stat-pill pill-accent" title="MoneyPuck playoff probability"><span class="sl">Playoff Odds</span> <span class="sv">{playoff_pct*100:.0f}%</span></span>
    <span class="stat-pill"><span class="sl">Record</span> <span class="sv">{record}</span></span>
    <span class="stat-pill" title="Record vs teams above .500"><span class="sl">vs .500+</span> <span class="sv">{vs500_str}</span></span>
    <span class="stat-pill" title="Goals scored minus goals allowed"><span class="sl">Goal Diff</span> <span class="sv">{goal_diff_str}</span></span>
    <span class="stat-pill" title="Power play goals / power play shots — league rank out of 32"><span class="sl">PP%</span> <span class="sv">{pp_pct}% <small>({ordinal(pp_rank)})</small></span></span>
    <span class="stat-pill" title="Penalty kill save % — league rank out of 32"><span class="sl">PK%</span> <span class="sv">{pk_pct}% <small>({ordinal(pk_rank)})</small></span></span>
    <span class="stat-pill"><span class="sl">L10</span> <span class="sv">{l10}</span></span>
  </div>
</div>

<div class="container">
  <input type="radio" name="tab" id="tab-standings" checked>
  <input type="radio" name="tab" id="tab-schedule">
  <input type="radio" name="tab" id="tab-playoffs">
  <input type="radio" name="tab" id="tab-roster">
  <input type="radio" name="tab" id="tab-news">
  <input type="radio" name="tab" id="tab-community">
  <div class="tab-bar">
    <label for="tab-standings">Standings</label>
    <label for="tab-schedule">Remaining Games</label>
    <label for="tab-playoffs">Playoff Odds</label>
    <label for="tab-roster">Player Stats</label>
    <label for="tab-news">Trade Rumors</label>
    <label for="tab-community">Community</label>
  </div>
  <div class="panel" id="p-standings">{standings_html}</div>
  <div class="panel" id="p-schedule">{schedule_html}</div>
  <div class="panel" id="p-playoffs">{projections_html}</div>
  <div class="panel" id="p-roster">{roster_html}</div>
  <div class="panel" id="p-news">{news_html}</div>
  <div class="panel" id="p-community">
    <div class="community-list">
      <a href="https://www.reddit.com/r/{subreddit}/" target="_blank" rel="noopener" class="community-card"><div class="cc-head"><img src="https://www.google.com/s2/favicons?domain=reddit.com&sz=64" alt="" class="cc-icon"><div class="cc-name">r/{subreddit}</div></div><div class="cc-desc">Reddit community. Memes, highlights, post-game threads, and fan takes.</div></a>
      <a href="https://x.com/search?q=%22{team_name.replace(" ", "%20")}%22&src=typed_query&f=live" target="_blank" rel="noopener" class="community-card"><div class="cc-head"><img src="https://www.google.com/s2/favicons?domain=x.com&sz=64" alt="" class="cc-icon"><div class="cc-name">X / Twitter</div></div><div class="cc-desc">Live feed of {team_name} mentions. Breaking news, insider tweets, fan reactions.</div></a>
      <a href="https://forums.hfboards.com/" target="_blank" rel="noopener" class="community-card"><div class="cc-head"><img src="https://www.google.com/s2/favicons?domain=hfboards.com&sz=64" alt="" class="cc-icon"><div class="cc-name">HFBoards</div></div><div class="cc-desc">The longest-running hockey forum. Trade talk, game threads, prospect discussions.</div></a>
      <a href="https://www.nhl.com/stats/skaters?reportName=summary&amp;reportType=season&amp;sort=points,a_gamesPlayed&amp;seasonFrom=20252026&amp;seasonTo=20252026&amp;gameType=2" target="_blank" rel="noopener" class="community-card"><div class="cc-head"><img src="https://www.google.com/s2/favicons?domain=nhl.com&sz=64" alt="" class="cc-icon"><div class="cc-name">NHL League Stats</div></div><div class="cc-desc">Full league skater stats. Points leaders, goals, assists — sortable by every column.</div></a>
    </div>
  </div>
</div>
<div class="footer">Data from NHL API &amp; <a href="https://moneypuck.com">MoneyPuck</a><span class="footer-ts">Updated {now}</span></div>
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
<script>
(function(){{
  var root=document.documentElement;
  var btns=document.querySelectorAll('.theme-btn');
  var saved=localStorage.getItem('theme')||'dark';
  btns.forEach(function(b){{
    if(b.dataset.theme===saved) b.classList.add('active');
    b.addEventListener('click',function(){{
      var t=b.dataset.theme;
      root.setAttribute('data-theme',t);
      localStorage.setItem('theme',t);
      btns.forEach(function(x){{x.classList.remove('active')}});
      b.classList.add('active');
    }});
  }});
}})();
</script>
</body></html>'''

# ── Scoreboard ────────────────────────────────────────────

def build_scoreboard_html(scores_data, all_game_details, switcher_opts):
    """Generate a standalone scoreboard page showing today's NHL scores with expandable details."""
    eastern = timezone(timedelta(hours=-5))
    now = datetime.now(eastern).strftime("%B %-d, %Y at %-I:%M %p ET")

    games = scores_data.get("games", [])
    current_date = scores_data.get("currentDate", "")

    # Format display date
    display_date = current_date
    try:
        d = datetime.strptime(current_date, "%Y-%m-%d")
        display_date = d.strftime("%A, %B %-d, %Y")
    except Exception:
        pass

    game_cards = []
    for g in games:
        state = g.get("gameState", "")
        game_id = g.get("id", 0)
        away = g.get("awayTeam", {})
        home = g.get("homeTeam", {})
        away_abbrev = away.get("abbrev", "")
        home_abbrev = home.get("abbrev", "")
        away_score = away.get("score", 0)
        home_score = home.get("score", 0)
        away_name = away.get("placeName", {})
        home_name = home.get("placeName", {})
        if isinstance(away_name, dict):
            away_name = away_name.get("default", away_abbrev)
        if isinstance(home_name, dict):
            home_name = home_name.get("default", home_abbrev)
        away_full = TEAM_INFO.get(away_abbrev, {}).get("name", away_name)
        home_full = TEAM_INFO.get(home_abbrev, {}).get("name", home_name)

        # Game status
        period_desc = g.get("periodDescriptor", {})
        period_type = period_desc.get("periodType", "REG")
        period_num = period_desc.get("number", 0)
        clock = g.get("clock", {})
        time_remaining = clock.get("timeRemaining", "")

        if state in ("FINAL", "OFF"):
            if period_type == "OT":
                status = "Final/OT"
            elif period_type == "SO":
                status = "Final/SO"
            else:
                status = "Final"
            status_cls = "sb-final"
        elif state == "LIVE" or state == "CRIT":
            if period_type == "OT":
                status = f"OT {time_remaining}"
            elif period_type == "SO":
                status = "Shootout"
            else:
                ordinals = {1: "1st", 2: "2nd", 3: "3rd"}
                status = f"{ordinals.get(period_num, f'P{period_num}')} {time_remaining}"
            status_cls = "sb-live"
        elif state == "FUT" or state == "PRE":
            start = g.get("startTimeUTC", "")
            status = "Upcoming"
            if start:
                try:
                    utc_dt = datetime.strptime(start, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
                    et_dt = utc_dt.astimezone(eastern)
                    status = et_dt.strftime("%-I:%M %p ET")
                except Exception:
                    pass
            status_cls = "sb-upcoming"
        else:
            status = state
            status_cls = ""

        # Winner highlighting
        away_win = "sb-winner" if state in ("FINAL", "OFF") and away_score > home_score else ""
        home_win = "sb-winner" if state in ("FINAL", "OFF") and home_score > away_score else ""

        # Goal scorers (compact, for the card)
        goals = g.get("goals", [])
        away_scorers = {}
        home_scorers = {}
        for gl in goals:
            scorer = gl.get("name", {})
            if isinstance(scorer, dict):
                scorer = scorer.get("default", "")
            team_abbr = gl.get("teamAbbrev", {})
            if isinstance(team_abbr, dict):
                team_abbr = team_abbr.get("default", "")
            if team_abbr == away_abbrev:
                away_scorers[scorer] = away_scorers.get(scorer, 0) + 1
            elif team_abbr == home_abbrev:
                home_scorers[scorer] = home_scorers.get(scorer, 0) + 1

        away_goals_html = ""
        home_goals_html = ""
        for name, count in away_scorers.items():
            c = f" ({count})" if count > 1 else ""
            away_goals_html += f'<span class="sb-scorer">{name}{c}</span>'
        for name, count in home_scorers.items():
            c = f" ({count})" if count > 1 else ""
            home_goals_html += f'<span class="sb-scorer">{name}{c}</span>'

        # Team page links
        away_href = "index.html" if away_abbrev == DEFAULT_TEAM else f"{away_abbrev}.html"
        home_href = "index.html" if home_abbrev == DEFAULT_TEAM else f"{home_abbrev}.html"

        # ── Expandable detail section ──
        detail_html = ""
        details = all_game_details.get(game_id)
        if details and state not in ("FUT", "PRE"):
            # Scoring summary by period
            scoring_periods = details.get("scoring") or []
            scoring_html = ""
            for period in scoring_periods:
                p_num = period.get("periodDescriptor", {}).get("number", 0)
                p_type = period.get("periodDescriptor", {}).get("periodType", "REG")
                if p_type == "OT":
                    p_label = "OT"
                elif p_type == "SO":
                    p_label = "SO"
                else:
                    ordlabels = {1: "1st Period", 2: "2nd Period", 3: "3rd Period"}
                    p_label = ordlabels.get(p_num, f"Period {p_num}")

                goal_rows = ""
                for goal in period.get("goals", []):
                    g_time = goal.get("timeInPeriod", "")
                    g_first = goal.get("firstName", {})
                    g_last = goal.get("lastName", {})
                    if isinstance(g_first, dict):
                        g_first = g_first.get("default", "")
                    if isinstance(g_last, dict):
                        g_last = g_last.get("default", "")
                    g_team = goal.get("teamAbbrev", {})
                    if isinstance(g_team, dict):
                        g_team = g_team.get("default", "")
                    g_strength = goal.get("strength", "ev")
                    strength_badge = ""
                    if g_strength == "pp":
                        strength_badge = '<span class="gd-badge gd-pp">PP</span>'
                    elif g_strength == "sh":
                        strength_badge = '<span class="gd-badge gd-sh">SH</span>'
                    elif g_strength == "en":
                        strength_badge = '<span class="gd-badge gd-en">EN</span>'

                    assists_list = goal.get("assists", [])
                    assist_names = []
                    for a in assists_list:
                        a_first = a.get("firstName", {})
                        a_last = a.get("lastName", {})
                        if isinstance(a_first, dict):
                            a_first = a_first.get("default", "")
                        if isinstance(a_last, dict):
                            a_last = a_last.get("default", "")
                        assist_names.append(f"{a_first} {a_last}")
                    assists_str = ", ".join(assist_names) if assist_names else "Unassisted"

                    headshot = goal.get("headshot", "")
                    headshot_img = f'<img src="{headshot}" class="gd-headshot">' if headshot else ""

                    goal_rows += f'''<div class="gd-goal">
<div class="gd-time">{g_time}</div>
<div class="gd-logo"><img src="https://assets.nhle.com/logos/nhl/svg/{g_team}_dark.svg" class="gd-team-logo"></div>
{headshot_img}
<div class="gd-goal-info"><div class="gd-scorer-name">{g_first} {g_last} {strength_badge}</div><div class="gd-assists">{assists_str}</div></div>
</div>'''

                if goal_rows:
                    scoring_html += f'<div class="gd-period"><div class="gd-period-label">{p_label}</div>{goal_rows}</div>'

            # Box score tables
            boxscore = details.get("boxscore")
            box_html = ""
            if boxscore:
                for side, side_label in [("awayTeam", away_abbrev), ("homeTeam", home_abbrev)]:
                    team_data = boxscore.get(side, {})
                    side_name = away_full if side == "awayTeam" else home_full

                    # Skaters (forwards + defense)
                    skaters = team_data.get("forwards", []) + team_data.get("defense", [])
                    skater_rows = ""
                    for p in sorted(skaters, key=lambda x: -(x.get("goals", 0)*10 + x.get("assists", 0)*5 + x.get("shots", 0))):
                        pname = p.get("name", {})
                        if isinstance(pname, dict):
                            pname = pname.get("default", "")
                        pos = p.get("position", "")
                        g_count = p.get("goals", 0)
                        a_count = p.get("assists", 0)
                        pts = g_count + a_count
                        pm = p.get("plusMinus", 0)
                        pm_str = f"+{pm}" if pm > 0 else str(pm)
                        sog = p.get("shots", 0)
                        hits = p.get("hits", 0)
                        blk = p.get("blockedShots", 0)
                        toi = p.get("toi", "0:00")
                        pts_cls = ' class="gd-pts-hl"' if pts > 0 else ""
                        skater_rows += f"<tr><td>{pname}</td><td>{pos}</td><td{pts_cls}>{g_count}</td><td{pts_cls}>{a_count}</td><td{pts_cls}>{pts}</td><td>{pm_str}</td><td>{sog}</td><td>{hits}</td><td>{blk}</td><td>{toi}</td></tr>"

                    # Goalies
                    goalies = team_data.get("goalies", [])
                    goalie_rows = ""
                    for gk in goalies:
                        gname = gk.get("name", {})
                        if isinstance(gname, dict):
                            gname = gname.get("default", "")
                        sa = gk.get("saveShotsAgainst", "")
                        if isinstance(sa, dict):
                            sa = sa.get("default", "")
                        svs = gk.get("saves", 0)
                        sa_num = gk.get("shotsAgainst", 0)
                        sv_pct = gk.get("savePctg", "")
                        if sv_pct and isinstance(sv_pct, (int, float)):
                            sv_pct = f"{sv_pct:.3f}"
                        elif sv_pct is None:
                            sv_pct = "-"
                        toi = gk.get("toi", "0:00")
                        goalie_rows += f"<tr><td>{gname}</td><td>{sa}</td><td>{sv_pct}</td><td>{toi}</td></tr>"

                    box_html += f'''<div class="gd-box-team">
<div class="gd-box-team-name">{side_name}</div>
<div class="gd-tbl-wrap"><table class="gd-tbl"><thead><tr><th>Skater</th><th>Pos</th><th>G</th><th>A</th><th>P</th><th>+/-</th><th>SOG</th><th>HIT</th><th>BLK</th><th>TOI</th></tr></thead><tbody>{skater_rows}</tbody></table></div>
<div class="gd-tbl-wrap"><table class="gd-tbl gd-goalie-tbl"><thead><tr><th>Goalie</th><th>Saves</th><th>SV%</th><th>TOI</th></tr></thead><tbody>{goalie_rows}</tbody></table></div>
</div>'''

            if scoring_html or box_html:
                detail_html = f'''<div class="gd-data" id="gd-{game_id}" style="display:none">
<div class="gd-panel-header">
<div class="gd-panel-teams">
<img src="https://assets.nhle.com/logos/nhl/svg/{away_abbrev}_dark.svg" class="gd-panel-logo"><span>{away_full}</span>
<span class="gd-panel-vs">vs</span>
<img src="https://assets.nhle.com/logos/nhl/svg/{home_abbrev}_dark.svg" class="gd-panel-logo"><span>{home_full}</span>
</div>
<div class="gd-panel-score">{away_score} — {home_score}<span class="gd-panel-status">{status}</span></div>
</div>
{f'<div class="gd-section"><div class="gd-section-title">Scoring Summary</div>{scoring_html}</div>' if scoring_html else ''}
{f'<div class="gd-section"><div class="gd-section-title">Box Score</div>{box_html}</div>' if box_html else ''}
</div>'''

        has_detail = f' data-game="{game_id}"' if detail_html else ""
        clickable_cls = " sb-clickable" if detail_html else ""

        game_cards.append(f'''<div class="sb-game{clickable_cls}"{has_detail if detail_html else ""}>
<div class="sb-status {status_cls}">{status}</div>
<div class="sb-matchup" onclick="if(this.closest('.sb-clickable'))openPanel(this.closest('.sb-game').dataset.game)">
<div class="sb-team-row {away_win}">
<a href="{away_href}" class="sb-team-link" onclick="event.stopPropagation()"><img src="https://assets.nhle.com/logos/nhl/svg/{away_abbrev}_dark.svg" alt="{away_abbrev}" class="sb-logo"></a>
<div class="sb-team-info"><div class="sb-team-name">{away_full}</div><div class="sb-scorers">{away_goals_html}</div></div>
<div class="sb-score">{away_score if state not in ("FUT", "PRE") else ""}</div>
</div>
<div class="sb-team-row {home_win}">
<a href="{home_href}" class="sb-team-link" onclick="event.stopPropagation()"><img src="https://assets.nhle.com/logos/nhl/svg/{home_abbrev}_dark.svg" alt="{home_abbrev}" class="sb-logo"></a>
<div class="sb-team-info"><div class="sb-team-name">{home_full}</div><div class="sb-scorers">{home_goals_html}</div></div>
<div class="sb-score">{home_score if state not in ("FUT", "PRE") else ""}</div>
</div>
</div>
{detail_html}
</div>''')

    no_games = '<div class="sb-empty">No games scheduled today.</div>' if not game_cards else ""
    games_html = "\n".join(game_cards)

    return f'''<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>NHL Scoreboard — {display_date}</title>
<script>document.documentElement.setAttribute('data-theme',localStorage.getItem('theme')||'dark')</script>
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin><link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>
:root,:root[data-theme="dark"]{{--bg:#101012;--bg-surface:rgba(255,255,255,0.03);--bg-elevated:rgba(255,255,255,0.05);--bg-hover:rgba(255,255,255,0.07);--border:rgba(255,255,255,0.06);--text:#e8e8ec;--text-secondary:#9898a0;--text-muted:#56565e;--accent:#e8384f;--green:#34d399;--red:#fb7185;--card-shadow:0 1px 2px rgba(0,0,0,0.4),0 0 0 1px rgba(255,255,255,0.04);--card-shadow-hover:0 4px 12px rgba(0,0,0,0.5),0 0 0 1px rgba(255,255,255,0.08);--text-strong:#fff;--tab-active-shadow:0 1px 3px rgba(0,0,0,0.3),inset 0 1px 0 rgba(255,255,255,0.06);--footer-link-deco:rgba(255,255,255,0.1);--panel-bg:#18181b;--overlay:rgba(0,0,0,0.5)}}
:root[data-theme="light"]{{--bg:#f8f8fa;--bg-surface:rgba(0,0,0,0.025);--bg-elevated:rgba(0,0,0,0.04);--bg-hover:rgba(0,0,0,0.05);--border:rgba(0,0,0,0.08);--text:#1a1a1e;--text-secondary:#6b6b73;--text-muted:#a0a0a8;--accent:#c8102e;--green:#059669;--red:#e11d48;--card-shadow:0 1px 3px rgba(0,0,0,0.06),0 0 0 1px rgba(0,0,0,0.04);--card-shadow-hover:0 4px 12px rgba(0,0,0,0.1),0 0 0 1px rgba(0,0,0,0.06);--text-strong:#000;--tab-active-shadow:0 1px 3px rgba(0,0,0,0.06),inset 0 1px 0 rgba(255,255,255,0.8);--footer-link-deco:rgba(0,0,0,0.12);--panel-bg:#fff;--overlay:rgba(0,0,0,0.25)}}
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:'Inter',system-ui,-apple-system,sans-serif;background:var(--bg);color:var(--text);line-height:1.55;-webkit-font-smoothing:antialiased}}
a{{color:var(--text);text-decoration:none}}

/* Header */
.sb-header{{max-width:700px;margin:0 auto;padding:40px 28px 0;display:flex;justify-content:space-between;align-items:flex-start}}
.sb-header-left h1{{font-size:20px;font-weight:600;letter-spacing:-0.4px;color:var(--text-strong)}}
.sb-date{{font-size:13px;color:var(--text-secondary);margin-top:2px;font-weight:500}}
.sb-header-right{{display:flex;align-items:center;gap:8px;padding-top:2px}}
.team-select{{appearance:none;-webkit-appearance:none;background:var(--bg-surface);color:var(--text);border:1px solid var(--border);border-radius:8px;padding:6px 28px 6px 10px;font-size:12px;font-family:inherit;font-weight:500;cursor:pointer;transition:all 0.2s ease;background-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='10' height='6'%3E%3Cpath d='M0 0l5 6 5-6z' fill='%239898a0'/%3E%3C/svg%3E");background-repeat:no-repeat;background-position:right 8px center}}.team-select:hover{{background-color:var(--bg-elevated)}}.team-select:focus{{outline:none;box-shadow:0 0 0 2px var(--accent)}}.team-select optgroup{{font-weight:600;color:var(--text-muted)}}.team-select option{{background:var(--bg);color:var(--text)}}
.theme-toggle{{display:flex;gap:2px;padding:2px;background:var(--bg-surface);border-radius:8px}}
.theme-btn{{display:flex;align-items:center;justify-content:center;width:28px;height:26px;border:none;background:transparent;color:var(--text-muted);cursor:pointer;border-radius:6px;transition:all 0.2s ease;padding:0}}.theme-btn:hover{{color:var(--text-secondary);background:var(--bg-hover)}}
.theme-btn.active{{color:var(--text-strong);background:var(--bg-elevated);box-shadow:var(--tab-active-shadow)}}

/* Game grid */
.sb-grid{{max-width:700px;margin:0 auto;padding:28px 28px 60px;display:flex;flex-direction:column;gap:12px}}

.sb-game{{background:var(--bg-surface);border-radius:14px;box-shadow:var(--card-shadow);overflow:hidden;transition:box-shadow 0.2s ease}}
.sb-game:hover{{box-shadow:var(--card-shadow-hover)}}
.sb-clickable{{cursor:pointer}}
.sb-clickable .sb-matchup:hover{{background:var(--bg-hover)}}

.sb-status{{padding:8px 16px;font-size:10px;font-weight:600;text-transform:uppercase;letter-spacing:1px;color:var(--text-muted);border-bottom:1px solid var(--border)}}
.sb-live{{color:var(--red);animation:pulse 2s ease-in-out infinite}}
.sb-final{{color:var(--text-muted)}}
.sb-upcoming{{color:var(--text-secondary)}}
@keyframes pulse{{0%,100%{{opacity:1}}50%{{opacity:0.5}}}}

.sb-matchup{{transition:background 0.15s}}
.sb-team-row{{display:flex;align-items:center;padding:12px 16px;gap:12px;color:var(--text)}}
.sb-team-row+.sb-team-row{{border-top:1px solid var(--border)}}
.sb-team-link{{flex-shrink:0;line-height:0}}.sb-team-link:hover{{opacity:0.8}}
.sb-logo{{width:36px;height:36px}}
.sb-team-info{{flex:1;min-width:0}}
.sb-team-name{{font-size:14px;font-weight:600;color:var(--text-secondary)}}
.sb-winner .sb-team-name{{color:var(--text-strong)}}
.sb-winner .sb-score{{color:var(--text-strong)}}
.sb-scorers{{display:flex;flex-wrap:wrap;gap:4px;margin-top:2px}}
.sb-scorer{{font-size:10px;color:var(--text-muted);font-weight:500}}
.sb-scorer+.sb-scorer::before{{content:"\\00b7 ";margin-right:0}}
.sb-score{{font-size:28px;font-weight:700;letter-spacing:-1px;color:var(--text-muted);min-width:36px;text-align:right;font-variant-numeric:tabular-nums}}

.sb-empty{{text-align:center;padding:48px 20px;color:var(--text-muted);font-size:14px}}

/* Side panel */
.panel-overlay{{position:fixed;inset:0;background:var(--overlay);z-index:100;opacity:0;pointer-events:none;transition:opacity 0.25s ease}}
.panel-overlay.open{{opacity:1;pointer-events:auto}}
.side-panel{{position:fixed;top:0;right:0;bottom:0;width:min(520px,90vw);background:var(--panel-bg);z-index:101;transform:translateX(100%);transition:transform 0.3s cubic-bezier(0.16,1,0.3,1);overflow-y:auto;box-shadow:-4px 0 24px rgba(0,0,0,0.3)}}
.side-panel.open{{transform:translateX(0)}}
.panel-close{{position:sticky;top:0;display:flex;justify-content:flex-end;padding:16px 20px 8px;background:var(--panel-bg);z-index:1}}
.panel-close-btn{{width:32px;height:32px;border:none;background:var(--bg-surface);color:var(--text-muted);border-radius:8px;cursor:pointer;display:flex;align-items:center;justify-content:center;transition:all 0.15s}}.panel-close-btn:hover{{background:var(--bg-elevated);color:var(--text)}}
.panel-body{{padding:0 24px 32px}}

/* Panel header */
.gd-panel-header{{margin-bottom:24px;padding-bottom:16px;border-bottom:1px solid var(--border)}}
.gd-panel-teams{{display:flex;align-items:center;gap:8px;margin-bottom:8px;flex-wrap:wrap}}
.gd-panel-logo{{width:24px;height:24px}}
.gd-panel-teams span{{font-size:13px;font-weight:600;color:var(--text)}}
.gd-panel-vs{{color:var(--text-muted);font-weight:400;font-size:11px}}
.gd-panel-score{{font-size:24px;font-weight:700;letter-spacing:-0.5px;color:var(--text-strong);font-variant-numeric:tabular-nums}}
.gd-panel-status{{font-size:11px;font-weight:500;color:var(--text-muted);margin-left:8px;text-transform:uppercase;letter-spacing:0.5px}}

/* Game detail sections */
.gd-section{{margin-bottom:24px}}
.gd-section:last-child{{margin-bottom:0}}
.gd-section-title{{font-size:11px;font-weight:600;text-transform:uppercase;letter-spacing:0.8px;color:var(--text-muted);margin-bottom:12px;padding-bottom:6px;border-bottom:1px solid var(--border)}}

.gd-period{{margin-bottom:16px}}
.gd-period:last-child{{margin-bottom:0}}
.gd-period-label{{font-size:10px;font-weight:600;text-transform:uppercase;letter-spacing:0.6px;color:var(--text-muted);margin-bottom:8px}}
.gd-goal{{display:flex;align-items:center;gap:10px;padding:6px 0;border-bottom:1px solid var(--border)}}
.gd-goal:last-child{{border-bottom:none}}
.gd-time{{font-size:11px;font-weight:600;color:var(--text-secondary);font-variant-numeric:tabular-nums;min-width:40px}}
.gd-logo{{flex-shrink:0}}.gd-team-logo{{width:20px;height:20px}}
.gd-headshot{{width:28px;height:28px;border-radius:50%;flex-shrink:0}}
.gd-goal-info{{flex:1;min-width:0}}
.gd-scorer-name{{font-size:12px;font-weight:600;color:var(--text)}}
.gd-assists{{font-size:10px;color:var(--text-muted);margin-top:1px}}
.gd-badge{{font-size:9px;font-weight:700;padding:1px 4px;border-radius:3px;margin-left:4px;vertical-align:middle}}
.gd-pp{{background:rgba(251,191,36,0.15);color:#fbbf24}}
.gd-sh{{background:rgba(52,211,153,0.15);color:var(--green)}}
.gd-en{{background:rgba(152,152,160,0.15);color:var(--text-secondary)}}

.gd-box-team{{margin-bottom:16px}}.gd-box-team:last-child{{margin-bottom:0}}
.gd-box-team-name{{font-size:12px;font-weight:600;color:var(--text);margin-bottom:8px}}
.gd-tbl-wrap{{overflow-x:auto;margin-bottom:8px;border-radius:8px}}
.gd-tbl{{width:100%;border-collapse:collapse;font-size:11px;font-variant-numeric:tabular-nums}}
.gd-tbl th{{padding:6px 6px;font-size:9px;font-weight:600;text-transform:uppercase;letter-spacing:0.4px;color:var(--text-muted);text-align:left;white-space:nowrap;border-bottom:1px solid var(--border);background:var(--bg-surface)}}
.gd-tbl td{{padding:5px 6px;color:var(--text-secondary);white-space:nowrap;border-bottom:1px solid var(--border)}}
.gd-tbl tbody tr:hover td{{background:var(--bg-hover)}}
.gd-pts-hl{{color:var(--text-strong) !important;font-weight:600}}

.footer{{text-align:center;padding:36px 28px;font-size:11px;color:var(--text-muted);max-width:700px;margin:0 auto}}
.footer a{{color:var(--text-muted);text-decoration:underline;text-decoration-color:var(--footer-link-deco);text-underline-offset:2px}}.footer a:hover{{color:var(--text-secondary)}}
.footer-ts{{display:block;margin-top:6px;font-size:10px;color:var(--text-muted);opacity:0.7}}

@media(max-width:500px){{.sb-header{{padding:24px 16px 0;flex-direction:column;gap:12px}}.sb-logo{{width:28px;height:28px}}.sb-score{{font-size:22px}}.sb-team-name{{font-size:13px}}.sb-grid{{padding:16px 16px 40px}}.gd-tbl{{font-size:10px}}.side-panel{{width:100vw}}}}
</style></head><body>

<div class="sb-header">
  <div class="sb-header-left">
    <h1>NHL Scoreboard</h1>
    <div class="sb-date">{display_date}</div>
  </div>
  <div class="sb-header-right">
    <select class="team-select" onchange="if(this.value)window.location.href=this.value">
      <option value="">View Team...</option>
      {switcher_opts}
    </select>
    <div class="theme-toggle">
      <button class="theme-btn" data-theme="light" title="Light" aria-label="Light theme"><svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5"><circle cx="8" cy="8" r="3"/><path d="M8 1.5v2M8 12.5v2M1.5 8h2M12.5 8h2M3.4 3.4l1.4 1.4M11.2 11.2l1.4 1.4M3.4 12.6l1.4-1.4M11.2 4.8l1.4-1.4" stroke-linecap="round"/></svg></button>
      <button class="theme-btn" data-theme="dark" title="Dark" aria-label="Dark theme"><svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M13 8.5A5.5 5.5 0 017 3a6 6 0 00.2-1.5A6 6 0 1013.5 9a5 5 0 01-.5-.5z" stroke-linecap="round" stroke-linejoin="round"/></svg></button>
    </div>
  </div>
</div>

<div class="sb-grid">
{games_html}
{no_games}
</div>

<div class="footer">Data from NHL API<span class="footer-ts">Updated {now}</span></div>

<!-- Side panel -->
<div class="panel-overlay" id="panelOverlay" onclick="closePanel()"></div>
<div class="side-panel" id="sidePanel">
  <div class="panel-close"><button class="panel-close-btn" onclick="closePanel()" aria-label="Close"><svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"><path d="M4 4l8 8M12 4l-8 8"/></svg></button></div>
  <div class="panel-body" id="panelBody"></div>
</div>

<script>
(function(){{
  var root=document.documentElement;
  var btns=document.querySelectorAll('.theme-btn');
  var saved=localStorage.getItem('theme')||'dark';
  btns.forEach(function(b){{
    if(b.dataset.theme===saved) b.classList.add('active');
    b.addEventListener('click',function(){{
      var t=b.dataset.theme;
      root.setAttribute('data-theme',t);
      localStorage.setItem('theme',t);
      btns.forEach(function(x){{x.classList.remove('active')}});
      b.classList.add('active');
    }});
  }});
}})();
function openPanel(gameId){{
  var src=document.getElementById('gd-'+gameId);
  if(!src) return;
  document.getElementById('panelBody').innerHTML=src.innerHTML;
  document.getElementById('sidePanel').classList.add('open');
  document.getElementById('panelOverlay').classList.add('open');
  document.body.style.overflow='hidden';
}}
function closePanel(){{
  document.getElementById('sidePanel').classList.remove('open');
  document.getElementById('panelOverlay').classList.remove('open');
  document.body.style.overflow='';
}}
document.addEventListener('keydown',function(e){{if(e.key==='Escape')closePanel()}});
</script>
</body></html>'''

# ── Main ──────────────────────────────────────────────────

def main():
    global TEAM

    # ── Shared data (fetch once) ──────────────────────────
    print("Fetching NHL standings...")
    standings = fetch_standings()
    # Use DEFAULT_TEAM just to get team lists from standings
    TEAM = DEFAULT_TEAM
    _, east_teams, west_teams, all_teams = get_team_data(standings)
    above500 = get_above500_teams(all_teams)
    team_records_map = get_team_records(all_teams)

    print("Fetching MoneyPuck playoff odds...")
    mp_odds = fetch_moneypuck_odds()
    print(f"  {len(mp_odds)} teams loaded")

    print("Fetching MoneyPuck team stats...")
    mp_stats = fetch_moneypuck_team_stats()
    print(f"  {len(mp_stats)} teams loaded")

    print("Fetching MoneyPuck player stats (all teams)...")
    all_mp_players = fetch_all_moneypuck_players()
    print(f"  {len(all_mp_players)} teams loaded")

    print("Fetching all team schedules...")
    all_schedules = fetch_all_schedules(all_teams)
    print(f"  {len(all_schedules)} team schedules fetched")

    # ── Per-team builds ───────────────────────────────────
    for team_abbrev in TEAM_INFO:
        TEAM = team_abbrev
        team_info = TEAM_INFO[TEAM]
        team_name = team_info["name"]
        print(f"\n{'='*50}")
        print(f"Building {team_name} ({TEAM})...")

        # Find this team in standings
        team_entry = next((t for t in all_teams if t["abbrev"] == TEAM), None)
        if not team_entry:
            print(f"  WARNING: {TEAM} not found in standings, skipping")
            continue
        print(f"  {team_entry['w']}-{team_entry['l']}-{team_entry['otl']} ({team_entry['pts']} pts)")

        # Determine conference
        conf_name = team_entry["conf"]
        conf_teams = east_teams if conf_name == "Eastern" else west_teams

        # Fetch team-specific data
        print(f"  Fetching club stats...")
        try:
            club_stats = fetch_club_stats()
        except Exception as e:
            print(f"  WARNING: club stats failed: {e}")
            club_stats = {"skaters": [], "goalies": []}

        print(f"  Fetching player stats...")
        try:
            nhl_skater_summary = fetch_nhl_skater_summary()
            nhl_goalie_summary = fetch_nhl_goalie_summary()
        except Exception as e:
            print(f"  WARNING: NHL stats API failed: {e}")
            nhl_skater_summary = {}
            nhl_goalie_summary = {}

        skaters = get_skaters(club_stats, nhl_skater_summary)
        goalies = get_goalies(club_stats, nhl_goalie_summary)
        print(f"  {len(skaters)} skaters, {len(goalies)} goalies")

        # Schedule from cached data
        schedule_data = all_schedules.get(TEAM, {"games": []})
        remaining = get_remaining_schedule(schedule_data, above500)
        results = get_results(schedule_data)
        vs500 = compute_vs_above500(results, above500)
        print(f"  {len(remaining)} remaining, vs .500: {vs500[0]}-{vs500[1]}-{vs500[2]}")

        # MoneyPuck player data (filtered from cached CSV)
        mp_players = all_mp_players.get(TEAM, {})

        # Compute conference records for this focus team
        conf_records = compute_conf_records(all_schedules, TEAM, conf_teams, above500)

        # News
        print(f"  Fetching news...")
        try:
            news_articles = fetch_team_news()
        except Exception as e:
            print(f"  WARNING: news fetch failed: {e}")
            news_articles = []
        print(f"  {len(news_articles)} articles found")

        # Delta tracking
        prev = load_previous()
        target = 93
        team_odds = mp_odds.get(TEAM, {}).get("ALL", {})
        needed = max(0, target - team_entry["pts"])
        proj_pts = team_odds.get("projPts", 0)
        gap = round(proj_pts - target, 1)
        deltas = {
            "playoffPct": prev.get("playoffPct"),
            "pts": prev.get("pts"),
            "needed": prev.get("needed"),
            "gap": prev.get("gap"),
        }
        current = {
            "playoffPct": team_odds.get("playoffPct", 0),
            "pts": team_entry["pts"],
            "needed": needed,
            "gap": gap,
        }
        if prev.get("pts") != team_entry["pts"]:
            save_current(current)
        elif not prev:
            save_current(current)

        above500_count = sum(1 for g in remaining if g["above500"])
        home_count = sum(1 for g in remaining if g["loc"] == "home")
        away_count = sum(1 for g in remaining if g["loc"] == "away")

        # Build HTML
        roster_html = build_roster_html(skaters, goalies, mp_players)
        standings_html = build_standings_section(conf_teams, conf_records, conf_name)
        projections_html = build_projections_html(team_entry, vs500, mp_odds, mp_stats, conf_teams)
        schedule_html = build_schedule_html(remaining, above500_count, home_count, away_count, team_records_map, mp_stats, mp_odds, results)
        news_html = build_news_html(news_articles)
        html = generate_html(team_entry, roster_html, standings_html, projections_html, schedule_html, news_html, vs500, mp_odds, deltas, mp_stats, all_teams)

        # Write file
        filename = "index.html" if TEAM == DEFAULT_TEAM else f"{TEAM}.html"
        with open(filename, "w") as f:
            f.write(html)
        print(f"  -> {filename} generated")

    # ── Scoreboard page ────────────────────────────────
    print(f"\n{'='*50}")
    print("Building scoreboard...")
    scores_data = fetch_scores()
    games = scores_data.get("games", [])

    # Fetch game details (boxscore + scoring) for completed/live games
    all_game_details = {}
    for g in games:
        gid = g.get("id", 0)
        gstate = g.get("gameState", "")
        if gstate in ("FINAL", "OFF", "LIVE", "CRIT"):
            print(f"  Fetching details for game {gid}...")
            all_game_details[gid] = fetch_game_details(gid)

    # Build team switcher for scoreboard nav
    sb_div_groups = [("Atlantic", []), ("Metropolitan", []), ("Central", []), ("Pacific", [])]
    for t in all_teams:
        for dname, dlist in sb_div_groups:
            if t["div"] == dname:
                dlist.append(t)
                break
    sb_switcher = ''
    for dname, dlist in sb_div_groups:
        dlist.sort(key=lambda x: x["name"])
        sb_switcher += f'<optgroup label="{dname}">'
        for t in dlist:
            a = t["abbrev"]
            fn = "index.html" if a == DEFAULT_TEAM else f"{a}.html"
            sb_switcher += f'<option value="{fn}">{t["name"]}</option>'
        sb_switcher += '</optgroup>'

    scoreboard_html = build_scoreboard_html(scores_data, all_game_details, sb_switcher)
    with open("scores.html", "w") as f:
        f.write(scoreboard_html)
    print(f"  -> scores.html generated ({len(games)} games, {len(all_game_details)} with details)")

    print(f"\n{'='*50}")
    print("Done! All 32 team pages + scoreboard generated.")

if __name__ == "__main__":
    main()
