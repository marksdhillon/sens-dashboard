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
    "BOS": {"name": "Boston Bruins", "franchise_id": 6, "accent": "#e8b230", "subreddit": "BostonBruins", "div": "Atlantic", "espn_id": 1, "hfboards": "https://forums.hfboards.com/forums/boston-bruins.15/"},
    "BUF": {"name": "Buffalo Sabres", "franchise_id": 19, "accent": "#6b9fff", "subreddit": "sabres", "div": "Atlantic", "espn_id": 2, "hfboards": "https://forums.hfboards.com/forums/buffalo-sabres.18/"},
    "DET": {"name": "Detroit Red Wings", "franchise_id": 12, "accent": "#e8384f", "subreddit": "DetroitRedWings", "div": "Atlantic", "espn_id": 5, "hfboards": "https://forums.hfboards.com/forums/detroit-red-wings.34/"},
    "FLA": {"name": "Florida Panthers", "franchise_id": 33, "accent": "#c8102e", "subreddit": "FloridaPanthers", "div": "Atlantic", "espn_id": 26, "hfboards": "https://forums.hfboards.com/forums/florida-panthers.28/"},
    "MTL": {"name": "Montreal Canadiens", "franchise_id": 1, "accent": "#d42e42", "subreddit": "Habs", "div": "Atlantic", "espn_id": 10, "hfboards": "https://forums.hfboards.com/forums/montreal-canadiens.16/"},
    "OTT": {"name": "Ottawa Senators", "franchise_id": 30, "accent": "#e8384f", "subreddit": "OttawaSenators", "div": "Atlantic", "espn_id": 14, "hfboards": "https://forums.hfboards.com/forums/ottawa-senators.19/"},
    "TBL": {"name": "Tampa Bay Lightning", "franchise_id": 31, "accent": "#6b9fff", "subreddit": "TampaBayLightning", "div": "Atlantic", "espn_id": 20, "hfboards": "https://forums.hfboards.com/forums/tampa-bay-lightning.27/"},
    "TOR": {"name": "Toronto Maple Leafs", "franchise_id": 5, "accent": "#6b9fff", "subreddit": "leafs", "div": "Atlantic", "espn_id": 21, "hfboards": "https://forums.hfboards.com/forums/toronto-maple-leafs.17/"},
    # Metropolitan
    "CAR": {"name": "Carolina Hurricanes", "franchise_id": 26, "accent": "#e8384f", "subreddit": "canes", "div": "Metropolitan", "espn_id": 7, "hfboards": "https://forums.hfboards.com/forums/carolina-hurricanes.26/"},
    "CBJ": {"name": "Columbus Blue Jackets", "franchise_id": 36, "accent": "#6b9fff", "subreddit": "BlueJackets", "div": "Metropolitan", "espn_id": 29, "hfboards": "https://forums.hfboards.com/forums/columbus-blue-jackets.31/"},
    "NJD": {"name": "New Jersey Devils", "franchise_id": 23, "accent": "#e8384f", "subreddit": "devils", "div": "Metropolitan", "espn_id": 11, "hfboards": "https://forums.hfboards.com/forums/new-jersey-devils.20/"},
    "NYI": {"name": "New York Islanders", "franchise_id": 22, "accent": "#f47d30", "subreddit": "NewYorkIslanders", "div": "Metropolitan", "espn_id": 12, "hfboards": "https://forums.hfboards.com/forums/new-york-islanders.22/"},
    "NYR": {"name": "New York Rangers", "franchise_id": 10, "accent": "#6b9fff", "subreddit": "rangers", "div": "Metropolitan", "espn_id": 13, "hfboards": "https://forums.hfboards.com/forums/new-york-rangers.24/"},
    "PHI": {"name": "Philadelphia Flyers", "franchise_id": 16, "accent": "#f47d30", "subreddit": "Flyers", "div": "Metropolitan", "espn_id": 15, "hfboards": "https://forums.hfboards.com/forums/philadelphia-flyers.21/"},
    "PIT": {"name": "Pittsburgh Penguins", "franchise_id": 17, "accent": "#e8b230", "subreddit": "penguins", "div": "Metropolitan", "espn_id": 16, "hfboards": "https://forums.hfboards.com/forums/pittsburgh-penguins.23/"},
    "WSH": {"name": "Washington Capitals", "franchise_id": 24, "accent": "#c8102e", "subreddit": "caps", "div": "Metropolitan", "espn_id": 23, "hfboards": "https://forums.hfboards.com/forums/washington-capitals.25/"},
    # --- Western Conference ---
    # Central
    "CHI": {"name": "Chicago Blackhawks", "franchise_id": 11, "accent": "#e8384f", "subreddit": "hawks", "div": "Central", "espn_id": 4, "hfboards": "https://forums.hfboards.com/forums/chicago-blackhawks.30/"},
    "COL": {"name": "Colorado Avalanche", "franchise_id": 27, "accent": "#c84060", "subreddit": "ColoradoAvalanche", "div": "Central", "espn_id": 17, "hfboards": "https://forums.hfboards.com/forums/colorado-avalanche.35/"},
    "DAL": {"name": "Dallas Stars", "franchise_id": 15, "accent": "#00a651", "subreddit": "DallasStars", "div": "Central", "espn_id": 9, "hfboards": "https://forums.hfboards.com/forums/dallas-stars.44/"},
    "MIN": {"name": "Minnesota Wild", "franchise_id": 37, "accent": "#2e8540", "subreddit": "wildhockey", "div": "Central", "espn_id": 30, "hfboards": "https://forums.hfboards.com/forums/minnesota-wild.39/"},
    "NSH": {"name": "Nashville Predators", "franchise_id": 34, "accent": "#ffb81c", "subreddit": "Predators", "div": "Central", "espn_id": 27, "hfboards": "https://forums.hfboards.com/forums/nashville-predators.33/"},
    "STL": {"name": "St. Louis Blues", "franchise_id": 18, "accent": "#4477ce", "subreddit": "stlouisblues", "div": "Central", "espn_id": 19, "hfboards": "https://forums.hfboards.com/forums/st-louis-blues.32/"},
    "UTA": {"name": "Utah Hockey Club", "franchise_id": 28, "accent": "#69b3e7", "subreddit": "UtahHC", "div": "Central", "espn_id": 129764, "hfboards": "https://forums.hfboards.com/forums/utah-mammoth.287/"},
    "WPG": {"name": "Winnipeg Jets", "franchise_id": 35, "accent": "#6888b0", "subreddit": "winnipegjets", "div": "Central", "espn_id": 28, "hfboards": "https://forums.hfboards.com/forums/winnipeg-jets.29/"},
    # Pacific
    "ANA": {"name": "Anaheim Ducks", "franchise_id": 32, "accent": "#f47d30", "subreddit": "AnaheimDucks", "div": "Pacific", "espn_id": 25, "hfboards": "https://forums.hfboards.com/forums/anaheim-ducks.41/"},
    "CGY": {"name": "Calgary Flames", "franchise_id": 21, "accent": "#d2001c", "subreddit": "CalgaryFlames", "div": "Pacific", "espn_id": 3, "hfboards": "https://forums.hfboards.com/forums/calgary-flames.37/"},
    "EDM": {"name": "Edmonton Oilers", "franchise_id": 25, "accent": "#ff6b2b", "subreddit": "EdmontonOilers", "div": "Pacific", "espn_id": 6, "hfboards": "https://forums.hfboards.com/forums/edmonton-oilers.38/"},
    "LAK": {"name": "Los Angeles Kings", "franchise_id": 14, "accent": "#a2aaad", "subreddit": "losangeleskings", "div": "Pacific", "espn_id": 8, "hfboards": "https://forums.hfboards.com/forums/los-angeles-kings.42/"},
    "SEA": {"name": "Seattle Kraken", "franchise_id": 39, "accent": "#68cfd1", "subreddit": "SeattleKraken", "div": "Pacific", "espn_id": 124292, "hfboards": "https://forums.hfboards.com/forums/seattle-kraken.275/"},
    "SJS": {"name": "San Jose Sharks", "franchise_id": 29, "accent": "#009aa6", "subreddit": "SanJoseSharks", "div": "Pacific", "espn_id": 18, "hfboards": "https://forums.hfboards.com/forums/san-jose-sharks.43/"},
    "VAN": {"name": "Vancouver Canucks", "franchise_id": 20, "accent": "#4080c4", "subreddit": "canucks", "div": "Pacific", "espn_id": 22, "hfboards": "https://forums.hfboards.com/forums/vancouver-canucks.36/"},
    "VGK": {"name": "Vegas Golden Knights", "franchise_id": 38, "accent": "#b4975a", "subreddit": "goldenknights", "div": "Pacific", "espn_id": 37, "hfboards": "https://forums.hfboards.com/forums/vegas-golden-knights.257/"},
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

def fetch_scores_for_date(date_str):
    """Fetch NHL scores for a specific date (YYYY-MM-DD)."""
    try:
        data = fetch_json(f"{NHL_API}/score/{date_str}")
        return data
    except Exception as e:
        print(f"  WARNING: scores fetch for {date_str} failed: {e}")
        return {"currentDate": date_str, "games": []}

# ESPN team abbreviation mapping (ESPN uses different abbrevs for some teams)
ESPN_ABBREV_MAP = {
    "OTT": "ott", "TOR": "tor", "MTL": "mtl", "BOS": "bos", "BUF": "buf",
    "DET": "det", "FLA": "fla", "TBL": "tb", "CAR": "car", "CBJ": "cbj",
    "NJD": "nj", "NYI": "nyi", "NYR": "nyr", "PHI": "phi", "PIT": "pit",
    "WSH": "wsh", "CHI": "chi", "COL": "col", "DAL": "dal", "MIN": "min",
    "NSH": "nsh", "STL": "stl", "WPG": "wpg", "ANA": "ana", "CGY": "cgy",
    "EDM": "edm", "LAK": "la", "SEA": "sea", "SJS": "sj", "VAN": "van",
    "VGK": "vgs", "UTA": "uta",
}

def fetch_espn_injuries():
    """Fetch all NHL injuries from ESPN injuries page. Returns dict of team_abbrev -> list of injuries."""
    url = "https://www.espn.com/nhl/injuries"
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    })
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            html = resp.read().decode("utf-8", errors="replace")
    except Exception as e:
        print(f"  WARNING: ESPN injuries fetch failed: {e}")
        return {}

    # Build reverse map: espn abbrev -> our abbrev
    reverse_map = {v: k for k, v in ESPN_ABBREV_MAP.items()}

    injuries = {}  # our_abbrev -> [{"name": ..., "pos": ..., "est_return": ..., "status": ..., "comment": ...}]

    import re as _re

    # ESPN structure: team sections separated by injuries__teamName spans,
    # each followed by a Table with Table__TR--sm rows containing Table__TD cells
    # Split by team name headers
    team_sections = _re.split(r'injuries__teamName[^"]*">', html)

    for section in team_sections[1:]:  # skip text before first team
        # Team name is at the start of this section
        team_name_match = _re.match(r'([^<]+)<', section)
        if not team_name_match:
            continue
        team_display = team_name_match.group(1).strip()

        # Find team abbrev from link in this section
        team_link = _re.search(r'/nhl/team/_/name/([a-z]+)', section)
        if team_link:
            espn_abbr = team_link.group(1)
        else:
            # Try matching team name to our team info
            espn_abbr = None
            for k, v in ESPN_ABBREV_MAP.items():
                if TEAM_INFO.get(k, {}).get("name", "") == team_display:
                    espn_abbr = v
                    break
            if not espn_abbr:
                continue

        our_abbr = reverse_map.get(espn_abbr)
        if not our_abbr:
            continue

        team_injuries = []

        # Find data rows (Table__TR--sm with data-idx attribute)
        rows = _re.findall(r'<tr[^>]*Table__TR--sm[^>]*>(.*?)</tr>', section, _re.DOTALL)
        for row in rows:
            # Extract cells
            cells = _re.findall(r'<td[^>]*>(.*?)</td>', row, _re.DOTALL)
            if len(cells) < 4:
                continue

            # Name: inside AnchorLink
            name_match = _re.search(r'AnchorLink[^>]*>([^<]+)<', cells[0])
            if not name_match:
                name_match = _re.search(r'>([^<]+)<', cells[0])
            if not name_match:
                continue
            name = name_match.group(1).strip()
            if not name or name == "NAME":
                continue

            # Clean cell text
            def _clean(s):
                return _re.sub(r'<[^>]+>', '', s).strip()

            pos = _clean(cells[1]) if len(cells) > 1 else ""
            est_return = _clean(cells[2]) if len(cells) > 2 else ""
            status = _clean(cells[3]) if len(cells) > 3 else ""
            comment = _clean(cells[4]) if len(cells) > 4 else ""

            team_injuries.append({
                "name": name,
                "pos": pos,
                "est_return": est_return,
                "status": status,
                "comment": comment,
            })

        if team_injuries:
            injuries[our_abbr] = team_injuries

    return injuries

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

def fetch_roster_birthdates():
    """Fetch roster to get birth info for each player. Returns {playerId: {birthDate, birthCity, birthCountry, birthStateProvince}}."""
    data = fetch_json(f"{NHL_API}/roster/{TEAM}/{SEASON}")
    bd_map = {}
    for group in ("forwards", "defensemen", "goalies"):
        for p in data.get(group, []):
            pid = p.get("id", 0)
            bd = p.get("birthDate", "")
            if pid:
                city = p.get("birthCity", {})
                if isinstance(city, dict):
                    city = city.get("default", "")
                country = p.get("birthCountry", "")
                prov = p.get("birthStateProvince", {})
                if isinstance(prov, dict):
                    prov = prov.get("default", "")
                bd_map[pid] = {"birthDate": bd, "birthCity": city, "birthCountry": country, "birthStateProvince": prov}
    return bd_map

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

def fetch_league_skater_leaders():
    """Fetch top skaters league-wide for leader boards (points, goals, assists, +/-)."""
    leaders = {}
    sorts = {
        "points": "points",
        "goals": "goals",
        "assists": "assists",
        "plusMinus": "plusMinus",
    }
    for key, prop in sorts.items():
        url = (
            "https://api.nhle.com/stats/rest/en/skater/summary?"
            "isAggregate=false&isGame=false"
            f"&sort=%5B%7B%22property%22:%22{prop}%22,%22direction%22:%22DESC%22%7D%5D"
            "&start=0&limit=10"
            "&factCayenneExp=gamesPlayed%3E=1"
            f"&cayenneExp=seasonId%3C={SEASON}%20and%20seasonId%3E={SEASON}%20and%20gameTypeId=2"
        )
        try:
            data = fetch_json(url)
            leaders[key] = data.get("data", [])
        except Exception as e:
            print(f"  WARNING: league skater leaders ({key}) failed: {e}")
            leaders[key] = []
    return leaders

def fetch_league_goalie_leaders():
    """Fetch top goalies league-wide for leader boards (wins, GAA, SV%)."""
    leaders = {}
    # GAA ascending (lower is better), others descending
    configs = {
        "wins": ("wins", "DESC"),
        "gaa": ("goalsAgainstAverage", "ASC"),
        "svPct": ("savePct", "DESC"),
    }
    for key, (prop, direction) in configs.items():
        url = (
            "https://api.nhle.com/stats/rest/en/goalie/summary?"
            "isAggregate=false&isGame=false"
            f"&sort=%5B%7B%22property%22:%22{prop}%22,%22direction%22:%22{direction}%22%7D%5D"
            "&start=0&limit=10"
            "&factCayenneExp=gamesPlayed%3E=10"
            f"&cayenneExp=seasonId%3C={SEASON}%20and%20seasonId%3E={SEASON}%20and%20gameTypeId=2"
        )
        try:
            data = fetch_json(url)
            leaders[key] = data.get("data", [])
        except Exception as e:
            print(f"  WARNING: league goalie leaders ({key}) failed: {e}")
            leaders[key] = []
    return leaders

def fetch_full_skater_stats():
    """Fetch top 50 skaters by points for the full stats table."""
    url = (
        "https://api.nhle.com/stats/rest/en/skater/summary?"
        "isAggregate=false&isGame=false"
        "&sort=%5B%7B%22property%22:%22points%22,%22direction%22:%22DESC%22%7D%5D"
        "&start=0&limit=50"
        "&factCayenneExp=gamesPlayed%3E=1"
        f"&cayenneExp=seasonId%3C={SEASON}%20and%20seasonId%3E={SEASON}%20and%20gameTypeId=2"
    )
    try:
        data = fetch_json(url)
        return data.get("data", [])
    except Exception as e:
        print(f"  WARNING: full skater stats failed: {e}")
        return []

def fetch_full_goalie_stats():
    """Fetch top 30 goalies by wins for the full stats table."""
    url = (
        "https://api.nhle.com/stats/rest/en/goalie/summary?"
        "isAggregate=false&isGame=false"
        "&sort=%5B%7B%22property%22:%22wins%22,%22direction%22:%22DESC%22%7D%5D"
        "&start=0&limit=30"
        "&factCayenneExp=gamesPlayed%3E=5"
        f"&cayenneExp=seasonId%3C={SEASON}%20and%20seasonId%3E={SEASON}%20and%20gameTypeId=2"
    )
    try:
        data = fetch_json(url)
        return data.get("data", [])
    except Exception as e:
        print(f"  WARNING: full goalie stats failed: {e}")
        return []

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

