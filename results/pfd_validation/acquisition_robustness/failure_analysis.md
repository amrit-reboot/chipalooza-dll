# Failure Analysis — Acquisition Robustness Investigation (LEVEL B)

All numbers in this file are read from `acquisition_results.csv` (Phase 3),
`boundary_fine.csv`, `boundary_summary.csv` and `boundary_recovery.csv`.
No result is estimated.

---

## 1. Verification of Phase-3 baseline claims

| Claim supplied for this phase | Verified from CSV? | Evidence |
|---|---|---|
| 406 tests executed | **Yes** | `acquisition_results.csv` = 406 rows |
| 76/91 correct-band cases locked | **Yes** | main ∧ band=functional: 76/91 |
| 76/78 excluding 25 MHz | **Yes** | 78 cases, 76 success |
| 25 MHz failed at Icp = 300 µA | **Yes** | 13/13 functional-band 25 MHz cases → `MIN_DELAY_RAIL` |
| Median lock time 24 cycles | **Yes** | median of `effective_lock_cycles` for 76 successes = 24.0 |
| Maximum lock time 111 cycles | **Yes** | max = 111 |
| No false LOCK assertions | **Yes** | 0 rows with any `HARMONIC_*` outcome across 406 tests |

---

## 2. Failure mechanism at low frequency (Investigation B)

Phase-3 diagnostic showed that reducing Icp restores 1T lock at 25 MHz. The
fine-resolution boundary study quantifies this:

### 25 MHz lower 1T basin edge (fine grid 0.980–1.120, step 0.002)

| Icp (µA) | Lower edge D/T | 1T points in grid |
|---:|---:|---:|
| 50 | 1.054 | 34 |
| 75 | 1.082 | 20 |
| 100 | 1.112 | 5 |
| 125 | — | 0 |
| 150 | — | 0 |
| 200 | — | 0 |
| 250 | — | 0 |
| 300 | — | 0 |

"—" means **no 1T lock anywhere in the 0.980–1.120 window**; it does not
assert that the entire basin is absent. The grid did not extend above 1.120.

At Icp = 300 µA the lower edge is above 1.120 T, so the coarse controller's
first `k = 1` placement (typically D/T ≈ 1.0–1.2) sits inside the rail region.
The fine loop then drives the delay to minimum every time — exactly the
Phase-3 failure signature.

---

## 3. 30 MHz lower-boundary failures (Investigation D)

### Lower 1T basin edge, same fine grid

| Icp (µA) | Lower edge D/T | 1T points | Min-rail points |
|---:|---:|---:|---:|
| 50 | 1.036 | 43 | 28 |
| 75 | 1.056 | 33 | 38 |
| 100 | 1.076 | 23 | 48 |
| 125 | 1.096 | 13 | 58 |
| 150 | 1.116 | 3 | 68 |
| 200 | — | 0 | 71 |
| 250 | — | 0 | 71 |
| 300 | — | 0 | 71 |

The lower edge moves **up** by ≈0.020 T for every +25 µA between 50 and
150 µA. Above 200 µA no 1T lock occurs below 1.120 T. This is a strong,
monotonic current dependence and is consistent with the first-order loop-gain
analysis: at 30 MHz, band 0 has a large delay sensitivity at D = T
(|dD/du| ≈ 61.9 ns/u), so a 300 µA pump moves D/T by ≈0.021 per cycle for a
5 % phase fraction — enough to overshoot the lower edge in a few cycles.

### Exact transition points (0.002 resolution)

Every Icp value produces a **single clean transition** from `MIN_DELAY_RAIL`
to `1T_LOCK`; there is no interleaving or bistable region at this resolution:

```
50 uA : rail up to 1.034, 1T from 1.036
75 uA : rail up to 1.054, 1T from 1.056
100 uA: rail up to 1.074, 1T from 1.076
125 uA: rail up to 1.094, 1T from 1.096
150 uA: rail up to 1.114, 1T from 1.116
200+  : rail throughout 0.980–1.120
```

### Can the baseline controller recover at 30 MHz?

`boundary_recovery.csv` tests starts 1.00, 1.01, 1.02, 1.03, 1.04 with the
unmodified Phase-3 controller:

