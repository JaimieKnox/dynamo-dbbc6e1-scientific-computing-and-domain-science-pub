# Vale domain program-contrast contract

This file is the unique published estimand. Fit trees under `/app/fit/case_*/` ship the same input filenames as production and do not ship expected CSVs. They are unlabeled extracts for schema and construction, not a check-only oracle. Production grading uses `/app/data` only. That production tree is not an isomorphic copy of any single fit tree.

## Inputs

Read these files from the chosen data root:

- `listings.csv` columns `hh_id,stratum,psu,listing_domain,region,urban,design_weight,list_seq`
- `interviews.csv` columns `hh_id,responded,phase2,y,tenure,assigned,interview_domain`
- `roster.csv` columns `hh_id,eligible_count`
- `domain_crosswalk.csv` columns `listing_domain,publish_domain`
- `census_domains.csv` columns `domain_id,region,urban_share,hh_count_census,urban_hh_count_census,eligible_count_census`

`urban` is `0` or `1`. `responded`, `phase2`, and `assigned` are `0` or `1`. Empty `y` is item missing. `assigned` is the household program arm. `list_seq` is a listing-pass index. The closed region set is the sorted unique `region` values in `census_domains.csv`. The reference region is the lexicographically last of those values. Treatment dummies exist for every other region, in lexicographic order of the included codes.

## Sample construction

A household may appear more than once in `listings.csv`. Sort listing rows by `hh_id`, then `psu`, then `list_seq`, all lexicographic as strings. Keep only the first row per `hh_id`.

Left-join `interviews.csv` onto the collapsed listings by `hh_id`. A listing with no interview row is a unit nonrespondent: `responded=0`, `phase2=0`, empty `y`, empty `tenure`, and empty `assigned`. Those listings remain in the collapsed listing sample used for unit-nonresponse cells.

The published domain of a collapsed listing is the `publish_domain` from `domain_crosswalk.csv` keyed by `listing_domain`. Ignore `interview_domain`. Overlap and emptiness are evaluated on that published domain, not on `listing_domain` and not on `interview_domain`.

Eligible-person counts come from `roster.csv` keyed by `hh_id`. A phase-two household with no roster row is dropped from the analysis sample. Missing roster on a unit nonrespondent or a phase-one-only respondent does not remove that household from the listing sample used for nonresponse cells.

Unit-nonresponse cells are the cross of `urban` and `region` on the collapsed listings. The unit-nonresponse factor on a respondent is the number of collapsed listings in its cell divided by the number of responding households in that cell.

Among respondents, phase-two cells are the same urban-by-region cells. The phase-two factor on a phase-two respondent is the number of respondents in its cell divided by the number of phase-two respondents in that cell. Households with `phase2=0` are excluded from the analysis sample.

Item-missing cells are the cross of `tenure` and `urban` among phase-two respondents that remain after the roster join. A missing `y` is replaced by the unweighted mean of observed `y` in that item cell. If that cell has no observed `y`, the household is dropped from the analysis sample. Households whose `assigned` is not `0` or `1` are dropped from the analysis sample.

Stratum PSU counts `n_h` use distinct `psu` values on the collapsed listings, including PSUs that contribute zero to a given domain contrast. Duplicate listing rows that were dropped do not add PSUs. Shipped strata each have at least two collapsed PSUs.

## Identification

A census domain is `empty` when the analysis sample contains no household in that published domain.

A census domain is `unidentified` when it has at least one analysis household but fails positivity: it does not contain both program arms, or the calibrated eligible-person total for either arm is not strictly positive.

A census domain is `identified` only when both arms are present in its analysis households and both calibrated eligible-person totals are strictly positive. Do not publish a numeric contrast for `empty` or `unidentified` domains. Filling zero, a one-arm mean, or an OLS gap on those rows is not a valid publication.

## Weights and contrast

The pre-calibration weight is design weight times the unit-nonresponse factor times the phase-two factor. Calibrate those weights to census household margins on the analysis sample with a linear g-weight whose columns are intercept of ones, household `urban`, then the included region dummies. The margin vector is `hh_count_census` for the intercept, `urban_hh_count_census` for urban, and `hh_count_census` summed over census domains in each included region. Calibration comes after the two response factors.

For an identified domain, the arm mean is the Hajek ratio of the calibrated total of `y` in that arm to the calibrated total of `eligible_count` in that arm. The published contrast is the treated arm mean minus the control arm mean. It is not an unweighted difference of household means, not an OLS coefficient on `assigned`, and not a small-area composite of domain rates.

The standard error is the square root of the with-replacement ultimate-cluster linearized variance of that contrast, clustered by PSU within stratum. Use `n_h` from the collapsed listings, retain zero-contribution PSUs, and do not apply a finite-population correction.

## Output

Write `/app/output/domain_contrasts.csv` as an ordinary non-symlink file with header

`domain_id,status,est_ate,est_se`

One row per census domain, in `census_domains.csv` order. `status` is `identified`, `unidentified`, or `empty`. For `identified` rows, quantize `est_ate` and `est_se` independently to 6 decimal places with round-half-even. For `unidentified` and `empty` rows, leave `est_ate` and `est_se` as empty fields. Use LF newlines. `/app/lib/survey_kit.py` is exploration IO only and is not a graded builder.
