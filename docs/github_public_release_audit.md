# GitHub Public Release Audit

Date: 2026-11-22 UTC
Project: Chipalooza Challenge #4 eight-phase DLL feasibility study
Target repository: `amrit-reboot/chipalooza-dll`

## 1. Purpose

This record documents the checks performed before publishing the local project as a public GitHub repository. It separates verified facts from publication decisions. No transistor-level simulation, layout work, package installation, or new experiment was performed for this audit.

## 2. Environment and authentication

| Item | Verified result |
|---|---|
| Git | 2.53.0.windows.2 |
| GitHub CLI | 2.102.0 |
| GitHub account | `amrit-reboot`, active account, HTTPS operations |
| Token scopes | `gist`, `read:org`, `repo`, `workflow`; token value not recorded |
| Git repository before Task 8 | absent; no `.git` directory |
| Target repository before creation | not found through GitHub API and public URL returned 404 |
| Simulation tools | no new ngspice, xschem, Docker, or PDK work run in Task 8 |

The 404 result was treated as permission to create the repository, not as evidence that another owner's repository was available. The owner name and repository name were checked before creation.

## 3. Baseline inventory

A fresh SHA-256 inventory was captured before any Task 8 file creation.

| Metric | Value |
|---|---:|
| Baseline file count | 168 |
| Baseline capture time | 2026-11-22T13:03:52.996955+00:00 |
| Baseline inventory SHA-256 | `011b916676ac62443a71b284370c6d6f6829d687e7bf4ad54cfaa56d2f873bee` |
| Public candidate file count before release docs | 144 |
| Final published file count | 147 |

The baseline inventory is retained in the local task workspace. It includes historical and submission files that are preserved locally but excluded from public Git.

## 4. Secret and privacy scan

A conservative pattern scan covered all text-like files, including hidden files. The scan searched for private key headers, GitHub tokens, AWS keys, Slack tokens, Google API keys, OpenAI-style keys, JWTs, generic credential assignments, email addresses, personal profile URLs, SSH URLs, and absolute local paths.

### 4.1 Credentials

No private keys, API tokens, access tokens, passwords, generic secret assignments, or JWTs were found. No secret value is reproduced in this document.

### 4.2 Contact and personal data

Email-like matches were limited to the official competition contact address and were found only in excluded submission documentation. Addresses are not reproduced here.

Personal profile links and biographical material were found in the designer CV and in submission audits. These files are excluded from public Git.

### 4.3 Machine-specific paths

Absolute local paths and a local username were found in the following retained files before cleanup:

- `results/environment_report.md`, lines 38, 42, 256, and 290.
- `scripts/env_audit.sh`, `scripts/iic.ps1`, and `scripts/iic.sh`, excluded from public Git.
- `README_submission.md`, `README_submission_v2.md`, `proposal/final_submission_audit_v2.md`, and `proposal/source_evidence_audit_v2.md`, excluded from public Git.

The four local path references in `results/environment_report.md` were redacted to generic placeholders. Tool versions, measured outcomes, dates, and technical conclusions were not changed. The original technical meaning of each line was preserved.

### 4.4 Submission archive

The root submission ZIP is excluded from public Git. Its filename contains a personal name, and it contains submission attachments with unresolved personal-input status. The local ZIP and its previously verified checksum were not altered.

## 5. License and ownership

No license, copyright header, SPDX tag, or license grant existed before Task 8. The user confirmed ownership or control of the original technical files and approved Apache License 2.0 for the public technical subset on 2026-11-22. The user did not approve publication of personal CV, equipment, email, or generated submission artifacts.

Accordingly:

- `LICENSE` contains the Apache License 2.0 text.
- `NOTICE` records ownership, publication scope, dependencies, and external references.
- The public repository license applies to original technical work in the public subset.
- Personal and submission-only files remain local and are ignored by Git.
- No Sky130 PDK, model library, corner file, foundry asset, paper PDF, or third-party source code is included.

## 6. Publication inclusion rules

### 6.1 Included

The public repository includes:

