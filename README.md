# Vale domain rates

Publish finite-population domain rates and census-denominator totals from a synthetic two-stage household survey.

## Approach

Construct analysis weights from collapsed listings, interviews, roster, a listing-to-publish crosswalk, unit-nonresponse cells, a phase-two subsample, and linear calibration. Form ratio directs, a unit-level weighted-least-squares synthetic, and a Prasad-Rao composite, including empty domains.

## Environment

Python 3.13 with numpy. Survey extracts live under `/app/data` and `/app/fit/case_*/`. The estimand is `/app/docs/CONTRACT.md`.

## Verification

Exact CSV match of `/app/output/domain_estimates.csv` against an independently recomputed closed-form estimator, plus probe refuse/accept checks and wrong-model divergence.
