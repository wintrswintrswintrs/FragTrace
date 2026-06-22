"""
stats_engine.py

Turns a parsed CS2 demo (via awpy) into a Leetify-style stats payload:
per-player core stats, advanced stats (KAST, ADR, Rating, clutches, entries,
multi-kills, utility), round-by-round timeline, and match metadata.

Column names used here are verified against awpy 2.0.2 source
(awpy/parsers/events.py, awpy/parsers/utils.py, awpy/stats/*.py):

  kills (demo.kills):
    attacker_name, attacker_steamid, attacker_side,
    victim_name, victim_steamid, victim_side,
    assister_name, assister_steamid, assister_side,
    weapon, headshot, tick, round_num
    (assistedflash is a native CS2 player_death field passed through
    unrenamed; guarded defensively below in case a given demo lacks it)

  damages (demo.damages):
    attacker_name, attacker_steamid, attacker_side,
    victim_name, victim_steamid, victim_side, victim_health,
    dmg_health, dmg_health_real, weapon, tick, round_num

  rounds (demo.rounds):
    round_num, start, freeze_end, end, winner, reason, bomb_plant, bomb_site

Note: "team_name"/"team_clan_name" columns get renamed to "*_side" by
awpy's fix_common_names, so there is no separate clan-name column to rely
on post-parse — "side" (ct/t) is the reliable grouping key, not clan tag.
"""

from __future__ import annotations

from typing import Any

import polars as pl
from awpy import Demo
from awpy.stats import adr, kast, rating


def _safe_div(a: float, b: float) -> float:
    return a / b if b else 0.0


def parse_demo_file(path: str) -> dict[str, Any]:
    """Parse a .dem file at `path` and return a full stats payload as a dict."""
    dem = Demo(path)
    dem.parse()

    header = dem.header or {}
    rounds_df = dem.rounds
    total_rounds = rounds_df.height if rounds_df is not None else 0

    # --- built-in awpy stats: ADR, KAST, Rating ---------------------------
    adr_df = _filter_side(adr(dem), "all")
    kast_df = _filter_side(kast(dem, trade_length_in_seconds=5), "all")
    rating_df = _filter_side(rating(dem), "all")

    # --- per-player raw aggregates from kills/damages ---------------------
    player_stats = _build_base_player_stats(dem, total_rounds)

    for row in adr_df.iter_rows(named=True):
        sid = str(row["steamid"])
        if sid in player_stats:
            player_stats[sid]["adr"] = round(row["adr"], 1)

    for row in kast_df.iter_rows(named=True):
        sid = str(row["steamid"])
        if sid in player_stats:
            player_stats[sid]["kast"] = round(row["kast"], 1)

    for row in rating_df.iter_rows(named=True):
        sid = str(row["steamid"])
        if sid in player_stats:
            player_stats[sid]["rating"] = round(row["rating"], 2)
            player_stats[sid]["impact"] = round(row["impact"], 2)
            player_stats[sid]["rounds_played"] = row.get("n_rounds", total_rounds)

    # --- extra stats not provided by awpy.stats out of the box -------------
    _add_multikills(dem, player_stats)
    _add_entries(dem, player_stats)
    _add_clutches(dem, player_stats)
    _add_utility(dem, player_stats)
    _add_headshot_pct(player_stats)
    _add_derived_ratios(player_stats, total_rounds)
    _assign_team_labels(dem, player_stats)

    # --- round timeline -----------------------------------------------------
    timeline = _build_round_timeline(dem)

    payload = {
        "map": header.get("map_name", "unknown"),
        "total_rounds": total_rounds,
        "final_score": _final_score(rounds_df),
        "players": sorted(
            player_stats.values(), key=lambda p: p["rating"], reverse=True
        ),
        "rounds": timeline,
    }
    return payload


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _filter_side(df: pl.DataFrame, side: str) -> pl.DataFrame:
    if "side" in df.columns:
        return df.filter(pl.col("side") == side)
    return df


def _new_player_record(sid: str, name: str, total_rounds: int) -> dict[str, Any]:
    return {
        "steamid": sid,
        "name": name,
        "team": "",
        "kills": 0,
        "deaths": 0,
        "assists": 0,
        "headshots": 0,
        "hs_pct": 0.0,
        "adr": 0.0,
        "kast": 0.0,
        "rating": 0.0,
        "impact": 0.0,
        "damage": 0,
        "rounds_played": total_rounds,
        "multi_kills": {"2k": 0, "3k": 0, "4k": 0, "5k": 0},
        "entry_kills": 0,
        "entry_attempts": 0,
        "clutches_won": 0,
        "clutches_played": 0,
        "utility_damage": 0,
        "flash_assists": 0,
        "kd_ratio": 0.0,
        "kpr": 0.0,
        "dpr": 0.0,
    }


