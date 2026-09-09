"""
xG difference by game state - Polonia Bytom vs Pogon Grodzisk Mazowiecki (match_id 4068759).

For each team and each game state (winning / drawing / losing): xG For, xG Against and
their difference, from StatsBomb event data.

Key assumption (PRE-SHOT): the game state of a shot is the scoreline BEFORE that shot.
A goal changes the state only for events that follow it, so a shot that makes it 1-0
counts as taken while drawing.

Run:  python src/xg_by_game_state.py
"""

from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
INPUT_PATH = PROJECT_ROOT / "data" / "match_4068759.csv"
OUTPUT_PATH = PROJECT_ROOT / "results" / "xg_by_game_state.csv"

# Home team first: fixes the sign of the tracked scoreline and the CSV row order.
HOME_TEAM = "Polonia Bytom"
# The club this submission is written for; the printed table takes its perspective,
# while the CSV keeps both teams.
REPORT_TEAM = "Pogoń Grodzisk Mazowiecki"
DECIMALS = 2

# Columns describing the event itself, as opposed to its nested freeze-frame or lineup
# children. Only these are needed here.
EVENT_COLUMNS = [
    "id", "index", "period", "timestamp", "minute", "second",
    "team_name", "event_type_name", "type_name", "outcome_name", "statsbomb_xg",
]

GAME_STATES = ["winning", "drawing", "losing"]
MIRROR_STATE = {"winning": "losing", "drawing": "drawing", "losing": "winning"}
STATE_LABELS_PL = {"winning": "prowadzenie", "drawing": "remis", "losing": "przegrywanie"}
TIMELINE_LABELS_PL = {"winning": "Pogoń prowadzi", "drawing": "Pogoń remisuje",
                      "losing": "Pogoń przegrywa"}


def game_state(goals_for, goals_against):
    """winning / drawing / losing for a scoreline seen from one team's side."""
    if goals_for > goals_against:
        return "winning"
    if goals_for < goals_against:
        return "losing"
    return "drawing"


def load_events(path):
    """Read the export and reduce it to one row per event.

    The file is in long format: StatsBomb's nested freeze_frame (shots) and lineup
    arrays are exploded into rows, so one Shot occupies one row per player in its
    freeze frame. Summing xG over raw rows multiplies every shot by that count.
    """
    raw = pd.read_csv(path, low_memory=False)

    # `id` is the event key, but before trusting drop_duplicates we check that every
    # column we read is constant within a repeated id - otherwise we would be keeping
    # an arbitrary row and never noticing.
    for column in EVENT_COLUMNS:
        assert raw.groupby("id")[column].nunique(dropna=False).max() <= 1, column

    # Deduplicate BEFORE sorting: pandas' default sort is not stable, so sorting first
    # would make the surviving row depend on the sort algorithm.
    events = raw.drop_duplicates(subset="id")[EVENT_COLUMNS].sort_values("index")
    events = events.reset_index(drop=True)

    assert len(events) == raw["id"].nunique()
    assert list(events["index"]) == list(range(1, len(events) + 1)), "Event index is not 1..N."

    # Seconds since kick-off. `timestamp` restarts at 00:00:00 in the second half, so
    # period-2 events are offset by the TRUE length of the first half (45:05 here)
    # rather than by a nominal 45:00.
    assert set(events["period"]) <= {1, 2}, (
        "Extra time present: the offset below would place periods 3+ as if they were "
        "the first half. This implementation is scoped to a two-period match."
    )
    parts = events["timestamp"].astype(str).str.split(":", expand=True)
    within_period = parts[0].astype(int) * 3600 + parts[1].astype(int) * 60 + parts[2].astype(float)
    first_half = within_period[(events["event_type_name"] == "Half End")
                               & (events["period"] == 1)].iloc[0]
    events["elapsed"] = within_period + (events["period"] == 2) * first_half

    shot_rows = raw[raw["event_type_name"] == "Shot"]
    unique_shots = events[events["event_type_name"] == "Shot"]
    print("Redukcja formatu long do jednego wiersza na zdarzenie")
    print(f"  wiersze w pliku    : {len(raw):>8}")
    print(f"  unikalne zdarzenia : {len(events):>8}")
    print(f"  wiersze Shot       : {len(shot_rows):>8}")
    print(f"  unikalne strzały   : {len(unique_shots):>8}")
    print(f"  naiwna suma xG     : {shot_rows['statsbomb_xg'].sum():>8.2f}")
    print(f"  poprawna suma xG   : {unique_shots['statsbomb_xg'].sum():>8.2f}\n")

    return events


