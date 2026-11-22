# Mathematical derivation — PFD-based DLL (LEVEL B)

**Status:** independent re-derivation of Problem 1. This document supersedes the
*interpretation* in `../report.md`, but does not delete it.

---

## 1. Definitions

| Symbol | Meaning |
|---|---|
| `T = 1/f` | reference period |
| `u ∈ [0,1]` | normalised control voltage; VCTRL rises with `u` |
| `D(u)` | **total** line delay (8 stages). Sky130 planning model: `dD/du < 0` |
| `r_n = nT` | reference rising edges |
| `b_n = nT + D_n` | feedback edges; `D_n` is the delay experienced by the edge launched at `r_n` |
| `Icp` | charge-pump current |
| `C` | loop capacitance |
| `{x}` | fractional part of `x` |

**Correct charge-pump polarity for this topology:** a net UP pulse raises
VCTRL, which *reduces* the current-starved delay. In the v1 code this is
`up_direction = +1`. The v1 experiments used `-1` — that is the root cause of
the 77/77 rail, not a topological impossibility.

---

## 2. Edge order with a pure delay

The feedback clock is the reference clock delayed by `D > 0`. Therefore an edge
launched at `r_n` emerges at `b_n = r_n + D`. Let `k = floor(D/T)`.

Two regimes:

1. **D < T** (`k=0`): `b_n` arrives before `r_(n+1)`. After the reset caused by
   `b_n`, the next event is `r_(n+1)`, which sets UP; the following `b_(n+1)`
   sets DOWN. Steady UP width = `b_(n+1) - r_(n+1) = D`.
2. **D > T** (`k ≥ 1`): `b_n` arrives *after* `r_(n+1)` but before `r_(n+2)`.
   `r_(n+1)` finds UP already asserted, so it does not retrigger. `b_n` sets
   DOWN and causes the reset. The next comparison starts at `r_(n+2)` and ends
   at `b_(n+1)`. Steady UP width = `b_(n+1) - r_(n+2) = D - kT`.

Both cases unify to:

> **Steady UP pulse width = `{D/T}·T`**
> **Steady DOWN pulse width ≈ 0**

Therefore, for a frozen delay:

\[
Q(D) = I_{CP}\,\mathrm{frac}(D/T)\,T \;\ge\; 0
\]

Measured in `review/tables/r4_charge_transfer.csv`: 60 points from D/T = 0.05 to
3.00, **maximum deviation from theory = 0.0000 Icp·T**. No DC bias, no charge
integration error. The sawtooth and its zeros at every `kT` are real.

### 2.1 Does the correction reverse across T?

**No.** Table below, from `test_pfd_v3.py`:

| Delay | Q / (Icp·T) |
|---:|---:|
| 0.98 T | 0.98 |
| 1.00 T | 0.00 |
| 1.02 T | 0.02 |
| 1.98 T | 0.98 |
| 2.00 T | 0.00 |
| 2.02 T | 0.02 |

The **magnitude wraps** from ≈1 to 0 at each integer multiple; the **sign does
not reverse** in the frozen transfer. My earlier claim that DOWN is never
asserted is true at steady state but **false during acquisition** (§4).

---

## 3. Loop dynamics and equilibria (frozen approximation)

With the correct polarity, `du/dt = Q/(CVDD)` and `dD/du < 0`. For a small
error `e = D - kT` just above a wrap point:

\[
\Delta u = \frac{I_{CP} T}{C V_{DD}}\frac{e}{T}
\qquad
\Delta D = \frac{dD}{du}\Delta u = -g\,e
\qquad
g = \frac{I_{CP}|dD/du|}{C V_{DD}}
\]

\[
e_{n+1} = (1-g)\,e_n
\]

At `Icp = 300 µA`, `C = 25 pF`, `VDD = 1.8 V`, `|dD/du| ≈ 11 ns` (band 1,
100 MHz): `g ≈ 0.074`, so convergence is exponential with ratio `≈0.93` —
matching the measured recurrence **0.93 at 1T** and **0.87 at 2T** in
`review/tables/r6_stability.csv`.

Consequences:

- `D = kT` is an **equilibrium** for every integer `k` for which `kT ≤ D_max`.
- With the frozen transfer it is attracting **from above** only
  (`0 < g < 2` gives `|1-g| < 1`).
- `k = 0` corresponds to zero delay; with a physical minimum it appears as the
  minimum-delay rail, not a useful lock.

**This already refutes the earlier claim that a DLL cannot lock with a PFD.**
Frequency integration is not required. The loop is first-order in phase, and the
wrap point provides a zero of the transfer characteristic.

---

## 4. Why the live basin is wider than the frozen prediction

During acquisition `u` changes by up to ~30% per cycle while several feedback
edges are still in flight. Those edges carry *different* delays: an older,
slower edge may emerge **before** the next reference edge and assert DOWN.