def _build_base_player_stats(dem: Demo, total_rounds: int) -> dict[str, dict[str, Any]]:
    """Initialize per-player stat dicts from kills/damages tables."""
    stats: dict[str, dict[str, Any]] = {}

    def ensure(sid: str, name: str) -> None:
        if sid and sid not in stats:
            stats[sid] = _new_player_record(sid, name or "Unknown", total_rounds)

    kills_df = dem.kills
    if kills_df is not None and kills_df.height > 0:
        cols = set(kills_df.columns)
        has_assistedflash = "assistedflash" in cols

        for row in kills_df.iter_rows(named=True):
            atk_sid = _norm_sid(row.get("attacker_steamid"))
            vic_sid = _norm_sid(row.get("victim_steamid"))
            ast_sid = _norm_sid(row.get("assister_steamid"))

            if atk_sid:
                ensure(atk_sid, row.get("attacker_name"))
            if vic_sid:
                ensure(vic_sid, row.get("victim_name"))
            if ast_sid:
                ensure(ast_sid, row.get("assister_name"))

            # Kill credit (exclude world/self where attacker missing or equals victim)
            if atk_sid and atk_sid != vic_sid:
                stats[atk_sid]["kills"] += 1
                if row.get("headshot"):
                    stats[atk_sid]["headshots"] += 1

            if vic_sid:
                stats[vic_sid]["deaths"] += 1

            if ast_sid:
                stats[ast_sid]["assists"] += 1
                if has_assistedflash and row.get("assistedflash"):
                    stats[ast_sid]["flash_assists"] += 1

    damages_df = dem.damages
    if damages_df is not None and damages_df.height > 0:
        for row in damages_df.iter_rows(named=True):
            atk_sid = _norm_sid(row.get("attacker_steamid"))
            if not atk_sid:
                continue
            ensure(atk_sid, row.get("attacker_name"))
            dmg = row.get("dmg_health_real")
            if dmg is None:
                dmg = row.get("dmg_health") or 0
            stats[atk_sid]["damage"] += int(dmg or 0)

    return stats


def _norm_sid(value: Any) -> str:
    if value is None:
        return ""
    return str(value)


def _add_headshot_pct(player_stats: dict[str, dict[str, Any]]) -> None:
    for p in player_stats.values():
        p["hs_pct"] = round(_safe_div(p["headshots"], p["kills"]) * 100, 1)


def _add_derived_ratios(player_stats: dict[str, dict[str, Any]], total_rounds: int) -> None:
    for p in player_stats.values():
        p["kd_ratio"] = round(_safe_div(p["kills"], p["deaths"]), 2)
        rp = p["rounds_played"] or total_rounds or 1
        p["kpr"] = round(_safe_div(p["kills"], rp), 2)
        p["dpr"] = round(_safe_div(p["deaths"], rp), 2)


def _add_multikills(dem: Demo, player_stats: dict[str, dict[str, Any]]) -> None:
    """Count 2k/3k/4k/5k (ace) rounds per player based on kills per round."""
    kills_df = dem.kills
    if kills_df is None or kills_df.height == 0:
        return
    # Exclude rows with no attacker (world damage) before counting
    valid = kills_df.filter(pl.col("attacker_steamid").is_not_null())
    counts = valid.group_by(["attacker_steamid", "round_num"]).agg(pl.len().alias("n"))
    for row in counts.iter_rows(named=True):
        sid = _norm_sid(row["attacker_steamid"])
        n = row["n"]
        if sid not in player_stats or n < 2:
            continue
        bucket = {2: "2k", 3: "3k", 4: "4k"}.get(n, "5k" if n >= 5 else None)
        if bucket:
            player_stats[sid]["multi_kills"][bucket] += 1


def _add_entries(dem: Demo, player_stats: dict[str, dict[str, Any]]) -> None:
    """Entry kill = first kill of the round (opening duel winner)."""
    kills_df = dem.kills
    if kills_df is None or kills_df.height == 0:
        return
    first_kills = kills_df.sort("tick").group_by("round_num", maintain_order=False).first()
    for row in first_kills.iter_rows(named=True):
        atk_sid = _norm_sid(row.get("attacker_steamid"))
        vic_sid = _norm_sid(row.get("victim_steamid"))
        if atk_sid and atk_sid in player_stats:
            player_stats[atk_sid]["entry_kills"] += 1
            player_stats[atk_sid]["entry_attempts"] += 1
        if vic_sid and vic_sid in player_stats:
            player_stats[vic_sid]["entry_attempts"] += 1


