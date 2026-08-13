Publish domain rates and totals for the Vale household survey.

The unique published estimand, schema, rounding, and sample-construction rules are in `/app/docs/CONTRACT.md`. Fit trees under `/app/fit/case_*/` ship the same input filenames as production. They do not ship expected CSVs. They are unlabeled extracts, not a check-only oracle.

Production grading is on `/app/data` only. That tree is not an isomorphic copy of any fit tree. Write outputs only under `/app/output/`. Production does not ship expected outputs. `/app/lib/survey_kit.py` exposes exploration IO helpers only and is not a graded builder.

Write:

- `/app/output/domain_estimates.csv`
