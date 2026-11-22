# Behavioral (Level B) 8-Phase DLL Prototype — Results

**Project:** Chipalooza Challenge #4 — 8-Phase DLL feasibility study
**Date:** 2026-11-21
**Model:** `scripts/dll_model.py` (Level B behavioral, discrete-time, cycle-by-cycle)
**Runner:** `scripts/run_behavioral.py`
**Reproduce:** `python scripts/run_behavioral.py`

---

## 0. Evidence level — read this first

**Everything in this document is LEVEL B (behavioral).**

There are no transistors in this model, no Sky130 device models, no parasitic
extraction and no Monte Carlo on real device parameters. The delay cell is an
algebraic curve; the loop is an idealised charge pump plus capacitor.

Therefore:

- No statement here is transistor-level evidence.
- The delay-cell ranges used below are **planning assumptions**, not measured
  silicon. They must be replaced by measured `Kd` and delay limits from Phase 2
  before any of these numbers can be treated as a design guarantee.
- Levels A (analytical), B (behavioral) and C (transistor) are labelled on every
  result. `UNVERIFIED` means exactly that.

---

## 1. Model summary

Eight identical current-starved stages. Normalised control `u = VCTRL/VDD`.

Hyperbolic delay characteristic (delay is inversely related to starved current):

```
t_stage(u) = t_hi / (1 + r*u),        r = t_hi/t_lo - 1
```

Band planning ranges (`t_lo` at u=1, `t_hi` at u=0):

| Band | Frequency | min line delay (u=1) | max line delay (u=0) | t_lo | t_hi |
|---|---|---|---|---|---|
| 0 | 25–60 MHz | 13.6 ns | 56.0 ns | 1.70 ns | 7.00 ns |
| 1 | 50–120 MHz | 6.8 ns | 28.0 ns | 0.85 ns | 3.50 ns |
| 2 | 100–200 MHz | 4.0 ns | 14.0 ns | 0.50 ns | 1.75 ns |

Loop update per reference cycle:

```
du = (Icp / (C_loop * VDD)) * pulse_width
pulse_width = min(|phase_error|, T/2)     sign preserved   (PFD, saturating)
```

Baseline run parameters: `Icp = 300 µA`, `C_loop = 25 pF`, `VDD = 1.8 V`,
dead zone 2 ps, startup initialised at minimum delay (`u0 = 1.0`).

---

## 2. Locking and lock time

![lock transient](../results/plots/lock_transient_100MHz.png)

Lock transient at 100 MHz, band 1: single monotonic settle, no overshoot,
`VCTRL/VDD` settles at 0.578, lock declared at cycle 52.

Band midpoints (`results/tables/lock_band_midpoints.csv`):

| f (MHz) | band | lock cycles | static error (ps) | static error (% T) | u final | delay/T | result |
|---:|---:|---:|---:|---:|---:|---:|---|
| 42.5 | 0 | 25 | −1.68 | −0.007 | 0.4427 | 0.9999 | PASS |
| 85.0 | 1 | 46 | −1.91 | −0.016 | 0.4428 | 0.9998 | PASS |
| 150.0 | 2 | 82 | −1.96 | −0.029 | 0.4402 | 0.9997 | PASS |

**Static error is dead-zone-limited at about 2 ps, i.e. ≈0.02% of T.**
This is a property of the model's dead zone, not of silicon. A real charge pump
adds UP/DOWN mismatch, leakage and charge injection, all of which this model
omits. The 2% T typical / 5% T maximum specification therefore **cannot** be
judged from this result — status: **UNVERIFIED at transistor level**, with a
behavioral floor of ≈0.03% T.

---

## 3. Frequency range and range switching

![frequency sweep](../results/plots/frequency_sweep.png)

Full sweep, 25–200 MHz in 5 MHz steps, band selected by the specified band edges
(`results/tables/frequency_sweep.csv`):

| Metric | Result |
|---|---|
| Frequencies true-locked at 1×T | **36 / 36** |
| Lock time | **15 … 97 cycles** |
| Static error | **0.003 – 0.039 % T** |
| Harmonic index | 1 everywhere |

Spec check: lock time typical 100 cycles / max 400 cycles → the worst measured
value (97 cycles) is inside the *typical* target with no margin at `Icp = 300 µA`.
Lowering `Icp` trades lock time for gain margin (§7).

