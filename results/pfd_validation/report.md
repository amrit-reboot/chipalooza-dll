# PFD Credibility Validation — Level B Behavioral

> ## ⚠️ SUPERSEDED INTERPRETATION — UNDER INDEPENDENT REVIEW (2026-11-21)
>
> The **data and code in this report are preserved unchanged**. However, the
> **headline conclusion** ("a DLL cannot lock with a PFD", §1, §3.3, §4, §8) has
> been shown to be **incorrect**: the 77 trials used the wrong charge-pump
> polarity (`up_direction = -1`). With the physically correct polarity the same
> model locks at 1T in 24/77 trials, and 11/11 in the quasi-static engine when
> started from a coarse preset of 1.2 T (see the review for dynamic-model caveats).
>
> The claim that `D_min < T/2` makes acquisition impossible (§7) is also
> **withdrawn**. See `review/report.md` and `derivation.md` for the corrected
> derivation and full evidence. This banner is intentional: nothing below has
> been erased.

**Project:** Chipalooza Challenge #4 — 8-Phase DLL feasibility study
**Scope:** Problem 1 only — credibility of the behavioral PFD and the startup/false-lock simulation
**Date:** 2026-11-21
**New code:** `scripts/pfd_validation/pfd_event_model.py`, `run_pfd_validation.py`, `test_pfd.py`
**Original model:** `scripts/dll_model.py` — **preserved unchanged** (backup in `results/pfd_validation/baseline_backup/`)

---

## 0. Evidence level

**Level B behavioral.** No transistors, no Sky130 models, no parasitic extraction.
The delay characteristic is reused unchanged from `dll_model.py` so that the *only*
thing changed in this investigation is the phase detector. Nothing here is
transistor-level evidence.

---

## 1. Headline conclusion

> **The earlier "55/55 true lock, zero false locks" result was an artefact of the
> model and is withdrawn.**
>
> The original detector was not a phase detector. It was an oracle that was told
> the exact delay error relative to exactly one period, so harmonic locking was
> impossible by construction.
>
> With a real edge-triggered PFD, **the specified architecture does not lock at 1T
> at all** — in all 77 acquisition trials the control rail saturates at maximum
> delay. The PFD is one-sided for a pure delay line: it can only assert UP.
>
> **1T lock is therefore NOT guaranteed and NOT demonstrated. It was previously
> only *asserted* by a model that could not fail.**

---

## 2. What was wrong with the original model

`scripts/dll_model.py` did this:

```python
err_raw = t_line - T
err = clip(err_raw, -T/2, +T/2)      # magnitude capped, sign preserved
du  = (Icp / (C*VDD)) * abs(err) * sign(err)
```

Three independent defects:

| # | Defect | Consequence |
|---|---|---|
| 1 | The model is **told** `t_line - T`. A real PFD only sees edge **order**, never the true delay. | The loop always knows the correct direction, so it can always find 1T. |
| 2 | The error is measured against **exactly 1T**. | Harmonic lock is impossible by construction. `harmonic_index` could never be anything but 1. |
| 3 | Large errors are silently **capped at T/2**. | The PFD's frequency-detection behaviour (holding an output asserted) is removed entirely, which is exactly the mechanism that governs acquisition. |

Defect 2 alone makes the previous startup sweep circular: the experiment could
not have produced any result other than "no false locks".

---

## 3. The replacement: event-driven PFD

`pfd_event_model.py` simulates real edges on a time line.

- Reference rising edges at `nT`.
- Each reference edge is scheduled to emerge from the line at `nT + D(u)`.
- Two latches: reference edge sets **UP**, feedback edge sets **DOWN**.
- When both are high, both are reset after `t_reset`.
- An edge arriving while an output is already high changes nothing — this is what
  produces frequency detection.
- Charge is integrated on the loop capacitor over the time each output is
  asserted alone. Overlap delivers zero net charge.