def prepare_shots(events):
    """The shots in chronological order, validated as the match's only source of goals.

    Uses `statsbomb_xg`, the pre-shot model. The export also carries
    `shot_execution_xg` and goalkeeper models, which answer a different question.
    """
    shots = events[events["event_type_name"] == "Shot"].copy()
    shots["is_goal"] = shots["outcome_name"] == "Goal"
    shots = shots.reset_index(drop=True)

    assert shots["statsbomb_xg"].notna().all(), "Some shots have no xG value."
    assert shots["team_name"].notna().all(), "Some shots have no team."
    assert shots["index"].is_monotonic_increasing, "Shots are not in chronological order."

    # The scoreline is walked through shots, so a goal recorded outside a Shot event
    # would desynchronise it for the rest of the match without breaking any xG total.
    goals_from_shots = int(shots["is_goal"].sum())
    goals_conceded = int((events["type_name"] == "Goal Conceded").sum())
    assert goals_from_shots == goals_conceded, (
        f"{goals_from_shots} goals from shots but {goals_conceded} 'Goal Conceded' events."
    )
    assert not events["event_type_name"].isin(["Own Goal For", "Own Goal Against"]).any(), (
        "Own goals present; this implementation is scoped to a match without them."
    )

    return shots


def assign_game_states(shots, team):
    """Game state immediately BEFORE each shot, from `team`'s point of view."""
    goals_for = goals_against = 0
    states = []

    for shot in shots.itertuples(index=False):
        # The state is read BEFORE the score is updated. This ordering IS the pre-shot
        # assumption - the central methodological decision of the task.
        states.append(game_state(goals_for, goals_against))
        if shot.is_goal:
            if shot.team_name == team:
                goals_for += 1
            else:
                goals_against += 1

    return pd.Series(states, index=shots.index, name="game_state")


def score_intervals(events, shots, home_team):
    """The match split into intervals of constant scoreline, with clock bounds and length.

    A goal ends the interval it occurs in and starts the next one - the pre-shot rule
    expressed on the time axis.
    """
    goals = shots[shots["is_goal"]]
    half_ends = events[events["event_type_name"] == "Half End"]
    final_whistle = half_ends.loc[half_ends["elapsed"].idxmax()]

    boundaries = (
        [(0.0, "0:00")]
        + [(goal.elapsed, f"{goal.minute}:{goal.second:02d}") for goal in goals.itertuples(index=False)]
        + [(final_whistle["elapsed"], f"{final_whistle['minute']}:{final_whistle['second']:02d}")]
    )

    home_goals = away_goals = 0
    rows = []
    for position, ((start, from_clock), (end, to_clock)) in enumerate(zip(boundaries, boundaries[1:])):
        rows.append({
            "from_clock": from_clock,
            "to_clock": to_clock,
            "score": f"{home_goals}-{away_goals}",
            "home_goals": home_goals,
            "away_goals": away_goals,
            "minutes": (end - start) / 60.0,
        })
        if position < len(goals):
            if goals.iloc[position]["team_name"] == home_team:
                home_goals += 1
            else:
                away_goals += 1

    return pd.DataFrame(rows)


def build_result_table(intervals, shots, teams):
    """One row per (team, game state): xG For, xG Against, their difference, and context."""
    home_team = teams[0]
    rows = []

    for team in teams:
        states = assign_game_states(shots, team)
        by_team = shots["team_name"] == team

        minutes = {state: 0.0 for state in GAME_STATES}
        for interval in intervals.itertuples(index=False):
            scored, conceded = (
                (interval.home_goals, interval.away_goals) if team == home_team
                else (interval.away_goals, interval.home_goals)
            )
            minutes[game_state(scored, conceded)] += interval.minutes

        for state in GAME_STATES:
            in_state = states == state
            rows.append({
                "team": team,
                "game_state": state,
                "xg_for": shots.loc[in_state & by_team, "statsbomb_xg"].sum(),
                "xg_against": shots.loc[in_state & ~by_team, "statsbomb_xg"].sum(),
                "shots_for": int((in_state & by_team).sum()),
                "shots_against": int((in_state & ~by_team).sum()),
                "minutes": minutes[state],
            })

    result = pd.DataFrame(rows)
    result["xg_difference"] = result["xg_for"] - result["xg_against"]
    return result[["team", "game_state", "xg_for", "xg_against", "xg_difference",
                   "shots_for", "shots_against", "minutes"]]


