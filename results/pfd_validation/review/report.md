# Independent Review of the PFD Conclusion — Problem 1

**Date:** 2026-11-21
**Level:** **B — behavioral only.** No transistors, no Sky130, no parasitics, no transistor-level claim.
**Scope:** Problem 1 only. No architecture or specification file modified. No Problem 2 work.
**Earlier evidence:** fully preserved. `../report.md` carries a "SUPERSEDED INTERPRETATION" banner; nothing was deleted.

> ## ⚠️ FINAL VALIDATION UPDATE (2026-11-21)
>
> A subsequent exact-event engine (`pfd_model_v4_final.py`) with sub-step event
> resolution (50–5000 substeps) has **withdrawn** the claim in §5 and §4 that
> "the true basin extends somewhat below kT" due to in-flight DOWN pulses.
> The v2 evidence used launch-time latching and could not correctly propagate
> changing delay. The v4 result is unambiguous: **starting below 1T always
> rails**; only a trajectory that starts above 1T may dip below and recover.
> The 1T-basin statement "T ≲ D_start ≲ 1.9T" is refined to
> **1.02T ≲ D_start ≲ 1.95T**. See `../final_validation/report.md` for the
> authoritative final evidence. All data in this report is preserved unchanged.

---

## TASK

Independently verify or refute the earlier conclusion that *"a DLL cannot lock with a PFD because it lacks frequency integration"*, by auditing the event-driven implementation, re-deriving detector polarity and phase error around D = T and 2T, and running new acquisition experiments from multiple starting points.

---

## CHANGES

**New files only** (all previous code, tables, plots and reports left in place):

| File | Purpose |
|---|---|
| `scripts/pfd_validation/pfd_model_v2_review.py` | audit model with explicit per-period charge accounting and a second, wrapping phase detector |
| `scripts/pfd_validation/audit_v1.py` | audit of the v1 scheduler, charge integral and polarity |
| `scripts/pfd_validation/pfd_model_v3.py` | corrected model: proper CP polarity, coarse preset, independent 8-stage dynamic propagation engine |
| `scripts/pfd_validation/test_pfd_v3.py` | 12 new tests (existing `test_pfd.py` untouched) |
| `scripts/pfd_validation/run_pfd_review.py` | R1–R6 review experiments |
| `../derivation.md` | full mathematical derivation |
| `tables/r1–r6*.csv`, `tables/r7_dynamic_preset_1p3.csv`, `plots/r2–r4*.png`, `logs/review_run.log`, `logs/audit_v1.log` | new evidence |
| `tables/r7_dynamic_preset_1p2.csv` | retained exploratory 1.2 T run; superseded by the 1.3 T table |

**Modified:** `../report.md` (added superseded-interpretation banner) and `../../behavioral_dll.md` (corrected the §0.1 note). No official architecture/spec file touched.

---

## METHOD

1. **Code audit** of `pfd_event_model.py` line by line: edge scheduling, reset/retrigger, charge integration, control polarity.
2. **Charge accounting** added independently (`pfd_model_v2_review.py`), measuring `Q` per reference period with the delay frozen and the charge pump active.
3. **Mathematical derivation** of the frozen PFD transfer and the per-cycle error recurrence (see `../derivation.md`).
4. **Two independent simulators**: the original event scheduler (delay latched at launch) and a new discrete 8-stage engine where each edge advances through the line while VCTRL changes in flight.
5. **New basin maps** (49 starting delays), a cross-frequency acquisition sweep (11 frequencies × 6 startup methods), and 12 automated assertions.

---

## RESULT

### 1. Why v1 railed in 77/77 trials — **the model was right, my interpretation was not**

The v1 acquisition experiments hardcoded `up_direction = -1`, defined as
*UP current lowers VCTRL → delay increases*. For a frozen delay the PFD's net
charge is **always non-negative**:

\[
Q(D) = I_{CP}\,\mathrm{frac}(D/T)\,T \;\ge\; 0
\]

With UP *increasing* delay, `dD/dt > 0` everywhere, so the control must run to
the maximum-delay rail. **77/77 was guaranteed by the chosen polarity, not by
DLL topology.** Re-running the identical 77-point grid with the physically
correct polarity (`up_direction = +1`: UP raises VCTRL, current-starved delay
falls) gives **24/77 1T locks** — see `tables/r1_polarity_grid.csv`.

### 2. Scheduler audit — **correct on all six checks**