- Intervals shorter than `t_dead` deliver no charge (dead zone).
- Control polarity is an explicit parameter, not hidden.

### 3.1 Detector unit tests — 9/9 pass

`python scripts/pfd_validation/test_pfd.py`

| Test | Property protected | Result |
|---|---|---|
| `test_reference_leads_feedback_asserts_up` | ref first → UP asserted | PASS |
| `test_up_pulse_width_tracks_phase_error` | UP width = delay for D<T (0.05/0.2/0.5/0.9 T) | PASS |
| `test_feedback_leading_reference_asserts_down` | fb first → DOWN asserted | PASS |
| `test_exact_alignment_produces_no_net_charge` | D=1T → no net charge | PASS |
| `test_harmonic_ambiguity_is_present` | D=1T, 2T, 3T are indistinguishable | PASS |
| `test_up_width_is_fractional_part_above_one_period` | D=1.1T → UP=0.1T | PASS |
| `test_control_polarity_is_negative_feedback` | chosen polarity raises delay | PASS |
| `test_charge_pump_dead_zone_blocks_tiny_pulses` | dead zone blocks sub-threshold charge | PASS |
| `test_rail_saturation_is_reported` | railed control is flagged | PASS |

One test initially **failed** and exposed a real defect: a phase-advanced feedback
edge was being scheduled before the simulation time origin, corrupting edge order.
Fixed by shifting the timeline and seeding the pre-`t_start` feedback edge.

### 3.2 Measured detector response

`results/pfd_validation/tables/detector_pulse_widths.csv`

| Fixed D/T | steady-state UP width | DOWN width |
|---:|---:|---:|
| 0.05 | 0.050 | 0.0005 |
| 0.20 | 0.200 | 0.0005 |
| 0.50 | 0.500 | 0.0005 |
| 0.90 | 0.900 | 0.0005 |
| 0.99 | 0.990 | 0.0005 |
| 1.00 | 0.000 | 0.0005 |
| 1.01 | 0.010 | 0.0005 |
| 1.10 | 0.100 | 0.0005 |
| 1.50 | 0.500 | 0.0005 |
| 2.00 | 0.000 | 0.0005 |
| 3.00 | 0.000 | 0.0005 |

Two facts are now measured rather than assumed:

1. **UP is asserted for `D` when D < T, and for `frac(D/T)` when D > T.** The
   detector output is a function of delay modulo T, which is the physical origin
   of the harmonic ambiguity.
2. **DOWN is never significant for a pure delay**, because a delay line can only
   make the feedback arrive *after* the reference. In the window after each reset,
   `ref` always arrives before `fb`.

### 3.3 Why this makes a PFD unusable here

A PFD reaches equilibrium only when the phase error is driven to zero by a
**frequency-integrating** control — that is, in a PLL, where a persistent UP
raises the VCO frequency until the phase catches up.

A DLL has **phase-only control**: adjusting the delay changes the phase directly
and does not integrate. A persistent UP therefore has no equilibrium to settle
into, so the control walks to the end of its range.

That is exactly what the simulation shows.

---

## 4. Acquisition results with the real PFD

Full matrix: 11 frequencies × 7 initial control values = **77 runs**, 4000 cycles,
`Icp = 300 µA`, `C_loop = 25 pF`.

![basin](../plots/acquisition_basin_100MHz.png)

`results/pfd_validation/tables/acquisition_matrix_up_increases_delay.csv`

| Outcome | Count |
|---|---|
| Sustained 1T lock | **0** |
| Ended near 1T but still moving | 7 |
| Settled at 2T | 28 |
| Settled at 3T | 42 |
| Oscillation | 0 |
| Rail saturation at maximum delay | **77 / 77** |

The acquisition basin at 100 MHz (`basin_map_100MHz.csv`) is unambiguous: **every
one of 71 starting delays from 0.05T to 3.55T ends at the same point, 2.8T** — the
maximum delay of band 1. The loop is not controlling phase; it is ratcheting.