Range switching works by construction in this model: the six switchable load
capacitors change `t_lo`/`t_hi`, and the loop re-acquires without any special
handling. **This is the strongest result of the prototype and the weakest in
terms of evidence** — it shows the *control concept* is sound, not that a
transistor delay line will cover the range.

---

## 4. Eight phases and tap spacing

![phase waveforms](../results/plots/phase_waveforms_100MHz.png)

Eight taps at 45° spacing (T = 10 ns, step = 1250 ps), 50% duty each, exactly as
intended. With perfectly matched stages the DNL is identically zero, which is
arithmetic, not evidence — so a mismatch Monte Carlo was run.

![tap DNL](../results/plots/tap_dnl.png)

`results/tables/tap_spacing_100MHz.csv` and the Monte Carlo (30 samples, 1%
per-stage delay sigma — a **behavioral assumption**, not Sky130 mismatch data):

| Quantity | Result | Spec | Status |
|---|---|---|---|
| Matched-stage DNL | 0.00% of T/8 | ±8% typical, ±15% max | trivial/ideal |
| MC mean worst-tap DNL | 1.43% of T/8 | ±8% | PASS (behavioral) |
| MC 99.7th percentile DNL | 2.63% of T/8 | ±15% | PASS (behavioral) |
| MC duty-cycle sigma (from taps) | 0.13% | — | — |

**Caveat (Role 6):** 30 samples is not a 3-sigma yield claim, and the 1% per-stage
sigma is invented for illustration. The real tap-spacing number depends entirely
on Sky130 device mismatch plus layout, i.e. Phase 9 + post-layout. Status for the
specification itself: **UNVERIFIED**.

---

## 5. Duty-cycle correction

![duty correction](../results/plots/duty_correction.png)

CLK50 is a set/reset latch: set on PHASE0 rise, reset on PHASE4 rise. Because
every tap is a delayed *rising* edge, the PHASE0→PHASE4 span is four stage delays
regardless of the input duty cycle. Input duty distortion is therefore removed
by construction.

`results/tables/duty_correction.csv` (50-sample mismatch MC per point):

| Input duty | Uncorrected | CLK50 corrected (mean) | sigma | Spec 45–55% |
|---:|---:|---:|---:|---|
| 30% | 30.00% | 49.99% | 0.17% | PASS |
| 50% | 50.00% | 49.99% | 0.16% | PASS |
| 70% | 70.00% | 49.96% | 0.18% | PASS |

This is a genuine architectural result, conditional on assumption A2: each delay
stage contains an even number of inversions so that a rising input edge produces
a rising edge at every tap. If a stage were inverting, CLK50 would invert
wholesale. **That assumption must be confirmed on the schematic in Phase 2.**

---

## 6. Startup and false lock

![startup sweep](../results/plots/startup_false_lock.png)

Startup sweep over initial control `u0 = 0.0 … 1.0` in 0.1 steps, five
frequencies, correct band, 2000 cycles each (`results/tables/startup_sweep.csv`):

| Outcome | Count |
|---|---|
| True lock at 1×T | **55 / 55** |
| Harmonic lock | 0 |
| No lock | 0 |

Every initial control value converged to the correct first harmonic, including
starting from maximum delay where the initial delay exceeds T (e.g. 25 MHz at
u0=0 gives 56 ns ≈ 1.4 T and still settles at 40 ns).

### Why this is not yet a "zero false locks" proof

The absence of harmonic lock is a **property of the saturating PFD model**, not a
demonstrated circuit result. The detector comparison below shows how sensitive
this is to the detector type (`results/tables/detector_comparison.csv`):

| f (MHz) | band | PFD | wrapping XOR detector |
|---:|---:|---|---|
| 25 | 0 | LOCK (1.000 T) | **NO LOCK (stuck at 0.340 T)** |
| 40 | 0 | LOCK | LOCK |
| 60 | 0 | LOCK | LOCK |
| 100 | 1 | LOCK | LOCK |
| 150 | 2 | LOCK | LOCK |
| 200 | 2 | LOCK | LOCK |