| Check | Evidence | Result |
|---|---|---|
| Repeated reference edges while PFD asserted | `audit_v1.log [A2]`, ref edges exactly T apart | PASS |
| Repeated feedback edges | fb edges exactly T apart | PASS |
| Edges crossing period boundaries | D = 1.35 T trace: `ref@0, ref@1T, fb@1.35T, ref@2T, fb@2.35T` | PASS |
| Near-simultaneous edges | reset delay 5 ps resolves coincident edges; Q(kT) ≈ 0 | PASS |
| Delays greater than one period | charge measured 0.05–3.00 T, exact match to theory | PASS |
| Delays changing dynamically | v1 latches D at **launch**; new 8-stage engine propagates with live `u` | PARTIAL — documented approximation; basins agree away from boundaries |

`test_delay_crossing_clock_boundary_is_modelled` verifies the second ref edge is
still emitted at 2T while the first fb edge is in flight.

### 3. Reset and retrigger — **correct**

The two-latch state machine sets UP on `ref`, DOWN on `fb`, and clears **both**
one reset delay after both have been high. Repeated ref edges while UP is high
do not re-arm it; this is what produces the wrap. For D > T two reference edges
occur before the first feedback edge — verified in the trace and the test.

### 4. Polarity around D = T and 2T — **direction does not reverse; magnitude wraps**

| D/T | Q / (Icp·T), frozen |
|---:|---:|
| 0.98 | 0.98 |
| **1.00** | **0.00** |
| 1.02 | 0.02 |
| 1.98 | 0.98 |
| **2.00** | **0.00** |
| 2.02 | 0.02 |

Transition `T⁻ → T⁺`: the charge drops from ≈Icp·T to 0. It never becomes
negative in steady state. With the correct polarity the small positive charge
just above `kT` reduces D, so `e_{n+1} = (1−g)e_n` with `g ≈ 0.07–0.13`; measured
recurrence ratios **0.93 at 1T**, **0.87 at 2T** (`tables/r6_stability.csv`).
`D = kT` is therefore a genuine stable equilibrium.

### 5. Charge pump — **no integration bug, no DC bias**

60-point transfer sweep (`tables/r4_charge_transfer.csv`, `plots/r4_charge_transfer.png`):
maximum deviation from `Icp·frac(D/T)·T` = **0.0000 Icp·T** after discarding the
startup transient. At D = 1T, 2T, 3T the net charge is zero. The one-sided pulse
is a property of the detector + pure delay, not an artefact of the integrator.

**However**, during acquisition, in-flight edges with different delays *do*
produce DOWN pulses. Example from D0 = 1.05 T: `Q/IcpT = +0.024, −0.028,
−0.026 …`; the loop dips below 1T and is pulled back. This is why the live basin
extends below `kT` even though the frozen transfer is one-sided.

### 6. "DLL cannot lock with a PFD" — **FALSE; withdrawn**

A DLL's feedback is the same edge train delayed, so its frequency already
equals `f`. There is no frequency error to integrate. The wrap points of the
PFD sawtooth supply the zeros; a first-order phase loop settles with
`e_{n+1} = (1−g)e_n`. Frequency integration is a PLL requirement for unbounded
phase acquisition, not a DLL requirement for lock. Counterexample: this model,
correct polarity, `D_start = 1.2 T` → **11/11 frequencies lock at 1T**.

### 7. "D_min < T/2 makes acquisition impossible" — **FALSE; withdrawn**

No `T/2` term exists in the derivation or the data. The real condition is that
the startup delay lie in the 1T basin, approximately `T ≲ D_start ≲ 1.9 T`.
At 25 MHz, `D_min = 0.34 T` fails, but `D_max = 1.40 T` **does** lock at 1T
(`tables/r5_cross_frequency.csv`). My earlier statement that "no phase detector
of any kind can acquire" at 25/30 MHz was wrong.

### 8. Minimal correct DLL and its equilibria

`D_{n+1} = D_n − g\,[D_n − kT]` for `k = floor(D_n/T)`, `0 < g < 2`.
Equilibria: `D* = kT`, `k = 0,1,2,…` while `kT ≤ D_max`. Measured at 100 MHz:
starts in `(1.0, 1.9) T → 1T`; starts in `[2.0, 3.0) T → 2T`; starts `< 1 T →
minimum-delay rail`. Harmonic locking is **possible but not unavoidable**.

### 9. Basin maps (`plots/r2_basin_maps.png`, `tables/r2_basin_maps.csv`)

| start D/T | event model final | dynamic 8-stage final |
|---|---|---|
| 0.60–0.99 | k=0 (rail) 8/8 | k=0 8/8 |
| 1.00–1.99 | k=1 20/20 | k=1 19/20 |
| 2.00–3.00 | k=2 21/21 | k=2 14/21, k=1 7/21 |

The engines differ only near basin boundaries; both agree in the robust window
**1.05–1.8 T** at 100 MHz. Across all 11 required frequencies with a 1.3 T
preset and 300 µA, the dynamic engine locks 1T in **10/11** cases — the single
failure is **25 MHz** (`tables/r7_dynamic_preset_1p3.csv`).

