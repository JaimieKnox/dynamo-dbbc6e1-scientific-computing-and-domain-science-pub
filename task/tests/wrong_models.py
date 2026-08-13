"""Fail-closed wrong-model contrasts against the contract estimator."""

from __future__ import annotations

import csv
from collections import defaultdict
from decimal import Decimal
from pathlib import Path

from estimator import estimate_rows, load_tree, qround, RATE_PLACES, TOTAL_PLACES


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _pack(census: list[dict[str, str]], rates: dict[str, float]) -> list[dict[str, str]]:
    out = []
    for rec in census:
        rate = rates.get(rec["domain_id"], 0.0)
        rate_s = qround(rate, RATE_PLACES)
        total = float(Decimal(rate_s) * Decimal(rec["eligible_count_census"]))
        out.append(
            {
                "domain_id": rec["domain_id"],
                "est_total": qround(total, TOTAL_PLACES),
                "est_rate": rate_s,
            }
        )
    return out


def _unweighted_means(data_dir: Path) -> list[dict[str, str]]:
    households, census = load_tree(data_dir)
    by_dom: dict[str, list[float]] = defaultdict(list)
    for rec in households:
        if rec["responded"] != "1":
            continue
        if rec["y"].strip() == "":
            continue
        elig = float(rec["eligible_count"] or 0)
        if elig <= 0:
            continue
        by_dom[rec["domain_id"]].append(float(rec["y"]) / elig)
    rates = {}
    for rec in census:
        vals = by_dom.get(rec["domain_id"], [])
        rates[rec["domain_id"]] = float(sum(vals) / len(vals)) if vals else 0.0
    return _pack(census, rates)


def _interview_domain_means(data_dir: Path) -> list[dict[str, str]]:
    interviews = _read_csv(data_dir / "interviews.csv")
    roster = {rec["hh_id"]: rec for rec in _read_csv(data_dir / "roster.csv")}
    census = _read_csv(data_dir / "census_domains.csv")
    by_dom: dict[str, list[float]] = defaultdict(list)
    for rec in interviews:
        if rec["responded"] != "1" or rec["y"].strip() == "":
            continue
        ros = roster.get(rec["hh_id"])
        if ros is None or ros["eligible_count"].strip() == "":
            continue
        elig = float(ros["eligible_count"])
        if elig <= 0:
            continue
        by_dom[rec["interview_domain"]].append(float(rec["y"]) / elig)
    rates = {}
    for rec in census:
        vals = by_dom.get(rec["domain_id"], [])
        rates[rec["domain_id"]] = float(sum(vals) / len(vals)) if vals else 0.0
    return _pack(census, rates)


def _uncollapsed_listing_direct(data_dir: Path) -> list[dict[str, str]]:
    listings = _read_csv(data_dir / "listings.csv")
    interviews = {rec["hh_id"]: rec for rec in _read_csv(data_dir / "interviews.csv")}
    roster = {rec["hh_id"]: rec for rec in _read_csv(data_dir / "roster.csv")}
    census = _read_csv(data_dir / "census_domains.csv")
    num: dict[str, float] = defaultdict(float)
    den: dict[str, float] = defaultdict(float)
    for rec in listings:
        iv = interviews.get(rec["hh_id"])
        if iv is None or iv["responded"] != "1" or iv["y"].strip() == "":
            continue
        ros = roster.get(rec["hh_id"])
        if ros is None or ros["eligible_count"].strip() == "":
            continue
        elig = float(ros["eligible_count"])
        if elig <= 0:
            continue
        w = float(rec["design_weight"])
        num[rec["listing_domain"]] += w * float(iv["y"])
        den[rec["listing_domain"]] += w * elig
    rates = {}
    for rec in census:
        d = den.get(rec["domain_id"], 0.0)
        rates[rec["domain_id"]] = (num[rec["domain_id"]] / d) if d > 0 else 0.0
    return _pack(census, rates)


def all_contrasts(data_dir: Path) -> bool:
    gold = estimate_rows(data_dir)
    gold_rates = [row["est_rate"] for row in gold]
    rivals = (
        _unweighted_means(data_dir),
        _interview_domain_means(data_dir),
        _uncollapsed_listing_direct(data_dir),
    )
    for rival in rivals:
        rival_rates = [row["est_rate"] for row in rival]
        if rival_rates == gold_rates:
            return False
    return True
