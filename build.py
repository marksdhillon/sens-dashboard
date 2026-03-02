#!/usr/bin/env python3
"""
Ottawa Senators Dashboard Builder
Fetches live data from the NHL API + MoneyPuck analytics and generates a static dashboard.
"""

import csv
import io
import json
import urllib.request
from datetime import datetime, timezone

TEAM = "OTT"
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
    """Fetch playoff/cup probabilities from MoneyPuck simulations."""
    rows = fetch_csv_rows(f"{MONEYPUCK}/simulations/simulations_recent.csv")
    odds = {}
    for r in rows:
        team = r.get("teamCode", "")
        scenario = r.get("scenerio", "")  # MoneyPuck typo
        if scenario == "ALL":
            odds[team] = {
                "playoffPct": float(r.get("madePlayoffs", 0)),
                "projPts": float(r.get("points", 0)),
                "cupPct": float(r.get("wonCup", 0)),
                "divWinPct": float(r.get("wonDivision", 0)),
            }
    return odds

def fetch_moneypuck_team_stats():
    """Fetch advanced team stats (xGF%, CF%, PP/PK, etc.) from MoneyPuck."""
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
            "name": f"{first} {last}", "pos": s.get("positionCode", ""),
            "gp": gp, "g": s.get("goals", 0), "a": s.get("assists", 0),
            "pts": pts, "pm": s.get("plusMinus", 0),
            "pim": s.get("penaltyMinutes", 0),
            "ppg": round(pts / gp, 2) if gp > 0 else 0,
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
            "name": f"{first} {last}", "gp": g.get("gamesPlayed", 0),
            "w": g.get("wins", 0), "l": g.get("losses", 0),
            "otl": g.get("overtimeLosses", 0),
            "gaa": round(g.get("goalsAgainstAverage", 0), 2),
            "svPct": round(g.get("savePercentage", 0), 3),
            "so": g.get("shutouts", 0),
        })
    goalies.sort(key=lambda x: x["gp"], reverse=True)
    return goalies

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

def cmp_bar(label, val_ott, val_opp, fmt="pct", higher_better=True):
    """Build a comparison bar: OTT value | bar | OPP value"""
    if fmt == "pct":
        s_ott = f"{val_ott*100:.1f}%"
        s_opp = f"{val_opp*100:.1f}%"
        pct_ott = val_ott * 100
        pct_opp = val_opp * 100
    elif fmt == "dec":
        s_ott = f"{val_ott:.2f}"
        s_opp = f"{val_opp:.2f}"
        pct_ott = val_ott * 20  # scale for display
        pct_opp = val_opp * 20
    else:
        s_ott = str(val_ott)
        s_opp = str(val_opp)
        pct_ott = val_ott
        pct_opp = val_opp

    total = pct_ott + pct_opp if (pct_ott + pct_opp) > 0 else 1
    w_ott = round(pct_ott / total * 100)
    w_opp = 100 - w_ott

    if higher_better:
        c_ott = "var(--green)" if val_ott > val_opp else "var(--red)" if val_ott < val_opp else "var(--text-muted)"
        c_opp = "var(--green)" if val_opp > val_ott else "var(--red)" if val_opp < val_ott else "var(--text-muted)"
    else:
        c_ott = "var(--green)" if val_ott < val_opp else "var(--red)" if val_ott > val_opp else "var(--text-muted)"
        c_opp = "var(--green)" if val_opp < val_ott else "var(--red)" if val_opp > val_ott else "var(--text-muted)"

    return f'''<div class="cmp-row">
<div class="cmp-label">{label}</div>
<div class="cmp-vals"><span style="color:{c_ott}">{s_ott}</span><span class="cmp-vs">vs</span><span style="color:{c_opp}">{s_opp}</span></div>
<div class="cmp-bar"><div class="cmp-bar-l" style="width:{w_ott}%;background:{c_ott}"></div><div class="cmp-bar-r" style="width:{w_opp}%;background:{c_opp}"></div></div>
</div>'''

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
        svp = f".{int(g['svPct']*1000):03d}" if 0 < g["svPct"] < 1 else f"{g['svPct']:.3f}"
        goalie_rows.append(f'<tr><td class="pname">{g["name"]}</td><td class="r">{g["gp"]}</td><td class="r">{g["w"]}</td><td class="r">{g["l"]}</td><td class="r">{g["otl"]}</td><td class="r">{g["gaa"]:.2f}</td><td class="r">{svp}</td><td class="r">{g["so"]}</td></tr>')
    return f'''<div class="stitle"><span class="dot"></span> Skater Statistics</div>
<div class="scroll-x"><table class="tbl"><thead><tr><th>Player</th><th class="r">GP</th><th class="r">G</th><th class="r">A</th><th class="r">PTS</th><th class="r">+/-</th><th class="r">PIM</th><th class="r">P/GP</th></tr></thead>
<tbody>{"".join(rows)}</tbody></table></div>
<div style="margin-top:22px"><div class="stitle"><span class="dot"></span> Goaltenders</div>
<div class="scroll-x"><table class="tbl"><thead><tr><th>Player</th><th class="r">GP</th><th class="r">W</th><th class="r">L</th><th class="r">OTL</th><th class="r">GAA</th><th class="r">SV%</th><th class="r">SO</th></tr></thead>
<tbody>{"".join(goalie_rows)}</tbody></table></div></div>'''

