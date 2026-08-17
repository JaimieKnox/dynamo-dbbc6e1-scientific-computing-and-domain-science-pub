# Vale domain cumulative incidence contract

This file is the unique published estimand. Fit trees under `/app/fit/case_*/` ship the same input filenames as production plus a published `domain_cif.csv` worked example. They are unlabeled extracts for schema and construction. Production grading uses `/app/data` only. That production tree is not an isomorphic copy of any single fit tree. Copying a fit table onto production does not satisfy the contract.

## Inputs

Read these files from the chosen data root:

- `listings.csv` columns `hh_id,listing_domain`
- `events.csv` columns `hh_id,onset_day,listing_day,event_day,event_type,report_domain`
- `domain_crosswalk.csv` columns `listing_domain,publish_domain`
- `census_domains.csv` column `domain_id`

Days are integers. `event_type` is `0` for a censored exit, `1` for the event of interest, or `2` for a competing event. `report_domain` is not the published domain.

## Analysis time

Time is days since onset. A household enters the risk set after it is listed. It is at risk on day `t` when `listing_day - onset_day < t <= event_day - onset_day`. Origin time is not listing time. A household listed after the horizon does not enter the risk set. A household listed before onset, or with an event before listing, does not enter the risk set.

## Horizon and competing events

The published incidence is the cumulative incidence of event type `1` at day 90 in the presence of event type `2`. Treating type `2` as independent censoring is not the published incidence. Type `0` is censoring.

The unique hazard increments, product-limit survival through both event types, and person linearized standard error are the construction that reproduces every fit published table. The published incidence uses the delayed-entry at-risk count. The published standard error uses the origin at-risk count, as if every household were listed on onset. Fit published tables list every household on onset, so those two counts coincide there. Production listing can follow onset, and the published SE is not the delayed-entry Greenwood formula.

## Identification

The published domain of a household is the `publish_domain` of its `listing_domain`. `listing_domain` and `report_domain` are not the published domain.

- `empty`: no event household in that published domain
- `unidentified`: at least one household, but none enter the risk set before day 90
- `identified`: at least one household is at risk on some day `t` with `1 <= t <= 90`

Numeric fields are published only for `identified` domains. Other rows leave those fields empty.

## Output

Write `/app/output/domain_cif.csv` as an ordinary non-symlink file with header

`domain_id,status,est_cif,est_se`

One row per census domain, in `census_domains.csv` order. `status` is `identified`, `unidentified`, or `empty`. For `identified` rows, quantize `est_cif` and `est_se` independently to 6 decimal places with round-half-even. For `unidentified` and `empty` rows, leave `est_cif` and `est_se` as empty fields. Use LF newlines. `/app/lib/survey_kit.py` is exploration IO only and is not a graded builder.