Investigation of that failure: at 25 MHz the first UP pulse of the dynamic model
is the full startup delay (1.3 T) and the band-0 loop gain is large enough to
overshoot below T into the k=0 basin. Reducing `Icp` to 50, 100 or 150 µA
restores a 1T lock at both 25 and 30 MHz (same table). **This is a proposal;
nothing was applied.**

### 10. Cross-frequency acquisition (`tables/r5_cross_frequency.csv`)

| Startup method | 1T locks / 11 |
|---|---:|
| minimum-delay forcing (**current architecture**) | **0** |
| maximum-delay | 2 |
| coarse preset 1.2 T | **11** |
| coarse preset 1.5 T | **11** |
| coarse preset 1.8 T | **11** |
| dynamic engine, preset 1.3 T, 300 µA | 10 (25 MHz fails) |
| dynamic engine, preset 1.3 T, 50–150 µA | 11 |

### 11. New tests

`python scripts/pfd_validation/test_pfd_v3.py` → **12/12 PASS**.
Existing `test_pfd.py` → **9/9 PASS** (unchanged).

---

## Revised conclusion

1. **The original "55/55 true lock" result remains withdrawn** — the old detector was an oracle.
2. **The v1 event model is physically sound**; the 77/77 rail was caused by an incorrect charge-pump polarity chosen in the experiment, and by my failure to test the opposite polarity before generalising.
3. **1T acquisition is possible and demonstrated at Level B**: 11/11 frequencies from a 1.2–1.8 T preset in the event model; 10/11 in the independent dynamic model at 300 µA, and 11/11 when band 0 uses 50–150 µA. Twelve new tests support the detector and loop behaviour.
4. **1T lock is not guaranteed by the current architecture.** Harmonic locks at 2T/3T occur when startup lands in those basins. The specified minimum-delay forcing lands in the k=0 basin at all 11 frequencies.
5. **Frequency integration is not required for DLL lock.** That earlier statement is withdrawn.
6. **The `T/2` capture claim is withdrawn.**
7. Remaining honest limitations: Level B only; CP polarity must be confirmed in a transistor-level PFD/CP before claiming silicon feasibility; basin boundaries depend on the dynamic model, so the 1.05–1.8 T preset window is a behavioural result, not a PVT-proven margin.

---

## STATUS

- v1 *code audit*: **PASS** (scheduler, reset, charge integral correct)
- v1 *interpretation*: **FAIL** — wrong polarity assumption, over-generalised conclusion (withdrawn)
- Corrected PFD polarity: **PASS** (24/77 1T on the original grid)
- Coarse-preset acquisition (event model): **PASS** (11/11 at 1.2–1.8 T; 12/12 new tests)
- Coarse-preset acquisition (dynamic model, 300 µA): **WITHIN 20%** (10/11; 25 MHz fails)
- Official minimum-delay startup: **FAIL** (0/11 1T; lands in k=0 basin)
- 1T acquisition possible: **PASS (Level B)**
- 1T lock guaranteed by current architecture: **FAIL**
- Harmonic lock unavoidable: **FAIL** (observed, not universal)
- Transistor-level validity: **UNVERIFIED** (out of scope)

---

## ISSUES

1. The **minimum-delay forcing** in the official architecture is incompatible with the 1T basin in this Level B model. Any correction is an architecture change and needs your approval; **none was applied**.
2. Basin boundaries shift between the quasi-static and dynamic engines. At 25 MHz the dynamic engine fails at the nominal 300 µA for every tested preset; 50–150 µA restores lock. This is a band-0 gain issue, not a detector failure. The preset window is chosen from model overlap, not worst-case PVT.
3. The current `Icp = 300 µA` working point was never formally approved (open question from an earlier phase). Any change remains subject to your approval.
4. `VCTRL → delay` polarity is assumed from current-starved inverter physics. It must be verified in Phase 3 transistor simulation.
5. No dead-zone mismatch, charge injection, leakage or supply noise is included. Jitter/PVT conclusions are untouched by this review.
6. Earlier unfavourable results were preserved and relabelled rather than deleted, per the project rules.

---

## NEXT STEP

Your decision before any other work:
- **(a)** approve a proposal to replace minimum-delay forcing with a coarse ~1.3 T delay preset, with band-0 `Icp` reduced to ≤150 µA (architecture/component changes — none applied); and/or
- **(b)** approve adding a harmonic-checking lock detector that verifies `D ≈ T`, not merely edge alignment; and/or
- **(c)** keep the architecture unchanged and record the 0/11 acquisition result as a known risk in the proposal.