def build_standings_section(east_teams):
    atlantic = sorted([t for t in east_teams if t["div"] == "Atlantic"], key=lambda x: -x["pts"])
    metro = sorted([t for t in east_teams if t["div"] == "Metropolitan"], key=lambda x: -x["pts"])

    def team_row(t, rank, is_playoff=False, is_cutoff=False, is_sens=False):
        rc = "in" if is_playoff else "out"
        cls = ' class="sens-row"' if is_sens else (' class="cutoff"' if is_cutoff else '')
        pp = f".{int(t['ptsPct']*1000):03d}" if t['ptsPct'] < 1 else f"{t['ptsPct']:.3f}"
        return f'<tr{cls}><td class="{rc}">{rank}</td><td class="tcol">{t["name"]}</td><td class="r">{t["gp"]}</td><td class="r">{t["w"]}</td><td class="r">{t["l"]}</td><td class="r">{t["otl"]}</td><td class="r bpts">{t["pts"]}</td><td class="r">{pp}</td></tr>'

    def div_table(teams, name):
        rows = [team_row(t, i+1, i<3, i==2, t["abbrev"]==TEAM) for i, t in enumerate(teams)]
        return f'''<div class="div-label">{name}</div><div class="scroll-x"><table class="tbl">
<thead><tr><th></th><th>Team</th><th class="r">GP</th><th class="r">W</th><th class="r">L</th><th class="r">OTL</th><th class="r">PTS</th><th class="r">P%</th></tr></thead>
<tbody>{"".join(rows)}</tbody></table></div>'''

    wc_all = sorted(atlantic[3:] + metro[3:], key=lambda x: -x["pts"])
    wc_rows = []
    for i, t in enumerate(wc_all):
        is_sens = t["abbrev"] == TEAM
        label = f"WC{i+1}" if i < 2 else str(i+1)
        rem = 82 - t["gp"]
        cls = ' class="sens-row"' if is_sens else (' class="cutoff"' if i == 1 else '')
        bg = ' style="background:rgba(34,197,94,0.06)"' if i < 2 and not is_sens else ''
        rc = "in" if i < 2 else "out"
        if is_sens: rc = ""
        wc_rows.append(f'<tr{cls}{bg}><td class="{rc}">{label}</td><td class="tcol">{t["name"]}</td><td>{t["divAbbrev"][:3].upper()}</td><td class="r">{t["gp"]}</td><td class="r bpts">{t["pts"]}</td><td class="r">{rem}</td><td class="r">{t["pts"]+rem*2}</td></tr>')

    return div_table(atlantic, "Atlantic Division") + div_table(metro, "Metropolitan Division") + f'''<div class="div-label">Wild Card Race (Top 2 Qualify)</div><div class="scroll-x"><table class="tbl">
<thead><tr><th></th><th>Team</th><th>Div</th><th class="r">GP</th><th class="r">PTS</th><th class="r">Remaining</th><th class="r">Max Pts</th></tr></thead>
<tbody>{"".join(wc_rows)}</tbody></table></div>'''

