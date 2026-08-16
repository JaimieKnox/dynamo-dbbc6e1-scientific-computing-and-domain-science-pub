# Vale domain cumulative incidence

Publish identified domain cumulative incidence at a fixed horizon from a synthetic household follow-up. Leave unidentified and empty domains blank.

## Approach

Construct risk sets from onset dates, listing dates, and event times. Publish the competing-event cumulative incidence of the event of interest at day 90 only when a domain has at least one household in the risk set.

## Environment

Python 3.13 with numpy. Follow-up extracts live under `/app/data` and `/app/fit/case_*/`. Fit trees include published worked tables. The estimand is `/app/docs/CONTRACT.md`.

## Verification

Exact CSV match of `/app/output/domain_cif.csv` against an independently recomputed estimator, including identification status and blank numeric fields, plus wrong-model divergence.
