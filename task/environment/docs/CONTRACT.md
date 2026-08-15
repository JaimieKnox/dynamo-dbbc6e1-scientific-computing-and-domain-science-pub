# Vale domain program-contrast contract

This file is the unique published estimand. Fit trees under `/app/fit/case_*/` ship the same input filenames as production plus a published `domain_contrasts.csv` worked example. They are unlabeled extracts for schema and construction. Production grading uses `/app/data` only. That production tree is not an isomorphic copy of any single fit tree. Copying a fit table onto production does not satisfy the contract.

## Inputs

Read these files from the chosen data root:

- `listings.csv` columns `hh_id,stratum,psu,listing_domain,region,urban,design_weight,list_seq`
- `interviews.csv` columns `hh_id,responded,phase2,y,tenure,assigned,interview_domain`
- `roster.csv` columns `hh_id,eligible_count`
- `domain_crosswalk.csv` columns `listing_domain,publish_domain`
- `census_domains.csv` columns `domain_id,region,urban_share,hh_count_census,urban_hh_count_census,eligible_count_census`

`urban` is `0` or `1`. `responded`, `phase2`, and `assigned` are `0` or `1`. Empty `y` is item missing. `assigned` is the household program arm. `list_seq` is a listing-pass index.

## Analysis sample

A household may appear more than once in `listings.csv`. Collapse to one row per `hh_id`.

Attach interviews by `hh_id`. A listing with no interview is a unit nonrespondent and stays in the listing sample used for nonresponse cells. The published domain of a household is the `publish_domain` of its `listing_domain`. Status, emptiness, and the contrast use that published domain. `listing_domain` and `interview_domain` are not the published domain. Eligible counts come from `roster.csv`. A phase-two household with no roster row is out of the analysis sample.

Unit-nonresponse, phase-two response, item completion, and the linear calibration of household analysis weights to census household margins are determined by the unique construction that reproduces every fit published table. Item completion fills missing `y` before the analysis sample is closed. A household that still has no `y` after that completion, or with `assigned` other than `0` or `1`, is out of the analysis sample. Households with `phase2=0` are out of the analysis sample. Do not drop a household solely because `y` was missing before item completion.

## Identification

Status is evaluated on the published domain of the analysis sample.

- `empty`: no analysis household in that published domain
- `unidentified`: at least one analysis household, but not both program arms, or either arm has a calibrated eligible-person total that is not strictly positive
- `identified`: both arms are present and both calibrated eligible-person totals are strictly positive

Numeric contrast fields are published only for `identified` domains. Other rows leave those fields empty.

## Weights and contrast

Analysis weights start from the design weight, then the unique response adjustments and unique linear calibration recovered from the fit published tables.

For an identified domain the arm mean is the sum of `w * (y / eligible_count)` divided by the sum of `w`, over analysis households in that arm, where `w` is the analysis weight. The published contrast is treated minus control. The published standard error is the unique with-replacement cluster linearized standard error of that contrast that reproduces every fit published table.

## Output

Write `/app/output/domain_contrasts.csv` as an ordinary non-symlink file with header

`domain_id,status,est_ate,est_se`

One row per census domain, in `census_domains.csv` order. `status` is `identified`, `unidentified`, or `empty`. For `identified` rows, quantize `est_ate` and `est_se` independently to 6 decimal places with round-half-even. For `unidentified` and `empty` rows, leave `est_ate` and `est_se` as empty fields. Use LF newlines. `/app/lib/survey_kit.py` is exploration IO only and is not a graded builder.
