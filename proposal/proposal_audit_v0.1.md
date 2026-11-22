# Proposal Audit — Draft v0.1

**Document audited:** `proposal/proposal_v0.1.md`  
**Date:** 2026-11-21  
**Outcome:** Draft is internally consistent with the available repository evidence and is suitable for **review only**. It is **not submission-ready**.

---

## TASK

Audit the Draft v0.1 proposal against actual project reports, CSV data, the official Chipalooza Challenge #4 requirements, repository baseline specifications, figure availability, and reference metadata. Identify unsupported claims, source inconsistencies, placeholders, and decisions still required.

---

## CHANGES

New files only:

| File | Purpose |
|---|---|
| `proposal/proposal_v0.1.md` | Draft proposal, 15 numbered sections |
| `proposal/proposal_audit_v0.1.md` | This audit |

No official specification, architecture, design, simulation, script, or validated result file was modified. No files were deleted. Problem 2 was not started. No tools or dependencies were installed.

---

## METHOD

1. Read the principal reports:
   - `results/behavioral_dll.md`
   - `results/environment_report.md`
   - `results/pfd_validation/report.md`
   - `results/pfd_validation/final_validation/report.md`
   - `results/pfd_validation/review/report.md`
   - `results/pfd_validation/acquisition_investigation/report.md`
   - `results/pfd_validation/acquisition_investigation/references.md`
   - `results/pfd_validation/acquisition_controller/report.md`
   - `results/pfd_validation/acquisition_controller/failure_analysis.md`
   - `results/pfd_validation/acquisition_controller/coarse_actuator.md`
   - `results/pfd_validation/acquisition_robustness/report.md`
   - `results/pfd_validation/acquisition_robustness/failure_analysis.md`
2. Recomputed statistics directly from CSVs rather than accepting report text.
3. Read official challenge rules from `https://opencircuitdesign.com/chipalooza/rules-4.html`.
4. Used `AGENTS.md` as the project baseline specification source. `spec/` contained no files, so no separate official brief was available locally.
5. Verified figure files by PNG signature and dimensions and cross-checked their source reports.
6. Checked external reference metadata using DOI/Crossref, arXiv, institutional pages, publisher/search results, and the patent record. Full-text PDF retrieval was not possible for some publisher-hosted PDFs; metadata was still validated where possible.

---

## 1. Official requirement coverage

The official Chipalooza Challenge #4 rules require the main proposal to provide:

| Official requirement | Proposal coverage | Status |
|---|---|---|
| Type of IP block | Section 4 | PASS |
| List of I/O, including test ports | Section 7 | PASS with open issues flagged |
| Functional description | Section 5 | PASS |
| Target specification with average/minimum/maximum and absolute limits | Section 8 | PASS |
| Outline of a test plan for measurement validation | Section 12 | PASS |
| Equipment list, separately | Explicitly excluded from main document | PASS |
| Designer CVs, separately | Explicitly excluded from main document | PASS |
| No personal/institutional details in main document | Metadata contains no such details | PASS |

The 15-section internal structure is present and numbered Sections 1–15.

---

## 2. Verified numeric evidence

### 2.1 Phase 3 acquisition-controller CSV

Source: `results/pfd_validation/acquisition_controller/acquisition_results.csv`

| Check | Recomputed result | Proposal wording | Status |
|---|---:|---|---|
| Total rows | 406 | 406 | PASS |
| Main matrix | 273 | 273 | PASS |
| Main successes | 128 | 128 | PASS |
| Correct-band cases | 91 | 91 | PASS |
| Correct-band successes | 76 | 76 | PASS |
| Correct band excluding 25 MHz | 78 cases, 76 successes | 78, 76 | PASS |
| 25 MHz correct band at 300 µA | 0/13 | stated as historical failure | PASS |
| Randomized tests | 35, 30 successes | 35, 30 | PASS |
| Boundary tests | 84, 69 successes | 84, 69 | PASS |
| Harmonic LOCK assertions | 0 | 0 | PASS |
| Effective lock time, successful correct-band cases | min 7, median 24, max 111 | reported in evidence base | PASS |

