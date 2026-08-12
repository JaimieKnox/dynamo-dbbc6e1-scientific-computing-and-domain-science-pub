Publish domain rates and totals for the Vale household survey.

Fit trees under `/app/fit/case_*/` ship the same input filenames as production. They do not ship expected CSVs. The digest-allowlisted check-only probe `/app/bin/sae_ref` may be used on those trees only. The unique published estimand, schema, rounding, and closed formulas are in `/app/docs/CONTRACT.md`.

Usage:

`/app/bin/sae_ref check DATA_DIR OUT_DIR`

`sae_ref check` exits 0 when `OUT_DIR`'s `domain_estimates.csv` matches the allowlisted digest for that fit input tree. It never writes golden CSVs. It exits nonzero with a short non-spoiling message on mismatch, and refuses production `/app/data` and any other or mutated directory.

Production grading is on `/app/data` only. Write outputs only under `/app/output/`. That production tree does not ship expected outputs. `/app/lib/survey_kit.py` exposes exploration IO helpers only and is not a graded builder.

Write:

- `/app/output/domain_estimates.csv`
