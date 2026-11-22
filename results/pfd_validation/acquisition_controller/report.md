# Phase 3 — Behavioral Startup Controller Prototype (LEVEL B)

**Date:** 2026-11-21
**Level:** **B — behavioral only.** No transistors, no Sky130, no parasitics, no Docker, no installation.
**Scope:** Investigation/prototype of the Option-A digital cycle-counting acquisition controller.
**Architecture/spec status:** **UNCHANGED.** No official file in `spec/`, `design/`, `sim/`, or `AGENTS.md` was edited. Problem 2 not started.
**Preservation:** All existing validated results retained unchanged.

---

## TASK

Implement and validate a behavioral prototype of the cycle-counting acquisition controller, using only observable edge-count information (no forced `D=1.3T`, no delay assignment from knowledge of `T`), test the required frequencies/bands/initial conditions, and report acquisition performance, failure modes and actuator requirements without fabricating results.

---

## CHANGES

New files only:

| File | Purpose |
|---|---|
| `scripts/pfd_validation/acquisition_controller.py` | Behavioral FSM controller (`AcquisitionController`) |
| `scripts/pfd_validation/run_acquisition_tests.py` | Testbench / sweep driver |
| `results/pfd_validation/acquisition_controller/report.md` | This report |
| `failure_analysis.md` | Failure classification and root causes |
| `coarse_actuator.md` | Proposed coarse actuator description and range/resolution analysis |
| `controller_state_diagram.png` | FSM state diagram |
| `acquisition_results.csv` | 406 test rows (all fields) |
| `lock_time.csv` | Timing subset |
| `delay_trajectory.csv` | Per-step count/u/D·T⁻¹ trajectories (long format) |
| `delay_trajectories.png` | Representative trajectory plots |
| `summary_success.png` | Success-rate and lock-time summary |
| `run_summary.json` | Machine-readable run metadata |

No validated result file was modified.

---

## METHOD

1. **Baseline re-verification.** Before implementation, the supplied baseline was re-checked against actual data:
   - `f2_convergence.csv` (1000 substeps): starts 0.90T–1.02T → minimum-delay rail; 1.05T–1.95T → 1T lock. ✔
   - Ignored-REF count diagnostic: `floor(D/T)` verified for 0.68T/0.90T/1.35T/1.68T/2.10T/2.50T. ✔
   - Band limits from `dll_model.py`. ✔
   - **Refinement found:** the actual lower basin edge at 100 MHz is **≈1.035T** (1.03T rails, 1.04T locks) — slightly above the previously quoted 1.02T.
