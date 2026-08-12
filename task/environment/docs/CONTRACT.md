# Vale domain publication contract

This file is the unique published estimand. Fit trees under `/app/fit/case_*/` ship the same input filenames as production and do not ship expected CSVs. `/app/bin/sae_ref check DATA_DIR OUT_DIR` is a digest-allowlisted check-only probe on those fit trees. It never writes golden CSVs. It refuses `/app/data`, mutated trees, and any directory whose input digest is not allowlisted. Production grading uses `/app/data` only.

## Inputs

Read these files from the chosen data root:

- `households.csv` columns `hh_id,stratum,psu,domain_id,region,urban,tenure,design_weight,responded,phase2,y,eligible_count`
- `census_domains.csv` columns `domain_id,region,urban_share,hh_count_census,urban_hh_count_census,eligible_count_census`

`urban` is `0` or `1`. `responded` and `phase2` are `0` or `1`. Empty `y` is item missing. `eligible_count` is the household eligible-person count. Every sampled household appears in `households.csv`, including unit nonrespondents. The closed region set is the sorted unique `region` values in `census_domains.csv`. The reference region is the lexicographically last of those values. Treatment dummies exist for every other region, in lexicographic order of the included codes. Opposite dummy coding is rejected: sum-to-zero contrasts, dropping a different reference, and omitting the intercept.

## Analysis sample and weights

Unit-nonresponse cells are the cross of `urban` and `region` on the full sample. The unit-nonresponse factor on a respondent is the number of sampled households in its cell divided by the number of responding households in that cell. Opposite readings are rejected: dropping nonrespondents without this factor, and using a different cell definition.

Among respondents, phase-two cells are the same urban-by-region cells. The phase-two factor on a phase-two respondent is the number of respondents in its cell divided by the number of phase-two respondents in that cell. Households with `phase2=0` are excluded from the analysis sample. Opposite readings are rejected: treating every respondent as phase two, and applying the phase-two factor before the unit-nonresponse factor.

Item-missing cells are the cross of `tenure` and `urban` among phase-two respondents. A missing `y` is replaced by the unweighted mean of observed `y` in that item cell. If that cell has no observed `y`, the household is dropped from the analysis sample. Opposite readings are rejected: using urban-by-region cells for item imputation, complete-case deletion of every missing `y` when the item cell has an observed mean, and a weighted item mean.

The pre-calibration weight is design weight times the unit-nonresponse factor times the phase-two factor. Linear calibration uses Deville-Sarndal g-weights on the analysis sample. The calibration vector `z` has columns in this order: intercept of ones, household `urban`, then the included region dummies. The margin vector `T` is the census household totals of those columns: `hh_count_census` for the intercept, `urban_hh_count_census` for urban, and `hh_count_census` summed over domains in each included region. With `w` the pre-calibration weights, `g = 1 + z * (Z' W Z)^{-1} (T - Z' w)` in the usual row-wise sense, and the calibrated weight is `w * g`. Calibration comes after unit nonresponse and phase two. Opposite readings are rejected: frequency-weight interpretation of design weights, calibrating before nonresponse, and raking or logit-distance calibration.

## Direct rate and variance

The direct domain total of the outcome is the calibrated inverse-probability total of analysis-sample `y` in the domain. The direct eligible-person total is the same with `eligible_count`. The direct rate `R_d` is the ratio of those two totals. A direct rate is defined only when the domain has at least one analysis household and a strictly positive direct eligible-person total. Otherwise the domain is synthetic-only and is excluded from the between-domain variance calculation. Opposite readings are rejected: the unweighted mean of household `y / eligible_count`, and a direct rate that uses design weights without calibration.

For a defined direct rate, the household linearized residual is the domain indicator times (`y` minus `R_d` times `eligible_count`). The PSU total `z_hj,d` is the calibrated-weight sum of those residuals in PSU `j` of stratum `h`. Every sampled PSU in the stratum contributes a total, including zeros. The stratum mean is the unweighted mean of those `n_h` PSU totals, where `n_h` is the number of distinct PSUs in stratum `h` in the full `households.csv` sample. The linearized variance of the residual total is the sum over strata of `n_h` over (`n_h` minus 1) times the sum of squared deviations of PSU totals from the stratum mean. There is no finite-population correction and no extra degrees-of-freedom factor. Shipped strata each have at least two PSUs. The direct variance `psi_d` is that linearized variance divided by the square of the direct eligible-person total. Opposite readings are rejected: clustering at the household or the domain, dropping zero-contribution PSUs from `n_h`, applying a finite-population correction, and using a with-replacement factor other than `n_h` over (`n_h` minus 1).

## Working model, A, and composite

The unit-level working model is weighted least squares of analysis-sample `y` on the same `z` columns as calibration, with the calibrated weights as probability weights. The coefficient is `(X' W X)^{-1} X' W y`. The synthetic rate for domain `d` is `x_d` dot that coefficient, where `x_d` is intercept 1, census `urban_share`, and the region dummy row for that domain. Opposite readings are rejected: using household `urban` 0/1 in place of census `urban_share` on the synthetic row, and omitting the intercept.

The between-domain variance `A` is the Prasad and Rao 1990 Journal of the American Statistical Association moment estimator of the Fay-Herriot between-area variance with the leverage correction. It is not the Fay-Herriot 1979 iterative solver, not a Datta-Lahiri weighted moment, and not REML. On the `m` domains with a defined direct rate, form the unweighted OLS of those direct rates on the area-level matrix whose rows are the same census `x_d` vectors. Let `p` be that column count, let `h_ii` be the OLS leverages, and let `A_PR` be one over (`m` minus `p`) times (the sum of squared OLS residuals minus the sum of `psi_i` times (one minus `h_ii`)). Set `A` to the maximum of 0 and `A_PR`. If `m` is at most `p` or the area-level Gram matrix is singular, set `A` to 0. That OLS fit is used only to estimate `A`. It is not the published synthetic.

For a domain with a defined direct rate, `gamma` is `A` over (`A` plus `psi_d`), except that `gamma` is 1 when `psi_d` is 0, and `gamma` is 0 when `A` is 0 and `psi_d` is positive. Empty and undefined-direct domains have `gamma` 0. The published rate is `gamma` times the direct rate plus (one minus `gamma`) times the WLS synthetic. The published total is the published rate times `eligible_count_census`. Opposite readings are rejected: always-direct tables, always-synthetic tables, and publishing the inverse-probability total instead of rate times the census eligible-person count.

## Output

Write `/app/output/domain_estimates.csv` as an ordinary non-symlink file with header

`domain_id,est_total,est_rate`

One row per census domain, in `census_domains.csv` order. Quantize `est_rate` to 6 decimal places with round-half-even first. Then set `est_total` to that quantized rate times `eligible_count_census`, then quantize `est_total` to 2 decimal places with round-half-even. Use LF newlines. `/app/lib/survey_kit.py` is exploration IO only and is not a graded builder.