Startup strategy makes no difference (`startup_strategy.csv`):

| f (MHz) | start = min delay | start = max delay | start = 0.5 |
|---|---|---|---|
| 25 | 1.400T (max) | 1.400T | 1.400T |
| 100 | 2.800T (max) | 2.800T | 2.800T |
| 200 | 2.800T (max) | 2.800T | 2.800T |

All three strategies produce the identical railed endpoint. **The minimum-delay
startup strategy therefore does not select the intended 1T lock** — it cannot,
because there is no 1T equilibrium to select.

Control polarity was tested both ways. Only the negative-feedback polarity
(`UP` → lower VCTRL → longer delay) is physically consistent with a
"start fast, then slow down" startup; the opposite polarity is degenerate.

---

## 5. Comparison against the original model

`results/pfd_validation/tables/old_vs_new_model.csv`

| Metric | Result |
|---|---|
| Grid points compared | 77 |
| Identical verdicts | **0 / 77** |
| Old model claimed 1T lock | 77 / 77 |
| New model achieved 1T lock | 0 / 77 |

Every single case differs. This is not a marginal correction — the original
simulation and the event-driven simulation disagree on every tested point, because
one of them cannot fail and the other can.

The unfavourable result is retained and reported here rather than discarded.

---

## 6. Phase ambiguity and harmonic locking

The ambiguity is structural, not a modelling nuisance:

- With equal reference and feedback frequencies, a delay of `kT` produces perfectly
  aligned edges for **every** integer `k`.
- The PFD sees the same edge pattern for 1T, 2T and 3T (proven by
  `test_harmonic_ambiguity_is_present`).
- Nothing in the detector can distinguish them. Only the loop's starting point and
  the shape of its trajectory can.

This is why "does it lock?" is the wrong question. The correct question is
"**which harmonic does the control law select?**", and for a phase-only loop with
a bare PFD the answer is "the end of the range".

---

## 7. What a workable detector looks like

`results/pfd_validation/tables/wrap_detector_grid.csv` — same delay characteristic
and same grid, but a **wrapping phase detector** (mixer/XOR style) whose output is
proportional to the wrapped phase error:

| Outcome | Count |
|---|---|
| Sustained 1T lock | **47 / 77** |
| Settled at 2T | 17 |
| Settled at 3T | 8 |
| No lock | 5 |

So 1T *is* reachable — but only when the loop starts inside the detector's capture
window. That window is the real design constraint:

**Acquisition requires 0.5 T < D_min < 1.5 T.**

`results/pfd_validation/tables/capture_window.csv` applied to the current band plan:

| f (MHz) | band | D_min / T | D_max / T | capturable from min delay |
|---:|---:|---:|---:|---|
| 25 | 0 | **0.340** | 1.400 | **NO** |
| 30 | 0 | **0.408** | 1.680 | **NO** |
| 42.5 | 0 | 0.578 | 2.380 | YES |
| 50 | 0 | 0.680 | 2.800 | YES |
| 60 | 0 | 0.816 | 3.360 | YES |
| 85 | 1 | 0.578 | 2.380 | YES |
| 100 | 1 | 0.680 | 2.800 | YES |
| 120 | 1 | 0.816 | 3.360 | YES |
| 150 | 2 | 0.600 | 2.100 | YES |
| 180 | 2 | 0.720 | 2.520 | YES |
| 200 | 2 | 0.800 | 2.800 | YES |

**A concrete defect in the current band plan is exposed:** at 25 and 30 MHz the
minimum achievable delay is only 0.34T and 0.41T. No phase detector of any kind
can acquire from there, because the starting error exceeds a half period.

To fix it, the band-0 minimum delay must exceed `T/2` at 25 MHz, i.e.
`D_min > 20 ns`, i.e. **stage delay > 2.5 ns** — versus the 1.70 ns currently
planned. That is a band-plan change and needs your approval.

