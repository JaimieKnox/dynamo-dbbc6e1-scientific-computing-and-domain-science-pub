"""Verifier for Vale domain publication outputs."""

from __future__ import annotations

import csv
from pathlib import Path

from estimator import estimate_rows, OUT_FIELDS
from wrong_models import all_contrasts

DATA = Path("/app/data")
FIT = Path("/app/fit")
OUT = Path("/app/output")
TABLE = OUT / "domain_estimates.csv"
TESTS_PROD = Path("/tests/inputs/production")
INPUT_FILES = (
    "listings.csv",
    "interviews.csv",
    "roster.csv",
    "domain_crosswalk.csv",
    "census_domains.csv",
)


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def test_production_inputs_match_verifier_copy():
    """Success: production inputs under /app/data match the verifier copy."""
    for name in INPUT_FILES:
        left = DATA / name
        right = TESTS_PROD / name
        assert left.is_file(), name
        assert right.is_file(), name
        assert left.read_bytes() == right.read_bytes(), name


def test_output_file_is_ordinary():
    """Success: /app/output/domain_estimates.csv is an ordinary non-symlink file."""
    assert TABLE.is_file()
    assert not TABLE.is_symlink()


def test_output_schema_and_census_order():
    """Success: header and domain order match the census frame."""
    with TABLE.open(newline="", encoding="utf-8") as handle:
        header = next(csv.reader(handle))
    assert header == OUT_FIELDS
    census = _read_csv(TESTS_PROD / "census_domains.csv")
    actual = _read_csv(TABLE)
    assert [row["domain_id"] for row in actual] == [row["domain_id"] for row in census]


def test_rates_match_contract():
    """Success: est_rate matches the independently recomputed contract rates."""
    expected = estimate_rows(TESTS_PROD)
    actual = _read_csv(TABLE)
    assert [row["est_rate"] for row in actual] == [row["est_rate"] for row in expected]


def test_totals_match_contract():
    """Success: est_total matches the independently recomputed contract totals."""
    expected = estimate_rows(TESTS_PROD)
    actual = _read_csv(TABLE)
    assert [row["est_total"] for row in actual] == [row["est_total"] for row in expected]


def test_wrong_model_contrasts_diverge():
    """Success: unweighted, interview-domain, and uncollapsed-listing siblings diverge."""
    assert all_contrasts(TESTS_PROD) is True


def test_fit_inputs_have_no_expected_csvs():
    """Success: agent-visible fit cases ship inputs only."""
    assert FIT.is_dir()
    cases = sorted(path for path in FIT.iterdir() if path.is_dir())
    assert len(cases) >= 10
    for case in cases:
        assert not (case / "expected").exists(), case.name
        for name in INPUT_FILES:
            assert (case / name).is_file(), f"{case.name}/{name}"
        assert case.name.startswith("case_")
        assert case.name.removeprefix("case_").isdigit(), case.name
    assert not (Path("/app/bin") / "sae_ref").exists()
    assert not (Path("/app/bin") / "fit_hashes.json").exists()