def build_projections_html(sens, vs500, mp_odds, mp_stats):
    pts = sens["pts"]
    gp = sens["gp"]
    remaining = 82 - gp
    pace = round(sens["ptsPct"] * 2 * 82, 1)
    ott_odds = mp_odds.get(TEAM, {})
    playoff_pct = ott_odds.get("playoffPct", 0)
    proj_pts = ott_odds.get("projPts", pace)
    target = 93
    needed = max(0, target - pts)
    deficit = round(proj_pts - target, 1)
    progress_pct = round(pts / 164 * 100, 1)
    target_pct = round(target / 164 * 100, 1)
    w500, l500, otl500 = vs500
    rate_needed = round(needed / (remaining * 2), 3) if remaining > 0 else 0

    # Scenario math
    s1_w = (needed + 1) // 2
    s1_otl = needed % 2
    s1_l = max(0, remaining - s1_w - s1_otl)

    # OTT advanced stats
    ott_mp = mp_stats.get(TEAM, {})
    ott_all = ott_mp.get("all", {})
    ott_5v5 = ott_mp.get("5v5", {})

    # Playoff likelihood color
    if playoff_pct >= 0.6:
        po_color = "var(--green)"
    elif playoff_pct >= 0.35:
        po_color = "var(--yellow)"
    else:
        po_color = "var(--red)"

    deficit_str = f"+{deficit}" if deficit >= 0 else str(deficit)
    deficit_color = "var(--green)" if deficit >= 0 else "var(--red)"

    return f'''<div class="stitle"><span class="dot"></span> Playoff Projection Analysis</div>
<div class="playoff-hero">
  <div class="po-big"><div class="po-big-label">Playoff Probability</div><div class="po-big-num" style="color:{po_color}">{playoff_pct*100:.1f}%</div><div class="po-big-src">MoneyPuck Model</div></div>
  <div class="po-trio">
    <div class="po-stat"><div class="po-stat-val c-gold">{pts}</div><div class="po-stat-label">Current Pts</div></div>
    <div class="po-stat"><div class="po-stat-val" style="color:var(--sens-red)">{target}</div><div class="po-stat-label">Target Pts</div></div>
    <div class="po-stat"><div class="po-stat-val" style="color:{deficit_color}">{deficit_str}</div><div class="po-stat-label">vs Target</div></div>
  </div>
  <div class="po-trio">
    <div class="po-stat"><div class="po-stat-val c-yellow">{proj_pts:.0f}</div><div class="po-stat-label">MoneyPuck Proj</div></div>
    <div class="po-stat"><div class="po-stat-val c-blue">{needed}</div><div class="po-stat-label">Pts Needed</div></div>
    <div class="po-stat"><div class="po-stat-val" style="color:var(--red)">{w500}-{l500}-{otl500}</div><div class="po-stat-label">vs Above .500</div></div>
  </div>
</div>
<div class="pgrid">
  <div class="pcard"><div class="pct">Current Pace</div><div class="pnum" style="color:var(--yellow)">~{pace} pts</div><div class="pdesc">At .{int(sens["ptsPct"]*1000):03d} pts%, Ottawa projects to <strong>~{pace}</strong> over 82 games.</div></div>
  <div class="pcard"><div class="pct">Win Rate Needed</div><div class="pnum" style="color:var(--blue)">{rate_needed:.3f}</div><div class="pdesc">Must earn <strong>{round(needed/remaining,2) if remaining else 0} pts/game</strong> rest of way. Current: {pts/gp:.2f}.</div></div>
</div>
<div class="pcard" style="margin-bottom:20px">
  <div class="pct">Season Points Progress</div>
  <div class="pbar-wrap">
    <div class="pbar-labels"><span>0 pts</span><span>164 max</span></div>
    <div class="pbar"><div class="pbar-fill" style="width:{progress_pct}%"></div><div class="pbar-mark" style="left:{target_pct}%"><span>93 target</span></div></div>
    <div class="pbar-bottom"><span style="color:var(--sens-red);font-weight:600">{pts} earned</span><span style="color:var(--text-muted)">{needed} needed &rarr; {remaining} games</span></div>
  </div>
</div>
<div class="stitle"><span class="dot"></span> Ottawa Advanced Metrics (MoneyPuck)</div>
<div class="pgrid" style="grid-template-columns:1fr 1fr 1fr">
  <div class="pcard"><div class="pct">xGF% (5v5)</div><div class="pnum">{ott_5v5.get("xGFpct",0)*100:.1f}%</div><div class="pdesc">Expected goals for share at even strength. Above 50% = generating more than allowing.</div></div>
  <div class="pcard"><div class="pct">CF% (5v5)</div><div class="pnum">{ott_5v5.get("CFpct",0)*100:.1f}%</div><div class="pdesc">Corsi (shot attempts) share. Measures possession and territorial dominance.</div></div>
  <div class="pcard"><div class="pct">xGF% (All Sit.)</div><div class="pnum">{ott_all.get("xGFpct",0)*100:.1f}%</div><div class="pdesc">Expected goals share across all situations including special teams.</div></div>
</div>
<div class="stitle"><span class="dot"></span> Scenarios</div>
<div class="scenario"><div class="st"><span class="badge badge-g">Target</span> Reach 93 pts — Go ~{s1_w}-{s1_otl}-{s1_l}</div><div class="sd">A .587+ pace. Step up from season average but doable. Likely secures a Wild Card.</div></div>
<div class="scenario"><div class="st"><span class="badge badge-y">Stretch</span> Reach 96 pts — Lock it in</div><div class="sd">Win 2-3 more beyond target. Takes pressure off the final week.</div></div>
<div class="scenario"><div class="st"><span class="badge badge-r">Minimum</span> Reach 90 pts — Need help</div><div class="sd">Bare minimum. May sneak in if bubble teams collapse. 91 was last year's East cutoff.</div></div>
<div class="footnote"><strong>Data:</strong> Playoff probability from <a href="https://moneypuck.com/predictions.htm" style="color:var(--sens-gold)">MoneyPuck</a>. Advanced metrics from MoneyPuck team stats. Updated automatically after each game.</div>'''