The 13 main initial-condition labels were confirmed from `run_summary.json`: `min`, `max`, `0.68`, `0.90`, `1.00`, `1.02`, `1.05`, `1.10`, `1.30`, `1.50`, `1.95`, `2.10`, and `2.50`.

### 2.2 Phase 4 robustness sweep

Sources: `current_sweep.csv`, `lock_time.csv`, `strategy_comparison.csv`, `sweep_meta.json`.

| Check | Recomputed result | Proposal wording | Status |
|---|---:|---|---|
| Frequency/current combinations | 56 | 7 × 8 | PASS |
| Controller runs | 728 | 728 | PASS |
| Fixed 200 µA total | 91/91 | 91/91 | PASS |
| Fixed 200 µA median effective lock time | 26 cycles | 26 | PASS |
| Fixed 200 µA maximum effective lock time | 158 cycles | 158 | PASS |
| Fixed 200 µA cases ≤100 cycles | 85/91 | 85/91 | PASS |
| Fixed 200 µA cases >100 cycles | 6/91 | stated indirectly | PASS |
| Global worst effective lock time | 197 cycles | 197 | PASS |
| Global worst location from CSV | **200 MHz, 150 µA** | proposal uses this | PASS — see issue A1 |
| Harmonic LOCK assertions in 728 rows | 0 | 0 | PASS |
| Wrong-band cases re-swept | No | explicitly stated | PASS |

The fixed-200 µA per-frequency success and worst-lock values in Section 10.3 were checked against `current_sweep.csv` and match exactly.

### 2.3 Boundary study

Source: `boundary_summary.csv`.

| `Icp` | 30 MHz lower edge | 25 MHz lower edge | 30 MHz recovery |
|---:|---:|---:|---:|
| 50 µA | 1.036 | 1.054 | 5/5 |
| 75 µA | 1.056 | 1.082 | 5/5 |
| 100 µA | 1.076 | 1.112 | 5/5 |
| 125 µA | 1.096 | none in window | 5/5 |
| 150 µA | 1.116 | none in window | 5/5 |
| 200 µA | none in window | none in window | 5/5 |
| 250 µA | none in window | none in window | 5/5 |
| 300 µA | none in window | none in window | 2/5 |

These match Section 10.4. The proposal correctly states that the 30 MHz lower edge moves monotonically from 1.036 to 1.116 over 50–150 µA and that no 1T point was found in the measured window at 200–300 µA.

### 2.4 Strategy comparison

Source: `strategy_comparison.csv`.

- Fixed 200 µA: 91/91, worst 158 cycles.
- Fixed 300 µA: 76/91, worst 111 cycles.
- Band-dependent 200/200/300 µA: 91/91, worst 111 cycles.
- Descending-current/ExploreController results are investigation-only and were not adopted.

The proposal does not claim the 111-cycle result for the recommended fixed-current case. This is correct.

---

## 3. Specification source audit

The target tables in Section 8 were checked against `AGENTS.md` §4.1–4.3:

- supply: 1.62 / 1.80 / 1.98 V;
- temperature: −40 / 27 / +110 °C;
- corners: TT, SS, FF, SF, FS;
- input frequency: 25–200 MHz;
- input duty: 30–70%;
- input edge time: ≤1 ns;
- bands: 25–60, 50–120, 100–200 MHz;
- lock time: 100 typical / 400 maximum cycles;
- static phase error: ±2% / ±5% of `T`;
- tap DNL: ±8% / ±15% of `T/8`;
- `CLK50`: 50% / 45–55%;
- jitter: 25 / 60 ps RMS at 100 MHz;
- current: 1 mA typical at 100 MHz, 2 mA maximum at 200 MHz;
- load: ≥100 fF each;
- false locks: 0 / 0 in startup tests;
- area: ≤0.05 mm².

The stage-delay table was checked against `AGENTS.md` §4.4. All values match.

The official rules confirm that the target specification is designer-defined and that mid-design changes require approval. The proposal correctly treats these as project baseline targets rather than challenge-imposed values.

