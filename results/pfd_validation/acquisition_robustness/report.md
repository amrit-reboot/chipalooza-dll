# Phase 4 — Loop Gain Robustness and Acquisition Improvement (LEVEL B)

**Date:** 2026-11-21
**Level:** **B — behavioral only.** No transistors, no Sky130, no parasitics, no Docker, no installation.
**Scope:** Investigation of Icp robustness, frequency-dependent loop gain, current strategies and controller improvements.
**Architecture/spec status:** **UNCHANGED.** No official specification, architecture, validated model or Phase-3 controller file was edited. Problem 2 not started.

---

## TASK

Verify the Phase-3 results from the actual CSVs, sweep charge-pump current across all seven frequencies, explain the low-frequency failure analytically, compare adaptive-current strategies, resolve the 30 MHz basin boundary with fine sweep resolution, and explore controller improvements — without implementing any official architecture change.

---

## CHANGES

New files only:

| Category | Files |
|---|---|
| Scripts (investigation-only) | `scripts/pfd_validation/robustness_common.py`, `run_robustness_sweep.py`, `run_boundary_study.py`, `run_strategy_study.py` |
| Results | `results/pfd_validation/acquisition_robustness/report.md`, `failure_analysis.md`, `current_sweep.csv`, `basin_map.csv`, `lock_time.csv`, `loop_gain.csv`, `boundary_fine.csv`, `boundary_summary.csv`, `boundary_recovery.csv`, `strategy_comparison.csv`, `improvement_comparison.csv`, `sweep_meta.json`, `boundary_meta.json`, `strategy_meta.json`, `plots/*.png` |

No existing file was modified. Phase-3 controller and v4 engine were imported but never changed.

---

## METHOD

