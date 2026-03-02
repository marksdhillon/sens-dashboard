#!/usr/bin/env python3
"""
Ottawa Senators Dashboard Builder
Fetches live data from the NHL API and generates a static HTML dashboard.
Runs via GitHub Actions after each game.
"""

import json
import urllib.request
from datetime import datetime, timezone

TEAM = "OTT"
SEASON = "20252026"
NHL_API = "https://api-web.nhle.com/v1"

def fetch_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": "SensDashboard/1.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read())

def fetch_standings():
    return fetch_json(f"{NHL_API}/standings/now")

def fetch_club_stats():
    return fetch_json(f"{NHL_API}/club-stats/{TEAM}/now")

def fetch_schedule():
    return fetch_json(f"{NHL_API}/club-schedule-season/{TEAM}/{SEASON}")

def get_team_data(standings):
    """Extract Ottawa's data and full Eastern Conference standings."""
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
            "diff": team.get("goalDifferential", 0),
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
            "regWins": team.get("regulationWins", 0),
        }
        all_teams.append(info)
        if info["conf"] == "Eastern":
            east_teams.append(info)
        if abbrev == TEAM:
            sens = info
    return sens, east_teams, all_teams

def get_above500_teams(all_teams):
    """Teams with win% > .500"""
    return {t["abbrev"] for t in all_teams if t["gp"] > 0 and t["w"] / t["gp"] > 0.5}

def get_skaters(club_stats):
    skaters = []
    for s in club_stats.get("skaters", []):
        first = s.get("firstName", {})
        last = s.get("lastName", {})
        if isinstance(first, dict): first = first.get("default", "")
        if isinstance(last, dict): last = last.get("default", "")
        gp = s.get("gamesPlayed", 0)
        pts = s.get("points", 0)
        skaters.append({
            "name": f"{first} {last}",
            "pos": s.get("positionCode", ""),
            "gp": gp,
            "g": s.get("goals", 0),
            "a": s.get("assists", 0),
            "pts": pts,
            "pm": s.get("plusMinus", 0),
            "pim": s.get("penaltyMinutes", 0),
            "ppg": round(pts / gp, 2) if gp > 0 else 0,
            "shots": s.get("shots", 0),
            "shootPct": s.get("shootingPctg", 0),
        })
    skaters.sort(key=lambda x: x["pts"], reverse=True)
    return skaters

def get_goalies(club_stats):
    goalies = []
    for g in club_stats.get("goalies", []):
        first = g.get("firstName", {})
        last = g.get("lastName", {})
        if isinstance(first, dict): first = first.get("default", "")
        if isinstance(last, dict): last = last.get("default", "")
        goalies.append({
            "name": f"{first} {last}",
            "gp": g.get("gamesPlayed", 0),
            "w": g.get("wins", 0),
            "l": g.get("losses", 0),
            "otl": g.get("overtimeLosses", 0),
            "gaa": round(g.get("goalsAgainstAverage", 0), 2),
            "svPct": round(g.get("savePercentage", 0), 3),
            "so": g.get("shutouts", 0),
        })
    goalies.sort(key=lambda x: x["gp"], reverse=True)
    return goalies

def get_remaining_schedule(schedule_data, above500):
    """Get remaining games (not yet played)."""
    games = []
    for g in schedule_data.get("games", []):
        if g.get("gameType", 0) != 2:  # regular season only
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
        # Fallback: use abbrev if name is empty
        if not opp_name or opp_name == "None":
            opp_name = opp_abbrev
        game_date = g.get("gameDate", "")
        try:
            dt = datetime.strptime(game_date, "%Y-%m-%d")
            date_str = dt.strftime("%b %-d")
        except (ValueError, TypeError):
            date_str = game_date
        games.append({
            "date": date_str,
            "rawDate": game_date,
            "opp": opp_name,
            "oppAbbrev": opp_abbrev,
            "loc": "home" if is_home else "away",
            "above500": opp_abbrev in above500,
        })
    games.sort(key=lambda x: x["rawDate"])
    return games