| Icp (µA) | Recovery success |
|---:|---:|
| 50 – 250 | **5/5** |
| 300 | **2/5** |

At 300 µA, starts 1.00/1.01/1.02 fail (count sequence `1|1|1`, D/T nudged
1.00 → 1.23 but fine loop still rails), while 1.03/1.04 succeed. At all lower
currents the coarse re-nudge moves D/T far enough above the lower edge for
fine lock to succeed. **The 30 MHz problem is a current-dependent basin-edge
problem that coarse adjustment can normally repair; at 300 µA it cannot
always do so.**

### Safety margin for basin entry

If the fine current is 100 µA or less, a coarse entry target of
**D/T ≥ 1.12** gives at least 0.008 T margin at 30 MHz and 0.008 T at 25 MHz
(50 µA case). At 300 µA no such margin can be defined within the measured
window. These are Level B margins only; PVT and mismatch are not included.

---

## 4. Failure taxonomy for the robustness sweeps

| Failure mode | Trigger | Observed outcome |
|---|---|---|
| Minimum-delay rail | Start D/T below current-dependent lower edge | `final_ratio = Dmin/T`, no LOCK |
| Harmonic lock | High start D/T with very low Icp (see `basin_map.csv`) | `harmonic_index ≥ 2` |
| Coarse step limit | Band cannot place D/T in [1,2) | `UNSETTLED`, no LOCK |
| Fine attempts exhausted | Lower edge above reachable coarse placement | `MIN_DELAY_RAIL`, no LOCK |

No case asserted LOCK on a rail or harmonic outcome.

---

## 5. Non-monotonic current response and rail pockets (new finding)

Controller success is **not monotonic in Icp**. The full sweep found:

| Point | Success | Failing starts |
|---|---:|---|
| 25 MHz, 100 µA | 8/13 | `max`, 1.50, 1.95, 2.10, 2.50 |
| 25 MHz, 250 µA | 11/13 | 1.00, 1.02 |
| 30 MHz, 300 µA | 11/13 | 1.00, 1.02 |
| 100 MHz, 50 µA | 8/13 | harmonic-limited starts |
| 150 MHz, 50/75 µA | 7/13, 8/13 | harmonic-limited starts |
| 200 MHz, 75/100/125/150 µA | 7/13, 7/13, 8/13, 10/13 | harmonic-limited starts |

Direct v4 diagnostic at 25 MHz (200 cycles, 300 substeps) shows why the
25 MHz cases fail despite a coarsely measured basin:

| Icp | `u=0.000` (D/T=1.400) | `u=0.005` (1.379) | `u=0.030` (1.280) | `u=0.100` (1.067) |
|---:|---|---|---|---|
| 100 µA | **rails to 0.34T** | 1T lock (6 cycles) | 1T lock (2 cycles) | **rails** |
| 250 µA | 1T lock (6 cycles) | 1T lock (6 cycles) | **rails** | **rails** |

- At 100 µA the **maximum-delay actuator endpoint itself** (`u=0`) rails, so
  every high initial delay that clamps to `u=0` fails after three fine attempts.
- At 250 µA an **interior unlocked pocket** near `u=0.03` traps the controller
  after its lower-edge nudge from 1.00T/1.02T.
- The 0.05-resolution basin map reports 1.15–3.00T and 1.35–3.00T respectively;
  it cannot resolve either pocket. Basin maps must therefore be read as coarse
  samples, not proven continuous intervals.

These are properties of the validated v4 behavioral engine at its actuator
endpoints. They are reported as modelling caveats, not predictions of hardware
behaviour. The 200 µA recommendation avoids both pockets in all 13 tested
25 MHz starts.

---

## 6. Scope limits

- Basin boundaries are measured at a single PVT point, `C_loop = 25 pF`,
  `t_dead = 10 ps`, `t_reset = 5 ps`, 150 cycles, 150 substeps.
- The 0.002 grid resolves the 30 MHz boundary to ±0.002 T; it does not prove
  behaviour between grid points or under Monte Carlo mismatch.
- Metastability, asynchronous edge behaviour, transistor nonidealities and
  switching transients are **not** simulated.