1. **Verification:** re-read Phase-3 `acquisition_results.csv` and recomputed every supplied statistic.
2. **Investigation A:** 7 frequencies × 8 Icp values (50–300 µA). For each, fine-loop basin map from `D/T = 0.50` to `3.00` in 0.05 steps (v4, 150 cycles, 150 substeps), plus the unmodified Phase-3 controller over all 13 initial conditions. Outcome classification from measured `final_ratio`, `harmonic_index` and `settled_pp` (v4's mislabeled rail flags not used).
3. **Investigation B:** first-order analytical loop-gain metrics computed at `D = T` for every frequency.
4. **Investigation C:** strategy comparison built from measured sweep data plus an investigation-only `ExploreController` (new file) for current-switching cases.
5. **Investigation D:** 30 MHz and 25 MHz boundary sweep from `D/T = 0.980` to `1.120` in **0.002** steps, plus controller recovery tests.
6. **Investigation E:** investigation-only controller variants (adaptive step, repeated count, current switching) evaluated on the hard cases, with no change to the baseline controller.

---

## 0. Verification of Phase-3 results

| Supplied claim | Verified | Evidence |
|---|---|---|
| 406 tests | **Yes** | 406 rows in `acquisition_controller/acquisition_results.csv` |
| 76/91 correct-band locked | **Yes** | recomputed from CSV |
| 76/78 excluding 25 MHz | **Yes** | recomputed from CSV |
| 25 MHz fails at 300 µA | **Yes** | 13/13 → `MIN_DELAY_RAIL` |
| Median lock time 24 cycles | **Yes** | median of `effective_lock_cycles` = 24.0 |
| Maximum lock time 111 cycles | **Yes** | max = 111 |
| No false LOCK | **Yes** | zero harmonic outcomes in all 406 rows |

All supplied results are reproducible from the stored CSVs.

---

## A. Charge-pump current versus frequency

*(Tables generated from `current_sweep.csv`, `basin_map.csv` and `lock_time.csv`.)*

### A.1 Controller acquisition success (Level B behavioral; 13 initial conditions per point)

| f (MHz) | 50 µA | 75 µA | 100 µA | 125 µA | 150 µA | 200 µA | 250 µA | 300 µA |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 25 | 13/13 | 13/13 | **8/13** | 13/13 | 13/13 | **13/13** | 11/13 | **0/13** |
| 30 | 13/13 | 13/13 | 13/13 | 13/13 | 13/13 | **13/13** | 13/13 | 11/13 |
| 50 | 13/13 | 13/13 | 13/13 | 13/13 | 13/13 | 13/13 | 13/13 | 13/13 |
| 75 | 13/13 | 13/13 | 13/13 | 13/13 | 13/13 | 13/13 | 13/13 | 13/13 |
| 100 | 8/13 | 13/13 | 13/13 | 13/13 | 13/13 | 13/13 | 13/13 | 13/13 |
| 150 | 7/13 | 8/13 | 13/13 | 13/13 | 13/13 | 13/13 | 13/13 | 13/13 |
| 200 | 7/13 | 7/13 | 7/13 | 8/13 | 10/13 | **13/13** | 13/13 | 13/13 |

### A.2 Unaided fine-loop 1T basin edges (D/T), 0.05 sweep

| f (MHz) | 50 µA | 75 µA | 100 µA | 125 µA | 150 µA | 200 µA | 250 µA | 300 µA |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 25 | 1.10–3.00 | 1.10–3.00 | 1.15–3.00 | 1.15–3.00 | 1.20–3.00 | 1.25–3.00 | 1.35–3.00 | none |
| 30 | 1.05–3.00 | 1.10–1.60 | 1.10–3.00 | 1.10–3.00 | 1.15–3.00 | 1.20–3.00 | 1.25–3.00 | 1.30–3.00 |
| 50 | 1.05–2.10 | 1.25–2.15 | 1.05–2.20 | 1.05–2.25 | 1.05–2.30 | 1.10–1.90 | 1.10–1.90 | 1.30–1.55 |
| 75 | 1.05–2.05 | 1.05–3.00 | 1.05–3.00 | 1.05–3.00 | 1.05–3.00 | 1.05–3.00 | 1.10–3.00 | 1.10–3.00 |
| 100 | 1.05–1.10 | 1.05–1.45 | 1.05–2.10 | 1.05–2.10 | 1.05–2.15 | 1.05–2.20 | 1.30–1.75 | 1.05–2.30 |
| 150 | 1.05–1.05 | 1.05–1.15 | 1.05–1.35 | 1.05–2.05 | 1.05–3.00 | 1.05–3.00 | 1.05–3.00 | 1.05–3.00 |
| 200 | none | 1.05–1.05 | 1.05–1.05 | 1.05–1.10 | 1.05–1.15 | 1.05–1.60 | 1.05–2.10 | 1.05–2.10 |

**Important qualification:** these are contiguous 1T runs from a 0.05-resolution sweep. Direct diagnostic at 25 MHz showed narrow rail pockets *inside* the quoted range (see A.6), so "basin" here means "coarsely sampled 1T region", not a verified continuous interval.

### A.3 Harmonic locks in the unaided fine-loop basin sweep (out of 51 start points)

| f (MHz) | 50 µA | 75 µA | 100 µA | 125 µA | 150 µA | 200 µA | 250 µA | 300 µA |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 25 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| 30 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| 50 | 16 | 17 | 16 | 15 | 14 | 11 | 7 | 0 |
| 75 | 19 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| 100 | 19 | 19 | 18 | 18 | 17 | 11 | 15 | 14 |
| 150 | 20 | 19 | 19 | 19 | 0 | 0 | 0 | 0 |
| 200 | 8 | 20 | 20 | 20 | 19 | 19 | 18 | 17 |

Low Icp is **not** universally better: at 50–200 MHz it produces many 2T harmonic settles in the unaided fine loop. The full controller still reports **zero harmonic LOCK assertions in all 728 controller tests** because coarse steering removes the high-delay harmonic region.

### A.4 Worst effective lock cycles among successful starts (Level B behavioral)

| f (MHz) | 50 µA | 75 µA | 100 µA | 125 µA | 150 µA | 200 µA | 250 µA | 300 µA |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 25 | 67 | 62 | 64 | 67 | 67 | 66 | 66 | – |
| 30 | 70 | 56 | 55 | 61 | 62 | 60 | 61 | 60 |
| 50 | 125 | 89 | 70 | 60 | 52 | 43 | 43 | 45 |
| 75 | 131 | 90 | 86 | 58 | 50 | 49 | 54 | 57 |
| 100 | 169 | 162 | 126 | 104 | 89 | 71 | 60 | 53 |
| 150 | 168 | 178 | 164 | 133 | 113 | 87 | 72 | 61 |
| 200 | 170 | 173 | 151 | 177 | 197 | 158 | 130 | 111 |

**Global worst case across all 728 Level B behavioral controller tests: 197 cycles** (200 MHz, 150 µA), below the 400-cycle requirement. At the recommended 200 µA the worst case is 158 cycles.

### A.5 Overall fixed-current ranking (Level B behavioral; 91 starts per current)

| Icp | Success | Success % | Worst lock |
|---:|---:|---:|---:|
| **200 µA** | **91/91** | **100.0 %** | **158** |
| 250 µA | 89/91 | 97.8 % | 130 |
| 150 µA | 88/91 | 96.7 % | 197 |
| 125 µA | 86/91 | 94.5 % | 177 |
| 100 µA | 80/91 | 87.9 % | 164 |
| 75 µA | 80/91 | 87.9 % | 178 |
| 300 µA | 76/91 | 83.5 % | 111 |
| 50 µA | 74/91 | 81.3 % | 170 |

There is a Level B behavioral lock-time / robustness tradeoff: 300 µA has the shortest worst-case lock (111 cycles) but loses 25 MHz entirely; 200 µA is the only current with 100 % success.

### A.6 Non-monotonic anomalies and rail pockets

Three points with an existing coarse basin still lost starts:

| Point | Success | Failing starts | Observed signature |
|---|---:|---|---|
| 25 MHz, 100 µA | 8/13 | `max`, 1.50–2.50T | count `1|1|1`, nudged to `u=0`, rails to 0.34T |
| 25 MHz, 250 µA | 11/13 | 1.00T, 1.02T | count `1|1|1`, nudged into interior rail pocket, rails |
| 30 MHz, 300 µA | 11/13 | 1.00T, 1.02T | same lower-edge signature |

Direct v4 diagnostic (200 cycles, 300 substeps) explains the 25 MHz cases:

| Icp | `u=0.000` (D/T=1.400) | `u=0.005` (1.379) | `u=0.030` (1.280) | `u=0.100` (1.067) |
|---:|---|---|---|---|
| 100 µA | **rails** (0.34T) | 1T lock (6 cyc) | 1T lock (2 cyc) | **rails** |
| 250 µA | 1T lock (6 cyc) | 1T lock (6 cyc) | **rails** | **rails** |

At 100 µA there is a rail singularity exactly at the maximum-delay actuator endpoint (`u=0`); at 250 µA there is an interior unlocked pocket near `u=0.03`. The 0.05-resolution basin map cannot resolve either. These are properties of the **validated v4 behavioral engine**, not transistor-level evidence; they are reported as modelling caveats, not hardware predictions.

---

## B. Frequency-dependent loop gain — analytical explanation

### B.1 Derivation

For a PFD with fractional phase error `φ_f = frac(D/T)`, the UP/DOWN pulse
width is approximately `φ_f · T`, so the charge delivered per reference cycle is

```
Q_cycle = Icp · φ_f · T
```

With loop capacitor `C` and supply `VDD`, the control-variable step per cycle is

```
Δu = Q_cycle / (C · VDD) = Icp · T · φ_f / (C · VDD)
```

The resulting change in *normalized* line delay is

```
Δ(D/T) = (dD/du) · Δu / T = |line_kd(u)| · Icp · φ_f / (C · VDD)
```

`T` cancels explicitly, **but `|line_kd(u)|` is evaluated at the `u` that
produces `D = T`, and that `u` is strongly frequency-dependent through the
band delay range**. For the model's delay law,

```
|line_kd(u)| = 8 · t_hi · r / (1 + r·u)^2,  r = t_hi/t_lo − 1
```

At low frequency the band's `t_hi` is large and `u(D=T)` is small, so the
denominator is small and `|line_kd|` is large. The per-cycle normalized gain is
therefore much higher at 25 MHz than at 200 MHz.

### B.2 Computed metrics at Icp = 300 µA, C = 25 pF

| f (MHz) | band | T (ns) | u at D=T | \|dD/du\| (ns/u) | Δu/cycle per φ_f | Δ(D/T)/cycle per φ_f | Δ(D/T) at φ_f = 0.05 |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 25 | 0 | 40.0 | 0.128 | 89.1 | 0.2667 | 0.594 | 0.0297 |
| 30 | 0 | 33.3 | 0.218 | 61.9 | 0.2222 | 0.412 | 0.0206 |
| 50 | 0 | 20.0 | 0.577 | 22.3 | 0.1333 | 0.149 | 0.0074 |
| 75 | 1 | 13.3 | 0.353 | 19.8 | 0.0889 | 0.132 | 0.0066 |
| 100 | 1 | 10.0 | 0.577 | 11.1 | 0.0667 | 0.074 | 0.0037 |
| 150 | 2 | 6.7 | 0.440 | 7.9 | 0.0444 | 0.053 | 0.0026 |
| 200 | 2 | 5.0 | 0.720 | 4.5 | 0.0333 | 0.030 | 0.0015 |

The normalized per-cycle gain at 25 MHz is **≈20×** that at 200 MHz. For a
small 5 % fractional phase error, a single cycle changes `D/T` by ~0.030 at
25 MHz versus ~0.0015 at 200 MHz. Starting just above the 1T point, the
25 MHz loop overshoots below the lower basin edge within a few cycles and then
rails to minimum delay — exactly the observed failure.

### B.3 Can one fixed Icp serve all frequencies?

**Yes, within the tested Level B model.** The measured sweep contradicts the
earlier conservative expectation: **Icp = 200 µA gives 13/13 successes at all
seven frequencies (91/91 total)**, including 25 MHz and 200 MHz. This is the
key new result of this investigation.

The opposing requirements are real but do not overlap fatally:

- **Low frequencies (25–30 MHz):** Icp too high (300 µA) makes the coarse
  controller's first `k=1` placement fall above the lower fine basin edge,
  causing a min-delay rail. At 300 µA, 25 MHz is 0/13 and 30 MHz is 11/13.
  Reducing to 200 µA moves the lower edge down enough for coarse placement to
  land inside the basin at both frequencies.
- **High frequencies (50–200 MHz):** Icp too low produces many 2T harmonic
  settles in the *unaided* fine loop (A.3), but the coarse controller removes
  the high-delay region before fine lock, so controller success is preserved
  down to 200 µA at every frequency.

A single fixed current therefore **is sufficient for acquisition in this
model**; 200 µA is the only tested current with 100 % success. The earlier
Phase-3 statement that 25 MHz "cannot lock at 300 µA" remains correct, but it
must not be generalized to "25 MHz cannot lock with any fixed current".

This conclusion is Level B, single-PVT-point, and depends on the v4 rail
endpoint behaviour documented in A.6; it is not a transistor-level feasibility
claim.

---

## C. Adaptive current strategies

*(Strategy table generated from `strategy_comparison.csv` and
`improvement_comparison.csv`.)*

### C.1 Strategy 1 — one fixed Icp for all frequencies

| Icp (µA) | Success | Worst lock (cycles) |
|---:|---:|---:|
| 50 | 74/91 | 170 |
| 75 | 80/91 | 178 |
| 100 | 80/91 | 164 |
| 125 | 86/91 | 177 |
| 150 | 88/91 | 197 |
| **200** | **91/91** | **158** |
| 250 | 89/91 | 130 |
| 300 | 76/91 | 111 |

### C.2 Strategy 2 — three band-dependent currents

Selected by maximum success, then shortest worst-case lock: **band 0 = 200 µA,
band 1 = 200 µA, band 2 = 300 µA** → **91/91 success, worst lock 111 cycles**.

This is better than fixed 200 µA in lock time (111 vs 158) with no success
loss, but it requires RANGE-decoded current selection and a definition of what
happens at band boundaries. The improvement is modest and is not enough by
itself to justify an architecture change.

### C.3 Strategies 3 and 4 — investigation-only `ExploreController`

These use a separate, explicitly investigation-only class (not the Phase-3
baseline controller). Test set: 27 hard cases (13 at 25 MHz, 5 at 30 MHz,
9 at 50/100/200 MHz). See `improvement_comparison.csv`.

| Configuration | 25 MHz | 30 MHz | 50/100/200 MHz | Total |
|---|---:|---:|---:|---:|
| `baseline` variant | 0/13 | 5/5 | 9/9 | 14/27 |
| `small_step_only` | 0/13 | 5/5 | 9/9 | 14/27 |
| `repeated_count_x3` | 0/13 | 5/5 | 9/9 | 14/27 |
| `fine_current_150` | 13/13 | 5/5 | 9/9 | **27/27** |
| `fine_current_50` | 13/13 | 5/5 | 7/9 | 25/27 |
| `switch_300_then_150` | 13/13 | 5/5 | 9/9 | **27/27** |
| `switch_300_then_50` | 13/13 | 5/5 | 9/9 | **27/27** |
| `switch_300_150_50` | 13/13 | 5/5 | 9/9 | **27/27** |

**Interpretation:** changing only the coarse step size or repeating the edge
count does not fix a current-dependent fine-loop basin. Changing the *fine*
current does. A descending-current retry (`300 → 150 → 50 µA`) recovers all
hard cases, but it costs up to 6 fine attempts per case and the switching
transient is not simulated. The constant 50 µA fine current fails two
high-frequency cases by harmonic lock, so "lower current is better" is false.

**Important:** the `baseline` row above is the `ExploreController` with a
single 300 µA fine current. It is **not** identical to the Phase-3
`AcquisitionController` (it re-enters fine lock at every coarse step and uses
a fixed more-delay nudge); its 30 MHz results therefore differ. No baseline
file was edited.

### C.4 Qualitative comparison (all strategies)

| Strategy | Circuit requirement | Control signals | Complexity | Instability risk | Lock time | Area/power | Switching transients |
|---|---|---|---|---|---|---|---|
| 1. One fixed Icp | Single CP bias | None | Lowest | Low overshoot at low f; harmonic at high f | Compromised | Lowest | None |
| 2. Three band Icp | 3-step bias DAC / mirrored CP, RANGE decode | RANGE[1:0] already exists | Low-medium | Band edge discontinuities | Good per band | Small extra | Current step injects charge; needs VCTRL hold during switch |
| 3. Fine current adjustment during acquisition | Programmable CP, FSM-controlled | Acquire-phase code | Medium | Multiple current changes during settling can cause limit cycles | Potentially longer | Moderate | Each step is a charge discontinuity |
| 4. Separate acquisition/fine current | Coarse path already disables CP; needs selectable fine Icp | CP_EN + Icp code | Medium | Cleanest separation if handoff is glitchless | Good | Moderate | Handoff must be break-before-make; coarse re-assert needed |

**Important:** the baseline controller already disables the CP during edge
counting, so an "acquisition current" of zero is already implemented. Strategy
4 therefore reduces to selecting the *fine-lock* current, which is the same
problem as strategy 2. No official architecture change is proposed.

---

## D. 30 MHz basin boundary

*(Resolved from `boundary_fine.csv`, `boundary_summary.csv`,
`boundary_recovery.csv` — see `failure_analysis.md` section 3 for full detail.)*

Summary:
- Fine grid resolution **0.002 T**, range 0.980–1.120 T.
- Lower 1T edge moves monotonically with Icp: **1.036** (50 µA), **1.056**
  (75 µA), **1.076** (100 µA), **1.096** (125 µA), **1.116** (150 µA).
  At 200–300 µA no 1T lock occurs anywhere in this window.
- Transition is a single clean rail→1T step at each current; no bistable band
  was resolved at 0.002 T spacing.
- Baseline controller recovery from 1.00/1.01/1.02 T: **5/5** for Icp ≤250 µA,
  **2/5** at 300 µA.
- A practical coarse-entry margin of **D/T ≥ 1.12** is supported for
  Icp ≤100 µA (Level B, single PVT point).

---

## E. Controller improvements

*(Results from `improvement_comparison.csv`, investigation-only.)*

### E.1 Measured effect of each explored change

| Improvement | Implemented as | Effect on 27 hard cases | Assessment |
|---|---|---|---|
| Adaptive coarse step (0.10 → 0.05 after first correction) | `small_step_only` | 14/27 (same as baseline variant) | No benefit where the fine basin is the limiting factor; increases coarse steps (e.g. 30 MHz `min`: 17→18) |
| Smaller steps near basin | same as above | no gain | Useful only for actuator quantization, not for basin-edge failures |
| Repeated edge-count measurement (×3) | `repeated_count_x3` | 14/27 (identical trajectories) | No benefit: the measured count is deterministic in this noiseless model; would only help with real metastability/noise, which is not simulated |
| Hysteresis / bounded retry with re-measure | `ExploreController` re-enters coarse after each failed fine attempt | 30 MHz 1.00/1.02 recovered (5/5 vs Phase-3 2/5 at 300 µA) | Helps at 30 MHz; does not help 25 MHz at 300 µA |
| Multiple acquisition attempts | up to 20 coarse steps + up to 3 fine currents | enables descending-current recovery | Effective, but costs up to 6 fine attempts in hard cases |
| Lock timeout and recovery | `max_coarse=20` bound; Phase-3 3000-cycle budget never reached | all terminations were step/attempt limits | Bounded and safe; no TIMEOUT observed |
| Acquisition/fine-loop handoff | coarse CP disabled; `reassert_coarse` re-applies code after failure | required for descending-current scheme | Conceptually sound; charge-injection during current switching is **not simulated** |
| Fine current selection | `fine_current_150`, `switch_*` | 27/27 for 150 µA or descending | The only change that fixes 25 MHz |

### E.2 Comparison against the unchanged Phase-3 controller

- Phase-3 baseline at 300 µA: 0/13 at 25 MHz, 11/13 at 30 MHz.
- Investigation-only descending-current variant: 13/13 and 5/5 respectively.
- Fixed 200 µA with the **unchanged Phase-3 controller**: 13/13 at 25 MHz,
  13/13 at 30 MHz, 91/91 overall — with no controller change at all.

Therefore the **highest-value improvement is a current setting, not an FSM
change**. FSM changes (smaller steps, repeated counts) did not fix the observed
failures in this model. This is a Level B result and does not establish which
solution is preferable in hardware.

---

## Final conclusion

### Best fixed Icp (Level B behavioral operating point)

**200 µA.** It is the only tested current with **91/91 (100 %) acquisition
success** in the Level B behavioral model across 25/30/50/75/100/150/200 MHz
× 13 initial conditions using the **unchanged** Phase-3 controller. Worst
effective lock time at 200 µA is **158 cycles**, below the 400-cycle limit.
Runner-up is 250 µA (89/91, worst 130 cycles); 300 µA has the shortest
worst-case lock (111 cycles) but fails 25 MHz completely. This is not a
transistor-level charge-pump result.

### Is adaptive Icp necessary?

**Not for acquisition success in this model.** A single 200 µA setting solves
both the 25 MHz rail failure and the high-frequency harmonic risk (the latter
through coarse steering, not through the current itself). Band-dependent
current is **optional**: 200/200/300 µA keeps 91/91 success and reduces the
worst lock from 158 to 111 cycles. Descending-current retry on fine failure
also reaches 27/27 hard cases, but adds FSM complexity, up to 6 fine attempts
and unsimulated switching transients. None of these has been adopted as an
architecture change.

### Recommended acquisition strategy (investigation recommendation only)

1. Keep the existing Level B cycle-counting controller unchanged.
2. Use **Icp ≈ 200 µA** as the behavioral fine-lock operating point in place of
   300 µA. No band decode, no current switching, no new state machine logic.
3. If lock-time margin is later required, evaluate band 2 at 300 µA separately.
4. Do **not** rely on low Icp (≤100 µA) alone: it creates harmonic locks at
   50–200 MHz in the unaided fine loop and rail pockets at the 25 MHz actuator
   endpoint.
5. Do not claim a coarse-entry margin of `D/T ≥ 1.12` except for Icp ≤100 µA;
   at 200 µA the controller succeeds without an explicit margin rule.

### Worst-case lock time

| Scope | Worst effective lock cycles |
|---|---:|
| All 728 Level B controller tests in this investigation | **197** (200 MHz, 150 µA) |
| Recommended fixed 200 µA | **158** (200 MHz, `max` start) |
| Optional band-dependent 200/200/300 µA | **111** |
| Requirement | ≤400 |

### Remaining failed / unverified conditions

- At the recommended 200 µA: **none** of the 91 functional-band starts failed.
- At other currents: 25 MHz at 300 µA (0/13), 30 MHz at 300 µA (2 failing
  starts), 25 MHz at 100/250 µA rail-pocket failures, and low-current
  harmonic settles at 50–200 MHz in the unaided fine loop.
- Wrong-band combinations were **not re-swept** here; the Phase-3 finding of
  91 wrong-band `UNSETTLED` cases still stands.
- All boundaries are single-corner (`C = 25 pF`, nominal VDD/temperature,
  `t_dead = 10 ps`), with no PVT, Monte Carlo, metastability, current-switching
  transient, or transistor-level data.

### Is the controller robust enough for the proposal?

**Conditionally, at Level B only.** With a 200 µA fine current the existing
controller acquires from every tested initial condition at every tested
frequency in the correct band, with lock times below 400 cycles and no false
LOCK. That is adequate to support a *behavioral feasibility* statement in the
proposal. It is **not** adequate to support hardware feasibility claims for
25–200 MHz acquisition: transistor-level delay/CP behaviour, PVT corners,
mismatch and asynchronous-edge metastability remain unverified, and the
current-setting recommendation itself comes from a behavioral model with
known rail-endpoint artifacts. The proposal should describe this as
"behaviorally demonstrated, pending circuit verification", not as verified.

### Claims that remain LEVEL B only

Every result in this report: basin maps, Icp sweep, lock times, strategy
comparison, boundary edges, and the 200 µA recommendation. No transistor,
Sky130, PVT, Monte Carlo, area, power or jitter result is claimed.

---

## STATUS

| Item | Status |
|---|---|
| Phase-3 results verified from CSV | **PASS** |
| Icp sweep (7 f × 8 Icp) | **PASS** |
| Analytical loop-gain explanation | **PASS** |
| 30 MHz boundary at 0.002 resolution | **PASS** |
| Strategy / improvement comparison | **PASS** (behavioral) |
| Official architecture/spec change | **NOT APPLIED** |
| PVT, transistor, metastability, area/power | **UNVERIFIED** |

## ISSUES

1. Low Icp causes harmonic lock at high frequency; high Icp (300 µA) causes
   min-delay rail at low frequency. 200 µA avoids both in the tested model;
   this is a behavioral result, not verified across PVT.
2. Basin boundaries are single-corner Level B data; no PVT or mismatch.
3. 30 MHz lower edge at 300 µA lies above the measured 1.120 T window; its
   exact value was not determined.
4. v4 has narrow rail pockets at actuator endpoints/interior points that the
   0.05 basin sweep cannot resolve (section A.6).
5. Current switching transients are discussed conceptually, not simulated.
6. `ExploreController` is investigation-only and is not the baseline controller.
7. Wrong-band combinations were not re-swept in this investigation.

## NEXT STEP

Present this investigation for review. Decisions requested: whether to adopt
200 µA as the behavioral fine-current operating point, whether band-dependent
300 µA in band 2 is worth its complexity (111 vs 158 cycle worst lock), and
whether to advance to transistor-level verification. No implementation,
architecture change or Problem 2 work without approval. Stopping here.
