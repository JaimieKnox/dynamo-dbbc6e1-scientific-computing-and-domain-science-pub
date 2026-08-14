#!/usr/bin/env python3
"""Finite-population domain program-contrast estimator."""

from __future__ import annotations

import csv
from decimal import Decimal, ROUND_HALF_EVEN
from pathlib import Path
from typing import Any

import numpy as np

ATE_PLACES = 6
SE_PLACES = 6
OUT_FIELDS = ["domain_id", "status", "est_ate", "est_se"]
STATUS_IDENTIFIED = "identified"
STATUS_UNIDENTIFIED = "unidentified"
STATUS_EMPTY = "empty"


def qround(value: float, places: int) -> str:
    quant = Decimal("1").scaleb(-places)
    return str(Decimal.from_float(float(value)).quantize(quant, rounding=ROUND_HALF_EVEN))


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _as_float(text: str) -> float:
    return float(text)


def _as_int(text: str) -> int:
    return int(text)


def _missing_y(text: str) -> bool:
    return text.strip() == ""


def region_dummy_names(regions: list[str]) -> tuple[str, list[str]]:
    ordered = sorted(set(regions))
    if not ordered:
        raise ValueError("no regions")
    reference = ordered[-1]
    included = ordered[:-1]
    return reference, included


def _collapse_listings(listings: list[dict[str, str]]) -> list[dict[str, str]]:
    ordered = sorted(listings, key=lambda r: (r["hh_id"], r["psu"], r.get("list_seq", "0")))
    best: dict[str, dict[str, str]] = {}
    for rec in ordered:
        if rec["hh_id"] not in best:
            best[rec["hh_id"]] = rec
    return [best[hh] for hh in sorted(best)]


def construct_sample(data_dir: Path) -> list[dict[str, str]]:
    listings = _read_csv(data_dir / "listings.csv")
    interviews = {rec["hh_id"]: rec for rec in _read_csv(data_dir / "interviews.csv")}
    roster = {rec["hh_id"]: rec for rec in _read_csv(data_dir / "roster.csv")}
    crosswalk = {
        rec["listing_domain"]: rec["publish_domain"]
        for rec in _read_csv(data_dir / "domain_crosswalk.csv")
    }
    if not listings:
        raise ValueError("empty listings")
    households = []
    for rec in _collapse_listings(listings):
        hh = rec["hh_id"]
        iv = interviews.get(hh)
        ros = roster.get(hh)
        listing_domain = rec["listing_domain"]
        publish = crosswalk.get(listing_domain)
        if publish is None:
            raise ValueError(f"missing crosswalk for {listing_domain}")
        if iv is None:
            responded = "0"
            phase2 = "0"
            y = ""
            tenure = ""
            assigned = ""
        else:
            responded = iv["responded"]
            phase2 = iv["phase2"]
            y = iv["y"]
            tenure = iv["tenure"]
            assigned = iv.get("assigned", "")
        eligible = ros["eligible_count"] if ros is not None else ""
        households.append(
            {
                "hh_id": hh,
                "stratum": rec["stratum"],
                "psu": rec["psu"],
                "domain_id": publish,
                "region": rec["region"],
                "urban": rec["urban"],
                "tenure": tenure,
                "design_weight": rec["design_weight"],
                "responded": responded,
                "phase2": phase2,
                "y": y,
                "assigned": assigned,
                "eligible_count": eligible,
            }
        )
    return households


def load_tree(data_dir: Path) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    households = construct_sample(data_dir)
    census = _read_csv(data_dir / "census_domains.csv")
    if not households:
        raise ValueError("empty households")
    if not census:
        raise ValueError("empty census")
    return households, census


def _design_matrix_rows(
    records: list[dict[str, Any]],
    included_regions: list[str],
) -> np.ndarray:
    rows = []
    for rec in records:
        row = [1.0, float(rec["urban"])]
        region = rec["region"]
        row.extend(1.0 if region == name else 0.0 for name in included_regions)
        rows.append(row)
    return np.asarray(rows, dtype=np.float64)


