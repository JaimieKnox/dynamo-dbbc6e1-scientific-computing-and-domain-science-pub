"""Verifier for Vale domain program-contrast outputs."""

from __future__ import annotations

import csv
from pathlib import Path

from estimator import estimate_rows, OUT_FIELDS, STATUS_EMPTY, STATUS_UNIDENTIFIED
from wrong_models import all_contrasts

DATA = Path("/app/data")
FIT = Path("/app/fit")
OUT = Path("/app/output")
TABLE = OUT / "domain_contrasts.csv"
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
    """Success: /app/output/domain_contrasts.csv is an ordinary non-symlink file."""
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


def test_status_and_blank_fields_match_contract():
    """Success: identification status and blank numeric fields match the contract."""
    expected = estimate_rows(TESTS_PROD)
    actual = _read_csv(TABLE)
    assert [row["status"] for row in actual] == [row["status"] for row in expected]
    for row in actual:
        if row["status"] in {STATUS_EMPTY, STATUS_UNIDENTIFIED}:
            assert row["est_ate"] == ""
            assert row["est_se"] == ""
        else:
            assert row["est_ate"] != ""
            assert row["est_se"] != ""


def test_ates_match_contract():
    """Success: est_ate matches the independently recomputed weighted mean-of-rates contrasts."""
    expected = estimate_rows(TESTS_PROD)
    actual = _read_csv(TABLE)
    assert [row["est_ate"] for row in actual] == [row["est_ate"] for row in expected]


def test_ses_match_contract():
    """Success: est_se matches the independently recomputed cluster linearized SEs."""
    expected = estimate_rows(TESTS_PROD)
    actual = _read_csv(TABLE)
    assert [row["est_se"] for row in actual] == [row["est_se"] for row in expected]


def test_wrong_model_contrasts_diverge():
    """Success: transcript Hajek, OLS, interview-domain, and listing-domain siblings diverge."""
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