---

## 8. Answers to the required questions

### Is the current DLL acquisition architecture credible?

**Not as specified.** A two-latch PFD feeding a charge pump into a phase-only
delay control has no equilibrium: the detector is structurally one-sided and the
control rails. This is a topological argument, not a numerical accident — it is
confirmed by the pulse-width measurements, the basin map and all 77 trials.

### Is 1T lock guaranteed, merely observed, or not demonstrated?

- **Not guaranteed.** No mechanism in the specification forces 1T.
- **Not reliably observed.** 0 of 77 trials reached it with the PFD.
- **Not demonstrated.** The previous "demonstration" is withdrawn as an artefact.

With a wrapping detector it becomes *observed* (47/77), still not *guaranteed*.

### What architectural modification is needed if false locks are unacceptable?

In priority order:

1. **Replace the PFD with a bidirectional phase detector.** A lead/lag (bang-bang)
   or wrapped-phase detector produces a genuine error signal with a zero at the
   target phase. A bare PFD cannot, because a DLL cannot integrate frequency.
2. **Guarantee the capture window in the band plan.** Every band must satisfy
   `0.5 T < D_min < 1.5 T` at its lowest frequency. The current band 0 fails this
   at 25–30 MHz by a wide margin.
3. **Keep minimum-delay startup, but as a capture aid, not as a lock guarantee.**
   It only helps if the minimum delay is already inside the capture window.
4. **Add an explicit lock detector with a harmonic check.** Verify that the
   measured line delay is within tolerance of exactly 1T (not 2T, not 3T) before
   asserting LOCK. A phase-only lock detector cannot distinguish harmonics.
5. **Consider a coarse frequency-aiding loop** (e.g. delay-range calibration at
   startup) if the band plan cannot guarantee the capture window across PVT.

None of these are implemented — they are proposals requiring your approval.

---

## 9. Limitations of this investigation

- Level B only. The PFD is ideal apart from reset delay and dead zone; no charge
  injection, no leakage, no mismatch inside the PFD itself.
- The delay characteristic is the same algebraic curve as before. If the real
  Sky130 cell's `Kd` differs, the numbers change — but the *structural* conclusion
  (one-sided PFD, no equilibrium) does not depend on `Kd`.
- The two-latch PFD with reset-on-both is the textbook implementation. Variants
  exist (e.g. reset-dominant PFDs); each must be checked on its own.
- Whether the intended silicon PFD behaves exactly this way must be confirmed in
  Phase 3 against a transistor-level PFD with charge pump.
- 77 acquisition trials is a systematic sweep, not a statistical campaign.

---

## 10. Files

**Code**
- `scripts/pfd_validation/pfd_event_model.py` — event-driven PFD and loop
- `scripts/pfd_validation/run_pfd_validation.py` — 7 experiments
- `scripts/pfd_validation/test_pfd.py` — 9 detector tests (9/9 pass)

**Tables** (`results/pfd_validation/tables/`)
`detector_pulse_widths.csv`, `acquisition_matrix_up_increases_delay.csv`,
`acquisition_matrix_up_decreases_delay.csv`, `basin_map_100MHz.csv`,
`old_vs_new_model.csv`, `startup_strategy.csv`, `capture_window.csv`,
`wrap_detector_grid.csv`

**Plots** (`results/pfd_validation/plots/`)
`detector_pulse_width.png`, `acquisition_basin_100MHz.png`,
`acquisition_heatmap_up_increases_delay.png`,
`acquisition_heatmap_up_decreases_delay.png`

**Logs** (`results/pfd_validation/logs/`)
`pfd_validation_run.log`

**Baseline backup** (`results/pfd_validation/baseline_backup/`)
`dll_model.py`, `run_behavioral.py`, `behavioral_dll.md`, `startup_sweep.csv`
(byte-identical copies of the originals, which remain unmodified in place)