def get_results(schedule_data):
    """Get completed game results for record vs above-.500."""
    results = []
    for g in schedule_data.get("games", []):
        if g.get("gameType", 0) != 2:
            continue
        state = g.get("gameState", "")
        if state not in ("FINAL", "OFF"):
            continue
        home = g.get("homeTeam", {})
        away = g.get("awayTeam", {})
        home_abbrev = home.get("abbrev", "")
        away_abbrev = away.get("abbrev", "")
        is_home = home_abbrev == TEAM
        opp_abbrev = away_abbrev if is_home else home_abbrev
        sens_score = home.get("score", 0) if is_home else away.get("score", 0)
        opp_score = away.get("score", 0) if is_home else home.get("score", 0)
        period = g.get("periodDescriptor", {}).get("periodType", "REG")
        if sens_score > opp_score:
            result = "W"
        elif period in ("OT", "SO") and sens_score < opp_score:
            result = "OTL"
        else:
            result = "L"
        results.append({
            "oppAbbrev": opp_abbrev,
            "result": result,
        })
    return results

def compute_vs_above500(results, above500):
    w, l, otl = 0, 0, 0
    for r in results:
        if r["oppAbbrev"] in above500:
            if r["result"] == "W": w += 1
            elif r["result"] == "L": l += 1
            else: otl += 1
    return w, l, otl

def build_standings_section(east_teams):
    """Build Atlantic, Metropolitan, and Wild Card HTML tables."""
    atlantic = sorted([t for t in east_teams if t["div"] == "Atlantic"], key=lambda x: -x["pts"])
    metro = sorted([t for t in east_teams if t["div"] == "Metropolitan"], key=lambda x: -x["pts"])

    def team_row(t, rank, is_playoff=False, is_cutoff=False, is_sens=False):
        rank_class = "in" if is_playoff else "out"
        row_class = ""
        if is_sens: row_class = ' class="sens-row"'
        elif is_cutoff: row_class = ' class="cutoff"'
        pts_pct = f".{int(t['ptsPct']*1000):03d}" if t['ptsPct'] < 1 else f"{t['ptsPct']:.3f}"
        return f'<tr{row_class}><td class="{rank_class}">{rank}</td><td class="tcol">{t["name"]}</td><td class="r">{t["gp"]}</td><td class="r">{t["w"]}</td><td class="r">{t["l"]}</td><td class="r">{t["otl"]}</td><td class="r bpts">{t["pts"]}</td><td class="r">{pts_pct}</td></tr>'

    def div_table(teams, div_name):
        rows = []
        for i, t in enumerate(teams):
            is_playoff = i < 3
            is_cutoff = i == 2
            is_sens = t["abbrev"] == TEAM
            rows.append(team_row(t, i + 1, is_playoff, is_cutoff, is_sens))
        return f'''<div class="div-label">{div_name}</div>
<div class="scroll-x"><table class="tbl">
<thead><tr><th></th><th>Team</th><th class="r">GP</th><th class="r">W</th><th class="r">L</th><th class="r">OTL</th><th class="r">PTS</th><th class="r">P%</th></tr></thead>
<tbody>{"".join(rows)}</tbody></table></div>'''

    # Wild card: all non-top-3 teams, sorted by points
    atl_wc = atlantic[3:]
    met_wc = metro[3:]
    wc_all = sorted(atl_wc + met_wc, key=lambda x: -x["pts"])

    wc_rows = []
    for i, t in enumerate(wc_all):
        is_in = i < 2
        is_cutoff = i == 1
        is_sens = t["abbrev"] == TEAM
        label = f"WC{i+1}" if i < 2 else str(i + 1)
        div_short = t["divAbbrev"][:3].upper()
        remaining = 82 - t["gp"]
        max_pts = t["pts"] + remaining * 2
        row_class = ""
        bg = ""
        if is_sens:
            row_class = ' class="sens-row"'
        elif is_cutoff:
            row_class = ' class="cutoff"'
        if is_in and not is_sens:
            bg = ' style="background:rgba(34,197,94,0.06)"'
        rank_class = "in" if is_in else "out"
        if is_sens: rank_class = ""
        wc_rows.append(f'<tr{row_class}{bg}><td class="{rank_class}">{label}</td><td class="tcol">{t["name"]}</td><td>{div_short}</td><td class="r">{t["gp"]}</td><td class="r bpts">{t["pts"]}</td><td class="r">{remaining}</td><td class="r">{max_pts}</td></tr>')

    wc_html = f'''<div class="div-label">Wild Card Race (Top 2 Qualify)</div>
<div class="scroll-x"><table class="tbl">
<thead><tr><th></th><th>Team</th><th>Div</th><th class="r">GP</th><th class="r">PTS</th><th class="r">Remaining</th><th class="r">Max Pts</th></tr></thead>
<tbody>{"".join(wc_rows)}</tbody></table></div>'''

    return div_table(atlantic, "Atlantic Division") + div_table(metro, "Metropolitan Division") + wc_html