2. **Controller implementation.** FSM drives the validated v4 exact-event engine. Count measurement runs with charge pump effectively disabled (`icp = 1 nA`), so `ignored_ref` = `floor(D/T)`. Fine lock uses the validated `icp = 300 µA`, `C = 25 pF`.
3. **Test matrix.** 7 frequencies × 3 bands × 13 initial conditions = 273 main tests; plus 35 randomized, 14 deterministic-init, and 84 boundary tests = **406 total**.
4. **Analysis.** Outcome classification from measured `final_ratio` (v4's `rail_min`/`rail_max` flags were found unreliable for this purpose — see Issues).

### Observable definition

With CP disabled, the controller counts reference edges that arrive while the first PFD UP pulse is still asserted:

| Count `k` | Condition | Interpretation | Action |
|---:|---|---|---|
| 0 | FB before next REF | `D < T` | increase delay (`u −= Δu`) |
| 1 | FB after exactly one REF | `T ≤ D < 2T` | try fine lock |
| ≥2 | FB after multiple REFs | `D ≥ 2T` | decrease delay (`u += Δu`) |

**No numerical `T`, no period measurement, and no forced delay preset is used by the controller.** The testbench converts the requested *initial condition* `D/T` into a starting `u` — that is a testbench action, not controller logic.

---

## RESULTS

### 1. Acquisition success percentages

| Test set | Tests | 1T locks | Success |
|---|---:|---:|---:|
| Main matrix (all bands) | 273 | 128 | **46.9 %** |
| Main matrix, functional band only | 91 | 76 | **83.5 %** |
| Functional band, excluding 25 MHz | 78 | 76 | **97.4 %** |
| Randomized initial conditions | 35 | 30 | **85.7 %** |
| Deterministic INITIALIZE | 14 | 12 | **85.7 %** |
| Edge-count boundary | 84 | 69 | **82.1 %** |
| **All tests** | **406** | **239** | **58.9 %** |

The low overall figure is dominated by deliberately mismatched band/frequency combinations, which cannot work by construction. **In the correct band, all frequencies except 25 MHz acquire successfully from every tested initial condition.**

### 2. Success by frequency × band (main matrix)

| f (MHz) | band 0 | band 1 | band 2 | functional band |
|---:|---:|---:|---:|---:|
| 25 | 0/13 | 0/13 | 0/13 | **0/13** |
| 30 | 11/13 | 0/13 | 0/13 | 11/13 |
| 50 | 13/13 | 13/13 | 0/13 | 13/13 |
| 75 | 13/13 | 13/13 | 0/13 | 13/13 |
| 100 | 0/13 | 13/13 | 13/13 | 13/13 |
| 150 | 0/13 | 13/13 | 13/13 | 13/13 |
| 200 | 0/13 | 0/13 | 13/13 | 13/13 |

### 3. Timing (successful functional-band cases, n = 76)

| Metric | Min | Median | Max |
|---|---:|---:|---:|
| Cycles to enter 1T basin (coarse) | 6 | 6 | 54 |
| Fine-lock cycles (v4 detection, relative to fine start) | 0 | 9 | 94 |
| **Effective detected lock time** (coarse + fine) | **7** | **24** | **111** |
| Total simulated cycles (fixed 200-cycle fine window included) | 206 | 212 | 666 |
| Coarse adjustments | 0 | 1 | 10 |
| Fine attempts | 1 | 1 | 3 |

All 76 effective lock times are **below 400 cycles**; 73/76 are also ≤100 cycles, with 3 cases at 103, 109 and 111 cycles (higher-frequency starts). This is a Level B result only; it excludes circuit overhead not modelled in v4.

### 4. Delay trajectories

`delay_trajectories.png` shows 18 representative cases. Typical behaviour:
- From minimum delay: `k = 0` repeats while `u` steps down, until `D/T` crosses ≈1.05 and `k = 1`; fine lock then succeeds.
- From maximum delay: `k = 2` (or 3+) steps `u` up until `k = 1`; fine lock succeeds.
- From `1.00T`/`1.02T`: `k = 1` initially, but fine lock fails; the controller nudges `u` down (more delay) and retries — recovery demonstrated at all frequencies except 25 MHz.

### 5. Harmonic-lock cases

Fine-lock outcomes are classified from `final_ratio` and `harmonic_index`:

| Outcome | Count (main, 273) |
|---|---:|
| `1T_LOCK` | 128 |
| `MIN_DELAY_RAIL` | 54 |
| `UNSETTLED` (coarse step-limit, wrong band) | 91 |

**No case ended in an undetected 2T harmonic lock.** Two mechanisms prevent it:
1. The coarse classifier steers whenever `k ≥ 2`, which removes the high-delay harmonic region.
2. `LOCK_VERIFY` requires `harmonic_index == 1` before asserting LOCK.

A separate diagnostic (temp script) showed that at 100 MHz, starts of 2.5T–2.8T **do** settle at 2T when the fine loop runs unaided; the controller avoids these by steering first. This confirms harmonic lock is a real risk that this controller addresses, but it has not been eliminated in silicon.

### 6. Failure cases

See `failure_analysis.md`. Summary:

| Root cause | Cases (main) |
|---|---:|
| 25 MHz fine-loop cannot 1T-lock at any reachable delay (Icp = 300 µA) | 13 (functional band) |
| 30 MHz at D/T = 1.00–1.02: basin lower-edge sensitivity | 2 (functional band) |
| Wrong band for frequency (band cannot reach 1T) | 91 (UNSETTLED) |
| Other out-of-band min-delay rails | 39 |

### 7. Edge-count ambiguity

Boundary tests (84 cases) give a clean classification:

| D/T | Observed count | Meaning |
|---|---|---|
| 0.99 | 0 | FB before next REF |
| 1.00 – 1.99 | 1 | FB after one REF |
| 2.00 – 2.05 | 2 | FB after multiple REFs |

**Boundary findings:**
- At exactly `D/T = 1.00`, v4 counts `k = 1` (REF edge is processed before the coincident FB event). This is a genuine tie that hardware must resolve deterministically.
- At exactly `D/T = 2.00`, v4 counts `k = 2`; the controller therefore steers down even though the fine loop could lock 1T from 2.0T–2.3T. This is conservative but safe.
- `1.00T`/`1.02T` give `k = 1` yet fail fine lock at 25/30 MHz — count alone cannot identify proximity to the lower basin edge. The LOCK_VERIFY retry loop covers this.
- At 150 MHz, one boundary case showed count sequence `1 → 2 → 1` before locking: a nudge temporarily crossed the 2T boundary and the classifier recovered. Good stability evidence.

### 8. Controller stability

- Only **9 of 406** cases showed any count-direction reversal. Eight were wrong-band cases; one was the recovered 150 MHz boundary case.
- Max coarse adjustments in a successful functional-band case: **10** (25 MHz is excluded — it never succeeded).
- Mode switching is bounded by `max_coarse_steps = 20`, `max_fine_attempts = 3`, and a 3000-cycle budget. TIMEOUT was not reached in any test; FAIL was reached on step/attempt limits.

### 9. Coarse actuator range and resolution

See `coarse_actuator.md`. Key numbers:

| f (MHz) | band | D/T range | u-window for count = 1 | Width |
|---:|---:|---|---:|---:|
| 25 | 0 | 0.34 – 1.40 | 0.000 – 0.128 | 0.128 |
| 30 | 0 | 0.41 – 1.68 | 0.000 – 0.218 | 0.218 |
| 50 | 0 | 0.68 – 2.80 | 0.128 – 0.577 | 0.449 |
| 75 | 1 | 0.51 – 2.10 | 0.016 – 0.353 | 0.337 |
| 100 | 1 | 0.68 – 2.80 | 0.128 – 0.577 | 0.449 |
| 150 | 2 | 0.60 – 2.10 | 0.020 – 0.440 | 0.420 |
| 200 | 2 | 0.80 – 2.80 | 0.160 – 0.720 | 0.560 |

The prototype's `Δu = 0.10` is smaller than every count-1 window, so no functional-band case skips the basin. A 4-bit coarse code (`Δu ≈ 0.067`) would provide additional margin; a 3-bit code (`Δu = 0.125`) would be marginal at 25 MHz.

### 10. Frequency-band transition issues

- Every wrong-band combination failed except 52/182 cases where a neighbouring band happened to cover the needed delay (e.g. 50/75 MHz in either band 0 or 1).
- **Automatic band selection is not implemented and not solved.** Changing `REF_CLK` frequency while locked leaves the current delay wrong; the FSM has no re-acquire trigger on frequency change.
- `RESET_N` and `DLL_EN` are represented in the model as the RESET state and CP-enable gating; their exact polarity/timing is not specified here.

### 11. RESET and timeout behaviour

- RESET disables fine-loop control and starts COARSE_ACQUIRE with the physical delay preserved (configurable deterministic `max`/`mid` init also tested — 12/14 success, both failures at 25 MHz).
- TIMEOUT (3000-cycle budget) was never triggered; the binding limits were `max_coarse_steps` and `max_fine_attempts`.
- On FAIL, `LOCK` is never asserted. No false LOCK assertion occurred.

### 12. Asynchronous edges / metastability (conceptual only)

- REF and FB are asynchronous at startup; the counter must be reset by the same event that starts the PFD UP pulse, otherwise `k` is meaningless.
- A real implementation needs synchronizers on the FB-detect and counter-output paths, and defined behaviour for coincident REF/FB edges (see D/T = 1.00 tie above).
- **Behavioral simulation cannot establish metastability safety or MTBF.** No claim is made.

---

## STATUS

| Item | Status |
|---|---|
| Controller behavioral model implemented | **PASS** |
| Testbench and required sweeps executed | **PASS** |
| Count-only acquisition (no T knowledge / no preset) | **PASS** |
| Acquisition 30–200 MHz in correct band | **PASS** (behavioral) |
| Acquisition at 25 MHz, Icp = 300 µA | **FAIL** (fine-loop limitation) |
| Lock time ≤400 cycles | **PASS** (Level B detected cycles) |
| Harmonic-lock avoidance | **PASS** (Level B classification) |
| Metastability / PVT / transistor feasibility | **UNVERIFIED** |
| Official architecture / spec change | **NOT APPLIED** |

---

## ISSUES

1. **25 MHz fails completely at Icp = 300 µA.** Diagnostic only: reducing Icp to 150 µA restores lock from 1.2T/1.4T; 30 µA also fixes 1.05T. This indicates excessive per-cycle loop gain at low frequency (charge per cycle ∝ T). No controller setting was changed; this needs review before any hardware commitment.
2. **v4 `rail_min`/`rail_max` flags are unreliable** for classifying the min/max *delay* rails — they test `u` near 0/1, which correspond to max/min delay respectively (naming inversion). All outcome classification in this work used `final_ratio` instead. v4 itself was not modified.
3. **Count alone cannot resolve the lower basin edge** (1.00–1.03T). The retry/verify loop is essential; it is not a single-pass acquisition.
4. **Band selection and frequency-change handling remain unsolved.**
5. All results are LEVEL B. No transistor, Monte Carlo, PVT, area, power or jitter claim is made.

---

## NEXT STEP

Present these results for review. Specifically requested decisions:
1. Whether to investigate band-dependent CP current for 25 MHz.
2. Whether to specify a coarse actuator (4-bit DAC / switched loads) as an architecture change — requires explicit approval.
3. Whether to extend this prototype to frequency-change re-acquisition and a quantified 1T lock detector.

No implementation, architecture edit, or Problem 2 work will proceed without approval. Stopping here.