def build_schedule_html(remaining, above500_count, home_count, away_count, team_records, mp_stats, mp_odds):
    ott_all = mp_stats.get(TEAM, {}).get("all", {})
    ott_5v5 = mp_stats.get(TEAM, {}).get("5v5", {})
    ott_pp = mp_stats.get(TEAM, {}).get("pp", {})
    ott_pk = mp_stats.get(TEAM, {}).get("pk", {})

    # Compute OTT PP% and PK%
    # PP%: pp goals / (pp goals + pk goals allowed by opponents... actually PP% = pp_gf / pp_opportunities)
    # We don't have opportunities directly, so use penalties drawn as proxy
    # Actually, let's compute from goals and shots as a simpler metric
    ott_gp = ott_all.get("gp", 1)

    cards = []
    for i, g in enumerate(remaining):
        a5 = " a5" if g["above500"] else ""
        prefix = "@ " if g["loc"] == "away" else "vs "
        loc_class = "gl-a" if g["loc"] == "away" else "gl-h"
        loc_text = "AWAY" if g["loc"] == "away" else "HOME"

        # Opponent data
        opp = g["oppAbbrev"]
        opp_rec = team_records.get(opp, {})
        opp_record = f'{opp_rec.get("w",0)}-{opp_rec.get("l",0)}-{opp_rec.get("otl",0)}'
        opp_pts = opp_rec.get("pts", 0)
        opp_odds = mp_odds.get(opp, {})
        opp_mp = mp_stats.get(opp, {})
        opp_all = opp_mp.get("all", {})
        opp_5v5 = opp_mp.get("5v5", {})

        # Build comparison bars
        bars = []
        bars.append(cmp_bar("xGF% (5v5)", ott_5v5.get("xGFpct", 0.5), opp_5v5.get("xGFpct", 0.5), "pct"))
        bars.append(cmp_bar("CF% (5v5)", ott_5v5.get("CFpct", 0.5), opp_5v5.get("CFpct", 0.5), "pct"))
        bars.append(cmp_bar("xGF% (All)", ott_all.get("xGFpct", 0.5), opp_all.get("xGFpct", 0.5), "pct"))
        bars.append(cmp_bar("GF/GP", ott_all.get("gfpg", 0), opp_all.get("gfpg", 0), "dec"))
        bars.append(cmp_bar("GA/GP", ott_all.get("gapg", 0), opp_all.get("gapg", 0), "dec", higher_better=False))
        bars.append(cmp_bar("CF% (All)", ott_all.get("CFpct", 0.5), opp_all.get("CFpct", 0.5), "pct"))

        cards.append(f'''<details class="gc-detail{a5}">
<summary class="gc"><div><div class="gd">{g["date"]}</div><div class="go">{prefix}{g["opp"]}</div></div><div style="display:flex;align-items:center;gap:8px"><div style="font-size:10px;color:var(--text-muted)">{opp_record} ({opp_pts}p)</div><div class="gl {loc_class}">{loc_text}</div></div></summary>
<div class="gc-expand">
  <div class="cmp-header"><span style="color:var(--sens-red);font-weight:700">OTT</span><span style="color:var(--text-muted);font-size:10px">MATCHUP</span><span style="font-weight:700">{opp}</span></div>
  {"".join(bars)}
</div></details>''')

    return f'''<div class="stitle"><span class="dot"></span> Remaining Schedule — {len(remaining)} Games</div>
<p style="font-size:11px;color:var(--text-secondary);margin-bottom:12px">Click any game for head-to-head advanced metrics (MoneyPuck)</p>
<div class="legend">
  <div class="legend-item"><div class="ldot" style="background:var(--yellow)"></div> vs. above-.500</div>
  <div class="legend-item"><div class="ldot" style="background:var(--green)"></div> Home</div>
  <div class="legend-item"><div class="ldot" style="background:var(--red)"></div> Away</div>
</div>
<div class="sched-grid">{"".join(cards)}</div>
<div style="margin-top:20px"><div class="stitle"><span class="dot"></span> Schedule Breakdown</div>
<div class="pgrid">
  <div class="pcard"><div class="pct">Home / Away</div><div class="pnum">{home_count} <span style="font-size:16px;color:var(--text-muted)">/</span> {away_count}</div><div class="pdesc">{home_count} home, {away_count} road.</div></div>
  <div class="pcard"><div class="pct">vs. Above .500</div><div class="pnum" style="color:var(--yellow)">{above500_count}</div><div class="pdesc">{above500_count} of {len(remaining)} against above-.500 teams.</div></div>
</div></div>'''