def run_checks(shots, result, intervals, teams, decimals):
    """Sanity checks. Any failure here would mean a wrong answer, so the script stops."""
    home_team, away_team = teams
    tolerance = 1e-9

    home_states = assign_game_states(shots, home_team)
    away_states = assign_game_states(shots, away_team)
    assert len(home_states) == len(shots) and home_states.notna().all()
    assert set(home_states) <= set(GAME_STATES)
    assert (home_states.map(MIRROR_STATE) == away_states).all(), "Game states are not mirrored."
    assert len(intervals) == int(shots["is_goal"].sum()) + 1, "Interval count != goals + 1."

    for team in teams:
        team_rows = result[result["team"] == team]
        by_team = shots["team_name"] == team
        # The three states partition the team's shots, so xG and counts must both add up.
        assert abs(team_rows["xg_for"].sum() - shots.loc[by_team, "statsbomb_xg"].sum()) < tolerance
        assert abs(team_rows["xg_against"].sum() - shots.loc[~by_team, "statsbomb_xg"].sum()) < tolerance
        assert team_rows["shots_for"].sum() == by_team.sum()
        assert team_rows["shots_against"].sum() == (~by_team).sum()

    match_lengths = result.groupby("team")["minutes"].sum()
    assert match_lengths.max() - match_lengths.min() < tolerance
    assert ((result["xg_for"] - result["xg_against"] - result["xg_difference"]).abs() < tolerance).all()

    # Symmetry: both teams' shots in an interval are the same events seen from opposite
    # sides, so xGD_A(state) == -xGD_B(mirror state) and all six values sum to zero.
    for state in GAME_STATES:
        home_value = result.loc[(result["team"] == home_team)
                                & (result["game_state"] == state), "xg_difference"].iloc[0]
        away_value = result.loc[(result["team"] == away_team)
                                & (result["game_state"] == MIRROR_STATE[state]), "xg_difference"].iloc[0]
        assert abs(home_value + away_value) < tolerance, f"Symmetry broken for {state}."
    assert abs(result["xg_difference"].sum()) < tolerance

    # The rounded table in the README must still add up when a reader checks it by hand.
    rounded = result[["xg_for", "xg_against", "xg_difference"]].round(decimals)
    assert ((rounded["xg_for"] - rounded["xg_against"]).round(decimals)
            == rounded["xg_difference"]).all(), (
        f"At {decimals} dp the printed table no longer satisfies xGD = xGF - xGA."
    )

    print("Wszystkie kontrole przeszły.\n")


def render_report(result, intervals, shots, teams, decimals):
    """Polish report: the table from REPORT_TEAM's perspective, then the score timeline."""
    report_is_home = teams[0] == REPORT_TEAM

    lines = [
        f"Różnica xG według stanu meczu (stan sprzed strzału, perspektywa: {REPORT_TEAM})",
        "| Stan Pogoni | xG Pogoni | Strzały Pogoni | xG Polonii | Strzały Polonii | Różnica xG Pogoni |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for state in GAME_STATES:
        row = result[(result["team"] == REPORT_TEAM)
                     & (result["game_state"] == state)].iloc[0]
        difference = f"{row.xg_difference:+.{decimals}f}".replace("-", "−")
        lines.append(
            f"| {STATE_LABELS_PL[state]} | {row.xg_for:.{decimals}f} | {row.shots_for} | "
            f"{row.xg_against:.{decimals}f} | {row.shots_against} | **{difference}** |"
        )

    lines.append("\nPrzebieg wyniku")
    for interval in intervals.itertuples(index=False):
        scored, conceded = (
            (interval.home_goals, interval.away_goals) if report_is_home
            else (interval.away_goals, interval.home_goals)
        )
        # Whole minutes: the clock follows StatsBomb's convention (the second half
        # restarts at 45:00) while durations are true elapsed time; rounded to minutes
        # the two agree.
        span = f"{interval.from_clock} – {interval.to_clock}"
        lines.append(f"{span:>15}   {interval.score.replace('-', '–'):^5}   "
                     f"{TIMELINE_LABELS_PL[game_state(scored, conceded)]:<16} "
                     f"{round(interval.minutes):>2} min")

    final = intervals.iloc[-1]
    drawing = result[(result["team"] == REPORT_TEAM) & (result["game_state"] == "drawing")].iloc[0]
    lines += [
        f"\nWynik końcowy: {teams[0]} {final['home_goals']} - {final['away_goals']} {teams[1]}",
        f"Remis: {round(drawing.minutes)} z {round(intervals['minutes'].sum())} minut, "
        f"{drawing.shots_for + drawing.shots_against} z {len(shots)} strzałów.",
    ]
    return "\n".join(lines)


def main():
    events = load_events(INPUT_PATH)
    shots = prepare_shots(events)

    teams = [HOME_TEAM] + sorted(set(events["team_name"].dropna()) - {HOME_TEAM})
    assert len(teams) == 2, f"Expected exactly two teams, found {teams}."
    assert REPORT_TEAM in teams, f"{REPORT_TEAM} not in {teams}."

    intervals = score_intervals(events, shots, teams[0])
    result = build_result_table(intervals, shots, teams)
    run_checks(shots, result, intervals, teams, DECIMALS)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    # Force LF: pandas writes CRLF by default, which would make every run dirty the
    # repository with a pure line-ending diff.
    result.to_csv(OUTPUT_PATH, index=False, lineterminator="\n")

    print(render_report(result, intervals, shots, teams, DECIMALS))
    print(f"\nKomplet sześciu wierszy i minuty: {OUTPUT_PATH.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