Measured in a live run starting at `D0 = 1.05 T` (`diag_q.py`, reproduced in
`test_dynamic_delay_changes_produce_down_pulses`):

| cycle | D/T | Q / (Icp·T) |
|---:|---:|---:|
| 0 | 1.050 | 0.000 (startup) |
| 1 | 0.974 | +0.024 |
| 2 | 0.972 | −0.028 ← DOWN from an in-flight edge |
| 3 | 0.974 | −0.026 |
| … | … | … |
| 18 | 0.991 | −0.010 |

So the loop crosses below 1T and is then pulled **back up** to 1T. The true
basin of `kT` therefore extends somewhat below `kT`, and its upper boundary is
shifted below `(k+1)T`. This is a Level B dynamical effect, visible only when
both clocks are simulated as continuous edge trains.

Basin map at 100 MHz (`review/tables/r2_basin_maps.csv`), 49 starting delays:

| start range | event model | dynamic 8-stage model |
|---|---|---|
| 0.60–0.99 T | all → k=0 (min-delay rail) | all → k=0 |
| 1.00–1.99 T | all → k=1 | 19/20 → k=1 |
| 2.00–3.00 T | all → k=2 | 14/21 → k=2, 7 → k=1 |

The two engines disagree only near basin boundaries; they agree throughout the
**robust window 1.05–1.8 T**. This is why the recommended preset is ≈1.2 T.

---

## 5. Band-plan consequences

The earlier claim "`D_min < T/2` makes acquisition impossible at 25/30 MHz" is
**withdrawn**. No `T/2` limit appears in the derivation or the data. The actual
condition is that the *startup delay* must fall inside the basin of `k=1`,
roughly `T ≲ D_start ≲ 1.9 T`.

Consequences from `review/tables/r5_cross_frequency.csv`:

| startup method | 1T locks |
|---|---|
| minimum-delay forcing (v1 proposal) | **0 / 11** |
| maximum-delay startup | 2 / 11 (rest lock at 2T/3T) |
| coarse preset 1.2 T | **11 / 11** |
| coarse preset 1.5 T | **11 / 11** |
| coarse preset 1.8 T | **11 / 11** |
| independent dynamic engine, preset 1.3 T, 300 µA | 10 / 11 (25 MHz fails) |
| independent dynamic engine, preset 1.3 T, 50–150 µA | 11 / 11 |

At 25 MHz, minimum delay is 0.34 T (basin 0 → no lock) but maximum delay is
1.40 T, which **does** lock at 1T in the event model. Therefore the earlier
statement that "no phase detector can acquire at 25/30 MHz" is false.

The remaining 25 MHz discrepancy is a **startup overshoot** in the dynamic
engine: the first UP pulse lasts the entire startup delay (≈1.3 T) rather than
the fractional error, and band 0 has the largest `g`, so the first correction
crosses below T into the k=0 basin. Reducing `Icp` from 300 µA to 50–150 µA
restores 1T at 25/30 MHz (`review/tables/r7_dynamic_preset_1p3.csv`). This is
reported as a proposal only; no value was changed.

---

## 6. DLL vs PLL PFD — rigorous distinction

- **PLL:** the feedback is generated by an oscillator whose *frequency* is the
  control variable. A persistent UP changes frequency, which integrates into
  phase, so the loop can remove an unbounded phase error. The PFD's frequency
  detection (one output held high) is essential there.
- **DLL:** the feedback is the *same edge train* delayed by `D`. Its frequency
  is already exactly `f`; there is no frequency error to integrate. The control
  variable is phase directly. The PFD transfer has a zero at every `kT` because
  `D` and `D+T` produce indistinguishable edge patterns at the detector.

Therefore:

> "A DLL cannot lock with a PFD because it lacks frequency integration" is
> **false**. A DLL with a two-latch PFD, correct charge-pump polarity and a
> startup delay inside the 1T basin has a stable 1T equilibrium.

What *is* true: a PFD-based DLL has **multiple equilibria** (`kT`) and a
**startup-dependent basin**. Harmonic locking is possible, not unavoidable.
It is avoided by forcing the initial delay into the 1T basin and by adding a
lock detector that verifies `D ≈ T` rather than merely "edges aligned".

---

## 7. What remains architecture-relevant (not changed)

The official architecture specifies **minimum-delay forcing** at startup. The
Level B evidence says that strategy lands in the `k=0` basin at all 11 tested
frequencies. A coarse preset to ≈1.3 T fixes it in the event model and in 10/11
dynamic runs; the 25 MHz dynamic failure is removed by reducing band-0 CP
current to ≤150 µA. Both are architecture/component changes and are **not
applied**. No specification or official architecture file was modified.