- baseline governance and specifications;
- architecture and decision records;
- the canonical technical proposal and historical technical proposal drafts;
- analytical and behavioral result reports;
- raw CSV and JSON result tables;
- generated plots that support published claims;
- behavioral models, validation engines, runners, and unit tests;
- public-release README, contributing guide, license, notice, audit, and manifest;
- `.gitattributes` to preserve exact file bytes by disabling line-ending conversion.

### 6.2 Excluded

The following local files and directories are excluded by `.gitignore`:

- `USER_INPUT_REQUIRED.md`;
- `README_submission.md` and `README_submission_v2.md`;
- `proposal/submission_email_v1.md`;
- `proposal/submission_readiness_v1.md`;
- `proposal/final_submission_audit_v1.md` and `proposal/final_submission_audit_v2.md`;
- `proposal/source_evidence_audit_v2.md`;
- `proposal/submission_manifest_v1.md` and `proposal/submission_manifest_v2.md`;
- `proposal/designer_cv_v1.md`;
- `proposal/equipment_list_v1.md`;
- `submission_package/`;
- the root submission ZIP;
- machine-specific helper scripts `scripts/env_audit.sh`, `scripts/iic.ps1`, and `scripts/iic.sh`;
- Python bytecode caches and editor or simulator temporary files.

Exclusion means not committed to public Git. No excluded file was deleted from the local workspace.

## 7. Documentation consistency

The canonical final proposal is `proposal/proposal_v1_submission.md`. Older proposal versions and audits remain as historical traceability material. `README.md` states their status and directs readers to the canonical file.

`AGENTS.md` retains the original phase plan and its first-task stop instruction. That text is part of the project history. `README.md` states that later work was executed beyond that initial instruction, so the stop text is not presented as the current project state.

Stale submission-status documents and local reproduction notes are excluded. The public README contains the supported reproduction commands and fixed random seeds.

## 8. Technical claim boundary

The public repository does not claim transistor-level, post-layout, silicon, or hardware validation. All current evidence is Level A analytical or Level B behavioral. The README explicitly states this boundary.

Claims reproduced in the README were checked against raw result files before publication:

- convergence runs in `results/pfd_validation/final_validation/tables/f2_convergence.csv`;
- acquisition runs in `results/pfd_validation/acquisition_controller/acquisition_results.csv`;
- robustness runs in `results/pfd_validation/acquisition_robustness/lock_time.csv`;
- frequency sweep in `results/tables/frequency_sweep.csv`;
- duty correction in `results/tables/duty_correction.csv`;
- jitter sensitivity in `results/tables/jitter_sensitivity.csv`.

No new result was fabricated and no failed result was removed.

## 9. Reproduction

The public README records Python environment checks, four main runner commands, two optional unit-test commands, and fixed seeds. The committed scripts are the source of the published tables and plots. Some historical plots were produced by earlier or temporary generators; this limitation is recorded in `NOTICE`.

Running the scripts may overwrite files under `results/`. Reproduction should be performed from a clean copy when the committed raw outputs must be preserved.

## 10. Integrity decisions

- No pre-existing technical result file was deleted.
- No simulation output was regenerated for publication.
- No excluded file was overwritten.
- No remote repository was overwritten.
- No force push or destructive Git operation was used.
- The submission ZIP checksum was not recomputed or changed.
- The four redactions in `results/environment_report.md` are the only change to a pre-existing published technical file, and they affect only local path text.

## 11. Publication verification

Publication completed on 2026-11-22. The initial content commit is `4d87a6f048298e1248f677f02a4ebf4f768a39d7`. These verification results were recorded in a separate documentation commit after the initial push.

| Check | Result |
|---|---|
| Repository | `https://github.com/amrit-reboot/chipalooza-dll` |
| Visibility | public |
| Default branch | `main` |
| Local HEAD after initial push | `4d87a6f048298e1248f677f02a4ebf4f768a39d7` |
| Remote `main` after initial push | same commit |
| Remote blob count | 147 |
| Excluded-file matches on remote | 0 |
| README, LICENSE, NOTICE, audit, and manifest on remote | present |
| Push mode | normal push, no force |
| Public page check | repository page returned the expected title, description, public label, and rendered README |

No operation in this workflow overwrote a remote branch or repository.
