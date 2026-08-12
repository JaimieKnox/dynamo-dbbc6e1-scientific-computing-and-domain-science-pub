#!/usr/bin/env python3
"""Closed-form Vale domain rate and total estimator."""

from __future__ import annotations

import csv
from decimal import Decimal, ROUND_HALF_EVEN
from pathlib import Path
from typing import Any

import numpy as np

RATE_PLACES = 6
TOTAL_PLACES = 2
OUT_FIELDS = ["domain_id", "est_total", "est_rate"]


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


def load_tree(data_dir: Path) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    households = _read_csv(data_dir / "households.csv")
    census = _read_csv(data_dir / "census_domains.csv")
    if not households:
        raise ValueError("empty households")
    if not census:
        raise ValueError("empty census")
    return households, census


def _design_matrix_rows(
    records: list[dict[str, Any]],
    included_regions: list[str],
    urban_key: str,
) -> np.ndarray:
    rows = []
    for rec in records:
        row = [1.0, float(rec[urban_key])]
        region = rec["region"]
        row.extend(1.0 if region == name else 0.0 for name in included_regions)
        rows.append(row)
    return np.asarray(rows, dtype=np.float64)


def estimate_rows(data_dir: Path) -> list[dict[str, str]]:
    households, census = load_tree(data_dir)
    reference, included = region_dummy_names([row["region"] for row in census])
    _ = reference

    sampled_cells: dict[tuple[int, str], list[dict[str, str]]] = {}
    for rec in households:
        key = (_as_int(rec["urban"]), rec["region"])
        sampled_cells.setdefault(key, []).append(rec)

    nr_factor: dict[tuple[int, str], float] = {}
    for key, members in sampled_cells.items():
        n_sampled = len(members)
        n_resp = sum(_as_int(rec["responded"]) for rec in members)
        if n_resp <= 0:
            raise ValueError(f"empty NR cell {key}")
        nr_factor[key] = n_sampled / n_resp

    respondents = [rec for rec in households if _as_int(rec["responded"]) == 1]
    resp_cells: dict[tuple[int, str], list[dict[str, str]]] = {}
    for rec in respondents:
        key = (_as_int(rec["urban"]), rec["region"])
        resp_cells.setdefault(key, []).append(rec)

    phase2_factor: dict[tuple[int, str], float] = {}
    for key, members in resp_cells.items():
        n_resp = len(members)
        n_p2 = sum(_as_int(rec["phase2"]) for rec in members)
        if n_p2 <= 0:
            raise ValueError(f"empty phase2 cell {key}")
        phase2_factor[key] = n_resp / n_p2

    phase2 = [rec for rec in respondents if _as_int(rec["phase2"]) == 1]

    item_cells: dict[tuple[str, int], list[dict[str, str]]] = {}
    for rec in phase2:
        key = (rec["tenure"], _as_int(rec["urban"]))
        item_cells.setdefault(key, []).append(rec)

    item_mean: dict[tuple[str, int], float] = {}
    for key, members in item_cells.items():
        observed = [ _as_float(rec["y"]) for rec in members if not _missing_y(rec["y"])]
        if observed:
            item_mean[key] = float(np.mean(np.asarray(observed, dtype=np.float64)))

    analysis: list[dict[str, Any]] = []
    for rec in phase2:
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
                "w2": w2,
            }
        )
    if not analysis:
        raise ValueError("empty analysis sample")

    z = _design_matrix_rows(analysis, included, "urban")
    w2 = np.asarray([row["w2"] for row in analysis], dtype=np.float64)
    t_hat = z.T @ w2
    ztwz = z.T @ (w2[:, None] * z)

    totals = {
        "intercept": 0.0,
        "urban": 0.0,
    }
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

    y = np.asarray([row["y"] for row in analysis], dtype=np.float64)
    xtwx = z.T @ (w_cal[:, None] * z)
    xtwy = z.T @ (w_cal * y)
    beta = np.linalg.solve(xtwx, xtwy)

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

    direct: dict[str, dict[str, float]] = {}
    for dom in domains:
        members = analysis_by_domain.get(dom, [])
        if not members:
            continue
        t_d = sum(rec["w"] * rec["y"] for rec in members)
        e_d = sum(rec["w"] * rec["eligible_count"] for rec in members)
        if e_d <= 0.0:
            continue
        r_d = t_d / e_d
        z_psu: dict[tuple[str, str], float] = {}
        for stratum, psus in psu_by_stratum.items():
            for psu in psus:
                z_psu[(stratum, psu)] = 0.0
        for rec in members:
            key = (rec["stratum"], rec["psu"])
            z_psu[key] += rec["w"] * (rec["y"] - r_d * rec["eligible_count"])
        var = 0.0
        for stratum, psus in psu_by_stratum.items():
            n_h = len(psus)
            vals = np.asarray([z_psu[(stratum, psu)] for psu in sorted(psus)], dtype=np.float64)
            zbar = float(vals.mean())
            var += (n_h / (n_h - 1)) * float(np.sum((vals - zbar) ** 2))
        psi = var / (e_d * e_d)
        direct[dom] = {"r": r_d, "psi": psi, "e": e_d, "t": t_d}

    syn: dict[str, float] = {}
    x_area_rows = []
    y_area = []
    psi_area = []
    area_ids = []
    for rec in census:
        x_d = [1.0, _as_float(rec["urban_share"])]
        x_d.extend(1.0 if rec["region"] == name else 0.0 for name in included)
        x_arr = np.asarray(x_d, dtype=np.float64)
        syn[rec["domain_id"]] = float(x_arr @ beta)
        if rec["domain_id"] in direct:
            x_area_rows.append(x_d)
            y_area.append(direct[rec["domain_id"]]["r"])
            psi_area.append(direct[rec["domain_id"]]["psi"])
            area_ids.append(rec["domain_id"])

    a_val = 0.0
    m = len(area_ids)
    p = 2 + len(included)
    if m > p and x_area_rows:
        x_area = np.asarray(x_area_rows, dtype=np.float64)
        y_a = np.asarray(y_area, dtype=np.float64)
        psi_a = np.asarray(psi_area, dtype=np.float64)
        xtx = x_area.T @ x_area
        try:
            beta_ols = np.linalg.solve(xtx, x_area.T @ y_a)
            resid = y_a - x_area @ beta_ols
            hat = x_area @ np.linalg.solve(xtx, x_area.T)
            lever = np.clip(np.diag(hat), 0.0, 1.0)
            a_pr = (float(np.sum(resid ** 2)) - float(np.sum(psi_a * (1.0 - lever)))) / (m - p)
            a_val = max(0.0, a_pr)
        except np.linalg.LinAlgError:
            a_val = 0.0

    out = []
    for rec in census:
        dom = rec["domain_id"]
        syn_d = syn[dom]
        if dom not in direct:
            gamma = 0.0
            rate = syn_d
        else:
            psi = direct[dom]["psi"]
            r_d = direct[dom]["r"]
            if psi == 0.0:
                gamma = 1.0
            elif a_val == 0.0:
                gamma = 0.0
            else:
                gamma = a_val / (a_val + psi)
            rate = gamma * r_d + (1.0 - gamma) * syn_d
        rate_s = qround(rate, RATE_PLACES)
        total = float(Decimal(rate_s) * Decimal(rec["eligible_count_census"]))
        total_s = qround(total, TOTAL_PLACES)
        out.append({"domain_id": dom, "est_total": total_s, "est_rate": rate_s})
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
