"""Fail-closed wrong-model domain CIF tables against the contract estimator."""

from __future__ import annotations

from pathlib import Path

from estimator import estimate_rows

GRADED_PROD = Path("/app/data")


def all_contrasts(data_dir: Path | None = None) -> bool:
    if data_dir is None:
        data_dir = GRADED_PROD
    gold = estimate_rows(data_dir)
    gold_key = [(row["status"], row["est_cif"], row["est_se"]) for row in gold]
    rivals = (
        estimate_rows(data_dir, treat_compete_as_censor=True),
        estimate_rows(data_dir, ignore_delay=True),
        estimate_rows(data_dir, treat_compete_as_censor=True, ignore_delay=True),
        estimate_rows(data_dir, use_report_domain=True),
        estimate_rows(data_dir, se_origin=False),
    )
    for rival in rivals:
        rival_key = [(row["status"], row["est_cif"]) for row in rival]
        if rival_key == gold_key:
            return False
    return True