def generate_html(sens, roster_html, standings_html, projections_html, schedule_html, vs500, mp_odds):
    now = datetime.now(timezone.utc).strftime("%B %-d, %Y at %-I:%M %p UTC")
    record = f"{sens['w']}-{sens['l']}-{sens['otl']}"
    remaining = 82 - sens["gp"]
    pace = round(sens["ptsPct"] * 2 * 82, 1)
    home_rec = f"{sens['homeW']}-{sens['homeL']}-{sens['homeOtl']}"
    road_rec = f"{sens['roadW']}-{sens['roadL']}-{sens['roadOtl']}"
    l10 = f"{sens['l10w']}-{sens['l10l']}-{sens['l10otl']}"
    w500, l500, otl500 = vs500
    ott_odds = mp_odds.get(TEAM, {})
    playoff_pct = ott_odds.get("playoffPct", 0)

    if playoff_pct >= 0.6: po_color = "var(--green)"
    elif playoff_pct >= 0.35: po_color = "var(--yellow)"
    else: po_color = "var(--red)"

    return f'''<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Ottawa Senators 2025-26 Dashboard</title>
<style>
:root{{--sens-red:#C52032;--sens-black:#1A1A2E;--sens-gold:#C8A951;--bg-dark:#0D0D1A;--bg-card:#16162A;--border:rgba(200,169,81,0.15);--text-primary:#EEEEF0;--text-secondary:#9999B0;--text-muted:#666680;--green:#22C55E;--red:#EF4444;--yellow:#EAB308;--blue:#3B82F6}}
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;background:var(--bg-dark);color:var(--text-primary);line-height:1.4}}
a{{color:var(--sens-gold)}}
.hero{{background:linear-gradient(135deg,var(--sens-black) 0%,#1a0a0e 50%,var(--sens-black) 100%);border-bottom:1px solid var(--border);padding:28px 24px 24px}}
.hero-inner{{max-width:1100px;margin:0 auto}}
.team-header{{display:flex;align-items:center;gap:14px;margin-bottom:18px}}
.team-logo{{width:52px;height:52px;background:var(--sens-red);border-radius:12px;display:flex;align-items:center;justify-content:center;font-weight:900;font-size:20px;color:white;box-shadow:0 4px 16px rgba(197,32,50,0.35);letter-spacing:-1px}}
.team-name{{font-size:26px;font-weight:800;letter-spacing:-0.5px}}.team-name b{{color:var(--sens-red)}}
.team-sub{{font-size:12px;color:var(--text-secondary);font-weight:500;margin-top:2px}}
.chips{{display:flex;gap:10px;flex-wrap:wrap}}
.chip{{background:rgba(255,255,255,0.06);border:1px solid var(--border);border-radius:10px;padding:10px 16px;min-width:90px;text-align:center}}
.chip .cl{{font-size:9px;text-transform:uppercase;letter-spacing:1.1px;color:var(--text-muted);font-weight:600;margin-bottom:3px}}
.chip .cv{{font-size:20px;font-weight:800;letter-spacing:-0.5px}}
.c-gold{{color:var(--sens-gold)}}.c-blue{{color:var(--blue)}}.c-yellow{{color:var(--yellow)}}.c-green{{color:var(--green)}}
.container{{max-width:1100px;margin:0 auto;padding:20px 24px 40px}}
input[name="tab"]{{display:none}}
.tab-bar{{display:flex;gap:3px;background:rgba(255,255,255,0.04);border-radius:10px;padding:3px;margin-bottom:20px;border:1px solid var(--border)}}
.tab-bar label{{flex:1;padding:9px 12px;border-radius:7px;font-size:12px;font-weight:600;text-align:center;cursor:pointer;color:var(--text-secondary);transition:all 0.15s}}
.tab-bar label:hover{{color:var(--text-primary);background:rgba(255,255,255,0.04)}}
.panel{{display:none}}
#tab-roster:checked~.tab-bar label[for="tab-roster"],#tab-standings:checked~.tab-bar label[for="tab-standings"],#tab-playoffs:checked~.tab-bar label[for="tab-playoffs"],#tab-schedule:checked~.tab-bar label[for="tab-schedule"]{{background:var(--sens-red);color:white;box-shadow:0 2px 10px rgba(197,32,50,0.3)}}
#tab-roster:checked~#p-roster,#tab-standings:checked~#p-standings,#tab-playoffs:checked~#p-playoffs,#tab-schedule:checked~#p-schedule{{display:block}}
.stitle{{font-size:15px;font-weight:700;margin-bottom:14px;display:flex;align-items:center;gap:8px}}
.stitle .dot{{width:7px;height:7px;border-radius:50%;background:var(--sens-red);flex-shrink:0}}
.tbl{{width:100%;border-collapse:collapse;font-size:12px}}
.tbl th{{background:rgba(255,255,255,0.04);padding:8px 10px;font-weight:600;font-size:9px;text-transform:uppercase;letter-spacing:0.8px;color:var(--text-muted);text-align:left;border-bottom:1px solid var(--border)}}
.tbl th.r,.tbl td.r{{text-align:right}}.tbl td{{padding:8px 10px;border-bottom:1px solid rgba(255,255,255,0.03);font-variant-numeric:tabular-nums}}
.tbl tbody tr:hover{{background:rgba(197,32,50,0.05)}}
.pname{{font-weight:600;white-space:nowrap}}
.pos-tag{{display:inline-block;font-size:9px;font-weight:700;padding:1px 5px;border-radius:3px;margin-left:5px;vertical-align:middle}}
.pos-fw{{background:rgba(59,130,246,0.15);color:#60A5FA}}.pos-d{{background:rgba(34,197,94,0.15);color:#4ADE80}}
.plus{{color:var(--green)}}.minus{{color:var(--red)}}.pts-lead{{color:var(--sens-gold);font-weight:700}}
.tbl .sens-row{{background:rgba(197,32,50,0.1)}}.tbl .sens-row td:first-child{{font-weight:700;color:var(--sens-red)}}
.tbl .cutoff td{{border-bottom:2px dashed var(--sens-gold)}}
.in{{color:var(--green);font-weight:600}}.out{{color:var(--text-muted)}}.tcol{{font-weight:600;white-space:nowrap}}.bpts{{font-weight:700}}
.div-label{{margin:20px 0 6px;font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:1px;color:var(--text-muted)}}
.div-label:first-child{{margin-top:0}}.sub-note{{font-size:11px;color:var(--text-secondary);margin-bottom:14px}}
.pgrid{{display:grid;grid-template-columns:1fr 1fr;gap:14px;margin-bottom:20px}}
@media(max-width:700px){{.pgrid{{grid-template-columns:1fr}}}}
.pcard{{background:var(--bg-card);border:1px solid var(--border);border-radius:12px;padding:18px}}
.pcard .pct{{font-size:10px;text-transform:uppercase;letter-spacing:1.1px;color:var(--text-muted);font-weight:600;margin-bottom:10px}}
.pcard .pnum{{font-size:32px;font-weight:900;letter-spacing:-1px;line-height:1;margin-bottom:5px}}
.pcard .pdesc{{font-size:11px;color:var(--text-secondary);line-height:1.5}}.pcard .pdesc strong{{color:var(--text-primary)}}
/* Playoff hero */
.playoff-hero{{background:var(--bg-card);border:1px solid var(--border);border-radius:14px;padding:24px;margin-bottom:20px;display:flex;align-items:center;gap:24px;flex-wrap:wrap}}
.po-big{{text-align:center;min-width:140px}}
.po-big-label{{font-size:10px;text-transform:uppercase;letter-spacing:1.2px;color:var(--text-muted);font-weight:600;margin-bottom:8px}}
.po-big-num{{font-size:48px;font-weight:900;letter-spacing:-2px;line-height:1}}
.po-big-src{{font-size:9px;color:var(--text-muted);margin-top:4px}}
.po-trio{{display:flex;gap:20px;flex-wrap:wrap}}
.po-stat{{text-align:center;min-width:60px}}
.po-stat-val{{font-size:22px;font-weight:800;letter-spacing:-0.5px}}
.po-stat-label{{font-size:9px;text-transform:uppercase;letter-spacing:0.8px;color:var(--text-muted);font-weight:600;margin-top:2px}}
.pbar-wrap{{margin:16px 0}}.pbar-labels{{display:flex;justify-content:space-between;font-size:10px;color:var(--text-muted);margin-bottom:5px}}
.pbar{{height:9px;background:rgba(255,255,255,0.06);border-radius:5px;position:relative;overflow:visible}}
.pbar-fill{{height:100%;border-radius:5px;background:linear-gradient(90deg,var(--sens-red),#E04050)}}
.pbar-mark{{position:absolute;top:-3px;width:2px;height:15px;background:var(--sens-gold);border-radius:1px}}
.pbar-mark span{{position:absolute;top:-16px;font-size:9px;color:var(--sens-gold);font-weight:600;white-space:nowrap;transform:translateX(-50%);left:50%}}
.pbar-bottom{{display:flex;justify-content:space-between;margin-top:6px;font-size:10px}}
.scenario{{background:var(--bg-card);border:1px solid var(--border);border-radius:10px;padding:14px 18px;margin-bottom:10px}}
.scenario .st{{font-weight:700;font-size:13px;margin-bottom:5px;display:flex;align-items:center;gap:7px}}
.scenario .sd{{font-size:11px;color:var(--text-secondary);line-height:1.5}}
.badge{{display:inline-block;font-size:9px;font-weight:700;padding:2px 7px;border-radius:4px;text-transform:uppercase;letter-spacing:0.5px}}
.badge-g{{background:rgba(34,197,94,0.15);color:var(--green)}}.badge-y{{background:rgba(234,179,8,0.15);color:var(--yellow)}}.badge-r{{background:rgba(239,68,68,0.15);color:var(--red)}}
.footnote{{margin-top:20px;padding:10px 14px;background:rgba(255,255,255,0.02);border:1px solid var(--border);border-radius:8px;font-size:10px;color:var(--text-muted);line-height:1.6}}
/* Schedule + expandable game cards */
.sched-grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:7px}}
.gc-detail{{border-radius:8px;overflow:hidden}}
.gc-detail.a5{{border-left:3px solid var(--yellow)}}
.gc-detail summary.gc{{background:var(--bg-card);border:1px solid var(--border);border-radius:8px;padding:10px 12px;display:flex;justify-content:space-between;align-items:center;cursor:pointer;list-style:none}}
.gc-detail summary.gc::-webkit-details-marker{{display:none}}
.gc-detail summary.gc::marker{{display:none;content:""}}
.gc-detail[open] summary.gc{{border-bottom-left-radius:0;border-bottom-right-radius:0;border-bottom:1px solid var(--border)}}
.gc .gd{{font-size:10px;color:var(--text-muted);font-weight:500}}.gc .go{{font-size:12px;font-weight:600}}
.gc .gl{{font-size:9px;padding:2px 5px;border-radius:3px;font-weight:600}}.gc .gl-h{{background:rgba(34,197,94,0.12);color:var(--green)}}.gc .gl-a{{background:rgba(239,68,68,0.12);color:var(--red)}}
.gc-expand{{background:var(--bg-card);border:1px solid var(--border);border-top:0;border-bottom-left-radius:8px;border-bottom-right-radius:8px;padding:14px}}
.cmp-header{{display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;font-size:13px}}
.cmp-row{{margin-bottom:8px}}
.cmp-label{{font-size:9px;text-transform:uppercase;letter-spacing:0.8px;color:var(--text-muted);font-weight:600;margin-bottom:3px}}
.cmp-vals{{display:flex;justify-content:space-between;font-size:12px;font-weight:700;margin-bottom:3px}}
.cmp-vs{{font-size:9px;color:var(--text-muted);font-weight:400}}
.cmp-bar{{display:flex;height:6px;border-radius:3px;overflow:hidden;gap:2px}}
.cmp-bar-l,.cmp-bar-r{{height:100%;border-radius:3px;opacity:0.6}}
.legend{{display:flex;gap:14px;margin-bottom:10px;font-size:10px;color:var(--text-secondary)}}.legend-item{{display:flex;align-items:center;gap:5px}}.ldot{{width:9px;height:9px;border-radius:3px}}
.scroll-x{{overflow-x:auto;-webkit-overflow-scrolling:touch}}
.updated{{text-align:center;padding:16px;font-size:10px;color:var(--text-muted)}}
</style></head><body>
<div class="hero"><div class="hero-inner">
  <div class="team-header">
    <div class="team-logo">OTT</div>
    <div><div class="team-name">Ottawa <b>Senators</b></div><div class="team-sub">2025-26 &middot; Updated {now}</div></div>
  </div>
  <div class="chips">
    <div class="chip"><div class="cl">Record</div><div class="cv">{record}</div></div>
    <div class="chip"><div class="cl">Points</div><div class="cv c-gold">{sens["pts"]}</div></div>
    <div class="chip"><div class="cl">Playoff %</div><div class="cv" style="color:{po_color}">{playoff_pct*100:.0f}%</div></div>
    <div class="chip"><div class="cl">vs .500+</div><div class="cv" style="color:var(--red)">{w500}-{l500}-{otl500}</div></div>
    <div class="chip"><div class="cl">Remaining</div><div class="cv c-blue">{remaining}</div></div>
    <div class="chip"><div class="cl">Pts Pace</div><div class="cv c-yellow">{pace}</div></div>
    <div class="chip"><div class="cl">GF / GA</div><div class="cv">{sens["gf"]} / {sens["ga"]}</div></div>
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
<div class="updated">Auto-updated via GitHub Actions &middot; NHL API + <a href="https://moneypuck.com">MoneyPuck</a> &middot; {now}</div>
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
    skaters = get_skaters(club_stats)
    goalies = get_goalies(club_stats)
    print(f"  {len(skaters)} skaters, {len(goalies)} goalies")

    print("Fetching NHL schedule...")
    schedule_data = fetch_schedule()
    remaining = get_remaining_schedule(schedule_data, above500)
    results = get_results(schedule_data)
    vs500 = compute_vs_above500(results, above500)
    print(f"  {len(remaining)} remaining, vs .500: {vs500[0]}-{vs500[1]}-{vs500[2]}")

    print("Fetching MoneyPuck playoff odds...")
    mp_odds = fetch_moneypuck_odds()
    ott_odds = mp_odds.get(TEAM, {})
    print(f"  Playoff: {ott_odds.get('playoffPct',0)*100:.1f}%, Proj: {ott_odds.get('projPts',0):.0f} pts")

    print("Fetching MoneyPuck team stats...")
    mp_stats = fetch_moneypuck_team_stats()
    print(f"  {len(mp_stats)} teams loaded")

    above500_count = sum(1 for g in remaining if g["above500"])
    home_count = sum(1 for g in remaining if g["loc"] == "home")
    away_count = sum(1 for g in remaining if g["loc"] == "away")

    print("Building HTML...")
    roster_html = build_roster_html(skaters, goalies)
    standings_html = build_standings_section(east_teams)
    projections_html = build_projections_html(sens, vs500, mp_odds, mp_stats)
    schedule_html = build_schedule_html(remaining, above500_count, home_count, away_count, team_records, mp_stats, mp_odds)
    html = generate_html(sens, roster_html, standings_html, projections_html, schedule_html, vs500, mp_odds)

    with open("index.html", "w") as f:
        f.write(html)
    print("Done! index.html generated.")

if __name__ == "__main__":
    main()
