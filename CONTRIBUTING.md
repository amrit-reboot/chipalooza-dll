# Contributing

This repository documents a pre-layout feasibility study. Contributions should make the evidence trail clearer, not make the project look more complete than it is.

## Rules

1. Preserve original evidence. Do not delete or rewrite raw CSVs, historical reports, validated scripts, or prior proposal versions to make results look cleaner.
2. Do not change a baseline specification unless the change is explicitly documented and approved. Record the reason, date, and decision source.
3. Distinguish targets from demonstrated results. Use Level A for analytical work, Level B for behavioral models, Level C for transistor-level Sky130 work, and Level D for post-layout work.
4. Record simulation conditions, tool versions, parameters, and random seeds with every result.
5. Keep raw generated results separate from processed tables and plots.
6. Add a source path to every numerical claim in documentation.
7. Do not claim transistor-level validation without actual Sky130 MOSFET simulation evidence.
8. Do not claim post-layout, DRC, LVS, silicon, or hardware measurement results without corresponding files.
9. If a result is withdrawn or superseded, add a correction notice instead of silently replacing the old text.
10. Do not add secrets, private contact data, machine-specific paths, or generated caches to the repository.

## Suggested workflow

- Make small changes tied to a single report, script, or evidence set.
- Reproduce affected results in a clean copy before overwriting committed data.
- Update the relevant report and source path reference in the same commit.
- Keep documentation formal and technically specific. Avoid unverified feasibility claims.
