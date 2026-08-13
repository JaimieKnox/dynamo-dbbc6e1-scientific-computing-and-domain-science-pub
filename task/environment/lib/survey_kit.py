"""Exploration IO helpers. Not a graded domain estimator."""

from __future__ import annotations

import csv
from pathlib import Path


def _read(data_dir: str | Path, name: str) -> list[dict[str, str]]:
    path = Path(data_dir) / name
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def read_listings(data_dir: str | Path) -> list[dict[str, str]]:
    return _read(data_dir, "listings.csv")


def read_interviews(data_dir: str | Path) -> list[dict[str, str]]:
    return _read(data_dir, "interviews.csv")


def read_roster(data_dir: str | Path) -> list[dict[str, str]]:
    return _read(data_dir, "roster.csv")


def read_crosswalk(data_dir: str | Path) -> list[dict[str, str]]:
    return _read(data_dir, "domain_crosswalk.csv")


def read_census(data_dir: str | Path) -> list[dict[str, str]]:
    return _read(data_dir, "census_domains.csv")


def write_domain_csv(path: str | Path, rows: list[dict[str, str]]) -> None:
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    fields = ["domain_id", "status", "est_ate", "est_se"]
    with out.open("w", newline="\n", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row[key] for key in fields})
