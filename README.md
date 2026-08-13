# Vale domain program contrasts

Publish identified finite-population program contrasts from a synthetic two-stage household survey. Leave unidentified and empty domains blank.

## Approach

Construct analysis weights from collapsed listings, interviews, roster, and a listing-to-publish crosswalk. Publish a Hajek treated-minus-control contrast only when positivity holds on the published domain.

## Environment

Python 3.13 with numpy. Survey extracts live under `/app/data` and `/app/fit/case_*/`. The estimand is `/app/docs/CONTRACT.md`.

## Verification

Exact CSV match of `/app/output/domain_contrasts.csv` against an independently recomputed estimator, including identification status and blank numeric fields, plus wrong-model divergence.