def build_roster_html(skaters, goalies):
    max_pts = max((s["pts"] for s in skaters), default=0)
    rows = []
    for s in skaters:
        pos_class = "pos-d" if s["pos"] == "D" else "pos-fw"
        pm_val = s["pm"]
        pm_class = "plus" if pm_val > 0 else "minus" if pm_val < 0 else ""
        pm_str = f"+{pm_val}" if pm_val > 0 else str(pm_val)
        pts_class = ' pts-lead' if s["pts"] == max_pts else ''
        rows.append(f'<tr><td class="pname">{s["name"]} <span class="pos-tag {pos_class}">{s["pos"]}</span></td><td class="r">{s["gp"]}</td><td class="r">{s["g"]}</td><td class="r">{s["a"]}</td><td class="r{pts_class}">{s["pts"]}</td><td class="r {pm_class}">{pm_str}</td><td class="r">{s["pim"]}</td><td class="r">{s["ppg"]:.2f}</td></tr>')

    goalie_rows = []
    for g in goalies:
        svp = f".{int(g['svPct']*1000):03d}" if g["svPct"] < 1 else f"{g['svPct']:.3f}"
        goalie_rows.append(f'<tr><td class="pname">{g["name"]}</td><td class="r">{g["gp"]}</td><td class="r">{g["w"]}</td><td class="r">{g["l"]}</td><td class="r">{g["otl"]}</td><td class="r">{g["gaa"]:.2f}</td><td class="r">{svp}</td><td class="r">{g["so"]}</td></tr>')

    return f'''<div class="stitle"><span class="dot"></span> Skater Statistics</div>
<div class="scroll-x"><table class="tbl">
<thead><tr><th>Player</th><th class="r">GP</th><th class="r">G</th><th class="r">A</th><th class="r">PTS</th><th class="r">+/-</th><th class="r">PIM</th><th class="r">P/GP</th></tr></thead>
<tbody>{"".join(rows)}</tbody></table></div>
<div style="margin-top:22px"><div class="stitle"><span class="dot"></span> Goaltenders</div>
<div class="scroll-x"><table class="tbl">
<thead><tr><th>Player</th><th class="r">GP</th><th class="r">W</th><th class="r">L</th><th class="r">OTL</th><th class="r">GAA</th><th class="r">SV%</th><th class="r">SO</th></tr></thead>
<tbody>{"".join(goalie_rows)}</tbody></table></div></div>'''

