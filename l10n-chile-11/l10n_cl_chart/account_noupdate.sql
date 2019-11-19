UPDATE ir_model_data
SET noupdate = TRUE
WHERE module like 'l10n_cl_chart' AND noupdate = FALSE
AND model IN (
'account.tax')
