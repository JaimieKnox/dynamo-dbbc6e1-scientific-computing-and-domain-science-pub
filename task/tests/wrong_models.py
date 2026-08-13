"""Fail-closed wrong-model contrasts against the contract estimator."""

from __future__ import annotations

import csv
from collections import defaultdict
from pathlib import Path

from estimator import (
    ATE_PLACES,
    SE_PLACES,
    STATUS_EMPTY,
    STATUS_IDENTIFIED,
    STATUS_UNIDENTIFIED,
    estimate_rows,
    load_tree,
    qround,
)


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _pack(
    census: list[dict[str, str]],
    ate: dict[str, float],
    identified: set[str],
    *,
    always_fill: bool,
) -> list[dict[str, str]]:
    out = []
    for rec in census:
        dom = rec["domain_id"]
        if always_fill:
            val = ate.get(dom, 0.0)
            out.append(
                {
                    "domain_id": dom,
                    "status": STATUS_IDENTIFIED,
                    "est_ate": qround(val, ATE_PLACES),
                    "est_se": qround(0.0, SE_PLACES),
                }
            )
            continue
        if dom not in ate and dom not in identified:
            out.append(
                {
                    "domain_id": dom,
                    "status": STATUS_EMPTY,
                    "est_ate": "",
                    "est_se": "",
                }
            )
            continue
        if dom not in identified:
            out.append(
                {
                    "domain_id": dom,
                    "status": STATUS_UNIDENTIFIED,
                    "est_ate": "",
                    "est_se": "",
                }
            )
            continue
        out.append(
            {
                "domain_id": dom,
                "status": STATUS_IDENTIFIED,
                "est_ate": qround(ate[dom], ATE_PLACES),
                "est_se": qround(0.0, SE_PLACES),
            }
        )
    return out


def _ols_always_fill(data_dir: Path) -> list[dict[str, str]]:
    households, census = load_tree(data_dir)
    by_dom: dict[str, dict[int, list[float]]] = defaultdict(lambda: {0: [], 1: []})
    for rec in households:
        if rec["responded"] != "1" or rec["y"].strip() == "":
            continue
        if rec["assigned"] not in {"0", "1"}:
            continue
        elig = float(rec["eligible_count"] or 0)
        if elig <= 0:
            continue
        by_dom[rec["domain_id"]][int(rec["assigned"])].append(float(rec["y"]) / elig)
    ate = {}
    for rec in census:
        arms = by_dom.get(rec["domain_id"], {0: [], 1: []})
        m1 = sum(arms[1]) / len(arms[1]) if arms[1] else 0.0
        m0 = sum(arms[0]) / len(arms[0]) if arms[0] else 0.0
        ate[rec["domain_id"]] = m1 - m0
    return _pack(census, ate, set(ate), always_fill=True)


def _interview_domain_ols(data_dir: Path) -> list[dict[str, str]]:
    interviews = _read_csv(data_dir / "interviews.csv")
    roster = {rec["hh_id"]: rec for rec in _read_csv(data_dir / "roster.csv")}
    census = _read_csv(data_dir / "census_domains.csv")
    by_dom: dict[str, dict[int, list[float]]] = defaultdict(lambda: {0: [], 1: []})
    for rec in interviews:
        if rec["responded"] != "1" or rec["y"].strip() == "":
            continue
        if rec.get("assigned", "") not in {"0", "1"}:
            continue
        ros = roster.get(rec["hh_id"])
        if ros is None or ros["eligible_count"].strip() == "":
            continue
        elig = float(ros["eligible_count"])
        if elig <= 0:
            continue
        by_dom[rec["interview_domain"]][int(rec["assigned"])].append(float(rec["y"]) / elig)
    ate = {}
    identified = set()
    for rec in census:
        arms = by_dom.get(rec["domain_id"], {0: [], 1: []})
        if arms[0] and arms[1]:
            identified.add(rec["domain_id"])
            ate[rec["domain_id"]] = (sum(arms[1]) / len(arms[1])) - (sum(arms[0]) / len(arms[0]))
        elif arms[0] or arms[1]:
            ate[rec["domain_id"]] = 0.0
    return _pack(census, ate, identified, always_fill=False)


def _listing_domain_overlap(data_dir: Path) -> list[dict[str, str]]:
    listings = _read_csv(data_dir / "listings.csv")
    interviews = {rec["hh_id"]: rec for rec in _read_csv(data_dir / "interviews.csv")}
    roster = {rec["hh_id"]: rec for rec in _read_csv(data_dir / "roster.csv")}
    census = _read_csv(data_dir / "census_domains.csv")
    by_dom: dict[str, dict[int, list[float]]] = defaultdict(lambda: {0: [], 1: []})
    for rec in listings:
        iv = interviews.get(rec["hh_id"])
        if iv is None or iv["responded"] != "1" or iv["y"].strip() == "":
            continue
        if iv.get("assigned", "") not in {"0", "1"}:
            continue
        ros = roster.get(rec["hh_id"])
        if ros is None or ros["eligible_count"].strip() == "":
            continue
        elig = float(ros["eligible_count"])
        if elig <= 0:
            continue
        by_dom[rec["listing_domain"]][int(iv["assigned"])].append(float(iv["y"]) / elig)
    ate = {}
    identified = set()
    for rec in census:
        arms = by_dom.get(rec["domain_id"], {0: [], 1: []})
        if arms[0] and arms[1]:
            identified.add(rec["domain_id"])
            ate[rec["domain_id"]] = (sum(arms[1]) / len(arms[1])) - (sum(arms[0]) / len(arms[0]))
        elif arms[0] or arms[1]:
            ate[rec["domain_id"]] = 0.0
    return _pack(census, ate, identified, always_fill=False)


def _hajek_ratio_of_totals(data_dir: Path) -> list[dict[str, str]]:
    from hajek_transcript import estimate_rows as hajek_rows

    return hajek_rows(data_dir)


def all_contrasts(data_dir: Path) -> bool:
    gold = estimate_rows(data_dir)
    gold_key = [(row["status"], row["est_ate"]) for row in gold]
    rivals = (
        _ols_always_fill(data_dir),
        _interview_domain_ols(data_dir),
        _listing_domain_overlap(data_dir),
        _hajek_ratio_of_totals(data_dir),
    )
    for rival in rivals:
        rival_key = [(row["status"], row["est_ate"]) for row in rival]
        if rival_key == gold_key:
            return False
    return True