def build_schedule_html(remaining, above500_count, home_count, away_count):
    cards = []
    for g in remaining:
        a5 = " a5" if g["above500"] else ""
        prefix = "@ " if g["loc"] == "away" else "vs "
        loc_class = "gl-a" if g["loc"] == "away" else "gl-h"
        loc_text = "AWAY" if g["loc"] == "away" else "HOME"
        cards.append(f'<div class="gc{a5}"><div><div class="gd">{g["date"]}</div><div class="go">{prefix}{g["opp"]}</div></div><div class="gl {loc_class}">{loc_text}</div></div>')

    return f'''<div class="stitle"><span class="dot"></span> Remaining Schedule — {len(remaining)} Games</div>
<div class="legend">
  <div class="legend-item"><div class="ldot" style="background:var(--yellow)"></div> vs. above-.500 team</div>
  <div class="legend-item"><div class="ldot" style="background:var(--green)"></div> Home</div>
  <div class="legend-item"><div class="ldot" style="background:var(--red)"></div> Away</div>
</div>
<div class="sched-grid">{"".join(cards)}</div>
<div style="margin-top:20px"><div class="stitle"><span class="dot"></span> Schedule Breakdown</div>
<div class="pgrid">
  <div class="pcard"><div class="pct">Home / Away</div><div class="pnum">{home_count} <span style="font-size:16px;color:var(--text-muted)">/</span> {away_count}</div><div class="pdesc">{home_count} home games, {away_count} road games.</div></div>
  <div class="pcard"><div class="pct">vs. Above .500 Teams</div><div class="pnum" style="color:var(--yellow)">{above500_count}</div><div class="pdesc">{above500_count} of {len(remaining)} remaining games against above-.500 teams.</div></div>
</div></div>'''

def build_projections_html(sens, remaining_count, vs500_record):
    pts = sens["pts"]
    gp = sens["gp"]
    remaining = 82 - gp
    pts_pct = sens["ptsPct"]
    pace = round(pts_pct * 2 * 82, 1)

    # Find WC2 cutoff (estimate ~93 based on historical)
    target = 93
    needed = max(0, target - pts)
    wins_needed = needed // 2
    otl_needed = needed % 2

    # Win rate needed
    if remaining > 0:
        rate_needed = round(needed / (remaining * 2), 3)
        ppg_needed = round(needed / remaining, 2)
    else:
        rate_needed = 0
        ppg_needed = 0

    progress_pct = round(pts / 164 * 100, 1)
    target_pct = round(target / 164 * 100, 1)

    w500, l500, otl500 = vs500_record

    # Scenario records
    if remaining > 0:
        s1_w = wins_needed + (1 if otl_needed else 0)
        s1_otl = 1 if not otl_needed else 0
        s1_l = remaining - s1_w - s1_otl
        if s1_l < 0:
            s1_w = remaining
            s1_otl = 0
            s1_l = 0
    else:
        s1_w, s1_otl, s1_l = 0, 0, 0

    return f'''<div class="stitle"><span class="dot"></span> Playoff Projection Analysis</div>
<div class="pgrid">
  <div class="pcard"><div class="pct">Current Pace</div><div class="pnum" style="color:var(--yellow)">~{pace} pts</div><div class="pdesc">At their current points percentage ({pts_pct:.3f}), Ottawa projects to <strong>~{pace} points</strong> over 82 games.</div></div>
  <div class="pcard"><div class="pct">Points Needed for 93</div><div class="pnum" style="color:var(--sens-gold)">{needed} pts</div><div class="pdesc">Need <strong>{needed} more points</strong> in {remaining} games to reach 93 — a safe playoff target.</div></div>
  <div class="pcard"><div class="pct">Win Rate Needed</div><div class="pnum" style="color:var(--blue)">{rate_needed:.3f}</div><div class="pdesc">Must earn <strong>{ppg_needed} pts/game</strong> the rest of the way. Current pace: {pts/gp:.2f}.</div></div>
  <div class="pcard"><div class="pct">Record vs Above .500</div><div class="pnum" style="color:var(--red)">{w500}-{l500}-{otl500}</div><div class="pdesc">Record against teams with winning records this season.</div></div>
</div>
<div class="pcard" style="margin-bottom:20px">
  <div class="pct">Season Points Progress</div>
  <div class="pbar-wrap">
    <div class="pbar-labels"><span>0 pts</span><span>82 games &rarr; 164 max</span></div>
    <div class="pbar">
      <div class="pbar-fill" style="width:{progress_pct}%"></div>
      <div class="pbar-mark" style="left:{target_pct}%"><span>93 pts target</span></div>
    </div>
    <div class="pbar-bottom">
      <span style="color:var(--sens-red);font-weight:600">{pts} pts earned</span>
      <span style="color:var(--text-muted)">{needed} pts needed &rarr; {remaining} games left</span>
    </div>
  </div>
</div>
<div class="stitle"><span class="dot"></span> Scenarios to Make the Playoffs</div>
<div class="scenario"><div class="st"><span class="badge badge-g">Target</span> Reach 93 points — Go ~{s1_w}-{s1_otl}-{s1_l}</div><div class="sd">A .587+ points pace the rest of the way. A step up from the season average but doable with a strong push. Likely secures a Wild Card spot.</div></div>
<div class="scenario"><div class="st"><span class="badge badge-y">Stretch</span> Reach 96 points — Lock it in</div><div class="sd">Win 2-3 more beyond the target to secure a spot with room to spare. Takes pressure off the final week.</div></div>
<div class="scenario"><div class="st"><span class="badge badge-r">Minimum</span> Reach 90 points — Need help</div><div class="sd">The bare minimum — may sneak in if other bubble teams collapse. Last year, 91 was the Eastern Conference cutoff.</div></div>
<div class="footnote"><strong>Key context:</strong> The Sens play at a 101-point pace with Ullmark in net vs. 70-point pace without him — goaltending health is the single biggest variable. The remaining schedule features {remaining} games with several matchups against fellow bubble teams.</div>'''