**Finding:** at 25 MHz the minimum line delay (13.6 ns) is only 0.34 T. A wrapping
(mixer/XOR-style) phase detector then reads the initial error with the wrong sign
and drives the loop further from lock. A PFD, which has frequency-detection
behaviour, recovers. This makes the PFD choice an architectural requirement rather
than a preference, and it sets a hard acquisition constraint:

```
minimum line delay must exceed T/2 at the lowest locked frequency,
otherwise a wrapping detector cannot acquire.
```

Under the PFD that constraint is relaxed, but the margin at 25 MHz (0.34 T) is
thin. A real PFD has its own blind zone, reset delay and charge-pump mismatch,
none of which are modelled. Status: **UNVERIFIED — needs transistor-level startup
testing (Phase 6) before "zero false locks" can be claimed.**

---

## 7. Loop gain and stability

Per-cycle gain `G = Icp·|dT_line/du| / (C·VDD)`, evaluated **at the actual locked
operating points** across the sweep (`results/tables/gain_vs_icp.csv`):

| Icp (µA) | worst G at lock points | max lock cycles | not locked | gain margin | lock ≤400 spec |
|---:|---:|---:|---:|---|---|
| 50 | 0.099 | 556 | 0 | OK | **FAIL** |
| 75 | 0.148 | 372 | 0 | OK | PASS |
| 100 | 0.198 | 280 | 0 | OK | PASS |
| 150 | 0.297 | 188 | 0 | OK | PASS |
| 200 | 0.396 | 142 | 0 | OK | PASS |
| 300 | 0.594 | 96 | 0 | MARGINAL | PASS |

Trade-off is exactly as expected: gain margin versus lock time.
`Icp = 50 µA` is too slow (556 cycles > 400). `Icp = 300 µA` locks fastest but its
worst-case gain of 0.59 leaves little room for the ±30–40% `Kd` variation that
silicon is expected to show.

At the rail side, `u → 0` (control at the positive rail, starving devices off),
the open-loop gain reaches 1.16 at 300 µA — above unity. That point is a clamp
extreme, not a settled lock point, so it does not by itself make the loop
unstable, but it does mean the loop must not be allowed to dwell there.

**Recommendation (needs your approval, not applied):** `Icp ≈ 150 µA` with
`C_loop = 25 pF` gives worst-case gain 0.30, 188-cycle maximum lock time, and
tolerates roughly a 3× increase in `Kd` before reaching unity gain. That is the
best robustness/lock-time balance in this table.

---

## 8. Jitter — ESTIMATE only

![jitter estimate](../results/plots/jitter_estimate.png)

No noise simulation exists without ngspice. This is a **Level A/B estimate**:
supply noise at 100 MHz is far above the DLL loop bandwidth, so the loop cannot
suppress it, and the total line delay modulates directly with the supply.

```
dT/T = S · ΔVDD/VDD            S = assumed relative supply sensitivity
period jitter = sqrt(2) · S · (ΔVDD/VDD) · T
```

With 20 mVrms supply noise at 100 MHz (`results/tables/jitter_sensitivity.csv`):

| Assumed S | dT rms | period jitter rms | 60 ps max |
|---:|---:|---:|---|
| 0.25 | 27.8 ps | 39.3 ps | PASS |
| 0.50 | 55.6 ps | 78.6 ps | FAIL |
| 1.00 | 111.1 ps | 157.1 ps | FAIL |
| 1.20 | 133.3 ps | 188.6 ps | FAIL |
| 2.00 | 222.2 ps | 314.3 ps | FAIL |

Break-even sensitivities for the 20 mVrms condition:

- **S ≤ 0.159 for the 25 ps typical target**
- **S ≤ 0.382 for the 60 ps maximum target**

**Interpretation:** the 25 ps / 60 ps jitter specification is dominated by supply
sensitivity, not by the DLL architecture. Unless `S` is driven below about 0.16
(local regulator, dedicated decoupling, or a supply-referenced delay cell) the
typical jitter target is out of reach at 20 mVrms noise. `S` itself is completely
unknown for this cell and must be measured in Phase 2/8. Status: **ESTIMATE.**

---

## 9. Power — ESTIMATE only

Not modelled. A first-order Level A estimate at 100 MHz:

- Dynamic delay-line current per stage ≈ `C_load · VDD · f`. With 30 fF and
  100 MHz: 5.4 µA, so 8 stages ≈ **43 µA**.