---

## 4. Evidence-level audit

| Proposal claim area | Evidence level used | Acceptable? |
|---|---|---|
| Acquisition sweeps and lock times | Level B | Yes, clearly labeled |
| PFD timestep convergence | Level B | Yes |
| Loop-gain explanation | Level A/B | Yes, described as analytical/behavioral |
| Delay-cell feasibility | No result claimed | Correct; UNVERIFIED |
| DCC performance | No result claimed | Correct; UNVERIFIED |
| Jitter | Earlier estimate only | Correct; ESTIMATE, not PASS |
| Power/current | Earlier estimate only | Correct; ESTIMATE, not PASS |
| Area | No result claimed | Correct; UNVERIFIED |
| Metastability/PVT/mismatch | No result claimed | Correct; UNVERIFIED |
| Transistor/post-layout | Explicitly excluded | Correct |

No Level A or Level B result is presented as Level C or D evidence.

---

## 5. Figure audit

All referenced PNG files exist, have valid PNG signatures, and have nonzero dimensions. The classification in Section 15.1 is appropriate:

| Figure path | Classification basis |
|---|---|
| `acquisition_investigation/block_diagrams/recommended.png` | Conceptual block diagram generated from the investigation; not a circuit schematic |
| `acquisition_robustness/plots/success_vs_icp.png` | Plot generated from behavioral sweep CSV |
| `acquisition_robustness/plots/lock_time_vs_icp.png` | Plot generated from behavioral sweep CSV |
| `acquisition_robustness/plots/boundary_30mhz.png` | Plot generated from 0.002-T boundary study |
| `acquisition_controller/controller_state_diagram.png` | Behavioral FSM prototype diagram; not hardware |

No schematic, layout, measured waveform, or transistor-level plot was fabricated or implied.

---

## 6. Reference validation

| Reference | Validation result |
|---|---|
| Razavi 2018 | Validated via accessible UCLA PDF and search metadata; vol. 10, no. 3, pp. 9–15, doi 10.1109/MSSC.2018.2844615 |
| Booth thesis | Corrected and validated: author **Eric R. Booth**, Boise State University, 2006; R. Jacob Baker was advisor, not author |
| Kim/Hyoung/Park 2015 | Validated via Crossref: *Electronics Letters* 51(2), 136–138, doi 10.1049/el.2014.3749 |
| Wei/Chen/Li/Yang 2017 | Validated via Crossref: *Electronics Letters* 53(2), 70–71, doi 10.1049/el.2016.3032 |
| Wainstein et al. 2025 | Validated via arXiv:2501.13238v2 metadata |
| Li and Cao 2016 | Validated via accessible WCSE PDF: pp. 563–566, doi 10.18178/wcse.2016.06.095 |
| US Patent 7,209,533 B1 | Validated via patent record; inventors H. Nguyen, Y.-S. Yang, V. Le; National Semiconductor |
| Official rules | Fetched directly from the official Chipalooza site |

No invented author, DOI, title, venue, or publication detail was retained. The proposal states that references are background only.

---

## 7. Corrections and unsupported claims removed

1. **Submission-ready language removed.** The proposal is explicitly Draft v0.1 for review.
2. **`91/91` scope narrowed.** It is stated as 91/91 correct-band cases at fixed 200 µA, not all possible bands or hardware conditions.
3. **`158` versus `111` cycles separated.** 158 is the fixed-200 µA worst case; 111 requires band-dependent current and was not adopted.
4. **Wrong-band failures retained.** The Phase 3 result of 91 wrong-band `UNSETTLED` cases is explicitly included.
5. **False-lock claim qualified.** No controller false/harmonic LOCK assertions occurred, but harmonic settles in unaided maps are acknowledged.
6. **Rail pockets retained.** Non-monotonic 25 MHz rail behavior is reported as a behavioral modeling caveat.
7. **Current-switching transients flagged.** Descending-current retry is not represented as an implemented solution.
8. **Interface omissions flagged.** The candidate list does not include `PHASE[0:7]`, `VC_LOW`, `VC_HIGH`, `CP_CUR`, or `MON_DIV[1:0]`.
9. **`PHASE_SEL[2:0]` direction flagged.** It is listed as an output because the draft instruction specified that direction, but a mux select would normally be an input.
10. **Thesis reference corrected.** Booth is the author; Baker is the advisor.
11. **No transistor-level claims.** Schematic, PVT, Monte Carlo, jitter, power, and area claims are absent or labeled unverified.

