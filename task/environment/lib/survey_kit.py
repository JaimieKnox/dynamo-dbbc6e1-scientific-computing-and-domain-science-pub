"""Exploration IO helpers. Not a graded domain estimator."""

from __future__ import annotations

import csv
from pathlib import Path


def read_households(data_dir: str | Path) -> list[dict[str, str]]:
    path = Path(data_dir) / "households.csv"
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def read_census(data_dir: str | Path) -> list[dict[str, str]]:
    path = Path(data_dir) / "census_domains.csv"
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_domain_csv(path: str | Path, rows: list[dict[str, str]]) -> None:
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    fields = ["domain_id", "est_total", "est_rate"]
    with out.open("w", newline="\n", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row[key] for key in fields})
