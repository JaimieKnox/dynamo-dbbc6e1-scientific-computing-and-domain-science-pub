# Vale domain publication contract

This file is the unique published estimand. Fit trees under `/app/fit/case_*/` ship the same input filenames as production and do not ship expected CSVs. `/app/bin/sae_ref check DATA_DIR OUT_DIR` is a digest-allowlisted check-only probe on those fit trees. It never writes golden CSVs. It refuses `/app/data`, mutated trees, and any directory whose input digest is not allowlisted. Production grading uses `/app/data` only.

Production `/app/data` is not an isomorphic copy of any single fit tree. Matching every allowlisted fit digest does not by itself prove that a script is valid on production.

## Inputs

Read these files from the chosen data root:

- `listings.csv` columns `hh_id,stratum,psu,listing_domain,region,urban,design_weight,list_seq`
- `interviews.csv` columns `hh_id,responded,phase2,y,tenure,interview_domain`
- `roster.csv` columns `hh_id,eligible_count`
- `domain_crosswalk.csv` columns `listing_domain,publish_domain`
- `census_domains.csv` columns `domain_id,region,urban_share,hh_count_census,urban_hh_count_census,eligible_count_census`

`urban` is `0` or `1`. `responded` and `phase2` are `0` or `1`. Empty `y` is item missing. `list_seq` is a listing-pass index. The closed region set is the sorted unique `region` values in `census_domains.csv`. The reference region is the lexicographically last of those values. Treatment dummies exist for every other region, in lexicographic order of the included codes. Opposite dummy coding is rejected: sum-to-zero contrasts, dropping a different reference, and omitting the intercept.

## Sample construction

A household may appear more than once in `listings.csv`. Sort listing rows by `hh_id`, then `psu`, then `list_seq`, all lexicographic as strings. Keep only the first row per `hh_id`. Opposite readings are rejected: keeping the last duplicate, averaging duplicate design weights, and treating every listing row as a distinct household.

Left-join `interviews.csv` onto the collapsed listings by `hh_id`. A listing with no interview row is a unit nonrespondent: `responded=0`, `phase2=0`, empty `y`, and empty `tenure`. Those listings remain in the collapsed listing sample used for unit-nonresponse cells. Do not drop them.

The published domain of a collapsed listing is the `publish_domain` from `domain_crosswalk.csv` keyed by `listing_domain`. Ignore `interview_domain`. Opposite readings are rejected: publishing on `interview_domain`, publishing on `listing_domain` without the crosswalk, and dropping a listing whose interview domain disagrees with its listing domain.

Eligible-person counts come from `roster.csv` keyed by `hh_id`. A phase-two household with no roster row is dropped from the analysis sample. Missing roster on a unit nonrespondent or a phase-one-only respondent does not remove that household from the listing sample used for nonresponse cells.

Unit-nonresponse cells are the cross of `urban` and `region` on the collapsed listings. The unit-nonresponse factor on a respondent is the number of collapsed listings in its cell divided by the number of responding households in that cell. Opposite readings are rejected: forming those cells on interviews only, and using `interview_domain` in place of listing `region`.

Among respondents, phase-two cells are the same urban-by-region cells. The phase-two factor on a phase-two respondent is the number of respondents in its cell divided by the number of phase-two respondents in that cell. Households with `phase2=0` are excluded from the analysis sample. Opposite readings are rejected: treating every respondent as phase two, and applying the phase-two factor before the unit-nonresponse factor.

Item-missing cells are the cross of `tenure` and `urban` among phase-two respondents that remain after the roster join. A missing `y` is replaced by the unweighted mean of observed `y` in that item cell. If that cell has no observed `y`, the household is dropped from the analysis sample. Opposite readings are rejected: using urban-by-region cells for item imputation, complete-case deletion of every missing `y` when the item cell has an observed mean, and a weighted item mean.

Stratum PSU counts `n_h` use distinct `psu` values on the collapsed listings, including PSUs that contribute zero to a given domain residual. Duplicate listing rows that were dropped do not add PSUs. Shipped strata each have at least two collapsed PSUs.

## Weights, direct rate, and composite

The pre-calibration weight is design weight times the unit-nonresponse factor times the phase-two factor. Linear calibration uses Deville-Sarndal g-weights on the analysis sample after those two factors. The calibration vector has columns in this order: intercept of ones, household `urban`, then the included region dummies. The margin vector is the census household totals of those columns: `hh_count_census` for the intercept, `urban_hh_count_census` for urban, and `hh_count_census` summed over census domains in each included region. Opposite readings are rejected: frequency-weight interpretation of design weights, calibrating before nonresponse, and raking or logit-distance calibration.

The direct domain total of the outcome is the calibrated inverse-probability total of analysis-sample `y` in the published domain. The direct eligible-person total is the same with `eligible_count`. The direct rate `R_d` is the ratio of those two totals. A direct rate is defined only when the domain has at least one analysis household and a strictly positive direct eligible-person total. Otherwise the domain is synthetic-only and is excluded from the between-domain variance calculation. Opposite readings are rejected: the unweighted mean of household `y / eligible_count`, and a direct rate that uses design weights without calibration.

Direct variance `psi_d` is the with-replacement ultimate-cluster linearization of that ratio, with factor `n_h` over (`n_h` minus 1), no finite-population correction, and zero-contribution PSUs retained in `n_h`. Opposite readings are rejected: clustering at the household or the domain, dropping zero-contribution PSUs from `n_h`, and applying a finite-population correction.

The unit-level working model is weighted least squares of analysis-sample `y` on the same columns as calibration, with the calibrated weights as probability weights. The synthetic rate for a census domain uses intercept 1, that domain's census `urban_share`, and the region dummy row. Opposite readings are rejected: using household `urban` 0/1 in place of census `urban_share` on the synthetic row, and omitting the intercept.

The between-domain variance `A` is the Prasad and Rao 1990 Journal of the American Statistical Association leverage-corrected moment estimator, truncated below at 0. It is not the Fay-Herriot 1979 iterative solver, not a Datta-Lahiri weighted moment, and not REML. The OLS fit used to form `A` is not the published synthetic. If the number of domains with a defined direct rate is at most the area-level column count, or the area-level Gram matrix is singular, set `A` to 0.

For a domain with a defined direct rate, `gamma` is `A` over (`A` plus `psi_d`), except that `gamma` is 1 when `psi_d` is 0, and `gamma` is 0 when `A` is 0 and `psi_d` is positive. Empty and undefined-direct domains have `gamma` 0. The published rate is `gamma` times the direct rate plus (one minus `gamma`) times the WLS synthetic. The published total is the published rate times `eligible_count_census`. Opposite readings are rejected: always-direct tables, always-synthetic tables, and publishing the inverse-probability total instead of rate times the census eligible-person count.

Fit trees `case_00` through `case_11` pin the unique numeric realization of those named formulas that this publication uses. A candidate that matches every allowlisted fit digest and then ignores construction, crosswalk, or duplicate-listing collapse on `/app/data` is not a valid production estimator.

## Output

Write `/app/output/domain_estimates.csv` as an ordinary non-symlink file with header

`domain_id,est_total,est_rate`

One row per census domain, in `census_domains.csv` order. Quantize `est_rate` to 6 decimal places with round-half-even first. Then set `est_total` to that quantized rate times `eligible_count_census`, then quantize `est_total` to 2 decimal places with round-half-even. Use LF newlines. `/app/lib/survey_kit.py` is exploration IO only and is not a graded builder.
