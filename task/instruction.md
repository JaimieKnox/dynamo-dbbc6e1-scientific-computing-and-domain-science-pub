Publish domain cumulative incidence for the Vale household follow-up.

The unique published estimand, identification rules, schema, and rounding are in `/app/docs/CONTRACT.md`. Fit trees under `/app/fit/case_*/` ship the same input filenames as production plus a published `domain_cif.csv` worked example. They are unlabeled extracts, not a check-only oracle. The unique construction of risk sets and competing-event incidence is the one that reproduces every fit published table. The published standard error uses the origin at-risk count, not the delayed-entry count that production incidence uses.

Production grading is on `/app/data` only. That tree is not an isomorphic copy of any fit tree. Write outputs only under `/app/output/`. Production does not ship expected outputs. `/app/lib/survey_kit.py` exposes exploration IO helpers only and is not a graded builder.

Write:

- `/app/output/domain_cif.csv`
