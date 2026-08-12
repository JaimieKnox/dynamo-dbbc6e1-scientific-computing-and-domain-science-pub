"""Fail-closed wrong-model contrasts against the contract estimator."""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path

from estimator import estimate_rows, load_tree, qround, RATE_PLACES, TOTAL_PLACES
from decimal import Decimal


def _unweighted_means(data_dir: Path) -> list[dict[str, str]]:
    households, census = load_tree(data_dir)
    by_dom: dict[str, list[float]] = defaultdict(list)
    for rec in households:
        if rec["responded"] != "1":
            continue
        if rec["y"].strip() == "":
            continue
        elig = float(rec["eligible_count"])
        if elig <= 0:
            continue
        by_dom[rec["domain_id"]].append(float(rec["y"]) / elig)
    out = []
    for rec in census:
        vals = by_dom.get(rec["domain_id"], [])
        rate = float(sum(vals) / len(vals)) if vals else 0.0
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


def _mean_of_ratios_weighted(data_dir: Path) -> list[dict[str, str]]:
    households, census = load_tree(data_dir)
    num: dict[str, float] = defaultdict(float)
    den: dict[str, float] = defaultdict(float)
    for rec in households:
        if rec["responded"] != "1" or rec["y"].strip() == "":
            continue
        elig = float(rec["eligible_count"])
        if elig <= 0:
            continue
        w = float(rec["design_weight"])
        ratio = float(rec["y"]) / elig
        num[rec["domain_id"]] += w * ratio
        den[rec["domain_id"]] += w
    out = []
    for rec in census:
        d = den.get(rec["domain_id"], 0.0)
        rate = (num[rec["domain_id"]] / d) if d > 0 else 0.0
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


def _always_direct_or_zero(data_dir: Path) -> list[dict[str, str]]:
    households, census = load_tree(data_dir)
    num: dict[str, float] = defaultdict(float)
    den: dict[str, float] = defaultdict(float)
    for rec in households:
        if rec["responded"] != "1" or rec["y"].strip() == "":
            continue
        w = float(rec["design_weight"])
        num[rec["domain_id"]] += w * float(rec["y"])
        den[rec["domain_id"]] += w * float(rec["eligible_count"])
    out = []
    for rec in census:
        d = den.get(rec["domain_id"], 0.0)
        rate = (num[rec["domain_id"]] / d) if d > 0 else 0.0
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


def all_contrasts(data_dir: Path) -> bool:
    gold = estimate_rows(data_dir)
    gold_rates = [row["est_rate"] for row in gold]
    rivals = (
        _unweighted_means(data_dir),
        _mean_of_ratios_weighted(data_dir),
        _always_direct_or_zero(data_dir),
    )
    for rival in rivals:
        rival_rates = [row["est_rate"] for row in rival]
        if rival_rates == gold_rates:
            return False
    return True
