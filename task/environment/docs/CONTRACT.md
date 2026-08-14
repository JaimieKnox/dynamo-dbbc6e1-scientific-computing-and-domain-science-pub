# Vale domain program-contrast contract

This file is the unique published estimand. Fit trees under `/app/fit/case_*/` ship the same input filenames as production plus a published `domain_contrasts.csv` worked example. They are unlabeled extracts for schema and construction. Production grading uses `/app/data` only. That production tree is not an isomorphic copy of any single fit tree. Copying a fit table onto production does not satisfy the contract.

## Inputs

Read these files from the chosen data root:

- `listings.csv` columns `hh_id,stratum,psu,listing_domain,region,urban,design_weight,list_seq`
- `interviews.csv` columns `hh_id,responded,phase2,y,tenure,assigned,interview_domain`
- `roster.csv` columns `hh_id,eligible_count`
- `domain_crosswalk.csv` columns `listing_domain,publish_domain`
- `census_domains.csv` columns `domain_id,region,urban_share,hh_count_census,urban_hh_count_census,eligible_count_census`

`urban` is `0` or `1`. `responded`, `phase2`, and `assigned` are `0` or `1`. Empty `y` is item missing. `assigned` is the household program arm. `list_seq` is a listing-pass index. The closed region set is the sorted unique `region` values in `census_domains.csv`. The reference region is the lexicographically last of those values. Region columns used in calibration are the other codes, in lexicographic order.

## Analysis sample

A household may appear more than once in `listings.csv`. Collapse to one row per `hh_id` using the first listing pass.

Attach interviews by `hh_id`. A listing with no interview is a unit nonrespondent and stays in the listing sample used for nonresponse cells. The published domain of a household is the `publish_domain` of its `listing_domain`. Status, emptiness, and the contrast use that published domain. `listing_domain` and `interview_domain` are not the published domain. Eligible counts come from `roster.csv`. A phase-two household with no roster row is out of the analysis sample.

Unit-nonresponse and phase-two response are adjusted on urban-by-region cells of the collapsed listings. The unique cell factors are those that reproduce every fit published table. Item completion uses the unweighted mean of observed `y` in tenure-by-urban cells among remaining phase-two households. A household with no observed `y` in its item cell, or with `assigned` other than `0` or `1`, is out of the analysis sample. Households with `phase2=0` are out of the analysis sample.

## Identification

Status is evaluated on the published domain of the analysis sample.

- `empty`: no analysis household in that published domain
- `unidentified`: at least one analysis household, but not both program arms, or either arm has a calibrated eligible-person total that is not strictly positive
- `identified`: both arms are present and both calibrated eligible-person totals are strictly positive

Numeric contrast fields are published only for `identified` domains. Other rows leave those fields empty.

## Weights and contrast

Analysis weights start from the design weight, then the two urban-by-region response adjustments, then a single linear calibration of household analysis weights to census household margins on the analysis sample. The calibration columns are an intercept, household `urban`, and the included region columns. The margin vector is `hh_count_census` for the intercept, `urban_hh_count_census` for urban, and `hh_count_census` summed over census domains in each included region.

For an identified domain the arm mean is the sum of `w * (y / eligible_count)` divided by the sum of `w`, over analysis households in that arm, where `w` is the analysis weight. The published contrast is treated minus control.

The standard error is the with-replacement PSU linearized standard error of that contrast, treating the calibrated analysis weights as fixed. Stratum PSU counts use distinct `psu` values on the collapsed listings, including PSUs that contribute nothing to a given domain. Duplicate listing rows that were dropped do not add PSUs. Do not apply a finite-population correction.

## Output

Write `/app/output/domain_contrasts.csv` as an ordinary non-symlink file with header

`domain_id,status,est_ate,est_se`

One row per census domain, in `census_domains.csv` order. `status` is `identified`, `unidentified`, or `empty`. For `identified` rows, quantize `est_ate` and `est_se` independently to 6 decimal places with round-half-even. For `unidentified` and `empty` rows, leave `est_ate` and `est_se` as empty fields. Use LF newlines. `/app/lib/survey_kit.py` is exploration IO only and is not a graded builder.