- Charge pump: at lock the average current is `Icp · (pulse width)/T → 0`, so it
  contributes peak current but little average. Add roughly the PFD/logic bias.
- Buffers and duty corrector: unmodelled.

Order of magnitude: **≈0.1–0.5 mA at 100 MHz** against a 1 mA typical target.
This is plausible but is an estimate resting on an assumed 30 fF load. The 2 mA
at 200 MHz limit is **UNVERIFIED**.

---

## 10. Specification status after the behavioral prototype

| Specification | Target | Behavioral result | Method | Status |
|---|---|---|---|---|
| Lock time | ≤400 cyc (typ 100) | 15–97 cyc | Level B transient | PASS (behavioral) |
| Static phase error | ±2% T typ / ±5% max | ≤0.039% T | Level B transient | PASS (behavioral); **UNVERIFIED** in silicon |
| Tap spacing DNL | ±8% / ±15% of T/8 | 2.63% at p99.7 (1% assumed sigma) | Level B MC | ESTIMATE |
| CLK50 duty | 45–55% | 49.96–49.99% | Level B, 50-sample MC | PASS (behavioral) |
| Frequency range | 25–200 MHz | 36/36 locked | Level B sweep | PASS (behavioral) |
| False locks | 0 | 0/55 with PFD; 1 failure with XOR | Level B startup sweep | ESTIMATE |
| Loop stability | G < 1 | 0.59 worst at 300 µA | Level A calculation | PASS (analytical) |
| Jitter | 25 ps typ / 60 ps max | 188 ps at assumed S=1.2 | Level A estimate | **ESTIMATE — likely FAIL** |
| Supply current | 1 mA @100 MHz, 2 mA @200 MHz | ~0.1–0.5 mA | Level A estimate | ESTIMATE |
| Area | ≤0.05 mm² | not modelled | — | UNVERIFIED |
| Delay-cell range | T/8 per band, ±30–40% | planning values only | assumption | **UNVERIFIED** |

---

## 11. What this prototype does and does not prove

**It does demonstrate, reproducibly:**

1. The control loop concept locks across the whole 25–200 MHz range in 15–97 cycles.
2. Eight evenly spaced phases are produced and the tap-spacing error budget is dominated by stage mismatch.
3. Duty-cycle correction from a 30% or 70% input to 50% works and is insensitive to input duty by construction.
4. The charge-pump current / loop-capacitor trade-off, quantified, with a defensible operating point.
5. That the PFD choice is load-bearing: a wrapping detector fails to acquire at 25 MHz.
6. That the jitter specification, not the loop, is the binding risk.

**It does not prove:**

1. That a Sky130 current-starved inverter can reach 5 ns and 625 ps stage delays. **This is the single largest open risk.**
2. Any static phase error below ~2 ps (dead-zone artefact).
3. Any tap-spacing number against real device mismatch.
4. Zero false locks in a real PFD/charge pump with mismatch and leakage.
5. Jitter, power or area.

---

## 12. Recommended next steps (your call)

| Priority | Action | Why |
|---|---|---|
| 1 | Phase 1 loop mathematics, Level A only (no tools needed) | Quantifies gain/stability analytically and separates architecture risk from tool risk |
| 2 | Phase 2 single delay cell, transistor level | The delay-range claim is the project's biggest unknown; needs ngspice + Sky130 |
| 3 | Re-run this prototype at `Icp = 150 µA` | Gain margin 0.30, lock ≤188 cycles — better PVT headroom |
| 4 | Decide on jitter strategy early | If S > 0.16, the 25 ps target needs a supply strategy, not a DLL tweak |

---

## 13. Files produced

Plots: `results/plots/` — `lock_transient_100MHz.png`, `frequency_sweep.png`,
`phase_waveforms_100MHz.png`, `tap_dnl.png`, `duty_correction.png`,
`startup_false_lock.png`, `jitter_estimate.png`

Tables: `results/tables/` — `lock_band_midpoints.csv`, `frequency_sweep.csv`,
`tap_spacing_100MHz.csv`, `duty_correction.csv`, `startup_sweep.csv`,
`loop_gain.csv`, `gain_vs_icp.csv`, `detector_comparison.csv`,
`jitter_sensitivity.csv`

Code: `scripts/dll_model.py`, `scripts/run_behavioral.py`