def _cell_factor(
    members: list[dict[str, str]],
    pred,
    *,
    weighted: bool,
) -> float:
    if weighted:
        num = sum(_as_float(rec["design_weight"]) for rec in members)
        den = sum(_as_float(rec["design_weight"]) for rec in members if pred(rec))
    else:
        num = float(len(members))
        den = float(sum(1 for rec in members if pred(rec)))
    if den <= 0:
        raise ValueError("empty response cell")
    return num / den


def estimate_rows(data_dir: Path, *, weighted_response: bool = False) -> list[dict[str, str]]:
    households, census = load_tree(data_dir)
    reference, included = region_dummy_names([row["region"] for row in census])
    _ = reference

    sampled_cells: dict[tuple[int, str], list[dict[str, str]]] = {}
    for rec in households:
        key = (_as_int(rec["urban"]), rec["region"])
        sampled_cells.setdefault(key, []).append(rec)

    nr_factor: dict[tuple[int, str], float] = {}
    for key, members in sampled_cells.items():
        nr_factor[key] = _cell_factor(
            members,
            lambda rec: _as_int(rec["responded"]) == 1,
            weighted=weighted_response,
        )

    respondents = [rec for rec in households if _as_int(rec["responded"]) == 1]
    resp_cells: dict[tuple[int, str], list[dict[str, str]]] = {}
    for rec in respondents:
        key = (_as_int(rec["urban"]), rec["region"])
        resp_cells.setdefault(key, []).append(rec)

    phase2_factor: dict[tuple[int, str], float] = {}
    for key, members in resp_cells.items():
        phase2_factor[key] = _cell_factor(
            members,
            lambda rec: _as_int(rec["phase2"]) == 1,
            weighted=weighted_response,
        )

    phase2 = [rec for rec in respondents if _as_int(rec["phase2"]) == 1]

    item_cells: dict[tuple[str, int], list[dict[str, str]]] = {}
    for rec in phase2:
        key = (rec["tenure"], _as_int(rec["urban"]))
        item_cells.setdefault(key, []).append(rec)

    item_mean: dict[tuple[str, int], float] = {}
    for key, members in item_cells.items():
        observed = [_as_float(rec["y"]) for rec in members if not _missing_y(rec["y"])]
        if observed:
            item_mean[key] = float(np.mean(np.asarray(observed, dtype=np.float64)))

    analysis: list[dict[str, Any]] = []
    for rec in phase2:
        if rec["assigned"].strip() not in {"0", "1"}:
            continue
        if rec["eligible_count"].strip() == "":
            continue
        key = (rec["tenure"], _as_int(rec["urban"]))
        if _missing_y(rec["y"]):
            if key not in item_mean:
                continue
            y_val = item_mean[key]
        else:
            y_val = _as_float(rec["y"])
        nr_key = (_as_int(rec["urban"]), rec["region"])
        w2 = _as_float(rec["design_weight"]) * nr_factor[nr_key] * phase2_factor[nr_key]
        analysis.append(
            {
                "hh_id": rec["hh_id"],
                "stratum": rec["stratum"],
                "psu": rec["psu"],
                "domain_id": rec["domain_id"],
                "region": rec["region"],
                "urban": _as_int(rec["urban"]),
                "eligible_count": _as_float(rec["eligible_count"]),
                "y": y_val,
                "assigned": _as_int(rec["assigned"]),
                "w2": w2,
            }
        )
    if not analysis:
        raise ValueError("empty analysis sample")

    z = _design_matrix_rows(analysis, included)
    w2 = np.asarray([row["w2"] for row in analysis], dtype=np.float64)
    t_hat = z.T @ w2
    ztwz = z.T @ (w2[:, None] * z)

    totals = {"intercept": 0.0, "urban": 0.0}
    for name in included:
        totals[name] = 0.0
    for rec in census:
        hh = _as_float(rec["hh_count_census"])
        totals["intercept"] += hh
        totals["urban"] += _as_float(rec["urban_hh_count_census"])
        if rec["region"] in totals:
            totals[rec["region"]] += hh

    t_vec = np.asarray(
        [totals["intercept"], totals["urban"], *[totals[name] for name in included]],
        dtype=np.float64,
    )
    delta = np.linalg.solve(ztwz, t_vec - t_hat)
    g = 1.0 + z @ delta
    w_cal = w2 * g
    for rec, weight in zip(analysis, w_cal):
        rec["w"] = float(weight)

    psu_by_stratum: dict[str, set[str]] = {}
    for rec in households:
        psu_by_stratum.setdefault(rec["stratum"], set()).add(rec["psu"])
    for stratum, psus in psu_by_stratum.items():
        if len(psus) < 2:
            raise ValueError(f"stratum {stratum} has fewer than 2 PSUs")

    domains = [rec["domain_id"] for rec in census]
    analysis_by_domain: dict[str, list[dict[str, Any]]] = {dom: [] for dom in domains}
    for rec in analysis:
        analysis_by_domain.setdefault(rec["domain_id"], []).append(rec)

    out = []
    for rec in census:
        dom = rec["domain_id"]
        members = analysis_by_domain.get(dom, [])
        if not members:
            out.append(
                {
                    "domain_id": dom,
                    "status": STATUS_EMPTY,
                    "est_ate": "",
                    "est_se": "",
                }
            )
            continue
        arms = {int(row["assigned"]) for row in members}
        e1 = sum(row["w"] * row["eligible_count"] for row in members if row["assigned"] == 1)
        e0 = sum(row["w"] * row["eligible_count"] for row in members if row["assigned"] == 0)
        if arms != {0, 1} or e1 <= 0.0 or e0 <= 0.0:
            out.append(
                {
                    "domain_id": dom,
                    "status": STATUS_UNIDENTIFIED,
                    "est_ate": "",
                    "est_se": "",
                }
            )
            continue
        w1 = sum(row["w"] for row in members if row["assigned"] == 1)
        w0 = sum(row["w"] for row in members if row["assigned"] == 0)
        if w1 <= 0.0 or w0 <= 0.0:
            out.append(
                {
                    "domain_id": dom,
                    "status": STATUS_UNIDENTIFIED,
                    "est_ate": "",
                    "est_se": "",
                }
            )
            continue
        r1 = (
            sum(row["w"] * (row["y"] / row["eligible_count"]) for row in members if row["assigned"] == 1)
            / w1
        )
        r0 = (
            sum(row["w"] * (row["y"] / row["eligible_count"]) for row in members if row["assigned"] == 0)
            / w0
        )
        ate = r1 - r0
        z_psu: dict[tuple[str, str], float] = {}
        for stratum, psus in psu_by_stratum.items():
            for psu in psus:
                z_psu[(stratum, psu)] = 0.0
        for row in members:
            key = (row["stratum"], row["psu"])
            rate = row["y"] / row["eligible_count"]
            if row["assigned"] == 1:
                z_psu[key] += row["w"] * (rate - r1) / w1
            else:
                z_psu[key] -= row["w"] * (rate - r0) / w0
        var = 0.0
        for stratum, psus in psu_by_stratum.items():
            n_h = len(psus)
            vals = np.asarray([z_psu[(stratum, psu)] for psu in sorted(psus)], dtype=np.float64)
            zbar = float(vals.mean())
            var += (n_h / (n_h - 1)) * float(np.sum((vals - zbar) ** 2))
        se = float(np.sqrt(max(var, 0.0)))
        out.append(
            {
                "domain_id": dom,
                "status": STATUS_IDENTIFIED,
                "est_ate": qround(ate, ATE_PLACES),
                "est_se": qround(se, SE_PLACES),
            }
        )
    return out


def write_estimates(rows: list[dict[str, str]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="\n", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=OUT_FIELDS, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def estimate_to_file(data_dir: Path, out_path: Path) -> None:
    write_estimates(estimate_rows(data_dir), out_path)
