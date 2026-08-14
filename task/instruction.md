Publish domain program contrasts for the Vale household survey.

The unique published estimand, identification rules, schema, rounding, and sample-construction rules are in `/app/docs/CONTRACT.md`. The identified-domain arm mean is the sum of `w * (y / eligible_count)` divided by the sum of `w` on that arm. Fit trees under `/app/fit/case_*/` ship the same input filenames as production. They do not ship published tables. They are unlabeled extracts, not a check-only oracle.

Production grading is on `/app/data` only. That tree is not an isomorphic copy of any fit tree. Write outputs only under `/app/output/`. Production does not ship expected outputs. `/app/lib/survey_kit.py` exposes exploration IO helpers only and is not a graded builder.

Write:

- `/app/output/domain_contrasts.csv`