def generate_html(sens, skaters, goalies, standings_html, roster_html, projections_html, schedule_html):
    now = datetime.now(timezone.utc).strftime("%B %-d, %Y at %-I:%M %p UTC")
    record = f"{sens['w']}-{sens['l']}-{sens['otl']}"
    remaining = 82 - sens["gp"]
    pace = round(sens["ptsPct"] * 2 * 82, 1)
    home_rec = f"{sens['homeW']}-{sens['homeL']}-{sens['homeOtl']}"
    road_rec = f"{sens['roadW']}-{sens['roadL']}-{sens['roadOtl']}"
    l10 = f"{sens['l10w']}-{sens['l10l']}-{sens['l10otl']}"

    return f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Ottawa Senators 2025-26 Dashboard</title>
<style>
  :root {{
    --sens-red: #C52032; --sens-black: #1A1A2E; --sens-gold: #C8A951;
    --bg-dark: #0D0D1A; --bg-card: #16162A; --border: rgba(200,169,81,0.15);
    --text-primary: #EEEEF0; --text-secondary: #9999B0; --text-muted: #666680;
    --green: #22C55E; --red: #EF4444; --yellow: #EAB308; --blue: #3B82F6;
  }}
  * {{ margin:0; padding:0; box-sizing:border-box; }}
  body {{ font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif; background:var(--bg-dark); color:var(--text-primary); line-height:1.4; }}
  .hero {{ background:linear-gradient(135deg,var(--sens-black) 0%,#1a0a0e 50%,var(--sens-black) 100%); border-bottom:1px solid var(--border); padding:28px 24px 24px; }}
  .hero-inner {{ max-width:1100px; margin:0 auto; }}
  .team-header {{ display:flex; align-items:center; gap:14px; margin-bottom:18px; }}
  .team-logo {{ width:52px;height:52px;background:var(--sens-red);border-radius:12px;display:flex;align-items:center;justify-content:center;font-weight:900;font-size:20px;color:white;box-shadow:0 4px 16px rgba(197,32,50,0.35);letter-spacing:-1px; }}
  .team-name {{ font-size:26px;font-weight:800;letter-spacing:-0.5px; }}
  .team-name b {{ color:var(--sens-red); }}
  .team-sub {{ font-size:12px;color:var(--text-secondary);font-weight:500;margin-top:2px; }}
  .chips {{ display:flex;gap:10px;flex-wrap:wrap; }}
  .chip {{ background:rgba(255,255,255,0.06);border:1px solid var(--border);border-radius:10px;padding:10px 16px;min-width:90px;text-align:center; }}
  .chip .cl {{ font-size:9px;text-transform:uppercase;letter-spacing:1.1px;color:var(--text-muted);font-weight:600;margin-bottom:3px; }}
  .chip .cv {{ font-size:20px;font-weight:800;letter-spacing:-0.5px; }}
  .c-gold {{ color:var(--sens-gold); }} .c-blue {{ color:var(--blue); }} .c-yellow {{ color:var(--yellow); }} .c-green {{ color:var(--green); }}
  .container {{ max-width:1100px;margin:0 auto;padding:20px 24px 40px; }}
  input[name="tab"] {{ display:none; }}
  .tab-bar {{ display:flex;gap:3px;background:rgba(255,255,255,0.04);border-radius:10px;padding:3px;margin-bottom:20px;border:1px solid var(--border); }}
  .tab-bar label {{ flex:1;padding:9px 12px;border-radius:7px;font-size:12px;font-weight:600;text-align:center;cursor:pointer;color:var(--text-secondary);transition:all 0.15s; }}
  .tab-bar label:hover {{ color:var(--text-primary);background:rgba(255,255,255,0.04); }}
  .panel {{ display:none; }}
  #tab-roster:checked ~ .tab-bar label[for="tab-roster"],
  #tab-standings:checked ~ .tab-bar label[for="tab-standings"],
  #tab-playoffs:checked ~ .tab-bar label[for="tab-playoffs"],
  #tab-schedule:checked ~ .tab-bar label[for="tab-schedule"] {{ background:var(--sens-red);color:white;box-shadow:0 2px 10px rgba(197,32,50,0.3); }}
  #tab-roster:checked ~ #p-roster,
  #tab-standings:checked ~ #p-standings,
  #tab-playoffs:checked ~ #p-playoffs,
  #tab-schedule:checked ~ #p-schedule {{ display:block; }}
  .stitle {{ font-size:15px;font-weight:700;margin-bottom:14px;display:flex;align-items:center;gap:8px; }}
  .stitle .dot {{ width:7px;height:7px;border-radius:50%;background:var(--sens-red);flex-shrink:0; }}
  .tbl {{ width:100%;border-collapse:collapse;font-size:12px; }}
  .tbl th {{ background:rgba(255,255,255,0.04);padding:8px 10px;font-weight:600;font-size:9px;text-transform:uppercase;letter-spacing:0.8px;color:var(--text-muted);text-align:left;border-bottom:1px solid var(--border); }}
  .tbl th.r,.tbl td.r {{ text-align:right; }}
  .tbl td {{ padding:8px 10px;border-bottom:1px solid rgba(255,255,255,0.03);font-variant-numeric:tabular-nums; }}
  .tbl tbody tr:hover {{ background:rgba(197,32,50,0.05); }}
  .pname {{ font-weight:600;white-space:nowrap; }}
  .pos-tag {{ display:inline-block;font-size:9px;font-weight:700;padding:1px 5px;border-radius:3px;margin-left:5px;vertical-align:middle; }}
  .pos-fw {{ background:rgba(59,130,246,0.15);color:#60A5FA; }}
  .pos-d {{ background:rgba(34,197,94,0.15);color:#4ADE80; }}
  .plus {{ color:var(--green); }} .minus {{ color:var(--red); }}
  .pts-lead {{ color:var(--sens-gold);font-weight:700; }}
  .tbl .sens-row {{ background:rgba(197,32,50,0.1); }}
  .tbl .sens-row td:first-child {{ font-weight:700;color:var(--sens-red); }}
  .tbl .cutoff td {{ border-bottom:2px dashed var(--sens-gold); }}
  .in {{ color:var(--green);font-weight:600; }} .out {{ color:var(--text-muted); }}
  .tcol {{ font-weight:600;white-space:nowrap; }} .bpts {{ font-weight:700; }}
  .div-label {{ margin:20px 0 6px;font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:1px;color:var(--text-muted); }}
  .div-label:first-child {{ margin-top:0; }}
  .sub-note {{ font-size:11px;color:var(--text-secondary);margin-bottom:14px; }}
  .pgrid {{ display:grid;grid-template-columns:1fr 1fr;gap:14px;margin-bottom:20px; }}
  @media (max-width:700px) {{ .pgrid {{ grid-template-columns:1fr; }} }}
  .pcard {{ background:var(--bg-card);border:1px solid var(--border);border-radius:12px;padding:18px; }}
  .pcard .pct {{ font-size:10px;text-transform:uppercase;letter-spacing:1.1px;color:var(--text-muted);font-weight:600;margin-bottom:10px; }}
  .pcard .pnum {{ font-size:32px;font-weight:900;letter-spacing:-1px;line-height:1;margin-bottom:5px; }}
  .pcard .pdesc {{ font-size:11px;color:var(--text-secondary);line-height:1.5; }}
  .pcard .pdesc strong {{ color:var(--text-primary); }}
  .pbar-wrap {{ margin:16px 0; }}
  .pbar-labels {{ display:flex;justify-content:space-between;font-size:10px;color:var(--text-muted);margin-bottom:5px; }}
  .pbar {{ height:9px;background:rgba(255,255,255,0.06);border-radius:5px;position:relative;overflow:visible; }}
  .pbar-fill {{ height:100%;border-radius:5px;background:linear-gradient(90deg,var(--sens-red),#E04050); }}
  .pbar-mark {{ position:absolute;top:-3px;width:2px;height:15px;background:var(--sens-gold);border-radius:1px; }}
  .pbar-mark span {{ position:absolute;top:-16px;font-size:9px;color:var(--sens-gold);font-weight:600;white-space:nowrap;transform:translateX(-50%);left:50%; }}
  .pbar-bottom {{ display:flex;justify-content:space-between;margin-top:6px;font-size:10px; }}
  .scenario {{ background:var(--bg-card);border:1px solid var(--border);border-radius:10px;padding:14px 18px;margin-bottom:10px; }}
  .scenario .st {{ font-weight:700;font-size:13px;margin-bottom:5px;display:flex;align-items:center;gap:7px; }}
  .scenario .sd {{ font-size:11px;color:var(--text-secondary);line-height:1.5; }}
  .badge {{ display:inline-block;font-size:9px;font-weight:700;padding:2px 7px;border-radius:4px;text-transform:uppercase;letter-spacing:0.5px; }}
  .badge-g {{ background:rgba(34,197,94,0.15);color:var(--green); }}
  .badge-y {{ background:rgba(234,179,8,0.15);color:var(--yellow); }}
  .badge-r {{ background:rgba(239,68,68,0.15);color:var(--red); }}
  .footnote {{ margin-top:20px;padding:10px 14px;background:rgba(255,255,255,0.02);border:1px solid var(--border);border-radius:8px;font-size:10px;color:var(--text-muted);line-height:1.6; }}
  .sched-grid {{ display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:7px; }}
  .gc {{ background:var(--bg-card);border:1px solid var(--border);border-radius:8px;padding:10px 12px;display:flex;justify-content:space-between;align-items:center; }}
  .gc.a5 {{ border-left:3px solid var(--yellow); }}
  .gc .gd {{ font-size:10px;color:var(--text-muted);font-weight:500; }}
  .gc .go {{ font-size:12px;font-weight:600; }}
  .gc .gl {{ font-size:9px;padding:2px 5px;border-radius:3px;font-weight:600; }}
  .gc .gl-h {{ background:rgba(34,197,94,0.12);color:var(--green); }}
  .gc .gl-a {{ background:rgba(239,68,68,0.12);color:var(--red); }}
  .legend {{ display:flex;gap:14px;margin-bottom:10px;font-size:10px;color:var(--text-secondary); }}
  .legend-item {{ display:flex;align-items:center;gap:5px; }}
  .ldot {{ width:9px;height:9px;border-radius:3px; }}
  .scroll-x {{ overflow-x:auto;-webkit-overflow-scrolling:touch; }}
  .updated {{ text-align:center;padding:16px;font-size:10px;color:var(--text-muted); }}
</style>
</head>
<body>
<div class="hero"><div class="hero-inner">
  <div class="team-header">
    <div class="team-logo">OTT</div>
    <div><div class="team-name">Ottawa <b>Senators</b></div><div class="team-sub">2025-26 Season &middot; Updated {now}</div></div>
  </div>
  <div class="chips">
    <div class="chip"><div class="cl">Record</div><div class="cv">{record}</div></div>
    <div class="chip"><div class="cl">Points</div><div class="cv c-gold">{sens["pts"]}</div></div>
    <div class="chip"><div class="cl">GP</div><div class="cv">{sens["gp"]}</div></div>
    <div class="chip"><div class="cl">Remaining</div><div class="cv c-blue">{remaining}</div></div>
    <div class="chip"><div class="cl">GF / GA</div><div class="cv">{sens["gf"]} / {sens["ga"]}</div></div>
    <div class="chip"><div class="cl">Pts Pace</div><div class="cv c-yellow">{pace}</div></div>
    <div class="chip"><div class="cl">Home</div><div class="cv">{home_rec}</div></div>
    <div class="chip"><div class="cl">Road</div><div class="cv">{road_rec}</div></div>
    <div class="chip"><div class="cl">L10</div><div class="cv c-green">{l10}</div></div>
    <div class="chip"><div class="cl">Streak</div><div class="cv">{sens["streak"]}</div></div>
  </div>
</div></div>
<div class="container">
  <input type="radio" name="tab" id="tab-roster" checked>
  <input type="radio" name="tab" id="tab-standings">
  <input type="radio" name="tab" id="tab-playoffs">
  <input type="radio" name="tab" id="tab-schedule">
  <div class="tab-bar">
    <label for="tab-roster">Roster Stats</label>
    <label for="tab-standings">Standings</label>
    <label for="tab-playoffs">Playoff Projections</label>
    <label for="tab-schedule">Remaining Games</label>
  </div>
  <div class="panel" id="p-roster">{roster_html}</div>
  <div class="panel" id="p-standings">
    <div class="stitle"><span class="dot"></span> Eastern Conference — Wild Card Picture</div>
    <p class="sub-note">Top 3 from each division + 2 Wild Cards qualify. Dashed line = playoff cutoff.</p>
    {standings_html}
  </div>
  <div class="panel" id="p-playoffs">{projections_html}</div>
  <div class="panel" id="p-schedule">{schedule_html}</div>
</div>
<div class="updated">Auto-updated via GitHub Actions &middot; Data from NHL API &middot; {now}</div>
</body></html>'''


def main():
    print("Fetching standings...")
    standings = fetch_standings()
    sens, east_teams, all_teams = get_team_data(standings)
    above500 = get_above500_teams(all_teams)
    print(f"  Ottawa: {sens['w']}-{sens['l']}-{sens['otl']} ({sens['pts']} pts)")
    print(f"  Above .500 teams: {len(above500)}")

    print("Fetching club stats...")
    club_stats = fetch_club_stats()
    skaters = get_skaters(club_stats)
    goalies = get_goalies(club_stats)
    print(f"  {len(skaters)} skaters, {len(goalies)} goalies")

    print("Fetching schedule...")
    schedule_data = fetch_schedule()
    remaining = get_remaining_schedule(schedule_data, above500)
    results = get_results(schedule_data)
    vs500 = compute_vs_above500(results, above500)
    print(f"  {len(remaining)} games remaining, vs .500: {vs500[0]}-{vs500[1]}-{vs500[2]}")

    above500_in_remaining = sum(1 for g in remaining if g["above500"])
    home_count = sum(1 for g in remaining if g["loc"] == "home")
    away_count = sum(1 for g in remaining if g["loc"] == "away")

    print("Building HTML...")
    standings_html = build_standings_section(east_teams)
    roster_html = build_roster_html(skaters, goalies)
    projections_html = build_projections_html(sens, len(remaining), vs500)
    schedule_html = build_schedule_html(remaining, above500_in_remaining, home_count, away_count)

    html = generate_html(sens, skaters, goalies, standings_html, roster_html, projections_html, schedule_html)

    with open("index.html", "w") as f:
        f.write(html)
    print("Done! index.html generated.")

if __name__ == "__main__":
    main()
