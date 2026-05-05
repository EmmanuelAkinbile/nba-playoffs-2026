# NBA Playoffs 2026 — Role Player & Performance Analytics

![Power BI](https://img.shields.io/badge/Power%20BI-Dashboard-F2C811?logo=powerbi&logoColor=black)
![Python](https://img.shields.io/badge/Python-ETL%20Pipeline-3776AB?logo=python&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Supabase-4169E1?logo=postgresql&logoColor=white)
![Status](https://img.shields.io/badge/Status-Live%20%7C%20Daily%20Updates-brightgreen)

An end-to-end analytics project tracking the **2025–26 NBA Playoffs** in real time. A Python ETL pipeline pulls data daily from the NBA Stats API, loads it into a hosted PostgreSQL database on Supabase, and powers a four-page Power BI dashboard covering playoff results, team efficiency, player performance, and role player impact.

> **Live dashboard updates automatically each day as new playoff games are played.**

---

## Context & Business Problem

The NBA Playoffs are the highest-stakes games of the season — and one of the most analytically rich environments in professional sports. While star players dominate the headlines, championship teams are routinely defined by the contributions of their supporting cast: the "role players" who provide reliable scoring, defense, and efficiency without the primary ball-handling responsibility.

This project asks a focused question: **who is actually carrying teams beyond their stars, and how do those contributions shift across playoff rounds?**

The analysis is framed around three business-style questions:

1. **Team efficiency** — Which teams translate regular season performance into playoff success, and how does pace and scoring change under playoff conditions?
2. **Player performance** — How do individual players perform relative to their regular season baseline, and does scoring output vary by position or age?
3. **The supporting cast** — Which role players are overperforming their regular season numbers, and what share of team scoring comes from non-star contributors?

---

## Dashboard Overview

The dashboard is organized across four pages, each targeting a distinct analytical lens.

### Page 1 — Playoff Picture
High-level snapshot of the current state of the playoffs. KPI cards display total games played, teams remaining, current round, and average margin of victory. A series tracker shows current matchups and series leaders. The Latest Games table logs recent results in real time. Supporting visuals include a Top 10 Playoff Scorers horizontal bar chart and a Teams by Points treemap showing cumulative scoring output per team.

### Page 2 — Team Overview
Cross-filters by conference, team, and round. Six KPI cards surface aggregate metrics: Regular Season PPG, Playoff PPG, Regular Season Pace, Playoff Pace, Playoff RPG, and Playoff APG. A dual bar chart compares Regular vs. Playoff scoring for each team side by side. A scatter plot maps each team's offensive rating against their defensive rating, visually segmenting efficient teams from inefficient ones. A detailed table below shows regular season wins, win percentage, PPG, and pace for each playoff team.

### Page 3 — Player Analysis
Cross-filters by team, round, position, and role (Role Player / Star). A bubble scatter chart plots average playoff points against age, with bubble size representing scoring volume and colour distinguishing role players from stars. A bar chart breaks down Playoff PPG by position (G, F, C). A detailed player table lists every player's age, years in league, and full playoff stat line — PPG, FG%, RPG, APG, SPG, and BPG.

### Page 4 — The Supporting Cast
The focal page of the project. A stacked bar chart shows each team's scoring split between role player points and star points, surfacing which teams are the most dependent on their supporting cast vs. their stars. A ranked table lists the top role players by Playoff PPG alongside their Regular Season PPG, highlighting over- and under-performers. A donut chart shows the league-wide bench vs. starter scoring split (74.5% starters, 25.5% bench). A bar chart breaks down average Playoff PPG by experience level — Veteran, Seasoned Veteran, Early Career, Sophomore, and Rookie.

---

## Key Insights

- **Role players are outperforming their regular season baselines.** Players like RJ Barrett (19.26 → 24.14), Scottie Barnes (18.10 → 24.14), and Tobias Harris (13.27 → 21.57) are all posting significantly higher scoring averages in the playoffs than during the regular season.
- **Guards lead in playoff scoring by position** (10.40 PPG), slightly ahead of forwards (9.39) and centres (9.19) — consistent with the guard-heavy offensive systems favoured by top playoff teams.
- **Veterans and Seasoned Veterans post the highest average playoff PPG**, with both groups outscoring Early Career players — suggesting playoff experience is a measurable performance factor.
- **The bench contributes ~25% of total scoring league-wide**, though this figure varies considerably by team. Teams like Toronto and San Antonio show notably higher role player scoring share, indicating less star-dependence.
- **Playoff pace drops noticeably from regular season pace** for most teams (e.g. 100.40 → 96.80 for OKC), consistent with the slower, more defensive style the postseason typically demands.
- **OKC and the New York Knicks lead the field in playoff PPG**, posting 122.80 and the top scoring outputs respectively despite both transitioning from young regular season squads.

---

## Architecture & Pipeline

```
nba_api (NBA Stats API)
        │
        ▼
   Python ETL (pandas + SQLAlchemy)
   ├── fetch_teams.py         → Static — runs once
   ├── fetch_players.py       → Static — runs once
   ├── fetch_team_standings.py → Static — runs once
   ├── fetch_games.py         → Append-only — new games only
   ├── fetch_stats.py         → Append (game stats) + Delete/Reinsert (aggregates)
   └── fetch_team_stats.py    → Delete/Reinsert — refreshed daily
        │
        ▼
   Supabase PostgreSQL (hosted, Canada Central)
   8 tables — see schema below
        │
        ▼
   Power BI Desktop (psqlODBC connection)
   DAX measures for all aggregations
        │
        ▼
   Power BI Service (published via OneDrive sync)
   Auto-refreshes daily via scheduled dataset refresh
```

### Pipeline Logic by Table Type

| Table Type | Tables | Behaviour |
|---|---|---|
| Static | `teams`, `players`, `team_standings`, `player_regular_season_stats` | Populated once — skipped on all subsequent runs |
| Append-only | `games`, `player_game_stats` | New rows inserted only — existing records never overwritten |
| Delete + Reinsert | `player_playoff_stats`, `team_stats` | Cleared and recalculated on every run to reflect updated totals |

### Scheduling

The pipeline runs daily via **Windows Task Scheduler**, which calls `run_pipeline.py` — a single orchestrator script that chains all six fetch scripts in the correct dependency order. Power BI Service refreshes the dataset on a matching daily schedule.

---

## Database Schema

| Table | Description |
|---|---|
| `teams` | Static — team name, abbreviation, conference, division |
| `players` | Roster info — position, age, years in league, experience level, All-Star selections |
| `games` | Playoff game results — scores, round, home/away team IDs |
| `player_game_stats` | Per-player per-game box score stats (append-only) |
| `player_regular_season_stats` | 2025–26 regular season totals per player — loaded once |
| `player_playoff_stats` | Aggregated playoff stats by player and round — refreshed daily |
| `team_standings` | Regular season W/L record, home/away splits, conference rank |
| `team_stats` | Playoff team averages (PPG, rebounds, assists, pace) — refreshed daily |

---

## Key Design Decisions

**Totals stored, averages computed in DAX.** All raw statistics (points, rebounds, assists, etc.) are stored as totals in the database. All per-game averages (PPG, RPG, APG) are calculated in Power BI as DAX measures. This keeps the pipeline flexible — no schema changes are needed when the number of games changes.

**Append-only for game-level data.** `player_game_stats` and `games` are never overwritten. The pipeline checks for existing `game_id` / `game_id + player_id` pairs on each run and inserts only new rows. This protects historical data and makes the pipeline safe for repeated daily execution.

**Delete + reinsert for aggregate tables.** `player_playoff_stats` and `team_stats` are cleared and recalculated on each run. Since these are derived summaries, a full refresh is simpler and more reliable than partial upserts.

**`is_star` as a DAX measure, not a stored column.** Player classification (Star vs. Role Player) is based on regular season PPG. This logic lives in Power BI as a DAX measure rather than a stored boolean, keeping it adjustable without a database migration.

**Retry logic on all API calls.** Every `nba_api` request uses a `fetch_with_retry` wrapper (5 attempts, 10-second sleep between retries) to handle rate limiting and transient failures gracefully.

---

## Tech Stack

| Layer | Tool |
|---|---|
| Data source | `nba_api` Python library (unofficial NBA Stats API wrapper) |
| ETL | Python — `pandas`, `SQLAlchemy` |
| Database | Supabase PostgreSQL (hosted, Canada Central region) |
| BI / Visualization | Power BI Desktop + Power BI Service |
| Scheduling | Windows Task Scheduler |
| Version control | Git / GitHub |

---

## Project Structure

```
nba-playoffs-2026/
├── src/
│   ├── config.py                    # Database connection config
│   ├── db.py                        # SQLAlchemy engine + upsert utility
│   ├── fetch_teams.py
│   ├── fetch_players.py
│   ├── fetch_games.py
│   ├── fetch_stats.py               # Player game stats + playoff aggregates
│   ├── fetch_team_standings.py
│   └── fetch_team_stats.py
├── run_pipeline.py                  # Orchestrator — runs all scripts in sequence
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```

---

## Setup

### 1. Clone the repo

```bash
git clone https://github.com/EmmanuelAkinbile/nba-playoffs-2026.git
cd nba-playoffs-2026
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure environment variables

```bash
cp .env.example .env
```

Edit `.env` with your Supabase connection string:

```
DATABASE_URL=postgresql://user:password@host:5432/postgres
```

### 4. Run the pipeline

```bash
python run_pipeline.py
```

Static tables are populated on first run and skipped on all subsequent runs. Playoff data updates automatically on every execution.

---

## Limitations & Notes

**NBA API rate limiting.** The `nba_api` library is an unofficial wrapper around the NBA Stats website and is subject to undocumented rate limits. Aggressive request patterns trigger throttling, which required adding retry logic and sleep intervals throughout the pipeline. All fetch functions use a `fetch_with_retry` wrapper with 5 attempts and a 10-second sleep between retries.

**Player ID scope.** The players table is populated from active playoff team rosters. Occasionally, a player who appears in a box score (a two-way contract player, late-season addition, or emergency signing) is not captured in the initial roster fetch. This required dropping the foreign key constraint on `player_game_stats.player_id` to allow those rows to insert without failing.

**Round detection from game IDs.** The `nba_api` does not return a clean "round" field for playoff games. Round is derived by parsing a positional segment of the `game_id` string. This logic was debugged during the build and confirmed accurate for the current season's game ID format.

**Regular season context is static.** Regular season stats and standings are loaded once at pipeline setup and not updated during the playoffs. Comparative metrics (e.g. Playoff PPG vs. Regular Season PPG) use end-of-season regular season figures as the baseline, which is the appropriate benchmark for playoff performance analysis.

**Data source dependency.** The pipeline depends entirely on the unofficial `nba_api` library. Any changes to the underlying NBA Stats website structure could break data retrieval without notice.

---

## Live Dashboard

🔗 [View the live Power BI dashboard](#) *(link to be added after publish)*

---

*Built by Emmanuel Akinbile · [GitHub](https://github.com/EmmanuelAkinbile) · [LinkedIn](https://www.linkedin.com/in/emmanuelajayi-akinbile/)*