def _add_clutches(dem: Demo, player_stats: dict[str, dict[str, Any]]) -> None:
    """
    Lightweight clutch detection (v1 heuristic): within each round, replay
    kills in tick order, tracking which side's roster (derived from
    attacker_side/victim_side appearing in that round's kills) has been
    reduced to exactly one player while the opposing side still has at
    least one alive. That lone player is the "clutcher" for the round; if
    their side wins the round, credit a clutch win.

    Limitation: roster reconstruction here uses only players who appear in
    the kills table for that round, which is accurate for who's alive/dead
    but can undercount a full 5-man roster if some players neither kill
    nor die in a round (e.g. a passive survivor). This is a known v1
    approximation — a fully precise version would walk demo.ticks
    health/is_alive per player per round, which is more expensive to
    compute and can be added later if clutch accuracy needs to improve.
    """
    kills_df = dem.kills
    rounds_df = dem.rounds
    if kills_df is None or rounds_df is None or kills_df.height == 0:
        return

    winners = {r["round_num"]: r.get("winner") for r in rounds_df.iter_rows(named=True)}

    for rnd, winner in winners.items():
        round_kills = kills_df.filter(pl.col("round_num") == rnd).sort("tick")
        if round_kills.height == 0:
            continue

        side_of: dict[str, str] = {}
        for row in round_kills.iter_rows(named=True):
            for prefix in ("attacker", "victim", "assister"):
                sid = _norm_sid(row.get(f"{prefix}_steamid"))
                side = row.get(f"{prefix}_side")
                if sid and side:
                    side_of[sid] = side

        alive_t = {sid for sid, s in side_of.items() if s == "t"}
        alive_ct = {sid for sid, s in side_of.items() if s == "ct"}

        clutcher = None
        clutch_side = None
        for row in round_kills.iter_rows(named=True):
            vic_sid = _norm_sid(row.get("victim_steamid"))
            vic_side = row.get("victim_side")
            if vic_side == "t":
                alive_t.discard(vic_sid)
            elif vic_side == "ct":
                alive_ct.discard(vic_sid)

            if clutcher is None:
                if len(alive_t) == 1 and len(alive_ct) >= 1:
                    clutcher = next(iter(alive_t))
                    clutch_side = "t"
                elif len(alive_ct) == 1 and len(alive_t) >= 1:
                    clutcher = next(iter(alive_ct))
                    clutch_side = "ct"

        if clutcher and clutcher in player_stats:
            player_stats[clutcher]["clutches_played"] += 1
            if winner and winner.lower() == clutch_side:
                player_stats[clutcher]["clutches_won"] += 1


def _add_utility(dem: Demo, player_stats: dict[str, dict[str, Any]]) -> None:
    """Sum utility (HE / molotov / incendiary) damage per attacker."""
    damages_df = dem.damages
    if damages_df is None or damages_df.height == 0:
        return
    util_weapons = ["hegrenade", "molotov", "incgrenade", "inferno"]
    util = damages_df.filter(pl.col("weapon").is_in(util_weapons))
    for row in util.iter_rows(named=True):
        sid = _norm_sid(row.get("attacker_steamid"))
        if sid in player_stats:
            dmg = row.get("dmg_health_real")
            if dmg is None:
                dmg = row.get("dmg_health") or 0
            player_stats[sid]["utility_damage"] += int(dmg or 0)


def _assign_team_labels(dem: Demo, player_stats: dict[str, dict[str, Any]]) -> None:
    """
    Label each player with the side ("ct"/"t") they played most often, for
    grouping in the UI (team rosters flip at halftime, so this is a
    best-effort "primary side" label rather than a fixed team name).
    """
    kills_df = dem.kills
    if kills_df is None or kills_df.height == 0:
        return
    side_counts: dict[str, dict[str, int]] = {}
    for row in kills_df.iter_rows(named=True):
        sid = _norm_sid(row.get("attacker_steamid"))
        side = row.get("attacker_side")
        if sid and side:
            side_counts.setdefault(sid, {}).setdefault(side, 0)
            side_counts[sid][side] += 1
    for sid, counts in side_counts.items():
        if sid in player_stats:
            primary = max(counts, key=counts.get)
            player_stats[sid]["team"] = primary


def _build_round_timeline(dem: Demo) -> list[dict[str, Any]]:
    rounds_df = dem.rounds
    kills_df = dem.kills
    if rounds_df is None:
        return []

    timeline = []
    for row in rounds_df.iter_rows(named=True):
        rnd = row["round_num"]
        round_kills = []
        if kills_df is not None:
            rk = kills_df.filter(pl.col("round_num") == rnd).sort("tick")
            for k in rk.iter_rows(named=True):
                round_kills.append(
                    {
                        "attacker": k.get("attacker_name"),
                        "victim": k.get("victim_name"),
                        "weapon": k.get("weapon"),
                        "headshot": bool(k.get("headshot")),
                    }
                )
        timeline.append(
            {
                "round_num": rnd,
                "winner": row.get("winner"),
                "reason": row.get("reason"),
                "bomb_site": row.get("bomb_site"),
                "kills": round_kills,
            }
        )
    return timeline


def _final_score(rounds_df: pl.DataFrame | None) -> dict[str, int]:
    if rounds_df is None or rounds_df.height == 0:
        return {"ct": 0, "t": 0}
    winner_col = rounds_df["winner"]
    lowered = winner_col.cast(pl.Utf8).str.to_lowercase()
    ct = (lowered == "ct").sum()
    t = (lowered == "t").sum()
    return {"ct": int(ct), "t": int(t)}
