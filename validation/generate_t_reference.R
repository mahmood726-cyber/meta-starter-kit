# Deterministic distribution references, not patient or trial observations.
# Run from repository root: Rscript validation/generate_t_reference.R
degrees <- c(1:100, 128, 256, 512, 1000, 10000, 1000000)
values <- qt(0.975, df = degrees)
stopifnot(all(is.finite(values)), all(diff(values) < 0))
writeLines(c("df,quantile_975", sprintf("%d,%.17g", degrees, values)),
           "validation/student_t_975.csv", useBytes = TRUE)
cat(R.version.string, "\n")
