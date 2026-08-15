Publish domain program contrasts for the Vale household survey.

The unique published estimand, identification rules, schema, and rounding are in `/app/docs/CONTRACT.md`. The identified-domain arm mean is the sum of `w * (y / eligible_count)` divided by the sum of `w` on that arm. Fit trees under `/app/fit/case_*/` ship the same input filenames as production plus a published `domain_contrasts.csv` worked example. They are unlabeled extracts, not a check-only oracle. The unique construction of weights, response adjustments, item completion, calibration, and cluster standard errors is the one that reproduces every fit published table. Item completion and the analysis sample follow CONTRACT.md, including households whose recovered completion cell has no observed `y`.

Production grading is on `/app/data` only. That tree is not an isomorphic copy of any fit tree. Write outputs only under `/app/output/`. Production does not ship expected outputs. `/app/lib/survey_kit.py` exposes exploration IO helpers only and is not a graded builder.

Write:

- `/app/output/domain_contrasts.csv`
