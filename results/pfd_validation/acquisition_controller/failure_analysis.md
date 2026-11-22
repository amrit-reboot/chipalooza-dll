# Failure Analysis — Behavioral Acquisition Controller (LEVEL B)

All figures come from `acquisition_results.csv` (406 tests). No result is estimated.

---

## 1. Outcome taxonomy

| Outcome label | Meaning | Detection |
|---|---|---|
| `1T_LOCK` | Settled at `D/T ≈ 1`, `harmonic_index == 1`, settled ripple ≤ 0.05 | v4 `final_ratio` + `harmonic_index` + `settled_pp` |
| `MIN_DELAY_RAIL` | Settled at or near `Dmin/T` (minimum delay) | `final_ratio ≤ Dmin/T + 0.03` |
| `MAX_DELAY_RAIL` | Settled at or near `Dmax/T` | `final_ratio ≥ Dmax/T − 0.03` |
| `HARMONIC_LOCK` | Settled at `k·T`, `k ≥ 2` | `harmonic_index ≥ 2` |
| `UNSETTLED` | Coarse search exhausted before fine lock | FSM reached step/attempt/cycle limit |

Note: v4's own `rail_min`/`rail_max` booleans were **not** used — they test `u` near 0/1, which maps to maximum/minimum delay respectively (inverted naming). See report Issue 2.

---

## 2. Main matrix failures (273 tests, 145 failures)

| Failure reason | Count | Functional-band? |
|---|---:|---|
| `coarse step limit (n=0 persisted)` | 65 | No — mostly bands too slow for the frequency |
| `coarse step limit (n≥2 persisted)` | 26 | No — mostly bands too fast for the frequency |
| `fine attempts exhausted (MIN_DELAY_RAIL)` | 54 | Yes: 15 at 25 MHz, 2 at 30 MHz; remainder out-of-band |

### 2.1 Wrong-band failures (91 UNSETTLED)

The band's delay range cannot place `D/T` in `[1, 2)`. Examples:
- 25 MHz in band 1 or 2: even *minimum* delay is only 0.17T / 0.11T → `k = 0` at every actuator setting; 20 coarse steps exhausted.
- 100 MHz in band 0: minimum delay is 1.36T (count = 1 reachable) but the fine loop is unstable at that operating point; outcomes were `MIN_DELAY_RAIL` rather than UNSETTLED.
- 200 MHz in band 0/1: minimum delay 2.72T / 1.36T → no usable basin.

**This is a band-coverage problem, not a controller bug.** The controller correctly reports failure when the actuator range is insufficient.

### 2.2 25 MHz functional-band failure (13/13)

Every initial condition ends in `MIN_DELAY_RAIL` after 3 fine attempts. Trajectory signature:
- From minimum delay: `k = 0` for 9 consecutive measurements while `u` steps down; D/T rises 0.34 → 1.4 (band maximum); `k = 1` at the top, but fine lock rails every time.
- From any other start: `k = 1` immediately (D/T ≥ 1.0), fine lock rails, nudges increase delay, hits the 1.4T band maximum, rails again.

**Root cause (diagnostic, not part of the controller):** The fine loop's per-cycle control step scales with reference period:

Δu/cycle = Icp · T / (C · VDD)

At 25 MHz (T = 40 ns) this is 4× the 100 MHz value. Direct diagnostic:

| Icp | D/T = 1.05 | D/T = 1.20 | D/T = 1.40 |
|---:|---|---|---|
| 300 µA | 0.340 (fail) | 0.340 (fail) | 0.340 (fail) |
| 150 µA | 0.340 (fail) | 1.000 (pass) | 1.000 (pass) |
| 75 µA | 0.340 (fail) | 1.000 (pass) | 1.000 (pass) |
| 30 µA | 1.000 (pass) | 1.000 (pass) | 1.000 (pass) |

Reducing Icp restores 1T lock. The prototype deliberately kept the validated 300 µA setting; no Icp change was applied.

### 2.3 30 MHz lower-edge failures (2/13)

Initial conditions 1.00T and 1.02T give `k = 1` but fine lock rails. Nudging increases D/T to 1.10–1.26, yet all three fine attempts still rail. The 30 MHz basin lower edge lies between 1.02T and 1.03T: boundary tests show 1.00/1.01/1.02 fail while 1.03/1.04 pass. At D/T = 1.00–1.02 the controller's coarse classifier and the fine-loop basin disagree — a genuine edge-count ambiguity that only LOCK_VERIFY can resolve, and here it does not.

---

## 3. Randomized and deterministic-init failures

- Random: 5/35 failures, all at 25 MHz.
- Deterministic INITIALIZE: 2/14 failures, both at 25 MHz (`init_max`, `init_mid`). `init_max` (u = 0) reaches count = 1 immediately at 25 MHz but still rails — confirming the failure is in the fine loop, not in coarse placement.
- No random or deterministic-init case failed at 30–200 MHz.

---

## 4. Boundary-set failures (15/84)

All 15 are at 25 MHz (12 cases) and 30 MHz at D/T = 1.00–1.02 (3 cases). At 50–200 MHz every boundary case from 0.99T to 2.05T succeeded, including the exact D/T = 1.00 and 2.00 ties.

---

## 5. Controller stability / mode-chatter analysis

- Count-direction reversals occurred in **9/406** cases. Eight were wrong-band cases at 100/200 MHz with count sequences such as `5|4|3|2|2|2|1|2|1|1` — the nudge after a harmonic failure pushed delay across a band boundary, and the classifier corrected it. All ended in FAIL (wrong band), none oscillated indefinitely.
- One functional-band case (150 MHz, D/T = 1.99) showed `1|2|1` and then locked — a single bounded excursion demonstrating recovery.
- No case reached the 3000-cycle TIMEOUT. All failures were declared at `max_coarse_steps = 20` or `max_fine_attempts = 3`.
- LOCK was never asserted on a rail or harmonic outcome.

---

## 6. What these failures do and do not prove

**Do prove (Level B):**
- The controller detects insufficient actuator range and reports FAIL rather than false-locking.
- The retry/verify loop can recover from lower-basin-edge starts at most frequencies.
- Harmonic lock is avoided by count classification + LOCK_VERIFY in the tested range.

**Do not prove:**
- That 25 MHz can meet the spec with any CP current (only a diagnostic sweep was run).
- That PVT corners, mismatch, or real asynchronous edge behaviour preserve these boundaries.
- That metastability of the FB-detect/counter interface is safe.
- Any post-layout or transistor-level result.
