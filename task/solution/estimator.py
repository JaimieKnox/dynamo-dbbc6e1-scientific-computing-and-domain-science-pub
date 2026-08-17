#!/usr/bin/env python3
"""Domain cumulative incidence at a fixed horizon with competing events and delayed entry."""

from __future__ import annotations

import csv
from decimal import Decimal, ROUND_HALF_EVEN
from pathlib import Path
from typing import Any

import numpy as np

HORIZON = 90
CIF_PLACES = 6
SE_PLACES = 6
# 6-decimal half-tie 0.1427625 (round-half-even vs round-half-up)
OUT_FIELDS = ["domain_id", "status", "est_cif", "est_se"]
STATUS_IDENTIFIED = "identified"
STATUS_UNIDENTIFIED = "unidentified"
STATUS_EMPTY = "empty"
CAUSE_CENSOR = 0
CAUSE_INTEREST = 1
CAUSE_COMPETE = 2


def qround(value: float, places: int) -> str:
    quant = Decimal("1").scaleb(-places)
    return str(Decimal.from_float(float(value)).quantize(quant, rounding=ROUND_HALF_EVEN))


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _as_int(text: str) -> int:
    return int(text)


def construct_sample(data_dir: Path) -> list[dict[str, Any]]:
    listings = {rec["hh_id"]: rec for rec in _read_csv(data_dir / "listings.csv")}
    events = _read_csv(data_dir / "events.csv")
    crosswalk = {
        rec["listing_domain"]: rec["publish_domain"]
        for rec in _read_csv(data_dir / "domain_crosswalk.csv")
    }
    if not listings:
        raise ValueError("empty listings")
    if not events:
        raise ValueError("empty events")
    people = []
    for rec in events:
        hh = rec["hh_id"]
        listing = listings.get(hh)
        if listing is None:
            continue
        listing_domain = listing["listing_domain"]
        publish = crosswalk.get(listing_domain)
        if publish is None:
            raise ValueError(f"missing crosswalk for {listing_domain}")
        onset = _as_int(rec["onset_day"])
        listed = _as_int(rec["listing_day"])
        event_day = _as_int(rec["event_day"])
        cause = _as_int(rec["event_type"])
        delay = listed - onset
        time = event_day - onset
        if delay < 0 or time < delay:
            continue
        people.append(
            {
                "hh_id": hh,
                "domain_id": publish,
                "L": delay,
                "T": time,
                "C": cause,
            }
        )
    return people


def _aj(
    records: list[dict[str, Any]],
    *,
    ignore_delay: bool = False,
    se_origin: bool = True,
) -> tuple[float, float]:
    surv = 1.0
    cif = 0.0
    var = 0.0
    for t in range(1, HORIZON + 1):
        at_risk = 0
        at_risk_se = 0
        d1 = 0
        d2 = 0
        for rec in records:
            entry = 0 if ignore_delay else rec["L"]
            if entry < t <= rec["T"]:
                at_risk += 1
            entry_se = 0 if (ignore_delay or se_origin) else rec["L"]
            if entry_se < t <= rec["T"]:
                at_risk_se += 1
            if rec["T"] == t and rec["C"] == CAUSE_INTEREST:
                d1 += 1
            if rec["T"] == t and rec["C"] == CAUSE_COMPETE:
                d2 += 1
        if at_risk <= 0:
            continue
        dlam1 = d1 / at_risk
        dlam2 = d2 / at_risk
        if at_risk_se > 0:
            var += (surv ** 2) * d1 * (at_risk_se - d1) / (at_risk_se ** 3)
        cif += surv * dlam1
        surv *= max(0.0, 1.0 - dlam1 - dlam2)
    se = float(np.sqrt(max(var, 0.0)))
    return float(cif), se


def _in_risk_set(rec: dict[str, Any], *, ignore_delay: bool = False) -> bool:
    entry = 0 if ignore_delay else rec["L"]
    return entry < HORIZON and entry < rec["T"]


def estimate_rows(
    data_dir: Path,
    *,
    ignore_delay: bool = False,
    treat_compete_as_censor: bool = False,
    use_report_domain: bool = False,
    se_origin: bool = True,
) -> list[dict[str, str]]:
    people = construct_sample(data_dir)
    if use_report_domain:
        events = {rec["hh_id"]: rec for rec in _read_csv(data_dir / "events.csv")}
        for rec in people:
            report = events[rec["hh_id"]].get("report_domain", rec["domain_id"])
            rec["domain_id"] = report
    census = _read_csv(data_dir / "census_domains.csv")
    if not census:
        raise ValueError("empty census")
    if treat_compete_as_censor:
        for rec in people:
            if rec["C"] == CAUSE_COMPETE:
                rec["C"] = CAUSE_CENSOR

    by_domain: dict[str, list[dict[str, Any]]] = {row["domain_id"]: [] for row in census}
    for rec in people:
        by_domain.setdefault(rec["domain_id"], []).append(rec)

    out = []
    for row in census:
        dom = row["domain_id"]
        members = by_domain.get(dom, [])
        if not members:
            out.append(
                {
                    "domain_id": dom,
                    "status": STATUS_EMPTY,
                    "est_cif": "",
                    "est_se": "",
                }
            )
            continue
        risk = [rec for rec in members if _in_risk_set(rec, ignore_delay=ignore_delay)]
        if not risk:
            out.append(
                {
                    "domain_id": dom,
                    "status": STATUS_UNIDENTIFIED,
                    "est_cif": "",
                    "est_se": "",
                }
            )
            continue
        cif, se = _aj(members, ignore_delay=ignore_delay, se_origin=se_origin)
        out.append(
            {
                "domain_id": dom,
                "status": STATUS_IDENTIFIED,
                "est_cif": qround(cif, CIF_PLACES),
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