---

## ISSUES

### A1 — Source inconsistency in the robustness report

`results/pfd_validation/acquisition_robustness/report.md` line 395 describes the global 197-cycle worst case as **150 MHz, 150 µA**. However:

- `current_sweep.csv` row for 200 MHz / 150 µA lists `lock_max = 197`;
- `lock_time.csv` maximum row is **200 MHz / 150 µA / max initial condition / 197 cycles**;
- the report's own Section A.4 table lists 200 MHz / 150 µA as 197.

The proposal follows the CSV evidence. No source file was changed. This should be corrected in a future audit of that report, subject to user approval.

### A2 — Candidate interface is incomplete/ambiguous

The requested candidate interface omits the baseline's primary `PHASE[0:7]` outputs and several control/status pins. It also lists `PHASE_SEL[2:0]` as an output. The proposal preserves the requested list but marks these as open issues. User decision is required before interface finalization.

### A3 — No local official brief

`spec/` was empty. The proposal uses `AGENTS.md` for baseline values and the official website for challenge requirements. If a separate official project brief exists, Section 8 must be rechecked against it.

### A4 — Toolchain blocked

`results/environment_report.md` records no available ngspice, xschem, Sky130 PDK, or IIC-OSIC-TOOLS image. This is correctly reflected, but it means no Level C work can begin without authorization.

### A5 — Page length is implementation-dependent

The Markdown draft is structured for a roughly 5–8 page rendered document, but exact pagination depends on template, font, and figure placement. No PDF page-count validation was performed.

---

## 9. Placeholders and information not invented

The main proposal intentionally contains no:

- designer names or CVs;
- team or institutional affiliation;
- sponsor claims beyond the official challenge page;
- equipment inventory;
- repository URL;
- license selection;
- pad assignment;
- transistor sizes;
- area or power measurements;
- layout or test photographs;
- submission confirmation.

These items remain to be supplied or approved separately.

---

## 10. Remaining uncertainty and required decisions

Before a final submission draft, the user must decide:

1. whether to adopt the cycle-counting/coarse-actuator acquisition direction as a proposal architecture;
2. whether `200 µA` is carried forward as a design target;
3. whether to add `PHASE[0:7]` to the candidate interface or define the candidate as test-only;
4. whether `PHASE_SEL[2:0]` is an input or an output;
5. whether to restore `VC_LOW`, `VC_HIGH`, `MON_DIV`, and `CP_CUR` observability/control;
6. whether to authorize toolchain/PDK setup;
7. whether any target specification should be revised — none is revised in v0.1.

---

## RESULT — Quality audit

| Audit item | Result |
|---|---|
| All 15 requested sections present | PASS |
| Official main-proposal requirements covered | PASS |
| All key numeric claims recomputed from CSV | PASS |
| Target specifications match baseline | PASS |
| Evidence levels clearly stated | PASS |
| Candidate interface marked proposed | PASS |
| Figures classified and not fabricated | PASS |
| References validated where possible | PASS |
| Unsupported transistor/layout claims absent | PASS |
| Remaining uncertainty explicit | PASS |
| Submission-ready | **NO — Draft v0.1 for review only** |

---

## STATUS

**PASS for draft completeness and evidence traceability.**  
**NOT PASS for submission readiness.**  
**UNVERIFIED for hardware feasibility.**

---

## NEXT STEP

Review Draft v0.1 with particular attention to the candidate interface, the proposed acquisition architecture, and the `200 µA` design target. Apply user decisions in a v0.2 draft before considering submission. Do not start Problem 2 or modify official baseline files without explicit approval.