def get_skaters(club_stats, nhl_summary, bd_map=None):
    """Build skater list merging club-stats (headshots) + NHL stats API (full summary)."""
    if bd_map is None:
        bd_map = {}
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

        # Birth info from roster
        bio = bd_map.get(pid, {})
        bd = bio.get("birthDate", "") if isinstance(bio, dict) else bio
        age = ""
        bd_display = ""
        if bd:
            try:
                from datetime import date as _date
                by, bm, bday = bd.split("-")
                born = _date(int(by), int(bm), int(bday))
                today = _date.today()
                age = today.year - born.year - ((today.month, today.day) < (born.month, born.day))
                bd_display = born.strftime("%b %-d, %Y")
            except Exception:
                age = ""
        birth_city = bio.get("birthCity", "") if isinstance(bio, dict) else ""
        birth_country = bio.get("birthCountry", "") if isinstance(bio, dict) else ""
        birth_prov = bio.get("birthStateProvince", "") if isinstance(bio, dict) else ""
        birthplace = birth_city
        if birth_prov:
            birthplace += f", {birth_prov}" if birthplace else birth_prov
        if birth_country:
            birthplace += f", {birth_country}" if birthplace else birth_country

        skaters.append({
            "name": f"{first} {last}",
            "pos": ns.get("positionCode", s.get("positionCode", "")),
            "headshot": headshot,
            "age": age,
            "birthDate": bd_display,
            "birthPlace": birthplace,
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

def get_goalies(club_stats, nhl_goalie_summary, bd_map=None):
    """Build goalie list merging club-stats (headshots) + NHL stats API (full summary)."""
    if bd_map is None:
        bd_map = {}
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

        # Birth info from roster
        bio = bd_map.get(pid, {})
        bd = bio.get("birthDate", "") if isinstance(bio, dict) else bio
        g_age = ""
        bd_display = ""
        if bd:
            try:
                from datetime import date as _date
                by, bm, bday = bd.split("-")
                born = _date(int(by), int(bm), int(bday))
                today = _date.today()
                g_age = today.year - born.year - ((today.month, today.day) < (born.month, born.day))
                bd_display = born.strftime("%b %-d, %Y")
            except Exception:
                g_age = ""
        birth_city = bio.get("birthCity", "") if isinstance(bio, dict) else ""
        birth_country = bio.get("birthCountry", "") if isinstance(bio, dict) else ""
        birth_prov = bio.get("birthStateProvince", "") if isinstance(bio, dict) else ""
        birthplace = birth_city
        if birth_prov:
            birthplace += f", {birth_prov}" if birthplace else birth_prov
        if birth_country:
            birthplace += f", {birth_country}" if birthplace else birth_country

        goalies.append({
            "name": f"{first} {last}",
            "headshot": g.get("headshot", ""),
            "age": g_age,
            "birthDate": bd_display,
            "birthPlace": birthplace,
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
<td class="r" data-sort="{s["age"] if s["age"] != "" else 0}">{s["age"]}</td>
<td class="r bio-col" data-sort="{s["birthDate"]}">{s["birthDate"]}</td>
<td class="r bio-col" data-sort="{s["birthPlace"]}">{s["birthPlace"]}</td>
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
<td class="r" data-sort="{g["so"]}">{g["so"]}</td><td class="r" data-sort="{g_toi_sec}">{g["toi"]}</td>
<td class="r" data-sort="{g["age"] if g["age"] != "" else 0}">{g["age"]}</td>
<td class="r bio-col" data-sort="{g["birthDate"]}">{g["birthDate"]}</td>
<td class="r bio-col" data-sort="{g["birthPlace"]}">{g["birthPlace"]}</td></tr>''')

    return f'''<div class="scroll-x"><table class="nhl-tbl sortable" id="skater-tbl">
<thead><tr><th class="rank sort-th" data-col="0" title="Rank by points">#</th><th class="name-col sort-th" data-col="1" title="Player name">Player</th><th class="r sort-th" data-col="2" title="Position (C, L, R, D)">Pos</th><th class="r sort-th" data-col="3" title="Games played this season">GP</th><th class="r sort-th" data-col="4" title="Goals scored">G</th><th class="r sort-th" data-col="5" title="Assists">A</th><th class="r sort-th" data-col="6" title="Points (goals + assists)">P</th><th class="r sort-th" data-col="7" title="Plus/minus: on-ice goal differential at even strength">+/-</th><th class="r sort-th" data-col="8" title="Penalty minutes">PIM</th><th class="r sort-th" data-col="9" title="Points per game played">P/GP</th><th class="r sort-th" data-col="10" title="Even-strength goals">EVG</th><th class="r sort-th" data-col="11" title="Even-strength points">EVP</th><th class="r sort-th" data-col="12" title="Power-play goals">PPG</th><th class="r sort-th" data-col="13" title="Power-play points">PPP</th><th class="r sort-th" data-col="14" title="Short-handed goals">SHG</th><th class="r sort-th" data-col="15" title="Short-handed points">SHP</th><th class="r sort-th" data-col="16" title="Overtime goals">OTG</th><th class="r sort-th" data-col="17" title="Game-winning goals">GWG</th><th class="r sort-th" data-col="18" title="Shots on goal">S</th><th class="r sort-th" data-col="19" title="Shooting %: goals ÷ shots on goal">S%</th><th class="r sort-th" data-col="20" title="Average time on ice per game">TOI</th><th class="r sort-th" data-col="21" title="Faceoff win %: faceoffs won ÷ total faceoffs">FO%</th><th class="r sort-th adv-hdr" data-col="22" title="Goals minus expected goals. Positive = scoring more than expected (MoneyPuck)">G-xG</th><th class="r sort-th adv-hdr" data-col="23" title="Expected goals for %: share of expected goals when on ice at 5v5 (MoneyPuck)">xGF%</th><th class="r sort-th adv-hdr" data-col="24" title="GameScore per game: composite rating combining goals, assists, shots, blocks, etc. (MoneyPuck)">GS/GP</th><th class="r sort-th" data-col="25" title="Player age">Age</th><th class="r sort-th" data-col="26" title="Date of birth">Birthday</th><th class="r sort-th" data-col="27" title="Birth city and country">From</th></tr></thead>
<tbody>{"".join(rows)}</tbody></table></div>

<h3 style="margin-top:32px">Goaltenders</h3>
<div class="scroll-x"><table class="nhl-tbl sortable" id="goalie-tbl">
<thead><tr><th class="rank sort-th" data-col="0" title="Rank by games played">#</th><th class="name-col sort-th" data-col="1" title="Player name">Player</th><th class="r sort-th" data-col="2" title="Games played">GP</th><th class="r sort-th" data-col="3" title="Games started">GS</th><th class="r sort-th" data-col="4" title="Wins">W</th><th class="r sort-th" data-col="5" title="Losses">L</th><th class="r sort-th" data-col="6" title="Overtime losses">OT</th><th class="r sort-th" data-col="7" title="Shots against">SA</th><th class="r sort-th" data-col="8" title="Goals against">GA</th><th class="r sort-th" data-col="9" title="Goals against average: goals allowed per 60 minutes">GAA</th><th class="r sort-th" data-col="10" title="Saves: shots faced minus goals allowed">SV</th><th class="r sort-th" data-col="11" title="Save %: saves ÷ shots against">SV%</th><th class="r sort-th" data-col="12" title="Shutouts: games with zero goals allowed">SO</th><th class="r sort-th" data-col="13" title="Total time on ice">TOI</th><th class="r sort-th" data-col="14" title="Player age">Age</th><th class="r sort-th" data-col="15" title="Date of birth">Birthday</th><th class="r sort-th" data-col="16" title="Birth city and country">From</th></tr></thead>
<tbody>{"".join(goalie_rows)}</tbody></table></div>'''

def build_news_html(articles):
    if not articles:
        return '<div class="empty-state"><span>&#128240;</span>No recent news found. Check back later.</div>'
    items = []
    for a in articles:
        items.append(f'''<a href="{a["link"]}" target="_blank" rel="noopener" class="news-item">
<div class="news-meta"><span class="news-source">{a["source"]}</span><span class="news-date">{a["date_str"]} &middot; {a["time_str"]}</span></div>
<div class="news-title">{a["title"]}</div></a>''')
    return f'<div class="news-list">{"".join(items)}</div>'

def build_injuries_html(injuries):
    """Build the injuries tab HTML. injuries is a list of dicts with name, pos, est_return, status, comment."""
    if not injuries:
        return '<div class="empty-state"><span>&#9989;</span>No reported injuries. Full health!</div>'

    rows = []
    for inj in injuries:
        name = inj.get("name", "")
        pos = inj.get("pos", "")
        est_return = inj.get("est_return", "")
        status = inj.get("status", "")
        comment = inj.get("comment", "")

        # Status badge color
        if "out" in status.lower():
            badge_cls = "inj-out"
        elif "day" in status.lower() or "dtd" in status.lower():
            badge_cls = "inj-dtd"
        elif "ir" in status.lower():
            badge_cls = "inj-ir"
        else:
            badge_cls = "inj-other"

        rows.append(f'''<tr>
<td class="inj-name">{name}</td>
<td class="inj-pos">{pos}</td>
<td><span class="inj-badge {badge_cls}">{status}</span></td>
<td class="inj-return">{est_return}</td>
<td class="inj-comment">{comment}</td>
</tr>''')

    return f'''<h3>Current Injuries</h3>
<div class="sub-note">Data from ESPN</div>
<div class="inj-tbl-wrap">
<table class="nhl-tbl inj-tbl sortable">
<thead><tr><th>Player</th><th>Pos</th><th>Status</th><th>Return</th><th>Details</th></tr></thead>
<tbody>{"".join(rows)}</tbody>
</table>
</div>'''

def fetch_transactions():
    """Fetch recent transactions for the current team from ESPN API."""
    espn_id = TEAM_INFO.get(TEAM, {}).get("espn_id", 0)
    if not espn_id:
        return []
    url = f"https://site.api.espn.com/apis/site/v2/sports/hockey/nhl/transactions?team={espn_id}&limit=50"
    data = fetch_json(url)
    txns = []
    for t in data.get("transactions", []):
        date_str = t.get("date", "")
        desc = t.get("description", "")
        if not desc:
            continue
        # Parse date
        display_date = ""
        if date_str:
            try:
                dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
                display_date = dt.strftime("%b %-d")
            except Exception:
                display_date = date_str[:10]
        # Classify transaction type
        dl = desc.lower()
        if "trade" in dl or "acquired" in dl or "in exchange" in dl:
            tx_type = "Trade"
            tx_cls = "tx-trade"
        elif "sign" in dl or "contract" in dl:
            tx_type = "Signing"
            tx_cls = "tx-sign"
        elif "waiver" in dl or "claimed" in dl:
            tx_type = "Waivers"
            tx_cls = "tx-waiver"
        elif "injured reserve" in dl or "long-term" in dl or " ir" in dl:
            tx_type = "IR"
            tx_cls = "tx-ir"
        elif "recalled" in dl or "call" in dl:
            tx_type = "Recall"
            tx_cls = "tx-recall"
        elif "assigned" in dl or "loaned" in dl or "sent" in dl:
            tx_type = "Assignment"
            tx_cls = "tx-assign"
        elif "activated" in dl or "reinstated" in dl:
            tx_type = "Activated"
            tx_cls = "tx-activate"
        else:
            tx_type = "Move"
            tx_cls = "tx-other"
        txns.append({"date": display_date, "desc": desc, "type": tx_type, "cls": tx_cls})
    return txns


def build_transactions_html(txns):
    """Build the transactions tab HTML."""
    if not txns:
        return '<div class="empty-state"><span>&#128221;</span>No recent transactions found.</div>'
    rows = []
    for t in txns:
        rows.append(f'''<div class="tx-row">
<span class="tx-date">{t["date"]}</span>
<span class="tx-badge {t["cls"]}">{t["type"]}</span>
<span class="tx-desc">{t["desc"]}</span>
</div>''')
    return f'''<h3>Transactions</h3>
<div class="sub-note">Data from ESPN &middot; 2025-26 Season</div>
<div class="tx-list">{"".join(rows)}</div>'''


def build_leaders_html(skater_leaders, goalie_leaders):
    """Build the NHL Leaders tab HTML with mini leaderboard cards."""

    def _leader_card(title, players, stat_key, fmt_fn, is_goalie=False):
        """Build a single leaderboard card."""
        rows = []
        for i, p in enumerate(players[:10]):
            rank = i + 1
            if is_goalie:
                name = p.get("goalieFullName", "")
                team = p.get("teamAbbrevs", "")
            else:
                name = p.get("skaterFullName", "")
                team = p.get("teamAbbrevs", "")
            val = fmt_fn(p.get(stat_key, 0))

            # Highlight current team's players
            hl = " ld-hl" if team == TEAM else ""
            headshot_id = p.get("playerId", 0)
            headshot = f"https://cms.nhl.bamgrid.com/images/headshots/current/60x60/{headshot_id}.jpg"

            rows.append(f'''<div class="ld-row{hl}">
<span class="ld-rank">{rank}</span>
<img src="{headshot}" class="ld-headshot" onerror="this.style.display='none'">
<div class="ld-info"><a href="https://www.hockeydb.com/ihdb/stats/find_player.php?full_name={name.replace(" ", "+")}" target="_blank" rel="noopener" class="ld-name">{name}</a><span class="ld-team">{team}</span></div>
<span class="ld-val">{val}</span>
</div>''')
        return f'''<div class="ld-card">
<div class="ld-title">{title}</div>
{"".join(rows)}
</div>'''

    def _fmt_int(v):
        return str(int(v)) if v is not None else "0"

    def _fmt_pm(v):
        v = int(v) if v is not None else 0
        return f"+{v}" if v > 0 else str(v)

    def _fmt_gaa(v):
        return f"{v:.2f}" if v is not None else "0.00"

    def _fmt_svpct(v):
        return f"{v:.3f}" if v is not None else ".000"

    cards = []
    cards.append(_leader_card("Points", skater_leaders.get("points", []), "points", _fmt_int))
    cards.append(_leader_card("Goals", skater_leaders.get("goals", []), "goals", _fmt_int))
    cards.append(_leader_card("Assists", skater_leaders.get("assists", []), "assists", _fmt_int))
    cards.append(_leader_card("Plus/Minus", skater_leaders.get("plusMinus", []), "plusMinus", _fmt_pm))
    cards.append(_leader_card("Wins", goalie_leaders.get("wins", []), "wins", _fmt_int, is_goalie=True))
    cards.append(_leader_card("Goals Against Avg", goalie_leaders.get("gaa", []), "goalsAgainstAverage", _fmt_gaa, is_goalie=True))
    cards.append(_leader_card("Save Pct", goalie_leaders.get("svPct", []), "savePct", _fmt_svpct, is_goalie=True))

    return f'''<h3>Skating Leaders</h3>
<div class="ld-grid">
{cards[0]}
{cards[1]}
{cards[2]}
{cards[3]}
</div>
<h3 style="margin-top:32px">Goaltending Leaders</h3>
<div class="ld-grid">
{cards[4]}
{cards[5]}
{cards[6]}
</div>'''

def build_full_stats_html(full_skaters, full_goalies):
    """Build the Full Stats table HTML with skater/goalie toggle."""
    # Skater rows
    skater_rows = ""
    for i, p in enumerate(full_skaters):
        rank = i + 1
        name = p.get("skaterFullName", "")
        team = p.get("teamAbbrevs", "")
        pos = p.get("positionCode", "")
        gp = p.get("gamesPlayed", 0)
        g = p.get("goals", 0)
        a = p.get("assists", 0)
        pts = p.get("points", 0)
        pm = p.get("plusMinus", 0)
        pm_str = f"+{pm}" if pm > 0 else str(pm)
        pim = p.get("penaltyMinutes", 0)
        ppg = p.get("ppGoals", 0)
        ppa = p.get("ppPoints", 0) - ppg  # ppPoints includes ppGoals
        sog = p.get("shots", 0)
        spct = p.get("shootingPct", 0)
        spct_str = f"{spct*100:.1f}" if spct else "0.0"
        toi_sec = p.get("timeOnIcePerGame", 0)
        toi_min = int(toi_sec // 60)
        toi_rem = int(toi_sec % 60)
        toi_str = f"{toi_min}:{toi_rem:02d}"
        gwg = p.get("gameWinningGoals", 0)
        headshot_id = p.get("playerId", 0)
        headshot = f"https://cms.nhl.bamgrid.com/images/headshots/current/60x60/{headshot_id}.jpg"
        team_href = "index.html" if team == DEFAULT_TEAM else f"{team}.html"

        skater_rows += f'''<tr>
<td class="fs-rank">{rank}</td>
<td class="fs-player"><img src="{headshot}" class="fs-headshot" onerror="this.style.display='none'"><a href="https://www.hockeydb.com/ihdb/stats/find_player.php?full_name={name.replace(" ", "+")}" target="_blank" rel="noopener" class="fs-name">{name}</a><span class="fs-meta"><a href="{team_href}" class="fs-team-link">{team}</a> · {pos}</span></td>
<td>{gp}</td><td class="fs-hl">{g}</td><td class="fs-hl">{a}</td><td class="fs-pts">{pts}</td>
<td>{pm_str}</td><td>{pim}</td><td>{ppg}</td><td>{ppa}</td>
<td>{sog}</td><td>{spct_str}</td><td>{toi_str}</td><td>{gwg}</td>
</tr>'''

    # Goalie rows
    goalie_rows = ""
    for i, p in enumerate(full_goalies):
        rank = i + 1
        name = p.get("goalieFullName", "")
        team = p.get("teamAbbrevs", "")
        gp = p.get("gamesPlayed", 0)
        gs = p.get("gamesStarted", 0)
        w = p.get("wins", 0)
        l = p.get("losses", 0)
        otl = p.get("otLosses", 0)
        ga = p.get("goalsAgainst", 0)
        gaa = p.get("goalsAgainstAverage", 0)
        gaa_str = f"{gaa:.2f}" if gaa else "0.00"
        sa = p.get("shotsAgainst", 0)
        sv = p.get("saves", 0)
        svpct = p.get("savePct", 0)
        svpct_str = f"{svpct:.3f}" if svpct else ".000"
        so = p.get("shutouts", 0)
        headshot_id = p.get("playerId", 0)
        headshot = f"https://cms.nhl.bamgrid.com/images/headshots/current/60x60/{headshot_id}.jpg"
        team_href = "index.html" if team == DEFAULT_TEAM else f"{team}.html"

        goalie_rows += f'''<tr>
<td class="fs-rank">{rank}</td>
<td class="fs-player"><img src="{headshot}" class="fs-headshot" onerror="this.style.display='none'"><a href="https://www.hockeydb.com/ihdb/stats/find_player.php?full_name={name.replace(" ", "+")}" target="_blank" rel="noopener" class="fs-name">{name}</a><span class="fs-meta"><a href="{team_href}" class="fs-team-link">{team}</a></span></td>
<td>{gp}</td><td>{gs}</td><td class="fs-hl">{w}</td><td>{l}</td><td>{otl}</td>
<td>{ga}</td><td class="fs-pts">{gaa_str}</td><td>{sa}</td><td>{sv}</td><td class="fs-pts">{svpct_str}</td><td>{so}</td>
</tr>'''

    return f'''<div class="fs-toggle">
<button class="fs-tab fs-active" onclick="switchFsTab(this,'fs-skaters')">Skating</button>
<button class="fs-tab" onclick="switchFsTab(this,'fs-goalies')">Goaltending</button>
</div>
<div class="fs-panel" id="fs-skaters">
<div class="fs-tbl-wrap"><table class="fs-tbl sortable">
<thead><tr><th class="fs-rank-h">#</th><th class="fs-player-h">Player</th><th>GP</th><th>G</th><th>A</th><th>PTS</th><th>+/-</th><th>PIM</th><th>PPG</th><th>PPA</th><th>SOG</th><th>S%</th><th>TOI/G</th><th>GWG</th></tr></thead>
<tbody>{skater_rows}</tbody>
</table></div>
</div>
<div class="fs-panel" id="fs-goalies" style="display:none">
<div class="fs-tbl-wrap"><table class="fs-tbl sortable">
<thead><tr><th class="fs-rank-h">#</th><th class="fs-player-h">Player</th><th>GP</th><th>GS</th><th>W</th><th>L</th><th>OTL</th><th>GA</th><th>GAA</th><th>SA</th><th>SV</th><th>SV%</th><th>SO</th></tr></thead>
<tbody>{goalie_rows}</tbody>
</table></div>
</div>'''

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
        return f'''<div class="div-label">{name}</div><div class="stnd-card"><div class="scroll-x"><table class="nhl-tbl stnd-tbl sortable">
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
<div class="stnd-card"><div class="scroll-x"><table class="nhl-tbl stnd-tbl sortable">
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
  <div class="kpi"><div class="kpi-val">{target}</div><div class="kpi-label">Playoff Target Pts</div></div>
  <div class="kpi"><div class="kpi-val">{proj_pts:.0f} <span style="font-size:16px;color:{diff_color}">({diff_sign}{proj_diff:.0f})</span></div><div class="kpi-label">Projected Pts</div></div>
  <div class="kpi"><div class="kpi-val">{playoff_pct*100:.0f}%</div><div class="kpi-label">Playoff Odds</div></div>
  <div class="kpi"><div class="kpi-val">{pts}</div><div class="kpi-label">Current Points</div></div>
</div>

<h3>Next Game Impact</h3>
<div class="scroll-x"><table class="nhl-tbl sortable">
<thead><tr><th>Outcome</th><th class="r">Playoffs</th><th class="r">Change</th><th class="r">Proj Pts</th><th class="r">2nd Rd</th><th class="r">Cup</th></tr></thead>
<tbody>{scenario_rows}</tbody></table></div>

<h3 style="margin-top:28px">{conf_name} Conference</h3>
<div class="scroll-x"><table class="nhl-tbl sortable">
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
        game_id = f"sg-{len(cards)}"
        cards.append(f'''<div class="game-card" onclick="openGamePanel('{game_id}')">
<div class="game-summary"><div class="game-left"><span class="game-date">{g["date"]}</span><span class="game-opp">{prefix}{g["opp"]}</span>{tags}</div><div class="game-right"><span class="game-meta">{opp_record} &middot; {o_pts}p</span><span class="game-loc loc-{g["loc"]}">{loc_text}</span></div></div>
</div>
<div class="game-detail-data" id="{game_id}" style="display:none">
  <div class="gp-header"><span class="gp-date">{g["date"]}</span><span class="gp-matchup">{TEAM} {prefix}{g["opp"]}</span><span class="gp-loc">{loc_text}</span></div>
  <ul class="matchup-notes">{notes_html}</ul>
  <table class="cmp-tbl"><thead><tr><th>{TEAM}</th><th></th><th>{opp}</th></tr></thead><tbody>{rows}</tbody></table>
</div>''')

    return f'''<div class="sched-meta">
  <div class="sm-card"><div class="sm-val">{len(remaining)}</div><div class="sm-label">Games Left</div></div>
  <div class="sm-card"><div class="sm-val">{home_count}</div><div class="sm-label">Home</div></div>
  <div class="sm-card"><div class="sm-val">{away_count}</div><div class="sm-label">Away</div></div>
  <div class="sm-card"><div class="sm-val">{above500_count}</div><div class="sm-label">vs .500+</div></div>
</div>
<div class="sched-list">{"".join(cards)}</div>'''

def generate_html(sens, roster_html, projections_html, schedule_html, news_html, injuries_html, transactions_html, vs500, mp_odds, deltas, mp_stats, all_teams):
    team_info = TEAM_INFO.get(TEAM, TEAM_INFO["OTT"])
    team_name = team_info["name"]
    accent = team_info["accent"]
    accent_soft_dark = accent_rgba(accent, 0.12)
    accent_light = darken_hex(accent, 0.85)
    accent_soft_light = accent_rgba(accent, 0.08)
    subreddit = team_info["subreddit"]
    hfboards_url = team_info.get("hfboards", "https://forums.hfboards.com/")

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

    # Conference and division rank
    team_div = TEAM_INFO.get(TEAM, {}).get("div", "")
    team_conf = sens.get("conf", "")
    conf_sorted = sorted([t for t in all_teams if t["conf"] == team_conf], key=lambda x: -x["pts"])
    div_sorted = sorted([t for t in all_teams if t["div"] == team_div], key=lambda x: -x["pts"])
    conf_rank = next((i+1 for i, t in enumerate(conf_sorted) if t["abbrev"] == TEAM), 0)
    div_rank = next((i+1 for i, t in enumerate(div_sorted) if t["abbrev"] == TEAM), 0)

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
:root,:root[data-theme="dark"]{{--bg:#0a0a0b;--bg-surface:rgba(255,255,255,0.035);--bg-elevated:rgba(255,255,255,0.055);--bg-hover:rgba(255,255,255,0.065);--border:rgba(255,255,255,0.08);--border-subtle:rgba(255,255,255,0.05);--text:rgba(255,255,255,0.85);--text-secondary:rgba(255,255,255,0.55);--text-muted:rgba(255,255,255,0.3);--accent:{accent};--accent-soft:{accent_soft_dark};--green:#34d399;--red:#f87171;--card-shadow:0 0 0 1px rgba(255,255,255,0.06);--card-shadow-hover:0 0 0 1px rgba(255,255,255,0.1);--text-strong:rgba(255,255,255,0.95);--ring-bg:rgba(255,255,255,0.06);--alt-row:rgba(255,255,255,0.02);--matchup-bg:rgba(255,255,255,0.02);--tag-bg:rgba(255,255,255,0.06);--tag-dash:rgba(255,255,255,0.1);--amber:#fbbf24;--amber-bg:rgba(251,191,36,0.08);--loc-home-bg:rgba(52,211,153,0.1);--loc-away-bg:rgba(255,255,255,0.03);--tab-active-shadow:none;--tab-hover-bg:rgba(255,255,255,0.04);--hs-bg:rgba(255,255,255,0.06);--footer-link-deco:rgba(255,255,255,0.12)}}
:root[data-theme="light"]{{--bg:#fbfbfc;--bg-surface:rgba(0,0,0,0.03);--bg-elevated:rgba(0,0,0,0.05);--bg-hover:rgba(0,0,0,0.06);--border:rgba(0,0,0,0.1);--border-subtle:rgba(0,0,0,0.06);--text:rgba(0,0,0,0.8);--text-secondary:rgba(0,0,0,0.5);--text-muted:rgba(0,0,0,0.3);--accent:{accent_light};--accent-soft:{accent_soft_light};--green:#059669;--red:#dc2626;--card-shadow:0 0 0 1px rgba(0,0,0,0.06);--card-shadow-hover:0 0 0 1px rgba(0,0,0,0.12);--text-strong:rgba(0,0,0,0.92);--ring-bg:rgba(0,0,0,0.06);--alt-row:rgba(0,0,0,0.02);--matchup-bg:rgba(0,0,0,0.025);--tag-bg:rgba(0,0,0,0.05);--tag-dash:rgba(0,0,0,0.14);--amber:#92400e;--amber-bg:rgba(251,191,36,0.12);--loc-home-bg:rgba(5,150,105,0.08);--loc-away-bg:rgba(0,0,0,0.03);--tab-active-shadow:none;--tab-hover-bg:rgba(0,0,0,0.04);--hs-bg:rgba(0,0,0,0.06);--footer-link-deco:rgba(0,0,0,0.14)}}
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:'Inter',system-ui,-apple-system,sans-serif;background:var(--bg);color:var(--text);line-height:1.55;-webkit-font-smoothing:antialiased;font-feature-settings:'cv02','cv03','cv04','cv11'}}
a{{color:var(--text);text-decoration:none}}
a:hover{{color:var(--text-strong)}}

/* Header */
.header{{max-width:880px;margin:0 auto;padding:32px 28px 0}}
.hdr-top{{display:flex;justify-content:space-between;align-items:center;margin-bottom:24px}}
.hdr-left{{display:flex;align-items:center;gap:14px}}
.team-logo{{width:40px;height:40px;opacity:0.9}}
.header h1{{font-size:18px;font-weight:600;letter-spacing:-0.3px;margin-bottom:0;color:var(--text-strong)}}
.header .subtitle{{font-size:12px;color:var(--text-muted);font-variant-numeric:tabular-nums}}
.live-badge{{display:inline-flex;align-items:center;gap:7px;padding:5px 12px 5px 9px;background:rgba(255,59,48,0.08);border:1px solid rgba(255,59,48,0.2);border-radius:100px;text-decoration:none;margin:10px 0 8px;transition:background 0.2s,border-color 0.2s}}
.live-badge:hover{{background:rgba(255,59,48,0.13);border-color:rgba(255,59,48,0.32)}}
.live-dot{{width:6px;height:6px;border-radius:50%;background:#ff3b30;flex-shrink:0;animation:liveDot 1.6s ease-in-out infinite}}
@keyframes liveDot{{0%,100%{{transform:scale(1);opacity:1}}50%{{transform:scale(0.55);opacity:0.45}}}}
.live-word{{font-size:10px;font-weight:700;letter-spacing:0.07em;text-transform:uppercase;color:#ff3b30}}
.live-sep{{width:1px;height:11px;background:rgba(255,59,48,0.22);flex-shrink:0}}
.live-info{{font-size:12px;font-weight:500;color:var(--text-secondary)}}
.hdr-pct{{text-align:right}}
.pct-val{{font-size:28px;font-weight:700;letter-spacing:-1.5px;line-height:1;color:var(--text)}}
.pct-label{{display:block;font-size:9px;color:var(--text-muted);text-transform:uppercase;letter-spacing:1px;margin-top:6px;font-weight:500}}
.delta{{display:inline-block;font-size:11px;font-weight:600;margin-left:4px;vertical-align:middle}}
@media(max-width:600px){{
.topbar-inner{{padding:0 12px}}
.topbar-tab{{padding:12px 10px;font-size:11px}}
.team-select{{font-size:10px;padding:4px 22px 4px 8px}}
.header{{padding:20px 16px 0}}
.team-logo{{width:32px;height:32px}}
.header h1{{font-size:15px}}
.hdr-left{{gap:10px}}
.pct-val{{font-size:22px}}
.pct-label{{font-size:8px}}
.stat-row{{gap:4px;padding-bottom:16px}}
.stat-pill{{padding:4px 8px;font-size:10px}}
.stat-pill .sl{{font-size:8px}}
.container{{padding:0 16px 40px}}
.tab-bar{{overflow-x:auto;-webkit-overflow-scrolling:touch;scrollbar-width:none;width:auto}}
.tab-bar::-webkit-scrollbar{{display:none}}
.tab-bar label{{padding:9px 11px;font-size:11px}}
.kpi-row{{gap:6px;margin-bottom:20px}}
.kpi{{min-width:70px;padding:12px 8px}}
.kpi-val{{font-size:20px}}
.kpi-label{{font-size:8px;margin-top:5px}}
.nhl-tbl thead th{{padding:8px 5px;font-size:8px}}
.nhl-tbl td{{padding:6px 5px;font-size:11px}}
.stnd-tbl td{{padding:5px 4px;font-size:10px}}
.stnd-tbl thead th{{padding:6px 4px;font-size:8px}}
a.pname{{font-size:11px}}
.hs{{width:24px;height:24px}}
.name-cell{{padding-left:2px}}
.name-flex{{gap:6px}}
.sched-meta{{gap:6px}}
.sm-card{{padding:12px 6px;min-width:60px}}
.sm-val{{font-size:18px}}
.sm-label{{font-size:8px;margin-top:5px}}
.game-summary{{padding:10px 12px}}
.game-left{{gap:8px}}
.game-date{{font-size:10px;min-width:38px}}
.game-opp{{font-size:12px}}
.game-right{{gap:6px}}
.game-meta{{font-size:10px}}
.game-tag{{font-size:8px;padding:1px 5px;margin-left:4px}}
.game-panel{{width:100%}}
.game-panel .panel-body{{padding:8px 16px 20px}}
.cmp-tbl{{font-size:11px}}
.cmp-tbl thead th{{padding:6px 4px;font-size:9px}}
.cmp-tbl td{{padding:5px 4px}}
.matchup-notes li{{font-size:10px;padding:5px 10px}}
.news-title{{font-size:12px}}
.news-item{{padding:10px 12px}}
.inj-tbl td{{font-size:11px}}
.inj-comment{{max-width:120px}}
.inj-badge{{font-size:9px;padding:2px 6px}}
.odds-ring{{width:60px;height:60px}}
.odds-ring svg{{width:60px;height:60px}}
.odds-ring .ring-val{{font-size:14px}}
.odds-ring .ring-label{{font-size:7px}}
.footer{{padding:24px 16px}}
}}

.stat-row{{display:flex;gap:6px;flex-wrap:wrap;padding-bottom:24px;margin-bottom:0}}
.stat-pill{{display:inline-flex;align-items:center;gap:5px;padding:5px 10px;background:var(--bg-surface);border-radius:6px;font-size:11px;white-space:nowrap;transition:background 0.15s ease}}
.stat-pill:hover{{background:var(--bg-elevated)}}
.stat-pill .sl{{color:var(--text-muted);font-size:9px;text-transform:uppercase;letter-spacing:0.5px;font-weight:500}}
.stat-pill .sv{{font-weight:600;color:var(--text)}}
.pill-accent{{background:var(--accent-soft)}}.pill-accent .sv{{color:var(--accent);font-weight:700}}

/* Tabs */
.container{{max-width:880px;margin:0 auto;padding:0 28px 60px}}
input[name="tab"]{{display:none}}
.tab-bar{{display:flex;gap:0;margin-bottom:32px;border-bottom:1px solid var(--border)}}
.tab-bar label{{padding:10px 14px;font-size:12px;font-weight:500;color:var(--text-muted);cursor:pointer;transition:color 0.15s ease;white-space:nowrap;position:relative;border-bottom:2px solid transparent;margin-bottom:-1px}}
.tab-bar label:hover{{color:var(--text-secondary)}}
.panel{{display:none}}
#tab-roster:checked~.tab-bar label[for="tab-roster"],
#tab-playoffs:checked~.tab-bar label[for="tab-playoffs"],
#tab-schedule:checked~.tab-bar label[for="tab-schedule"],
#tab-injuries:checked~.tab-bar label[for="tab-injuries"],
#tab-transactions:checked~.tab-bar label[for="tab-transactions"],
#tab-news:checked~.tab-bar label[for="tab-news"],
#tab-forums:checked~.tab-bar label[for="tab-forums"]{{color:var(--text-strong);font-weight:600;border-bottom-color:var(--text-strong)}}
#tab-roster:checked~#p-roster,
#tab-playoffs:checked~#p-playoffs,
#tab-schedule:checked~#p-schedule,
#tab-injuries:checked~#p-injuries,
#tab-transactions:checked~#p-transactions,
#tab-news:checked~#p-news,
#tab-forums:checked~#p-forums{{display:block}}

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
.bio-col{{white-space:nowrap;font-size:11px;color:var(--text-muted)}}
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
.kpi-row{{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:28px}}
.kpi{{flex:1;min-width:90px;padding:18px 14px;background:var(--bg-surface);border-radius:8px;text-align:center;border:1px solid var(--border);transition:border-color 0.15s ease}}
.kpi:hover{{border-color:var(--border)}}
.kpi-val{{font-size:26px;font-weight:700;letter-spacing:-1.5px;line-height:1;color:var(--text-strong)}}
.kpi-label{{font-size:9px;color:var(--text-muted);margin-top:7px;text-transform:uppercase;letter-spacing:0.8px;font-weight:500}}

/* Scenario impact */
.sc-label{{font-weight:600;white-space:nowrap;color:var(--text)}}
.sc-up{{color:var(--green);font-weight:600}}
.sc-down{{color:var(--red);font-weight:600}}
.footnote{{margin-top:36px;font-size:11px;color:var(--text-muted)}}

/* Schedule */
.sched-meta{{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:24px}}
.sm-card{{flex:1;min-width:70px;text-align:center;padding:16px 10px;background:var(--bg-surface);border-radius:8px;border:1px solid var(--border)}}
.sm-val{{font-size:22px;font-weight:700;line-height:1;color:var(--text-strong);letter-spacing:-0.5px}}
.sm-label{{font-size:9px;color:var(--text-muted);text-transform:uppercase;letter-spacing:0.8px;margin-top:7px;font-weight:500}}
.sched-list{{display:flex;flex-direction:column;gap:4px}}
.game-card{{border-radius:8px;overflow:hidden;cursor:pointer}}
.game-tag{{font-size:9px;font-weight:600;padding:2px 7px;border-radius:4px;margin-left:6px;letter-spacing:0.3px;vertical-align:middle}}
.tag-playoff{{color:var(--text-muted);background:var(--tag-bg)}}
.tag-desperate{{color:var(--amber);background:var(--amber-bg)}}
.tag-sellers{{color:var(--text-muted);background:transparent;border:1px dashed var(--tag-dash)}}
.tag-hot{{color:var(--text-strong);background:var(--accent)}}
.game-summary{{display:flex;justify-content:space-between;align-items:center;padding:11px 14px;cursor:pointer;background:var(--bg-surface);border-radius:8px;border:1px solid var(--border);transition:all 0.15s ease}}
.game-summary:hover{{background:var(--bg-elevated)}}
.game-left{{display:flex;align-items:center;gap:12px}}
.game-date{{font-size:11px;color:var(--text-muted);min-width:44px;font-weight:500;font-variant-numeric:tabular-nums}}
.game-opp{{font-size:13px;font-weight:600;color:var(--text)}}
.game-right{{display:flex;align-items:center;gap:10px}}
.game-meta{{font-size:11px;color:var(--text-muted)}}
.game-loc{{font-size:9px;font-weight:600;padding:3px 8px;border-radius:20px;letter-spacing:0.3px}}
.loc-home{{background:var(--loc-home-bg);color:var(--green)}}
.loc-away{{background:var(--loc-away-bg);color:var(--text-muted)}}
/* Game side panel */
.game-overlay{{position:fixed;inset:0;background:rgba(0,0,0,0.5);z-index:100;opacity:0;pointer-events:none;transition:opacity 0.2s ease}}
.game-overlay.open{{opacity:1;pointer-events:auto}}
.game-panel{{position:fixed;top:0;right:0;bottom:0;width:min(440px,90vw);background:var(--bg);z-index:101;transform:translateX(100%);transition:transform 0.25s cubic-bezier(0.16,1,0.3,1);overflow-y:auto;border-left:1px solid var(--border)}}
.game-panel.open{{transform:translateX(0)}}
.game-panel .panel-close{{display:flex;justify-content:flex-end;padding:12px 16px 0}}
.game-panel .panel-close-btn{{background:none;border:none;color:var(--text-muted);cursor:pointer;padding:6px;border-radius:6px}}
.game-panel .panel-close-btn:hover{{background:var(--bg-elevated);color:var(--text)}}
.game-panel .panel-body{{padding:8px 20px 24px}}
.gp-header{{display:flex;flex-direction:column;gap:4px;margin-bottom:16px;padding-bottom:12px;border-bottom:1px solid var(--border)}}
.gp-date{{font-size:11px;color:var(--text-muted);font-weight:500}}
.gp-matchup{{font-size:16px;font-weight:700;color:var(--text-strong);letter-spacing:-0.3px}}
.gp-loc{{font-size:11px;color:var(--text-muted)}}
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
.news-item{{display:block;padding:12px 14px;border-radius:6px;text-decoration:none;transition:background 0.15s ease}}
.news-item:hover{{background:var(--bg-hover);text-decoration:none}}
.news-meta{{display:flex;justify-content:space-between;align-items:center;margin-bottom:5px}}
.news-source{{font-size:9px;font-weight:600;text-transform:uppercase;letter-spacing:0.8px;color:var(--text-muted)}}
.news-date{{font-size:10px;color:var(--text-muted)}}
.news-title{{font-size:13px;font-weight:500;color:var(--text);line-height:1.45}}

/* Community */
.community-list{{display:grid;grid-template-columns:1fr 1fr;gap:10px}}
@media(max-width:560px){{.community-list{{grid-template-columns:1fr}}}}
.community-card{{display:block;padding:18px;background:var(--bg-surface);border-radius:8px;text-decoration:none;border:1px solid var(--border);transition:all 0.15s ease}}
.community-card:hover{{background:var(--bg-elevated);text-decoration:none}}
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
.stnd-card{{background:var(--bg-surface);border-radius:8px;border:1px solid var(--border);padding:4px 0;margin-bottom:8px;overflow:hidden}}
.stnd-card .scroll-x{{padding:0}}
.stnd-card .nhl-tbl thead th{{background:transparent}}

/* Community / Forums icons */
.cc-icon{{width:20px;height:20px;border-radius:4px;flex-shrink:0;opacity:0.85}}
.cc-head{{display:flex;align-items:center;gap:8px;margin-bottom:6px}}

/* Transactions */
.tx-list{{display:flex;flex-direction:column;gap:0}}
.tx-row{{display:flex;align-items:flex-start;gap:10px;padding:10px 0;border-bottom:1px solid var(--border)}}
.tx-row:last-child{{border-bottom:none}}
.tx-date{{font-size:11px;color:var(--text-muted);min-width:44px;flex-shrink:0;padding-top:1px}}
.tx-badge{{font-size:10px;font-weight:600;padding:2px 7px;border-radius:4px;white-space:nowrap;flex-shrink:0;text-transform:uppercase;letter-spacing:0.3px}}
.tx-trade{{background:rgba(232,56,79,0.15);color:#e8384f}}
.tx-sign{{background:rgba(0,166,81,0.15);color:#00a651}}
.tx-waiver{{background:rgba(244,125,48,0.15);color:#f47d30}}
.tx-ir{{background:rgba(232,178,48,0.15);color:#e8b230}}
.tx-recall{{background:rgba(107,159,255,0.15);color:#6b9fff}}
.tx-assign{{background:rgba(160,160,160,0.15);color:var(--text-muted)}}
.tx-activate{{background:rgba(0,166,81,0.15);color:#00a651}}
.tx-other{{background:rgba(160,160,160,0.15);color:var(--text-muted)}}
.tx-desc{{font-size:12px;color:var(--text-secondary);line-height:1.5}}

/* Mobile tabs — handled in 600px breakpoint above */

/* Standings sub-toggle */
.stnd-toggle input[type="radio"]{{display:none}}
.stnd-toggle-bar{{display:flex;gap:0;margin-bottom:20px;border-bottom:1px solid var(--border);width:fit-content}}
.stnd-toggle-bar label{{padding:8px 14px;font-size:11px;font-weight:500;color:var(--text-muted);cursor:pointer;transition:color 0.15s ease;white-space:nowrap;border-bottom:2px solid transparent;margin-bottom:-1px}}
.stnd-toggle-bar label:hover{{color:var(--text-secondary)}}
.sv-conf,.sv-wc{{display:none}}
#sv-conf:checked~.sv-conf{{display:block}}
#sv-wc:checked~.sv-wc{{display:block}}
#sv-conf:checked~.stnd-toggle-bar label[for="sv-conf"],#sv-wc:checked~.stnd-toggle-bar label[for="sv-wc"]{{color:var(--text-strong);font-weight:600;border-bottom-color:var(--text-strong)}}

/* Empty state */
.empty-state{{text-align:center;padding:48px 20px;color:var(--text-muted);font-size:13px}}
.empty-state span{{display:block;font-size:28px;margin-bottom:12px;opacity:0.4}}

/* Injuries */
.inj-tbl-wrap{{overflow-x:auto;border-radius:8px}}
.inj-tbl td{{font-size:12px}}
.inj-name{{font-weight:600;color:var(--text)}}
.inj-pos{{color:var(--text-muted);font-size:11px}}
.inj-badge{{font-size:10px;font-weight:600;padding:2px 8px;border-radius:4px;white-space:nowrap;display:inline-block}}
.inj-out{{background:rgba(248,113,113,0.12);color:var(--red)}}
.inj-ir{{background:rgba(248,113,113,0.12);color:var(--red)}}
.inj-dtd{{background:rgba(251,191,36,0.12);color:#fbbf24}}
.inj-other{{background:var(--bg-surface);color:var(--text-secondary)}}
.inj-return{{font-size:11px;color:var(--text-secondary)}}
.inj-comment{{font-size:11px;color:var(--text-muted);max-width:200px}}

/* NHL Leaders */


/* Footer */
.footer{{text-align:center;padding:36px 28px;font-size:11px;color:var(--text-muted);max-width:880px;margin:0 auto}}
.footer a{{color:var(--text-muted);text-decoration:underline;text-decoration-color:var(--footer-link-deco);text-underline-offset:2px}}.footer a:hover{{color:var(--text-secondary)}}
.footer-ts{{display:block;margin-top:6px;font-size:10px;color:var(--text-muted);opacity:0.7}}

/* Page transition */
@keyframes fadeIn{{from{{opacity:0}}to{{opacity:1}}}}
body{{animation:fadeIn 0.15s ease}}

/* Top bar */
.topbar{{position:sticky;top:0;z-index:50;background:var(--bg);border-bottom:1px solid var(--border);backdrop-filter:blur(12px);-webkit-backdrop-filter:blur(12px)}}
.topbar-inner{{max-width:1200px;margin:0 auto;padding:0 28px;display:flex;align-items:center;justify-content:space-between;height:44px}}
.topbar-left{{display:flex;align-items:center;gap:0}}
.topbar-tab{{font-size:12px;font-weight:500;color:var(--text-muted);padding:12px 14px;text-decoration:none;transition:color 0.15s;position:relative;height:44px;display:flex;align-items:center}}.topbar-tab:hover{{color:var(--text-secondary)}}.topbar-tab.active{{color:var(--text-strong);font-weight:600}}.topbar-tab.active::after{{content:"";position:absolute;bottom:0;left:14px;right:14px;height:2px;background:var(--text-strong);border-radius:1px}}
.topbar-right{{display:flex;align-items:center;gap:6px}}
.team-select{{appearance:none;-webkit-appearance:none;background:transparent;color:var(--text-secondary);border:1px solid var(--border);border-radius:6px;padding:5px 26px 5px 10px;font-size:11px;font-family:inherit;font-weight:500;cursor:pointer;transition:all 0.15s ease;background-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='10' height='6'%3E%3Cpath d='M0 0l5 6 5-6z' fill='%239898a0'/%3E%3C/svg%3E");background-repeat:no-repeat;background-position:right 8px center}}
.team-select:hover{{border-color:rgba(255,255,255,0.15);color:var(--text)}}
.team-select:focus{{outline:none;border-color:var(--accent)}}
.team-select optgroup{{font-weight:600;color:var(--text-muted)}}
.team-select option{{background:var(--bg);color:var(--text)}}

/* Theme toggle */
.theme-toggle{{display:flex;gap:1px;padding:1px;border:1px solid var(--border);border-radius:6px}}
.theme-btn{{display:flex;align-items:center;justify-content:center;width:26px;height:24px;border:none;background:transparent;color:var(--text-muted);cursor:pointer;border-radius:5px;transition:all 0.15s ease;padding:0}}.theme-btn:hover{{color:var(--text-secondary)}}
.theme-btn.active{{color:var(--text-strong);background:var(--bg-elevated)}}
</style></head><body>

<script>localStorage.setItem('lastTeamPage',location.pathname.split('/').pop()||'index.html')</script>
<div class="topbar">
  <div class="topbar-inner">
    <div class="topbar-left">
      <a href="scores.html" class="topbar-tab">Scores</a>
      <span class="topbar-tab active">Teams</span>
      <a href="standings.html" class="topbar-tab">Standings</a>
      <a href="leaders.html" class="topbar-tab">Stats</a>
    </div>
    <div class="topbar-right">
      <select class="team-select" onchange="if(this.value)window.location.href=this.value">{switcher_opts}</select>
      <div class="theme-toggle">
        <button class="theme-btn" data-theme="light" title="Light" aria-label="Light theme"><svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5"><circle cx="8" cy="8" r="3"/><path d="M8 1.5v2M8 12.5v2M1.5 8h2M12.5 8h2M3.4 3.4l1.4 1.4M11.2 11.2l1.4 1.4M3.4 12.6l1.4-1.4M11.2 4.8l1.4-1.4" stroke-linecap="round"/></svg></button>
        <button class="theme-btn" data-theme="dark" title="Dark" aria-label="Dark theme"><svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M13 8.5A5.5 5.5 0 017 3a6 6 0 00.2-1.5A6 6 0 1013.5 9a5 5 0 01-.5-.5z" stroke-linecap="round" stroke-linejoin="round"/></svg></button>
      </div>
    </div>
  </div>
</div>

<div class="header">
  <div class="hdr-top">
    <div class="hdr-left">
      <img src="https://assets.nhle.com/logos/nhl/svg/{TEAM}_dark.svg" alt="{team_name}" class="team-logo">
      <div>
        <h1>{team_name}</h1>
        <a href="scores.html" id="live-badge" class="live-badge" style="display:none"><span class="live-dot"></span><span class="live-word">Live</span><span class="live-sep"></span><span class="live-info" id="live-info"></span></a>
        <div class="subtitle">Updated {now}</div>
      </div>
    </div>
  </div>
  <div class="stat-row">
    <a href="standings.html" class="stat-pill pill-accent" title="{ordinal(conf_rank)} in {team_conf} Conference, {ordinal(div_rank)} in {team_div} Division"><span class="sl">Conf</span> <span class="sv">{ordinal(conf_rank)}</span></a>
    <a href="standings.html" class="stat-pill" title="{ordinal(div_rank)} in {team_div} Division"><span class="sl">{team_div}</span> <span class="sv">{ordinal(div_rank)}</span></a>
    <span class="stat-pill" title="MoneyPuck playoff probability"><span class="sl">Playoff Odds</span> <span class="sv">{playoff_pct*100:.0f}%</span></span>
    <span class="stat-pill"><span class="sl">Record</span> <span class="sv">{record}</span></span>
    <span class="stat-pill"><span class="sl">L10</span> <span class="sv">{l10}</span></span>
    <span class="stat-pill" title="Record against teams at or above .500"><span class="sl">vs .500</span> <span class="sv">{vs500_str}</span></span>
    <span class="stat-pill" title="Goals scored minus goals allowed"><span class="sl">Diff</span> <span class="sv">{goal_diff_str}</span></span>
    <span class="stat-pill" title="Power play — {ordinal(pp_rank)} in NHL"><span class="sl">PP</span> <span class="sv">{pp_pct}%</span></span>
    <span class="stat-pill" title="Penalty kill — {ordinal(pk_rank)} in NHL"><span class="sl">PK</span> <span class="sv">{pk_pct}%</span></span>
  </div>
</div>

<div class="container">
  <input type="radio" name="tab" id="tab-schedule" checked>
  <input type="radio" name="tab" id="tab-playoffs">
  <input type="radio" name="tab" id="tab-roster">
  <input type="radio" name="tab" id="tab-injuries">
  <input type="radio" name="tab" id="tab-transactions">
  <input type="radio" name="tab" id="tab-news">
  <input type="radio" name="tab" id="tab-forums">
  <div class="tab-bar">
    <label for="tab-schedule">Remaining Games</label>
    <label for="tab-playoffs">Playoff Odds</label>
    <label for="tab-roster">Player Stats</label>
    <label for="tab-injuries">Injuries</label>
    <label for="tab-transactions">Transactions</label>
    <label for="tab-news">News</label>
    <label for="tab-forums">Forums</label>
  </div>
  <div class="panel" id="p-schedule">{schedule_html}</div>
  <div class="panel" id="p-playoffs">{projections_html}</div>
  <div class="panel" id="p-roster">{roster_html}</div>
  <div class="panel" id="p-injuries">{injuries_html}</div>
  <div class="panel" id="p-transactions">{transactions_html}</div>
  <div class="panel" id="p-news">{news_html}</div>
  <div class="panel" id="p-forums">
    <div class="community-list">
      <a href="https://www.reddit.com/r/{subreddit}/" target="_blank" rel="noopener" class="community-card"><div class="cc-head"><img src="https://www.google.com/s2/favicons?domain=reddit.com&sz=64" alt="" class="cc-icon"><div class="cc-name">r/{subreddit}</div></div><div class="cc-desc">Reddit community. Memes, highlights, post-game threads, and fan takes.</div></a>
      <a href="{hfboards_url}" target="_blank" rel="noopener" class="community-card"><div class="cc-head"><img src="https://www.google.com/s2/favicons?domain=hfboards.com&sz=64" alt="" class="cc-icon"><div class="cc-name">HFBoards — {team_name}</div></div><div class="cc-desc">The longest-running hockey forum. Trade talk, game threads, prospect discussions.</div></a>
    </div>
  </div>
</div>
<div class="game-overlay" id="gameOverlay" onclick="closeGamePanel()"></div>
<div class="game-panel" id="gamePanel">
  <div class="panel-close"><button class="panel-close-btn" onclick="closeGamePanel()" aria-label="Close"><svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"><path d="M4 4l8 8M12 4l-8 8"/></svg></button></div>
  <div class="panel-body" id="gamePanelBody"></div>
</div>
<div class="footer">Data from NHL API &amp; <a href="https://moneypuck.com">MoneyPuck</a><span class="footer-ts">Updated {now}</span></div>
<script>
document.querySelectorAll('table.sortable').forEach(function(tbl){{
  tbl.querySelectorAll('thead th').forEach(function(th,idx){{
    th.classList.add('sort-th');
    th.addEventListener('click',function(){{
      var asc=th.classList.contains('asc');
      tbl.querySelectorAll('thead th').forEach(function(h){{h.classList.remove('asc','desc')}});
      var dir=asc?'desc':'asc';
      th.classList.add(dir);
      var tbody=tbl.querySelector('tbody');
      var rows=Array.from(tbody.querySelectorAll('tr'));
      rows.sort(function(a,b){{
        var ca=a.children[idx],cb=b.children[idx];
        var va=ca?(ca.hasAttribute('data-sort')?ca.dataset.sort:ca.textContent.trim()):'';
        var vb=cb?(cb.hasAttribute('data-sort')?cb.dataset.sort:cb.textContent.trim()):'';
        var na=parseFloat(va),nb=parseFloat(vb);
        if(!isNaN(na)&&!isNaN(nb))return dir==='asc'?na-nb:nb-na;
        return dir==='asc'?va.localeCompare(vb):vb.localeCompare(va);
      }});
      rows.forEach(function(r){{tbody.appendChild(r)}});
    }});
  }});
}});
</script>
<script>
(function(){{
  function swapLogos(theme){{
    document.querySelectorAll('img[src*="nhle.com/logos"]').forEach(function(img){{
      if(theme==='light'){{img.src=img.src.replace('_dark.svg','_light.svg');}}
      else{{img.src=img.src.replace('_light.svg','_dark.svg');}}
    }});
  }}
  var root=document.documentElement;
  var btns=document.querySelectorAll('.theme-btn');
  var saved=localStorage.getItem('theme')||'dark';
  swapLogos(saved);
  btns.forEach(function(b){{
    if(b.dataset.theme===saved) b.classList.add('active');
    b.addEventListener('click',function(){{
      var t=b.dataset.theme;
      root.setAttribute('data-theme',t);
      localStorage.setItem('theme',t);
      btns.forEach(function(x){{x.classList.remove('active')}});
      b.classList.add('active');
      swapLogos(t);
    }});
  }});
}})();
</script>
<script>
function openGamePanel(id){{
  var src=document.getElementById(id);
  if(!src) return;
  document.getElementById('gamePanelBody').innerHTML=src.innerHTML;
  document.getElementById('gamePanel').classList.add('open');
  document.getElementById('gameOverlay').classList.add('open');
  document.body.style.overflow='hidden';
}}
function closeGamePanel(){{
  document.getElementById('gamePanel').classList.remove('open');
  document.getElementById('gameOverlay').classList.remove('open');
  document.body.style.overflow='';
}}
document.addEventListener('keydown',function(e){{if(e.key==='Escape')closeGamePanel()}});
</script>
<script>
(function(){{
  var team='{TEAM}';
  function nhlFetch(url){{
    var e=encodeURIComponent(url);
    function tryProxy(base){{
      return fetch(base+e).then(function(r){{if(!r.ok)throw new Error(r.status);return r.json();}});
    }}
    // Race both proxies — resolve with whichever responds first successfully
    return new Promise(function(resolve,reject){{
      var done=false,errs=0;
      var proxies=['https://api.allorigins.win/raw?url=','https://corsproxy.io/?'];
      proxies.forEach(function(base){{
        tryProxy(base)
          .then(function(d){{if(!done){{done=true;resolve(d);}}}} )
          .catch(function(){{if(++errs===proxies.length&&!done)reject(new Error('all proxies failed'));}});
      }});
    }});
  }}
  function checkLive(){{
    nhlFetch('https://api-web.nhle.com/v1/score/now')
      .then(function(data){{
        var games=data.games||[];
        for(var i=0;i<games.length;i++){{
          var g=games[i];
          var st=g.gameState||'';
          if((st==='LIVE'||st==='CRIT')&&(g.awayTeam.abbrev===team||g.homeTeam.abbrev===team)){{
            var badge=document.getElementById('live-badge');
            if(badge){{
              var away=g.awayTeam.abbrev,home=g.homeTeam.abbrev;
              var as=g.awayTeam.score||0,hs=g.homeTeam.score||0;
              var per=g.periodDescriptor||{{}};
              var clk=g.clock||{{}};
              var pn=per.number||0;
              var tr=clk.timeRemaining||'';
              var ords={{1:'1st',2:'2nd',3:'3rd'}};
              var pstr=clk.inIntermission?'End of '+(ords[pn]||'P'+pn):per.periodType==='OT'?'OT '+tr:per.periodType==='SO'?'Shootout':(ords[pn]||'P'+pn)+' '+tr;
              var info=document.getElementById('live-info');
              if(info)info.textContent=away+' '+as+'\u2013'+hs+' '+home+'\u00a0\u00b7\u00a0'+pstr;
              badge.href='scores.html?game='+g.id;
              badge.style.display='inline-flex';
            }}
            return;
          }}
        }}
      }})
      .catch(function(){{}});
  }}
  checkLive();
  setInterval(checkLive,30000);
}})();
</script>
</body></html>'''

# ── Scoreboard ────────────────────────────────────────────

def _build_game_card(g, all_game_details, eastern, team_records=None, mp_stats=None, mp_odds=None):
    """Build a single game card HTML. Returns the card HTML string."""
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
        ordinals = {1: "1st", 2: "2nd", 3: "3rd"}
        in_intermission = clock.get("inIntermission", False)
        if in_intermission:
            status = f"End of {ordinals.get(period_num, f'P{period_num}')}"
        elif period_type == "OT":
            status = f"OT {time_remaining}"
        elif period_type == "SO":
            status = "Shootout"
        else:
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

        # Box score tables with team toggle
        boxscore = details.get("boxscore")
        box_html = ""
        if boxscore:
            team_panels = []
            team_tabs = []
            for idx, (side, side_label) in enumerate([("awayTeam", away_abbrev), ("homeTeam", home_abbrev)]):
                team_data = boxscore.get(side, {})
                side_name = away_full if side == "awayTeam" else home_full
                active_cls = " bx-active" if idx == 0 else ""

                team_tabs.append(f'<button class="bx-tab{active_cls}" data-bx="{idx}" onclick="switchBoxTab(this)">'
                                 f'<img src="https://assets.nhle.com/logos/nhl/svg/{side_label}_dark.svg" class="bx-tab-logo">'
                                 f'{side_name}</button>')

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

                display = "" if idx == 0 else ' style="display:none"'
                team_panels.append(f'''<div class="bx-panel" data-bx="{idx}"{display}>
<div class="gd-tbl-wrap"><table class="gd-tbl"><thead><tr><th>Skater</th><th>Pos</th><th>G</th><th>A</th><th>P</th><th>+/-</th><th>SOG</th><th>HIT</th><th>BLK</th><th>TOI</th></tr></thead><tbody>{skater_rows}</tbody></table></div>
<div class="gd-tbl-wrap"><table class="gd-tbl gd-goalie-tbl"><thead><tr><th>Goalie</th><th>Saves</th><th>SV%</th><th>TOI</th></tr></thead><tbody>{goalie_rows}</tbody></table></div>
</div>''')

            box_html = f'''<div class="bx-tabs">{"".join(team_tabs)}</div>
{"".join(team_panels)}'''

        if scoring_html or box_html:
            detail_html = f'''<div class="gd-data" id="gd-{game_id}" style="display:none">
<div class="gd-panel-header">
<div class="gd-panel-teams">
<img src="https://assets.nhle.com/logos/nhl/svg/{away_abbrev}_dark.svg" class="gd-panel-logo"><span>{away_full}</span>
<span class="gd-panel-vs">vs</span>
<img src="https://assets.nhle.com/logos/nhl/svg/{home_abbrev}_dark.svg" class="gd-panel-logo"><span>{home_full}</span>
</div>
<div class="gd-panel-score"><span class="gd-panel-score-val">{away_score} — {home_score}</span><span class="gd-panel-status">{status}</span></div>
</div>
{f'<div class="gd-section"><div class="gd-section-title">Scoring Summary</div>{scoring_html}</div>' if scoring_html else ''}
{f'<div class="gd-section"><div class="gd-section-title">Box Score</div>{box_html}</div>' if box_html else ''}
</div>'''

    # ── Preview panel for upcoming games ──
    if not detail_html and state in ("FUT", "PRE") and team_records:
        away_rec = team_records.get(away_abbrev, {})
        home_rec = team_records.get(home_abbrev, {})
        fmt_r = lambda w, l, o: f"{w}-{l}-{o}"

        a_record = fmt_r(away_rec.get("w",0), away_rec.get("l",0), away_rec.get("otl",0))
        h_record = fmt_r(home_rec.get("w",0), home_rec.get("l",0), home_rec.get("otl",0))
        a_pts = away_rec.get("pts", 0)
        h_pts = home_rec.get("pts", 0)
        a_home = fmt_r(away_rec.get("homeW",0), away_rec.get("homeL",0), away_rec.get("homeOtl",0))
        h_home = fmt_r(home_rec.get("homeW",0), home_rec.get("homeL",0), home_rec.get("homeOtl",0))
        a_away = fmt_r(away_rec.get("roadW",0), away_rec.get("roadL",0), away_rec.get("roadOtl",0))
        h_away = fmt_r(home_rec.get("roadW",0), home_rec.get("roadL",0), home_rec.get("roadOtl",0))
        a_l10 = fmt_r(away_rec.get("l10w",0), away_rec.get("l10l",0), away_rec.get("l10otl",0))
        h_l10 = fmt_r(home_rec.get("l10w",0), home_rec.get("l10l",0), home_rec.get("l10otl",0))
        a_gf = away_rec.get("gf", 0)
        h_gf = home_rec.get("gf", 0)
        a_ga = away_rec.get("ga", 0)
        h_ga = home_rec.get("ga", 0)
        a_gp = away_rec.get("gp", 1) or 1
        h_gp = home_rec.get("gp", 1) or 1

        def prow(label, v_a, v_h):
            return f'<tr><td class="cmp-stat-l">{v_a}</td><td class="cmp-stat-label">{label}</td><td class="cmp-stat-r">{v_h}</td></tr>'

        cmp_rows = (prow("Record", a_record, h_record) + prow("PTS", a_pts, h_pts)
                    + prow("Home", a_home, h_home) + prow("Away", a_away, h_away)
                    + prow("L10", a_l10, h_l10) + prow("GF", a_gf, h_gf) + prow("GA", a_ga, h_ga))

        # Insights
        notes = []
        pts_gap = abs(a_pts - h_pts)
        if pts_gap <= 3:
            notes.append(f"Separated by only {pts_gap} pts — a direct rival")
        elif a_pts > h_pts:
            notes.append(f"{away_abbrev} holds a {pts_gap}-pt lead")
        else:
            notes.append(f"{home_abbrev} holds a {pts_gap}-pt lead")

        if mp_odds:
            for abbr, label in [(away_abbrev, away_abbrev), (home_abbrev, home_abbrev)]:
                po = mp_odds.get(abbr, {}).get("ALL", {}).get("playoffPct", 0)
                if po >= 0.95:
                    notes.append(f"{label} is a virtual lock for playoffs ({po*100:.0f}%)")
                elif po >= 0.6:
                    notes.append(f"{label} projected for playoffs ({po*100:.0f}%)")
                elif po >= 0.2:
                    notes.append(f"{label} on the bubble ({po*100:.0f}%)")
                elif po > 0:
                    notes.append(f"{label} fading — {po*100:.0f}% playoff odds")

        a_gfpg = round(a_gf / a_gp, 1)
        h_gfpg = round(h_gf / h_gp, 1)
        combined = round(a_gfpg + h_gfpg, 1)
        if combined >= 6.6:
            notes.append(f"High-scoring matchup — combined {combined} goals/game avg")
        elif combined <= 5.2:
            notes.append(f"Low-scoring matchup — combined {combined} goals/game avg")

        for abbr, rec in [(away_abbrev, away_rec), (home_abbrev, home_rec)]:
            l10w = rec.get("l10w", 0)
            l10_str = fmt_r(rec.get("l10w",0), rec.get("l10l",0), rec.get("l10otl",0))
            if l10w >= 7:
                notes.append(f"{abbr} is hot — {l10_str} in last 10")
            elif l10w <= 3:
                notes.append(f"{abbr} is cold — {l10_str} in last 10")

        notes_html = "".join(f'<li>{n}</li>' for n in notes[:5])

        detail_html = f'''<div class="gd-data" id="gd-{game_id}" style="display:none">
<div class="gd-panel-header">
<div class="gd-panel-teams">
<img src="https://assets.nhle.com/logos/nhl/svg/{away_abbrev}_dark.svg" class="gd-panel-logo"><span>{away_full}</span>
<span class="gd-panel-vs">@</span>
<img src="https://assets.nhle.com/logos/nhl/svg/{home_abbrev}_dark.svg" class="gd-panel-logo"><span>{home_full}</span>
</div>
<div class="gd-panel-score"><span class="gd-panel-status">{status}</span></div>
</div>
<div class="gd-section"><div class="gd-section-title">Game Preview</div>
<ul class="pv-notes">{notes_html}</ul>
<table class="cmp-tbl"><thead><tr><th>{away_abbrev}</th><th></th><th>{home_abbrev}</th></tr></thead><tbody>{cmp_rows}</tbody></table>
</div>
</div>'''

    has_detail = f' data-game="{game_id}"' if detail_html else ""
    clickable_cls = " sb-clickable" if detail_html else ""

    return f'''<div class="sb-game{clickable_cls}" id="game-{game_id}"{has_detail if detail_html else ""} data-gid="{game_id}" data-away="{away_abbrev}" data-home="{home_abbrev}" data-state="{state}">
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
</div>'''


def build_scoreboard_html(all_days_scores, today_date_str, all_game_details, switcher_opts, team_records=None, mp_stats=None, mp_odds=None):
    """Generate a standalone scoreboard page with date navigation (7 days back + today + 7 days forward)."""
    eastern = timezone(timedelta(hours=-5))
    now = datetime.now(eastern).strftime("%B %-d, %Y at %-I:%M %p ET")

    # Build date strip buttons and per-day game sections
    date_btns = []
    day_sections = []
    DAY_NAMES = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

    for date_str, scores_data in all_days_scores:
        games = scores_data.get("games", [])
        is_today = date_str == today_date_str
        n_games = len(games)

        # Format date for button
        try:
            d = datetime.strptime(date_str, "%Y-%m-%d")
            day_name = DAY_NAMES[d.weekday()]
            month_day = d.strftime("%b %-d")
            display_full = d.strftime("%A, %B %-d, %Y")
        except Exception:
            day_name = ""
            month_day = date_str
            display_full = date_str

        active_cls = " ds-active" if is_today else ""
        today_dot = '<span class="ds-today-dot"></span>' if is_today else ""
        count_badge = f'<span class="ds-count">{n_games}</span>' if n_games > 0 else '<span class="ds-count ds-none">0</span>'
        date_btns.append(f'<button class="ds-btn{active_cls}" data-date="{date_str}" onclick="showDay(\'{date_str}\')">'
                         f'<span class="ds-day">{day_name}</span>'
                         f'<span class="ds-date">{month_day}</span>'
                         f'{today_dot}{count_badge}</button>')

        # Build game cards for this day — live games first, then upcoming, then final
        def _game_sort_key(g):
            s = g.get("gameState", "")
            if s in ("LIVE", "CRIT"): return 0
            elif s in ("FUT", "PRE"): return 1
            else: return 2
        game_cards = []
        for g in sorted(games, key=_game_sort_key):
            game_cards.append(_build_game_card(g, all_game_details, eastern, team_records, mp_stats, mp_odds))

        display_style = "" if is_today else ' style="display:none"'
        if game_cards:
            games_html = "\n".join(game_cards)
        else:
            games_html = '<div class="sb-empty">No games scheduled.</div>'

        day_sections.append(f'<div class="sb-day" id="day-{date_str}"{display_style}>'
                            f'<div class="sb-day-label">{display_full}</div>'
                            f'{games_html}</div>')

    date_strip_html = "\n".join(date_btns)
    days_html = "\n".join(day_sections)

    return f'''<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>NHL Scoreboard</title>
<script>document.documentElement.setAttribute('data-theme',localStorage.getItem('theme')||'dark')</script>
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin><link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>
:root,:root[data-theme="dark"]{{--bg:#0a0a0b;--bg-surface:rgba(255,255,255,0.035);--bg-elevated:rgba(255,255,255,0.055);--bg-hover:rgba(255,255,255,0.065);--border:rgba(255,255,255,0.08);--text:rgba(255,255,255,0.85);--text-secondary:rgba(255,255,255,0.55);--text-muted:rgba(255,255,255,0.3);--accent:#e8384f;--green:#34d399;--red:#f87171;--text-strong:rgba(255,255,255,0.95);--footer-link-deco:rgba(255,255,255,0.12);--panel-bg:#111113;--overlay:rgba(0,0,0,0.6)}}
:root[data-theme="light"]{{--bg:#fbfbfc;--bg-surface:rgba(0,0,0,0.03);--bg-elevated:rgba(0,0,0,0.05);--bg-hover:rgba(0,0,0,0.06);--border:rgba(0,0,0,0.1);--text:rgba(0,0,0,0.8);--text-secondary:rgba(0,0,0,0.5);--text-muted:rgba(0,0,0,0.3);--accent:#c8102e;--green:#059669;--red:#dc2626;--text-strong:rgba(0,0,0,0.92);--footer-link-deco:rgba(0,0,0,0.14);--panel-bg:#fff;--overlay:rgba(0,0,0,0.2)}}
*{{margin:0;padding:0;box-sizing:border-box}}
@keyframes fadeIn{{from{{opacity:0}}to{{opacity:1}}}}
body{{font-family:'Inter',system-ui,-apple-system,sans-serif;background:var(--bg);color:var(--text);line-height:1.5;-webkit-font-smoothing:antialiased;animation:fadeIn 0.15s ease}}
a{{color:var(--text);text-decoration:none}}

/* Top bar */
.topbar{{position:sticky;top:0;z-index:50;background:var(--bg);border-bottom:1px solid var(--border);backdrop-filter:blur(12px);-webkit-backdrop-filter:blur(12px)}}
.topbar-inner{{max-width:1200px;margin:0 auto;padding:0 28px;display:flex;align-items:center;justify-content:space-between;height:44px}}
.topbar-left{{display:flex;align-items:center;gap:0}}
.topbar-tab{{font-size:12px;font-weight:500;color:var(--text-muted);padding:12px 14px;text-decoration:none;transition:color 0.15s;position:relative;height:44px;display:flex;align-items:center}}.topbar-tab:hover{{color:var(--text-secondary)}}.topbar-tab.active{{color:var(--text-strong);font-weight:600}}.topbar-tab.active::after{{content:"";position:absolute;bottom:0;left:14px;right:14px;height:2px;background:var(--text-strong);border-radius:1px}}
.topbar-right{{display:flex;align-items:center;gap:6px}}
.team-select{{appearance:none;-webkit-appearance:none;background:transparent;color:var(--text-secondary);border:1px solid var(--border);border-radius:6px;padding:5px 26px 5px 10px;font-size:11px;font-family:inherit;font-weight:500;cursor:pointer;transition:all 0.15s ease;background-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='10' height='6'%3E%3Cpath d='M0 0l5 6 5-6z' fill='%239898a0'/%3E%3C/svg%3E");background-repeat:no-repeat;background-position:right 8px center}}.team-select:hover{{border-color:rgba(255,255,255,0.15);color:var(--text)}}.team-select:focus{{outline:none;border-color:var(--accent)}}.team-select optgroup{{font-weight:600;color:var(--text-muted)}}.team-select option{{background:var(--bg);color:var(--text)}}
.theme-toggle{{display:flex;gap:1px;padding:1px;border:1px solid var(--border);border-radius:6px}}
.theme-btn{{display:flex;align-items:center;justify-content:center;width:26px;height:24px;border:none;background:transparent;color:var(--text-muted);cursor:pointer;border-radius:5px;transition:all 0.15s ease;padding:0}}.theme-btn:hover{{color:var(--text-secondary)}}
.theme-btn.active{{color:var(--text-strong);background:var(--bg-elevated)}}

/* Date strip */
.date-strip-wrap{{max-width:700px;margin:0 auto;padding:16px 0 0;-webkit-mask-image:linear-gradient(to right,transparent,black 28px,black calc(100% - 28px),transparent);mask-image:linear-gradient(to right,transparent,black 28px,black calc(100% - 28px),transparent)}}
.date-strip{{display:flex;gap:4px;overflow-x:auto;scrollbar-width:none;-ms-overflow-style:none;padding:6px 20px 10px;scroll-snap-type:x proximity}}
.date-strip::-webkit-scrollbar{{display:none}}
.ds-btn{{display:flex;flex-direction:column;align-items:center;gap:2px;padding:9px 13px;border:1px solid transparent;background:transparent;border-radius:10px;cursor:pointer;transition:all 0.15s;min-width:58px;position:relative;flex-shrink:0;scroll-snap-align:start}}
.ds-btn:hover{{background:var(--bg-surface);border-color:var(--border)}}
.ds-btn.ds-active{{background:var(--bg-elevated);border-color:var(--border)}}
.ds-day{{font-size:10px;font-weight:500;color:var(--text-muted);text-transform:uppercase;letter-spacing:0.4px}}
.ds-date{{font-size:13px;font-weight:600;color:var(--text-secondary)}}
.ds-active .ds-day{{color:var(--accent)}}
.ds-active .ds-date{{color:var(--text-strong)}}
.ds-today-dot{{width:4px;height:4px;border-radius:50%;background:var(--accent);margin-top:2px}}
.ds-count{{font-size:9px;font-weight:600;color:var(--text-muted);margin-top:2px}}
.ds-none{{opacity:0.35}}

/* Scoreboard header */
.sb-header{{max-width:700px;margin:0 auto;padding:20px 28px 0}}
.sb-header h1{{font-size:18px;font-weight:600;letter-spacing:-0.3px;color:var(--text-strong)}}

/* Day label */
.sb-day{{display:flex;flex-direction:column;gap:8px}}
.sb-day-label{{font-size:12px;font-weight:500;color:var(--text-muted)}}

/* Game grid */
.sb-grid{{max-width:700px;margin:0 auto;padding:16px 28px 60px;display:flex;flex-direction:column;gap:8px}}

.sb-game{{background:var(--bg-surface);border-radius:10px;border:1px solid var(--border);overflow:hidden;transition:border-color 0.15s ease}}
.sb-game:hover{{border-color:rgba(255,255,255,0.12)}}
.sb-clickable{{cursor:pointer}}
.sb-clickable .sb-matchup:hover{{background:var(--bg-hover)}}

.sb-status{{padding:7px 14px;font-size:9px;font-weight:600;text-transform:uppercase;letter-spacing:0.8px;color:var(--text-muted);border-bottom:1px solid var(--border)}}
.sb-live{{color:var(--red);animation:pulse 2s ease-in-out infinite}}
.sb-final{{color:var(--text-muted)}}
.sb-upcoming{{color:var(--text-secondary)}}
@keyframes pulse{{0%,100%{{opacity:1}}50%{{opacity:0.5}}}}

.sb-matchup{{transition:background 0.15s}}
.sb-team-row{{display:flex;align-items:center;padding:10px 14px;gap:12px;color:var(--text)}}
.sb-team-row+.sb-team-row{{border-top:1px solid var(--border)}}
.sb-team-link{{flex-shrink:0;line-height:0}}.sb-team-link:hover{{opacity:0.8}}
.sb-logo{{width:32px;height:32px}}
.sb-team-info{{flex:1;min-width:0}}
.sb-team-name{{font-size:13px;font-weight:600;color:var(--text-secondary)}}
.sb-winner .sb-team-name{{color:var(--text-strong)}}
.sb-winner .sb-score{{color:var(--text-strong)}}
.sb-scorers{{display:flex;flex-wrap:wrap;gap:4px;margin-top:2px}}
.sb-scorer{{font-size:10px;color:var(--text-muted);font-weight:500}}
.sb-scorer+.sb-scorer::before{{content:"\\00b7 ";margin-right:0}}
.sb-score{{font-size:24px;font-weight:700;letter-spacing:-1px;color:var(--text-muted);min-width:32px;text-align:right;font-variant-numeric:tabular-nums}}

.sb-empty{{text-align:center;padding:48px 20px;color:var(--text-muted);font-size:13px}}

/* Side panel */
.panel-overlay{{position:fixed;inset:0;background:var(--overlay);z-index:100;opacity:0;pointer-events:none;transition:opacity 0.2s ease}}
.panel-overlay.open{{opacity:1;pointer-events:auto}}
.side-panel{{position:fixed;top:0;right:0;bottom:0;width:min(480px,90vw);background:var(--panel-bg);z-index:101;transform:translateX(100%);transition:transform 0.25s cubic-bezier(0.16,1,0.3,1);overflow-y:auto;border-left:1px solid var(--border)}}
.side-panel.open{{transform:translateX(0)}}
.panel-close{{position:sticky;top:0;display:flex;justify-content:flex-end;padding:14px 18px 6px;background:var(--panel-bg);z-index:1}}
.panel-close-btn{{width:28px;height:28px;border:none;background:transparent;color:var(--text-muted);border-radius:6px;cursor:pointer;display:flex;align-items:center;justify-content:center;transition:all 0.15s}}.panel-close-btn:hover{{color:var(--text)}}
.panel-body{{padding:0 22px 28px}}

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

/* Box score team toggle */
.bx-tabs{{display:flex;gap:0;border-bottom:1px solid var(--border);margin-bottom:12px}}
.bx-tab{{display:flex;align-items:center;gap:6px;padding:8px 14px;border:none;background:transparent;color:var(--text-muted);font-size:12px;font-weight:500;font-family:inherit;cursor:pointer;transition:color 0.15s;position:relative;border-bottom:2px solid transparent;margin-bottom:-1px}}
.bx-tab:hover{{color:var(--text-secondary)}}
.bx-tab.bx-active{{color:var(--text-strong);font-weight:600;border-bottom-color:var(--text-strong)}}
.bx-tab-logo{{width:18px;height:18px}}
.gd-box-team{{margin-bottom:16px}}.gd-box-team:last-child{{margin-bottom:0}}
.gd-box-team-name{{font-size:12px;font-weight:600;color:var(--text);margin-bottom:8px}}
.gd-tbl-wrap{{overflow-x:auto;margin-bottom:8px;border-radius:8px}}
.gd-tbl{{width:100%;border-collapse:collapse;font-size:11px;font-variant-numeric:tabular-nums}}
.gd-tbl th{{padding:6px 6px;font-size:9px;font-weight:600;text-transform:uppercase;letter-spacing:0.4px;color:var(--text-muted);text-align:left;white-space:nowrap;border-bottom:1px solid var(--border);background:var(--bg-surface)}}
.gd-tbl td{{padding:5px 6px;color:var(--text-secondary);white-space:nowrap;border-bottom:1px solid var(--border)}}
.gd-tbl tbody tr:hover td{{background:var(--bg-hover)}}
.gd-pts-hl{{color:var(--text-strong) !important;font-weight:600}}

/* Game preview comparison */
.pv-notes{{list-style:none;padding:0;margin:0 0 16px;font-size:11px;color:var(--text-secondary);line-height:1.5}}
.pv-notes li{{padding:5px 10px;background:var(--bg-surface);border-radius:6px;margin-bottom:3px;font-weight:500}}
.cmp-tbl{{width:100%;border-collapse:collapse;font-size:12px}}
.cmp-tbl thead th{{font-size:10px;font-weight:600;padding:8px 8px;border-bottom:1px solid var(--border);color:var(--text-secondary);text-transform:uppercase;letter-spacing:0.5px}}
.cmp-tbl thead th:first-child{{text-align:left}}
.cmp-tbl thead th:last-child{{text-align:right}}
.cmp-tbl td{{padding:6px 8px;border-bottom:1px solid var(--border);color:var(--text-secondary)}}
.cmp-stat-l{{font-weight:600;text-align:left;color:var(--text)}}
.cmp-stat-label{{text-align:center;font-size:10px;color:var(--text-muted);text-transform:uppercase;letter-spacing:0.5px;font-weight:500}}
.cmp-stat-r{{font-weight:600;text-align:right;color:var(--text)}}

.footer{{text-align:center;padding:36px 28px;font-size:11px;color:var(--text-muted);max-width:700px;margin:0 auto}}
.footer a{{color:var(--text-muted);text-decoration:underline;text-decoration-color:var(--footer-link-deco);text-underline-offset:2px}}.footer a:hover{{color:var(--text-secondary)}}
.footer-ts{{display:block;margin-top:6px;font-size:10px;color:var(--text-muted);opacity:0.7}}

@media(max-width:600px){{
.topbar-inner{{padding:0 12px}}
.topbar-tab{{padding:12px 10px;font-size:11px}}
.team-select{{font-size:10px;padding:4px 22px 4px 8px}}
.date-strip-wrap{{padding:12px 0 0}}
.date-strip{{padding:4px 14px 8px}}
.ds-btn{{padding:7px 10px;min-width:50px}}
.ds-day{{font-size:9px}}
.ds-date{{font-size:12px}}
.sb-header{{padding:16px 16px 0}}
.sb-header h1{{font-size:16px}}
.sb-logo{{width:26px;height:26px}}
.sb-score{{font-size:20px}}
.sb-team-name{{font-size:12px}}
.sb-team-row{{padding:8px 12px;gap:10px}}
.sb-grid{{padding:12px 16px 40px;gap:6px}}
.sb-status{{padding:6px 12px;font-size:8px}}
.sb-scorers{{gap:2px;margin-top:1px}}
.sb-scorer{{font-size:9px}}
.side-panel{{width:100%}}
.panel-body{{padding:0 16px 24px}}
.gd-panel-teams span{{font-size:12px}}
.gd-panel-score{{font-size:20px}}
.gd-tbl th{{padding:5px 4px;font-size:8px}}
.gd-tbl td{{padding:4px 4px;font-size:10px}}
.bx-tab{{padding:7px 10px;font-size:11px;gap:4px}}
.bx-tab-logo{{width:16px;height:16px}}
.pv-notes li{{font-size:10px;padding:4px 8px}}
.cmp-tbl{{font-size:11px}}
.cmp-tbl thead th{{padding:6px 4px;font-size:9px}}
.cmp-tbl td{{padding:5px 4px}}
.gd-goal{{gap:6px;padding:5px 0}}
.gd-time{{font-size:10px;min-width:34px}}
.gd-headshot{{width:22px;height:22px}}
.gd-scorer-name{{font-size:11px}}
.gd-assists{{font-size:9px}}
.footer{{padding:24px 16px}}
}}
</style></head><body>

<div class="topbar">
  <div class="topbar-inner">
    <div class="topbar-left">
      <span class="topbar-tab active">Scores</span>
      <a href="index.html" class="topbar-tab" onclick="var p=localStorage.getItem('lastTeamPage');if(p){{window.location.href=p;return false}}">Teams</a>
      <a href="standings.html" class="topbar-tab">Standings</a>
      <a href="leaders.html" class="topbar-tab">Stats</a>
    </div>
    <div class="topbar-right">
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
</div>

<div class="sb-header">
  <h1>NHL Scoreboard</h1>
</div>

<div class="date-strip-wrap">
  <div class="date-strip" id="dateStrip">
    {date_strip_html}
  </div>
</div>

<div class="sb-grid">
{days_html}
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
  function swapLogos(theme){{
    document.querySelectorAll('img[src*="nhle.com/logos"]').forEach(function(img){{
      if(theme==='light'){{img.src=img.src.replace('_dark.svg','_light.svg');}}
      else{{img.src=img.src.replace('_light.svg','_dark.svg');}}
    }});
  }}
  var root=document.documentElement;
  var btns=document.querySelectorAll('.theme-btn');
  var saved=localStorage.getItem('theme')||'dark';
  swapLogos(saved);
  btns.forEach(function(b){{
    if(b.dataset.theme===saved) b.classList.add('active');
    b.addEventListener('click',function(){{
      var t=b.dataset.theme;
      root.setAttribute('data-theme',t);
      localStorage.setItem('theme',t);
      btns.forEach(function(x){{x.classList.remove('active')}});
      b.classList.add('active');
      swapLogos(t);
    }});
  }});
}})();

// Date navigation
function showDay(dateStr){{
  document.querySelectorAll('.sb-day').forEach(function(el){{el.style.display='none'}});
  document.querySelectorAll('.ds-btn').forEach(function(el){{el.classList.remove('ds-active')}});
  var target=document.getElementById('day-'+dateStr);
  if(target) target.style.display='';
  var btn=document.querySelector('.ds-btn[data-date="'+dateStr+'"]');
  if(btn) btn.classList.add('ds-active');
}}

// Scroll date strip to center today on load
(function(){{
  var strip=document.getElementById('dateStrip');
  var active=strip.querySelector('.ds-active');
  if(active && strip){{
    var offset=active.offsetLeft-strip.offsetWidth/2+active.offsetWidth/2;
    strip.scrollLeft=offset;
  }}
}})();

// Keyboard nav: left/right arrows to switch days
document.addEventListener('keydown',function(e){{
  if(e.target.tagName==='INPUT'||e.target.tagName==='SELECT'||e.target.tagName==='TEXTAREA') return;
  if(e.key==='ArrowLeft'||e.key==='ArrowRight'){{
    var btns=Array.from(document.querySelectorAll('.ds-btn'));
    var idx=btns.findIndex(function(b){{return b.classList.contains('ds-active')}});
    if(idx<0) return;
    var next=e.key==='ArrowLeft'?idx-1:idx+1;
    if(next>=0&&next<btns.length){{
      showDay(btns[next].dataset.date);
      btns[next].scrollIntoView({{behavior:'smooth',block:'nearest',inline:'center'}});
    }}
  }}
}});

function switchBoxTab(btn){{
  var container=btn.closest('.gd-section');
  if(!container) container=btn.closest('.panel-body')||btn.parentElement.parentElement;
  var idx=btn.dataset.bx;
  container.querySelectorAll('.bx-tab').forEach(function(t){{t.classList.remove('bx-active')}});
  container.querySelectorAll('.bx-panel').forEach(function(p){{p.style.display='none'}});
  btn.classList.add('bx-active');
  var target=container.querySelector('.bx-panel[data-bx="'+idx+'"]');
  if(target) target.style.display='';
}}

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
<script>
(function(){{
  // Find today's date from the button with the today-dot marker
  var todayBtn=document.querySelector('.ds-today-dot');
  var TODAY=todayBtn?todayBtn.closest('.ds-btn').dataset.date:'';
  if(!TODAY) return;

  // Track whether all today's games are final so we can slow down polling
  var allFinal=false;

  // Real-time clock: maps gameId -> {{secs, fetchedAt, pNum, pType, inIntermission}}
  var liveClocks={{}};
  function parseClockSecs(tr){{var p=(tr||'').split(':');return p.length===2?parseInt(p[0]||0)*60+parseInt(p[1]||0):0;}}
  function fmtSecs(s){{if(s<0)s=0;var m=Math.floor(s/60),r=s%60;return m+':'+(r<10?'0':'')+r;}}

  // NHL API doesn't send CORS headers, so we need a proxy for browser fetches
  function nhlFetch(url){{
    var e=encodeURIComponent(url);
    function tryProxy(base){{
      return fetch(base+e).then(function(r){{if(!r.ok)throw new Error(r.status);return r.json();}});
    }}
    // Race both proxies — resolve with whichever responds first successfully
    return new Promise(function(resolve,reject){{
      var done=false,errs=0;
      var proxies=['https://api.allorigins.win/raw?url=','https://corsproxy.io/?'];
      proxies.forEach(function(base){{
        tryProxy(base)
          .then(function(d){{if(!done){{done=true;resolve(d);}}}} )
          .catch(function(){{if(++errs===proxies.length&&!done)reject(new Error('all proxies failed'));}});
      }});
    }});
  }}

  function isViewingToday(){{
    var active=document.querySelector('.ds-btn.ds-active');
    return active&&active.dataset.date===TODAY;
  }}

  function refreshScores(){{
    // Always fetch today's scores via /score/now (most reliable, includes current game states)
    // Append timestamp so the CORS proxy never serves a cached response
    nhlFetch('https://api-web.nhle.com/v1/score/now?_='+Date.now())
      .then(function(data){{
        var games=data.games||[];
        var hasLive=false;
        var hasFut=false;
        for(var i=0;i<games.length;i++){{
          var g=games[i];
          var gid=g.id;
          var card=document.querySelector('[data-gid="'+gid+'"]');
          if(!card) continue;
          var prevState=card.getAttribute('data-state');
          var st=g.gameState||'';
          card.setAttribute('data-state',st);

          var statusEl=card.querySelector('.sb-status');
          var rows=card.querySelectorAll('.sb-team-row');
          var scores=card.querySelectorAll('.sb-score');

          // Update scores for any non-future game
          if(st!=='FUT'&&st!=='PRE'){{
            var aS=g.awayTeam.score!=null?g.awayTeam.score:0;
            var hS=g.homeTeam.score!=null?g.homeTeam.score:0;
            if(scores[0]) scores[0].textContent=aS;
            if(scores[1]) scores[1].textContent=hS;
          }}

          // Update goal scorer chips
          var goalArr=g.goals||[];
          if(goalArr.length>0){{
            var awaySc={{}},homeSc={{}};
            var awayAbbr=card.getAttribute('data-away');
            var homeAbbr=card.getAttribute('data-home');
            for(var j=0;j<goalArr.length;j++){{
              var gl=goalArr[j];
              var sn=gl.name;if(typeof sn==='object')sn=sn['default']||'';
              var ta=gl.teamAbbrev;if(typeof ta==='object')ta=ta['default']||'';
              if(ta===awayAbbr)awaySc[sn]=(awaySc[sn]||0)+1;
              else if(ta===homeAbbr)homeSc[sn]=(homeSc[sn]||0)+1;
            }}
            function buildChips(obj){{
              var h='';for(var n in obj){{
                var c=obj[n]>1?' ('+obj[n]+')':'';
                h+='<span class="sb-scorer">'+n+c+'</span>';
              }}return h;
            }}
            var scorerEls=card.querySelectorAll('.sb-scorers');
            if(scorerEls[0])scorerEls[0].innerHTML=buildChips(awaySc);
            if(scorerEls[1])scorerEls[1].innerHTML=buildChips(homeSc);
          }}

          // Update status text
          if(statusEl){{
            var per=g.periodDescriptor||{{}};
            var pType=per.periodType||'REG';
            var pNum=per.number||0;
            var clk=g.clock||{{}};
            var tr=clk.timeRemaining||'';
            if(st==='FINAL'||st==='OFF'){{
              var txt=pType==='OT'?'Final/OT':pType==='SO'?'Final/SO':'Final';
              statusEl.className='sb-status sb-final';
              statusEl.textContent=txt;
              var aScore=g.awayTeam.score||0,hScore=g.homeTeam.score||0;
              if(rows[0])rows[0].className='sb-team-row'+(aScore>hScore?' sb-winner':'');
              if(rows[1])rows[1].className='sb-team-row'+(hScore>aScore?' sb-winner':'');
              var dp=document.getElementById('gd-'+gid);
              if(dp){{var sv=dp.querySelector('.gd-panel-score-val');var pst=dp.querySelector('.gd-panel-status');if(sv)sv.textContent=aScore+' \u2014 '+hScore;if(pst)pst.textContent=txt;}}
            }} else if(st==='LIVE'||st==='CRIT'){{
              hasLive=true;
              var ords={{1:'1st',2:'2nd',3:'3rd'}};
              var inInt=!!(clk.inIntermission);
              var txt=inInt?'End of '+(ords[pNum]||'P'+pNum):pType==='OT'?'OT '+tr:pType==='SO'?'Shootout':(ords[pNum]||'P'+pNum)+' '+tr;
              statusEl.className='sb-status sb-live';
              statusEl.textContent=txt;
              if(rows[0])rows[0].className='sb-team-row';
              if(rows[1])rows[1].className='sb-team-row';
              liveClocks[gid]={{secs:clk.secondsRemaining!=null?clk.secondsRemaining:parseClockSecs(tr),pNum:pNum,pType:pType,inIntermission:!!(clk.inIntermission),running:!!(clk.running)}};
              var dp=document.getElementById('gd-'+gid);
              if(dp){{var sv=dp.querySelector('.gd-panel-score-val');var pst=dp.querySelector('.gd-panel-status');if(sv)sv.textContent=aS+' \u2014 '+hS;if(pst)pst.textContent=txt;}}

            }} else if(st==='FUT'||st==='PRE'){{
              hasFut=true;
            }}
          }}
        }}
        // Adjust polling rate: 15s when live, 60s when waiting for games, stop when all done
        allFinal=!hasLive&&!hasFut;
        if(allFinal&&pollTimer){{
          clearInterval(pollTimer);
          pollTimer=null;
        }} else if(hasLive&&pollInterval!==15000){{
          clearInterval(pollTimer);
          pollInterval=15000;
          pollTimer=setInterval(refreshScores,pollInterval);
        }} else if(!hasLive&&hasFut&&pollInterval!==60000){{
          clearInterval(pollTimer);
          pollInterval=60000;
          pollTimer=setInterval(refreshScores,pollInterval);
        }}
        // Re-sort today's game cards: live first, then upcoming, then final
        if(hasLive){{
          var dayEl=document.getElementById('day-'+TODAY);
          if(dayEl){{
            var stOrd={{'LIVE':0,'CRIT':0,'FUT':1,'PRE':1,'FINAL':2,'OFF':2}};
            var cards=Array.from(dayEl.querySelectorAll('.sb-game'));
            cards.sort(function(a,b){{
              var sa=stOrd[a.getAttribute('data-state')];if(sa==null)sa=99;
              var sb=stOrd[b.getAttribute('data-state')];if(sb==null)sb=99;
              return sa-sb;
            }});
            cards.forEach(function(c){{dayEl.appendChild(c);}});
          }}
        }}
      }})
      .catch(function(){{}});
  }}

  // Start polling — 15s if any games already live, 60s if just future games
  var hasLiveNow=document.querySelector('[data-state="LIVE"],[data-state="CRIT"]');
  var pollInterval=hasLiveNow?15000:60000;
  var pollTimer=setInterval(refreshScores,pollInterval);

  // 1-second ticker: counts down live clocks — pauses when clock.running is false (stoppages)
  setInterval(function(){{
    for(var gid in liveClocks){{
      var c=liveClocks[gid];
      if(c.inIntermission||!c.running) continue;
      var card=document.querySelector('[data-gid="'+gid+'"]');
      if(!card) continue;
      var st=card.getAttribute('data-state');
      if(st!=='LIVE'&&st!=='CRIT'){{delete liveClocks[gid];continue;}}
      c.secs=Math.max(0,c.secs-1);
      var statusEl=card.querySelector('.sb-status');
      if(!statusEl) continue;
      var ords={{1:'1st',2:'2nd',3:'3rd'}};
      var txt=c.pType==='OT'?'OT '+fmtSecs(c.secs):c.pType==='SO'?'Shootout':(ords[c.pNum]||'P'+c.pNum)+' '+fmtSecs(c.secs);
      statusEl.textContent=txt;
      var dp=document.getElementById('gd-'+gid);
      if(dp){{var pst=dp.querySelector('.gd-panel-status');if(pst)pst.textContent=txt;}}
    }}
  }},1000);

  // Also refresh immediately on page load (data may be stale from build)
  refreshScores();

  // Open a specific game panel if URL contains ?game={id}
  (function(){{
    var params=new URLSearchParams(window.location.search);
    var gameId=params.get('game');
    if(gameId){{
      setTimeout(function(){{
        var target=document.getElementById('game-'+gameId);
        if(target){{
          target.scrollIntoView({{behavior:'smooth',block:'center'}});
          target.style.transition='box-shadow 0.4s ease';
          target.style.boxShadow='0 0 0 2px rgba(255,59,48,0.55),0 0 20px rgba(255,59,48,0.12)';
          setTimeout(function(){{target.style.boxShadow='';target.style.transition='';}},2200);
        }}
        if(typeof openPanel==='function')openPanel(gameId);
      }},600);
    }}
  }})();
}})();
</script>
</body></html>'''

def build_leaders_page(skater_leaders, goalie_leaders, full_skaters, full_goalies, switcher_opts):
    """Generate a standalone NHL Leaders page with Leaders and Full Stats views."""
    eastern = timezone(timedelta(hours=-5))
    now = datetime.now(eastern).strftime("%B %-d, %Y at %-I:%M %p ET")

    leaders_html = build_leaders_html(skater_leaders, goalie_leaders)
    full_stats_html = build_full_stats_html(full_skaters, full_goalies)

    return f'''<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>NHL Stats</title>
<script>document.documentElement.setAttribute('data-theme',localStorage.getItem('theme')||'dark')</script>
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin><link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>
:root,:root[data-theme="dark"]{{--bg:#0a0a0b;--bg-surface:rgba(255,255,255,0.035);--bg-elevated:rgba(255,255,255,0.055);--bg-hover:rgba(255,255,255,0.065);--border:rgba(255,255,255,0.08);--text:rgba(255,255,255,0.85);--text-secondary:rgba(255,255,255,0.55);--text-muted:rgba(255,255,255,0.3);--accent:#e8384f;--green:#34d399;--red:#f87171;--text-strong:rgba(255,255,255,0.95);--footer-link-deco:rgba(255,255,255,0.12)}}
:root[data-theme="light"]{{--bg:#fbfbfc;--bg-surface:rgba(0,0,0,0.03);--bg-elevated:rgba(0,0,0,0.05);--bg-hover:rgba(0,0,0,0.06);--border:rgba(0,0,0,0.1);--text:rgba(0,0,0,0.8);--text-secondary:rgba(0,0,0,0.5);--text-muted:rgba(0,0,0,0.3);--accent:#c8102e;--green:#059669;--red:#dc2626;--text-strong:rgba(0,0,0,0.92);--footer-link-deco:rgba(0,0,0,0.14)}}
*{{margin:0;padding:0;box-sizing:border-box}}
@keyframes fadeIn{{from{{opacity:0}}to{{opacity:1}}}}
body{{font-family:'Inter',system-ui,-apple-system,sans-serif;background:var(--bg);color:var(--text);line-height:1.5;-webkit-font-smoothing:antialiased;animation:fadeIn 0.15s ease}}
a{{color:var(--text);text-decoration:none}}

/* Top bar */
.topbar{{position:sticky;top:0;z-index:50;background:var(--bg);border-bottom:1px solid var(--border);backdrop-filter:blur(12px);-webkit-backdrop-filter:blur(12px)}}
.topbar-inner{{max-width:1200px;margin:0 auto;padding:0 28px;display:flex;align-items:center;justify-content:space-between;height:44px}}
.topbar-left{{display:flex;align-items:center;gap:0}}
.topbar-tab{{font-size:12px;font-weight:500;color:var(--text-muted);padding:12px 14px;text-decoration:none;transition:color 0.15s;position:relative;height:44px;display:flex;align-items:center}}.topbar-tab:hover{{color:var(--text-secondary)}}.topbar-tab.active{{color:var(--text-strong);font-weight:600}}.topbar-tab.active::after{{content:"";position:absolute;bottom:0;left:14px;right:14px;height:2px;background:var(--text-strong);border-radius:1px}}
.topbar-right{{display:flex;align-items:center;gap:6px}}
.team-select{{appearance:none;-webkit-appearance:none;background:transparent;color:var(--text-secondary);border:1px solid var(--border);border-radius:6px;padding:5px 26px 5px 10px;font-size:11px;font-family:inherit;font-weight:500;cursor:pointer;transition:all 0.15s ease;background-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='10' height='6'%3E%3Cpath d='M0 0l5 6 5-6z' fill='%239898a0'/%3E%3C/svg%3E");background-repeat:no-repeat;background-position:right 8px center}}.team-select:hover{{border-color:rgba(255,255,255,0.15);color:var(--text)}}.team-select:focus{{outline:none;border-color:var(--accent)}}.team-select optgroup{{font-weight:600;color:var(--text-muted)}}.team-select option{{background:var(--bg);color:var(--text)}}
.theme-toggle{{display:flex;gap:1px;padding:1px;border:1px solid var(--border);border-radius:6px}}
.theme-btn{{display:flex;align-items:center;justify-content:center;width:26px;height:24px;border:none;background:transparent;color:var(--text-muted);cursor:pointer;border-radius:5px;transition:all 0.15s ease;padding:0}}.theme-btn:hover{{color:var(--text-secondary)}}
.theme-btn.active{{color:var(--text-strong);background:var(--bg-elevated)}}

/* Page header + view toggle */
.ld-header{{max-width:1200px;margin:0 auto;padding:20px 28px 0;display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:12px}}
.ld-header h1{{font-size:18px;font-weight:600;letter-spacing:-0.3px;color:var(--text-strong)}}
.view-toggle{{display:flex;border:1px solid var(--border);border-radius:6px;overflow:hidden}}
.view-btn{{padding:6px 14px;font-size:11px;font-weight:500;font-family:inherit;border:none;background:transparent;color:var(--text-muted);cursor:pointer;transition:all 0.15s}}
.view-btn:hover{{color:var(--text-secondary)}}
.view-btn.vt-active{{background:var(--bg-elevated);color:var(--text-strong);font-weight:600}}
.ld-content{{max-width:1200px;margin:0 auto;padding:16px 28px 60px}}
h3{{font-size:14px;font-weight:600;margin-bottom:18px;letter-spacing:-0.1px;color:var(--text-secondary)}}

/* Leader cards */
.ld-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:16px}}
.ld-card{{background:var(--bg-surface);border:1px solid var(--border);border-radius:8px;padding:16px;overflow:hidden}}
.ld-title{{font-size:11px;font-weight:600;text-transform:uppercase;letter-spacing:0.8px;color:var(--text-muted);margin-bottom:12px;padding-bottom:8px;border-bottom:1px solid var(--border)}}
.ld-row{{display:flex;align-items:center;gap:10px;padding:5px 0}}
.ld-row+.ld-row{{border-top:1px solid var(--border)}}
.ld-hl{{background:rgba(255,255,255,0.03);border-radius:4px;padding:5px 6px;margin:0 -6px}}
:root[data-theme="light"] .ld-hl{{background:rgba(0,0,0,0.03)}}
.ld-rank{{font-size:11px;font-weight:600;color:var(--text-muted);min-width:18px;text-align:right;font-variant-numeric:tabular-nums}}
.ld-headshot{{width:28px;height:28px;border-radius:50%;flex-shrink:0;background:var(--bg-elevated)}}
.ld-info{{flex:1;min-width:0;display:flex;flex-direction:column}}
.ld-name{{font-size:12px;font-weight:600;color:var(--text);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;text-decoration:none;display:block}}.ld-name:hover{{color:var(--accent)}}
.ld-team{{font-size:10px;font-weight:500;color:var(--text-muted)}}
.ld-val{{font-size:14px;font-weight:700;color:var(--text-strong);font-variant-numeric:tabular-nums;min-width:36px;text-align:right}}
.ld-hl .ld-name{{color:var(--accent)}}
.ld-hl .ld-val{{color:var(--accent)}}

/* Full stats table */
.fs-toggle{{display:flex;gap:0;border-bottom:1px solid var(--border);margin-bottom:16px}}
.fs-tab{{display:flex;align-items:center;padding:8px 14px;border:none;background:transparent;color:var(--text-muted);font-size:12px;font-weight:500;font-family:inherit;cursor:pointer;transition:color 0.15s;border-bottom:2px solid transparent;margin-bottom:-1px}}
.fs-tab:hover{{color:var(--text-secondary)}}
.fs-tab.fs-active{{color:var(--text-strong);font-weight:600;border-bottom-color:var(--text-strong)}}
.fs-tbl-wrap{{overflow-x:auto;border-radius:8px;border:1px solid var(--border)}}
.fs-tbl{{width:100%;border-collapse:collapse;font-size:11px;font-variant-numeric:tabular-nums}}
.fs-tbl thead th{{padding:8px 8px;font-size:9px;font-weight:600;text-transform:uppercase;letter-spacing:0.4px;color:var(--text-muted);text-align:left;white-space:nowrap;border-bottom:1px solid var(--border);background:var(--bg-surface);position:sticky;top:0;cursor:pointer;user-select:none;transition:color 0.15s}}.fs-tbl thead th:hover{{color:var(--text-secondary)}}.fs-tbl thead th::after{{content:"";display:inline-block;margin-left:3px;opacity:0.3;font-size:8px;vertical-align:middle}}.fs-tbl thead th.asc::after{{content:"\25B2";opacity:0.8}}.fs-tbl thead th.desc::after{{content:"\25BC";opacity:0.8}}
.fs-tbl tbody tr{{transition:background 0.1s}}
.fs-tbl tbody tr:hover td{{background:var(--bg-hover)}}
.fs-tbl td{{padding:6px 8px;color:var(--text-secondary);white-space:nowrap;border-bottom:1px solid var(--border)}}
.fs-rank{{font-size:10px;font-weight:600;color:var(--text-muted);min-width:24px;text-align:right}}
.fs-rank-h{{min-width:24px;text-align:right}}
.fs-player{{display:flex;align-items:center;gap:8px;min-width:180px}}
.fs-player-h{{min-width:180px}}
.fs-headshot{{width:24px;height:24px;border-radius:50%;flex-shrink:0;background:var(--bg-elevated)}}
.fs-name{{font-size:12px;font-weight:600;color:var(--text);text-decoration:none}}.fs-name:hover{{color:var(--accent)}}
.fs-team-link{{color:var(--text-muted);text-decoration:none}}.fs-team-link:hover{{color:var(--text-secondary)}}
.fs-meta{{font-size:10px;color:var(--text-muted);margin-left:4px}}
.fs-hl{{font-weight:600;color:var(--text)}}
.fs-pts{{font-weight:700;color:var(--text-strong)}}

.footer{{text-align:center;padding:36px 28px;font-size:11px;color:var(--text-muted);max-width:1200px;margin:0 auto}}
.footer a{{color:var(--text-muted);text-decoration:underline;text-decoration-color:var(--footer-link-deco);text-underline-offset:2px}}.footer a:hover{{color:var(--text-secondary)}}
.footer-ts{{display:block;margin-top:6px;font-size:10px;color:var(--text-muted);opacity:0.7}}

@media(max-width:600px){{
.topbar-inner{{padding:0 12px}}
.topbar-tab{{padding:12px 10px;font-size:11px}}
.team-select{{font-size:10px;padding:4px 22px 4px 8px}}
.ld-header{{padding:16px 16px 0;gap:8px}}
.ld-header h1{{font-size:16px}}
.view-toggle{{flex-shrink:0}}
.view-btn{{padding:5px 10px;font-size:10px}}
.ld-content{{padding:12px 16px 40px}}
.ld-grid{{grid-template-columns:1fr;gap:12px}}
.ld-card{{padding:12px}}
.ld-title{{font-size:10px;margin-bottom:10px;padding-bottom:6px}}
.ld-headshot{{width:24px;height:24px}}
.ld-name{{font-size:11px}}
.ld-val{{font-size:13px}}
.ld-rank{{font-size:10px}}
.fs-toggle{{margin-bottom:12px}}
.fs-tab{{padding:7px 10px;font-size:11px}}
.fs-tbl{{font-size:10px}}
.fs-tbl thead th{{padding:6px 5px;font-size:8px}}
.fs-tbl td{{padding:5px 5px}}
.fs-player{{min-width:130px;gap:6px}}
.fs-headshot{{width:20px;height:20px}}
.fs-name{{font-size:11px}}
.fs-meta{{font-size:9px}}
.footer{{padding:24px 16px}}
}}
</style></head><body>

<div class="topbar">
  <div class="topbar-inner">
    <div class="topbar-left">
      <a href="scores.html" class="topbar-tab">Scores</a>
      <a href="index.html" class="topbar-tab" onclick="var p=localStorage.getItem('lastTeamPage');if(p){{window.location.href=p;return false}}">Teams</a>
      <a href="standings.html" class="topbar-tab">Standings</a>
      <span class="topbar-tab active">Stats</span>
    </div>
    <div class="topbar-right">
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
</div>

<div class="ld-header">
  <h1>NHL Stats</h1>
  <div class="view-toggle">
    <button class="view-btn vt-active" onclick="switchView(this,'view-leaders')">Leaders</button>
    <button class="view-btn" onclick="switchView(this,'view-fullstats')">Full Stats</button>
  </div>
</div>

<div class="ld-content">
  <div id="view-leaders">
    {leaders_html}
  </div>
  <div id="view-fullstats" style="display:none">
    {full_stats_html}
  </div>
</div>

<div class="footer">
  <span class="footer-ts">Updated {now}</span>
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

function switchView(btn,viewId){{
  document.querySelectorAll('.view-btn').forEach(function(b){{b.classList.remove('vt-active')}});
  btn.classList.add('vt-active');
  document.getElementById('view-leaders').style.display='none';
  document.getElementById('view-fullstats').style.display='none';
  document.getElementById(viewId).style.display='';
}}

function switchFsTab(btn,panelId){{
  var wrap=btn.closest('.ld-content')||document.querySelector('.ld-content');
  wrap.querySelectorAll('.fs-tab').forEach(function(t){{t.classList.remove('fs-active')}});
  wrap.querySelectorAll('.fs-panel').forEach(function(p){{p.style.display='none'}});
  btn.classList.add('fs-active');
  var target=document.getElementById(panelId);
  if(target) target.style.display='';
}}
document.querySelectorAll('table.sortable').forEach(function(tbl){{
  tbl.querySelectorAll('thead th').forEach(function(th,idx){{
    th.addEventListener('click',function(){{
      var asc=th.classList.contains('asc');
      tbl.querySelectorAll('thead th').forEach(function(h){{h.classList.remove('asc','desc')}});
      var dir=asc?'desc':'asc';
      th.classList.add(dir);
      var tbody=tbl.querySelector('tbody');
      var rows=Array.from(tbody.querySelectorAll('tr'));
      rows.sort(function(a,b){{
        var ca=a.children[idx],cb=b.children[idx];
        var va=ca?(ca.hasAttribute('data-sort')?ca.dataset.sort:ca.textContent.trim()):'';
        var vb=cb?(cb.hasAttribute('data-sort')?cb.dataset.sort:cb.textContent.trim()):'';
        var na=parseFloat(va),nb=parseFloat(vb);
        if(!isNaN(na)&&!isNaN(nb))return dir==='asc'?na-nb:nb-na;
        return dir==='asc'?va.localeCompare(vb):vb.localeCompare(va);
      }});
      rows.forEach(function(r){{tbody.appendChild(r)}});
    }});
  }});
}});
</script>
</body></html>'''


def build_standings_page(east_teams, west_teams, all_teams, mp_odds, switcher_opts):
    """Generate a standalone NHL Standings page with Conference, Division, and League views."""
    eastern = timezone(timedelta(hours=-5))
    now = datetime.now(eastern).strftime("%B %-d, %Y at %-I:%M %p ET")

    def fmt_rec(w, l, otl):
        return f"{w}-{l}-{otl}"

    def team_row(t, rank, is_playoff=False, is_cutoff=False, show_div=False, rank_label=None):
        cls_list = []
        if is_cutoff: cls_list.append("cutoff")
        cls = f' class="{" ".join(cls_list)}"' if cls_list else ''
        pp = f".{int(t['ptsPct']*1000):03d}" if t['ptsPct'] < 1 else f"{t['ptsPct']:.3f}"
        rank_cls = "rank-in" if is_playoff else "rank-out"
        l10 = fmt_rec(t["l10w"], t["l10l"], t["l10otl"])
        home = fmt_rec(t["homeW"], t["homeL"], t["homeOtl"])
        road = fmt_rec(t["roadW"], t["roadL"], t["roadOtl"])
        diff = t["gf"] - t["ga"]
        diff_str = f"+{diff}" if diff > 0 else str(diff)
        label = rank_label if rank_label else str(rank)
        po = mp_odds.get(t["abbrev"], {}).get("ALL", {}).get("playoffPct", 0)
        po_str = f"{po*100:.0f}%"
        div_td = f'<td>{t["divAbbrev"][:3].upper()}</td>' if show_div else ''
        fn = "index.html" if t["abbrev"] == DEFAULT_TEAM else f'{t["abbrev"]}.html'
        return f'''<tr{cls}><td class="{rank_cls}">{label}</td><td class="tcol"><a href="{fn}" class="tcol-link">{t["name"]}</a></td>{div_td}<td class="r">{t["gp"]}</td><td class="r">{t["w"]}</td><td class="r">{t["l"]}</td><td class="r">{t["otl"]}</td><td class="r bpts">{t["pts"]}</td><td class="r">{pp}</td><td class="r">{t["gf"]}</td><td class="r">{t["ga"]}</td><td class="r">{diff_str}</td><td class="r">{home}</td><td class="r">{road}</td><td class="r">{l10}</td><td class="r">{t["streak"]}</td><td class="r">{po_str}</td></tr>'''

    # Column headers
    base_cols = '<th class="r">GP</th><th class="r">W</th><th class="r">L</th><th class="r">OTL</th><th class="r">PTS</th><th class="r">P%</th><th class="r">GF</th><th class="r">GA</th><th class="r">DIFF</th><th class="r">Home</th><th class="r">Away</th><th class="r">L10</th><th class="r">STK</th><th class="r">PO%</th>'
    hdr_no_div = f'<thead><tr><th class="rank"></th><th class="name-col">Team</th>{base_cols}</tr></thead>'
    hdr_with_div = f'<thead><tr><th class="rank"></th><th class="name-col">Team</th><th>Div</th>{base_cols}</tr></thead>'

    def div_table(teams, name):
        rows = [team_row(t, i+1, i<3, i==2) for i, t in enumerate(teams)]
        return f'''<div class="div-label">{name}</div><div class="stnd-card"><div class="scroll-x"><table class="nhl-tbl stnd-tbl sortable">{hdr_no_div}<tbody>{"".join(rows)}</tbody></table></div></div>'''

    # ── Conference view (divisions + wild card) ──
    def conf_view(conf_teams, conf_name):
        if conf_name == "Eastern":
            d1n, d2n = "Atlantic", "Metropolitan"
        else:
            d1n, d2n = "Central", "Pacific"
        d1 = sorted([t for t in conf_teams if t["div"] == d1n], key=lambda x: -x["pts"])
        d2 = sorted([t for t in conf_teams if t["div"] == d2n], key=lambda x: -x["pts"])
        html = div_table(d1, f"{d1n} Division") + div_table(d2, f"{d2n} Division")
        # Wild card
        wc_all = sorted(d1[3:] + d2[3:], key=lambda x: -x["pts"])
        wc_rows = []
        for i, t in enumerate(wc_all):
            label = f"WC{i+1}" if i < 2 else str(i+1)
            wc_rows.append(team_row(t, i+1, i<2, i==1, True, label))
        html += f'''<div class="div-label">Wild Card Race</div><div class="stnd-card"><div class="scroll-x"><table class="nhl-tbl stnd-tbl sortable">{hdr_with_div}<tbody>{"".join(wc_rows)}</tbody></table></div></div>'''
        return html

    east_html = f'<h3 class="conf-label">Eastern Conference</h3>' + conf_view(east_teams, "Eastern")
    west_html = f'<h3 class="conf-label">Western Conference</h3>' + conf_view(west_teams, "Western")
    view_conference = east_html + west_html

    # ── Division view (4 clean division tables) ──
    divs = [("Atlantic", "Eastern"), ("Metropolitan", "Eastern"), ("Central", "Western"), ("Pacific", "Western")]
    view_division = ""
    for dname, cname in divs:
        dt = sorted([t for t in all_teams if t["div"] == dname], key=lambda x: -x["pts"])
        rows = [team_row(t, i+1, i<3, i==2) for i, t in enumerate(dt)]
        view_division += f'''<div class="div-label">{dname}</div><div class="stnd-card"><div class="scroll-x"><table class="nhl-tbl stnd-tbl sortable">{hdr_no_div}<tbody>{"".join(rows)}</tbody></table></div></div>'''

    # ── League view (all 32 teams ranked by points) ──
    league_sorted = sorted(all_teams, key=lambda x: (-x["pts"], -x["w"], x["gp"]))
    league_rows = []
    for i, t in enumerate(league_sorted):
        league_rows.append(team_row(t, i+1, i<16, i==15, True))
    view_league = f'''<div class="stnd-card"><div class="scroll-x"><table class="nhl-tbl stnd-tbl sortable">{hdr_with_div}<tbody>{"".join(league_rows)}</tbody></table></div></div>'''

    return f'''<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>NHL Standings</title>
<script>document.documentElement.setAttribute('data-theme',localStorage.getItem('theme')||'dark')</script>
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin><link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>
:root,:root[data-theme="dark"]{{--bg:#0a0a0b;--bg-surface:rgba(255,255,255,0.035);--bg-elevated:rgba(255,255,255,0.055);--bg-hover:rgba(255,255,255,0.065);--border:rgba(255,255,255,0.08);--border-subtle:rgba(255,255,255,0.05);--text:rgba(255,255,255,0.85);--text-secondary:rgba(255,255,255,0.55);--text-muted:rgba(255,255,255,0.3);--accent:#e8384f;--green:#34d399;--red:#f87171;--text-strong:rgba(255,255,255,0.95);--footer-link-deco:rgba(255,255,255,0.12)}}
:root[data-theme="light"]{{--bg:#fbfbfc;--bg-surface:rgba(0,0,0,0.03);--bg-elevated:rgba(0,0,0,0.05);--bg-hover:rgba(0,0,0,0.06);--border:rgba(0,0,0,0.1);--text:rgba(0,0,0,0.8);--text-secondary:rgba(0,0,0,0.5);--text-muted:rgba(0,0,0,0.3);--accent:#c8102e;--green:#059669;--red:#dc2626;--text-strong:rgba(0,0,0,0.92);--footer-link-deco:rgba(0,0,0,0.14)}}
*{{margin:0;padding:0;box-sizing:border-box}}
@keyframes fadeIn{{from{{opacity:0}}to{{opacity:1}}}}
body{{font-family:'Inter',system-ui,-apple-system,sans-serif;background:var(--bg);color:var(--text);line-height:1.5;-webkit-font-smoothing:antialiased;animation:fadeIn 0.15s ease}}
a{{color:var(--text);text-decoration:none}}

.topbar{{position:sticky;top:0;z-index:50;background:var(--bg);border-bottom:1px solid var(--border);backdrop-filter:blur(12px);-webkit-backdrop-filter:blur(12px)}}
.topbar-inner{{max-width:1200px;margin:0 auto;padding:0 28px;display:flex;align-items:center;justify-content:space-between;height:44px}}
.topbar-left{{display:flex;align-items:center;gap:0}}
.topbar-tab{{font-size:12px;font-weight:500;color:var(--text-muted);padding:12px 14px;text-decoration:none;transition:color 0.15s;position:relative;height:44px;display:flex;align-items:center}}.topbar-tab:hover{{color:var(--text-secondary)}}.topbar-tab.active{{color:var(--text-strong);font-weight:600}}.topbar-tab.active::after{{content:"";position:absolute;bottom:0;left:14px;right:14px;height:2px;background:var(--text-strong);border-radius:1px}}
.topbar-right{{display:flex;align-items:center;gap:6px}}
.team-select{{appearance:none;-webkit-appearance:none;background:transparent;color:var(--text-secondary);border:1px solid var(--border);border-radius:6px;padding:5px 26px 5px 10px;font-size:11px;font-family:inherit;font-weight:500;cursor:pointer;transition:all 0.15s ease;background-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='10' height='6'%3E%3Cpath d='M0 0l5 6 5-6z' fill='%239898a0'/%3E%3C/svg%3E");background-repeat:no-repeat;background-position:right 8px center}}.team-select:hover{{border-color:rgba(255,255,255,0.15);color:var(--text)}}.team-select:focus{{outline:none;border-color:var(--accent)}}.team-select optgroup{{font-weight:600;color:var(--text-muted)}}.team-select option{{background:var(--bg);color:var(--text)}}
.theme-toggle{{display:flex;gap:1px;padding:1px;border:1px solid var(--border);border-radius:6px}}
.theme-btn{{display:flex;align-items:center;justify-content:center;width:26px;height:24px;border:none;background:transparent;color:var(--text-muted);cursor:pointer;border-radius:5px;transition:all 0.15s ease;padding:0}}.theme-btn:hover{{color:var(--text-secondary)}}
.theme-btn.active{{color:var(--text-strong);background:var(--bg-elevated)}}

.st-header{{max-width:1200px;margin:0 auto;padding:20px 28px 0;display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:12px}}
.st-header h1{{font-size:18px;font-weight:600;letter-spacing:-0.3px;color:var(--text-strong)}}
.view-toggle{{display:flex;border:1px solid var(--border);border-radius:6px;overflow:hidden}}
.view-btn{{padding:6px 14px;font-size:11px;font-weight:500;font-family:inherit;border:none;background:transparent;color:var(--text-muted);cursor:pointer;transition:all 0.15s}}
.view-btn:hover{{color:var(--text-secondary)}}
.view-btn.vt-active{{background:var(--bg-elevated);color:var(--text-strong);font-weight:600}}
.st-content{{max-width:1200px;margin:0 auto;padding:16px 28px 60px}}
h3{{font-size:14px;font-weight:600;margin-bottom:18px;letter-spacing:-0.1px;color:var(--text-secondary)}}
.conf-label{{margin-top:32px;margin-bottom:8px;font-size:13px;font-weight:600;color:var(--text-secondary);letter-spacing:-0.1px}}
.conf-label:first-child{{margin-top:0}}

.div-label{{margin:24px 0 10px;font-size:11px;font-weight:500;text-transform:uppercase;letter-spacing:1.2px;color:var(--text-muted)}}
.div-label:first-child{{margin-top:0}}
.stnd-card{{background:var(--bg-surface);border-radius:8px;border:1px solid var(--border);padding:4px 0;margin-bottom:8px;overflow:hidden}}
.stnd-card .scroll-x{{padding:0}}
.scroll-x{{overflow-x:auto;-webkit-overflow-scrolling:touch}}
.nhl-tbl{{width:100%;border-collapse:collapse;font-size:12px;font-variant-numeric:tabular-nums}}
.nhl-tbl thead th{{background:transparent;color:var(--text-muted);padding:8px 6px;font-weight:500;font-size:9px;text-transform:uppercase;letter-spacing:0.5px;text-align:left;white-space:nowrap;border-bottom:1px solid var(--border);cursor:pointer;user-select:none;transition:color 0.15s}}.nhl-tbl thead th:hover{{color:var(--text-secondary)}}.nhl-tbl thead th::after{{content:"";display:inline-block;margin-left:3px;opacity:0.3;font-size:8px;vertical-align:middle}}.nhl-tbl thead th.asc::after{{content:"\25B2";opacity:0.8}}.nhl-tbl thead th.desc::after{{content:"\25BC";opacity:0.8}}
.nhl-tbl thead th.r{{text-align:right}}
.nhl-tbl thead th.rank{{width:30px;text-align:center}}
.nhl-tbl thead th.name-col{{min-width:140px}}
.nhl-tbl td{{padding:7px 6px;border:none;border-bottom:1px solid var(--border-subtle);white-space:nowrap;color:var(--text-secondary)}}
.nhl-tbl td.r{{text-align:right}}
.stnd-tbl td{{padding:7px 6px;font-size:11px}}.stnd-tbl thead th{{padding:8px 6px;font-size:9px}}
.rank-in{{font-weight:600;color:var(--text)}}.rank-out{{color:var(--text-muted)}}
.tcol{{font-weight:600;white-space:nowrap}}.tcol-link{{color:var(--text);text-decoration:none;transition:color 0.15s}}.tcol-link:hover{{color:var(--text-strong)}}
.bpts{{font-weight:700;color:var(--text)}}
.cutoff td{{border-bottom:2px dashed var(--text-muted)}}

.footer{{text-align:center;padding:36px 28px;font-size:11px;color:var(--text-muted);max-width:1200px;margin:0 auto}}
.footer a{{color:var(--text-muted);text-decoration:underline;text-decoration-color:var(--footer-link-deco);text-underline-offset:2px}}.footer a:hover{{color:var(--text-secondary)}}
.footer-ts{{display:block;margin-top:6px;font-size:10px;color:var(--text-muted);opacity:0.7}}

@media(max-width:600px){{
.topbar-inner{{padding:0 12px}}
.topbar-tab{{padding:12px 10px;font-size:11px}}
.team-select{{font-size:10px;padding:4px 22px 4px 8px}}
.st-header{{padding:16px 16px 0;gap:8px}}
.st-header h1{{font-size:16px}}
.view-btn{{padding:5px 10px;font-size:10px}}
.st-content{{padding:12px 16px 40px}}
.stnd-tbl td{{padding:5px 4px;font-size:10px}}
.stnd-tbl thead th{{padding:6px 4px;font-size:8px}}
.div-label{{font-size:10px;margin:20px 0 8px}}
.conf-label{{font-size:12px;margin-top:24px}}
.footer{{padding:24px 16px}}
}}
</style></head><body>

<div class="topbar">
  <div class="topbar-inner">
    <div class="topbar-left">
      <a href="scores.html" class="topbar-tab">Scores</a>
      <a href="index.html" class="topbar-tab" onclick="var p=localStorage.getItem('lastTeamPage');if(p){{window.location.href=p;return false}}">Teams</a>
      <span class="topbar-tab active">Standings</span>
      <a href="leaders.html" class="topbar-tab">Stats</a>
    </div>
    <div class="topbar-right">
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
</div>

<div class="st-header">
  <h1>NHL Standings</h1>
  <div class="view-toggle">
    <button class="view-btn vt-active" onclick="switchStView(this,'st-conference')">Conference</button>
    <button class="view-btn" onclick="switchStView(this,'st-division')">Division</button>
    <button class="view-btn" onclick="switchStView(this,'st-league')">League</button>
  </div>
</div>

<div class="st-content">
  <div id="st-conference">{view_conference}</div>
  <div id="st-division" style="display:none">{view_division}</div>
  <div id="st-league" style="display:none">{view_league}</div>
</div>

<div class="footer">Data from NHL API &amp; <a href="https://moneypuck.com">MoneyPuck</a><span class="footer-ts">Updated {now}</span></div>

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

function switchStView(btn,viewId){{
  document.querySelectorAll('.view-btn').forEach(function(b){{b.classList.remove('vt-active')}});
  btn.classList.add('vt-active');
  ['st-conference','st-division','st-league'].forEach(function(id){{
    document.getElementById(id).style.display='none';
  }});
  document.getElementById(viewId).style.display='';
}}
document.querySelectorAll('table.sortable').forEach(function(tbl){{
  tbl.querySelectorAll('thead th').forEach(function(th,idx){{
    th.addEventListener('click',function(){{
      var asc=th.classList.contains('asc');
      tbl.querySelectorAll('thead th').forEach(function(h){{h.classList.remove('asc','desc')}});
      var dir=asc?'desc':'asc';
      th.classList.add(dir);
      var tbody=tbl.querySelector('tbody');
      var rows=Array.from(tbody.querySelectorAll('tr'));
      rows.sort(function(a,b){{
        var ca=a.children[idx],cb=b.children[idx];
        var va=ca?(ca.hasAttribute('data-sort')?ca.dataset.sort:ca.textContent.trim()):'';
        var vb=cb?(cb.hasAttribute('data-sort')?cb.dataset.sort:cb.textContent.trim()):'';
        var na=parseFloat(va),nb=parseFloat(vb);
        if(!isNaN(na)&&!isNaN(nb))return dir==='asc'?na-nb:nb-na;
        return dir==='asc'?va.localeCompare(vb):vb.localeCompare(va);
      }});
      rows.forEach(function(r){{tbody.appendChild(r)}});
    }});
  }});
}});
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

    print("Fetching injuries from ESPN...")
    all_injuries = fetch_espn_injuries()
    print(f"  {len(all_injuries)} teams with injuries")

    print("Fetching league scoring leaders...")
    skater_leaders = fetch_league_skater_leaders()
    print(f"  Points: {len(skater_leaders.get('points', []))}, Goals: {len(skater_leaders.get('goals', []))}, Assists: {len(skater_leaders.get('assists', []))}, +/-: {len(skater_leaders.get('plusMinus', []))}")

    print("Fetching league goalie leaders...")
    goalie_leaders = fetch_league_goalie_leaders()
    print(f"  Wins: {len(goalie_leaders.get('wins', []))}, GAA: {len(goalie_leaders.get('gaa', []))}, SV%: {len(goalie_leaders.get('svPct', []))}")

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

        try:
            bd_map = fetch_roster_birthdates()
        except Exception:
            bd_map = {}

        skaters = get_skaters(club_stats, nhl_skater_summary, bd_map)
        goalies = get_goalies(club_stats, nhl_goalie_summary, bd_map)
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
        projections_html = build_projections_html(team_entry, vs500, mp_odds, mp_stats, conf_teams)
        schedule_html = build_schedule_html(remaining, above500_count, home_count, away_count, team_records_map, mp_stats, mp_odds, results)
        news_html = build_news_html(news_articles)
        injuries_html = build_injuries_html(all_injuries.get(TEAM, []))
        print(f"  Fetching transactions...")
        txns = fetch_transactions()
        transactions_html = build_transactions_html(txns)
        print(f"  {len(txns)} transactions found")
        html = generate_html(team_entry, roster_html, projections_html, schedule_html, news_html, injuries_html, transactions_html, vs500, mp_odds, deltas, mp_stats, all_teams)

        # Write file
        filename = "index.html" if TEAM == DEFAULT_TEAM else f"{TEAM}.html"
        with open(filename, "w") as f:
            f.write(html)
        print(f"  -> {filename} generated")

    # ── Scoreboard page ────────────────────────────────
    print(f"\n{'='*50}")
    print("Building scoreboard...")

    # Fetch today's scores first to get the current date
    today_scores = fetch_scores()
    today_date_str = today_scores.get("currentDate", datetime.now(timezone(timedelta(hours=-5))).strftime("%Y-%m-%d"))

    # Fetch 15 days: 7 days back + today + 7 days ahead
    from datetime import date as _date
    today_date = datetime.strptime(today_date_str, "%Y-%m-%d").date()
    all_days_scores = []  # list of (date_str, scores_data)

    for offset in range(-7, 8):
        d = today_date + timedelta(days=offset)
        d_str = d.strftime("%Y-%m-%d")
        if d_str == today_date_str:
            all_days_scores.append((d_str, today_scores))
        else:
            print(f"  Fetching scores for {d_str}...")
            all_days_scores.append((d_str, fetch_scores_for_date(d_str)))

    # Fetch game details for all completed/live games across all dates
    all_game_details = {}
    for d_str, scores_data in all_days_scores:
        for g in scores_data.get("games", []):
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

    scoreboard_html = build_scoreboard_html(all_days_scores, today_date_str, all_game_details, sb_switcher, team_records_map, mp_stats, mp_odds)
    with open("scores.html", "w") as f:
        f.write(scoreboard_html)
    total_games = sum(len(sd.get("games", [])) for _, sd in all_days_scores)
    print(f"  -> scores.html generated ({total_games} games across 15 days, {len(all_game_details)} with details)")

    # ── Leaders page ────────────────────────────────────
    print(f"\n{'='*50}")
    print("Building leaders page...")
    TEAM = DEFAULT_TEAM  # Highlight default team's players
    print("  Fetching full skater stats (top 50)...")
    full_skaters = fetch_full_skater_stats()
    print(f"  {len(full_skaters)} skaters loaded")
    print("  Fetching full goalie stats (top 30)...")
    full_goalies = fetch_full_goalie_stats()
    print(f"  {len(full_goalies)} goalies loaded")
    leaders_page_html = build_leaders_page(skater_leaders, goalie_leaders, full_skaters, full_goalies, sb_switcher)
    with open("leaders.html", "w") as f:
        f.write(leaders_page_html)
    print("  -> leaders.html generated")

    # ── Standings page ────────────────────────────────
    print(f"\n{'='*50}")
    print("Building standings page...")
    standings_page_html = build_standings_page(east_teams, west_teams, all_teams, mp_odds, sb_switcher)
    with open("standings.html", "w") as f:
        f.write(standings_page_html)
    print("  -> standings.html generated")

    print(f"\n{'='*50}")
    print("Done! All 32 team pages + scoreboard + leaders + standings generated.")

if __name__ == "__main__":
    main()
