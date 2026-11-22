# Startup Acquisition Investigation — 8-Phase DLL (LEVEL B)

**Date:** 2026-11-21
**Level:** **B — behavioral / analytical concept study only.** No transistor
simulation, no Sky130 device data, no Docker, no installation.
**Scope:** Architecture investigation and feasibility comparison only.
No solution implemented. No official architecture, specification, baseline, or
validated model file modified. Problem 2 not started.

---

## TASK

Investigate physically realizable startup/acquisition mechanisms for the DLL,
compare five options (A–E) against twelve required criteria, answer eleven
specific technical questions, and produce a recommendation — without changing
the design or claiming unverified performance.

---

## CHANGES

New directory and files only:

| Path | Content |
|---|---|
| `results/pfd_validation/acquisition_investigation/report.md` | this report |
| `option_comparison.csv` | 5 options × 12 criteria comparison matrix |
| `block_diagrams/*.png` | 6 conceptual block diagrams (matplotlib) |
| `references.md` | 7 external references + internal evidence index |

No edits to `scripts/`, `spec/`, `design/`, `sim/`, or any validated result file.

---

## METHOD

1. **Verified the supplied context** against actual code and result files
   (Section 0). Nothing was accepted on trust.
2. **Additional Level B diagnostics** using the existing validated v4 engine
   and the v2 frozen-transfer model:
   - band delay ranges Dmin/T and Dmax/T across 25–200 MHz;
   - startup ignored-reference-edge count versus fixed D/T;
   - frozen PFD UP-pulse width versus D/T (ambiguity check).
3. **Literature search** for practical DLL acquisition / harmonic-lock
   techniques implementable in CMOS.
4. **Option analysis** against the twelve requested criteria.

---

## 0. Verification of the supplied context

| Claim in the task context | Verified? | Evidence |
|---|---|---|
| Correct PFD/CP polarity established | **Yes** | `final_validation/report.md` §7, §1–5 |
| 1T lock achievable from suitable initial delay | **Yes** | `f2_convergence.csv`: 1.05T–1.95T all lock 1T |
| Initial delay ~1.10T–1.95T achieves 1T lock | **Yes** | `f2_convergence.csv` (1000 substeps) |
| Initial delay < ~1.02T rails to minimum | **Yes** | `f2_convergence.csv`: 0.90–1.02T → 0.68T rail |
| At 1.05T, trajectory dips below 1T then recovers | **Yes** | `f2_convergence.csv` outcome label; report §2 |
| Minimum delay ≈ 0.68T at 100 MHz | **Yes** | band 1 t_lo=0.85ns × 8 = 6.8 ns = 0.68T |
| v4 passed timestep-convergence testing | **Yes** | `f1_timestep_audit.csv`, `f2_convergence.csv`: identical 50–5000 substeps |
| 1.3T preset was a simulation preset, not a circuit | **Yes** | `final_validation/report.md` §6; `preset_feasibility.md` |
| Startup acquisition unresolved | **Yes** | `final_validation/report.md` §7, §NEXT STEP |

**Conclusion:** the context is accurate. One refinement: the verified 1T basin
starts near **1.05T** (1.05T locks with a brief excursion), not exactly 1.10T.
The band analysis below uses the conservative 1.02T–1.95T bounds from the
report.

---

## 0.1 New Level B diagnostics performed for this investigation

**(a) Band delay ranges** (from `dll_model.py` BANDS, N=8):

| f (MHz) | band | T (ns) | Dmin/T | Dmax/T | Max-delay startup basin |
|---:|---:|---:|---:|---:|---|
| 25 | 0 | 40.00 | 0.340 | 1.400 | 1T (inside basin) |
| 30 | 0 | 33.33 | 0.408 | 1.680 | 1T (inside basin) |
| 42.5 | 0 | 23.53 | 0.578 | 2.380 | 2T |
| 50 | 0 | 20.00 | 0.680 | 2.800 | 2T |
| 60 | 0 | 16.67 | 0.816 | 3.360 | 3T |
| 85 | 1 | 11.76 | 0.578 | 2.380 | 2T |
| 100 | 1 | 10.00 | 0.680 | 2.800 | 2T |
| 120 | 1 | 8.33 | 0.816 | 3.360 | 3T |
| 150 | 2 | 6.67 | 0.600 | 2.100 | 2T |
| 180 | 2 | 5.56 | 0.720 | 2.520 | 2T |
| 200 | 2 | 5.00 | 0.800 | 2.800 | 2T |

Implication: **band selection alone cannot guarantee a 1T basin start.**
Only 25/30 MHz have Dmax inside the basin; all other frequencies require
delay reduction from Dmax into (1T, 2T).

**(b) Startup ignored-REF count** (v4, Icp ≈ 0 to freeze delay):

| D/T | ignored REF edges at startup | floor(D/T) |
|---:|---:|---:|
| 0.68 | 0 | 0 |
| 0.90 | 0 | 0 |
| 1.35 | 1 | 1 |
| 1.68 | 1 | 1 |
| 2.10 | 2 | 2 |
| 2.50 | 2 | 2 |

This is the key hardware-observable quantity: counting how many reference
edges arrive before the first feedback edge yields **k = floor(D/T)** without
any knowledge of T.

**(c) UP pulse-width ambiguity** (frozen transfer): D/T = 0.68, 1.68 and 2.68
all produce the **same fractional UP pulse width ≈ 0.68T**. Therefore pulse
width alone cannot distinguish minimum-delay operation from harmonic lock —
edge counting is required.

---

## 1. Option A — Digital cycle-counting acquisition

### Block diagram
`block_diagrams/option_a.png`

### 1.1 Principle
On reset, set the VCDL toward maximum delay and hold the charge pump off.
Count reference edges from reset until the first feedback edge arrives. Define
the count as the number of *ignored* reference edges, verified in §0.1b as
`k = floor(D/T)`. Interpret:
- `k = 0` → `D < T` → min-delay rail basin → **increase** delay;
- `k = 1` → `T ≤ D < 2T` → **desired 1T basin**;
- `k ≥ 2` → `D ≥ 2T` → harmonic basin → **decrease** delay.

Steer the coarse delay until `k = 1`, then enable the analog loop.

**Convention note:** an earlier description used `ceil(D/T)` with desired count 2.
That is a different definition and is not the convention implemented by the
controller or used in this corrected report. `option_comparison.csv` retains the
original `ceil(D/T)` text as raw historical data and was not modified.
Boundary cases (`D ≈ T` or `D ≈ 2T`), coincident REF/FB edges, synchronizer
latency, and measurement-window flush discipline remain unresolved
implementation issues.

### 1.2 Additional components
2–3 bit REF-edge counter, first-FB detector, count decoder, coarse delay
actuator (switched load caps or small DAC), mode FSM, CP gating.

### 1.3 Area / power (qualitative)
Small digital block; modest analog coarse actuator. Much less than a second
VCDL. No numerical estimate claimed.

### 1.4 Startup sequence
RESET_N asserted → CP disabled, VCDL coarse code set to maximum → RESET_N
released → count REF edges until first FB → decode k → if k≠1 step coarse
code in the indicated direction → repeat → when k=1 stable for N cycles,
enter FINE mode.

### 1.5 Interaction with existing blocks
Directly gates CP enable; does not alter PFD logic. Uses the existing FB
(last tap) signal. Coarse actuator drives VCTRL or a separate coarse control
node through a MUX.

### 1.6 Fine-lock handoff
When k = 1, coarse actuator holds, CP is enabled, and the already-validated
behavioral v4 1T acquisition takes over from above (1.02T–1.95T basin).

### 1.7 Failure modes
- In-flight delay changes corrupt the count → mitigated by CP disabled during
  counting; a new edge train must flush the line between attempts.
- Exact D ≈ T or 2T gives ambiguous count → require hysteresis / two
  consecutive agreeing counts.
- REF glitches, metastability at FB detection, frequency change mid-count.

### 1.8 Suitability 25–200 MHz
Counting is frequency-independent in principle; at 200 MHz T=5 ns, a 2–3 bit
counter in Sky130 can resolve this. Not simulated at transistor level.

### 1.9 Distinguishes 1T from harmonic?
**Yes** — k = 1 versus k ≥ 2 directly identifies the basin.

### 1.10 Complexity
Medium.

### 1.11 Evidence
§0.1b; `final_validation/report.md` §6; [2], [3].

*(Additional criteria — control, termination, RESET/DLL_EN, frequency change —
are answered centrally in Section 6.)*

---

## 2. Option B — Coarse/fine delay architecture

### Block diagram
`block_diagrams/option_b.png`

### 2.1 Principle
Split the 8-stage VCDL (or add a preceding coarse section) into a digitally
controlled coarse delay and the existing analog fine delay. The coarse section
places total delay near T; the fine PFD/CP loop removes the residual. The
fine range only needs to cover one coarse step plus PVT variation.

### 2.2 Additional components
Switched capacitor loads or digital delay stages, coarse code register/DAC,
buffering and MUX, level shifters between digital coarse and analog fine
domains.

### 2.3 Area / power (qualitative)
Moderate to high — extra delay elements and routing. Literature reports
roughly 2x for the closely related PLL-assisted replica approach [1].

### 2.4 Startup sequence
Select coarse code (from band or a count estimate) → hold fine loop reset →
allow coarse delay to settle → enable fine PFD/CP.

### 2.5 Interaction
Coarse block sits in series before the existing fine VCDL; CP drives only the
fine control node. Taps after the fine section remain the phase outputs.

### 2.6 Fine handoff
Automatic once coarse code is fixed; fine loop locks the residual.

### 2.7 Failure modes
Coarse step too large → lands outside (1T, 2T); mismatch between coarse and
fine sections across PVT; extra load and duty-cycle distortion on PHASE outputs;
**still needs a period estimate to choose the coarse code** — this option does
not by itself solve the startup problem.

### 2.8 Suitability
Good if coarse range covers 1T across PVT; band ranges from §0.1a are
sufficient in the planning model.

### 2.9 Distinguishes 1T from harmonic?
**No by itself.** Must be paired with A/D/E1.

### 2.10 Complexity
Medium–high.

### 2.11 Evidence
`dll_model.py` BANDS; [1], [2], [5].

---

## 3. Option C — Delay-range / frequency-band selection

### Block diagram
`block_diagrams/option_c.png`

### 3.1 Principle
The design already has RANGE[1:0]. Selecting a band narrows the absolute
delay range. The idea is that a narrower range makes it easier to start in the
basin.

### 3.2 Additional components
None — existing pins and mux.

### 3.3 Area / power
Negligible incremental.

### 3.4 Startup sequence
Assert RANGE → apply existing startup → fine loop.

### 3.5 Interaction
Uses existing band mux; no change to PFD/CP.

### 3.6 Fine handoff
Unchanged.

### 3.7 Failure modes / decisive limitation
**Band selection alone cannot guarantee a suitable initial delay.**
From §0.1a, with minimum-delay startup Dmin/T = 0.34–0.82 at every frequency
— always below the basin. With maximum-delay startup, only 25/30 MHz land in
the basin; all higher frequencies land at 2T/3T. The band only bounds the
absolute delay; it does not measure T.

### 3.8 Suitability
Bands cover 25–200 MHz, but basin placement is not guaranteed.

### 3.9 Distinguishes 1T from harmonic?
**No.**

### 3.10 Complexity
Low.

### 3.11 Evidence
§0.1a; `dll_model.py` BANDS; [4] (band limits).

---

## 4. Option D — Startup control using PFD signals

### Block diagram
`block_diagrams/option_d.png`

### 4.1 Principle
Reuse the existing PFD outputs. A small FSM watches REF, UP, DOWN and the
reset state. Counting reference edges while UP remains asserted from startup
is *the same observable* as Option A (startup ignored-REF count). The FSM
steers the delay away from the rail and enables the CP when the count indicates
k = 1.

### 4.2 Additional components
Small digital FSM, coarse steering path, CP gate. No separate period-measurement
system.

### 4.3 Area / power
Very small digital.

### 4.4 Startup sequence
RESET_N → PFD reset, CP off → first UP asserted → count REF edges until first
DOWN (FB) → decode k → steer → k=1 → enable CP.

### 4.5 Interaction
Taps existing PFD signals; CP gated during coarse phase; no PFD redesign.

### 4.6 Fine handoff
As Option A.

### 4.7 Failure modes
- **UP pulse width alone is not sufficient** — verified ambiguity 0.68T vs
  1.68T in §0.1c. The FSM must count edges, not measure pulse width.
- PFD dead zone, metastability, in-flight edge changes (CP off requirement).
- If the FSM misinterprets a normal startup UP pulse as a fault, it can steer
  the loop the wrong way.

### 4.8 Suitability
Good at 25–200 MHz if FSM is fast enough.

### 4.9 Distinguishes 1T from harmonic?
**Yes, if it counts edges; no, if it uses pulse width only.**

### 4.10 Complexity
Low–medium.

### 4.11 Evidence
§0.1b/c; [6], [7].

---

## 5. Option E — Alternative acquisition detectors

### Block diagram
`block_diagrams/option_e.png`

### 5.1 E1 — Multiphase harmonic lock detector (HLD)
Monitors selected taps (e.g. P1, P2, P4, P8, P16) to detect if total delay
exceeds ~1.25–1.5 TREF. Requires comparators and logic. Demonstrated in 0.13 µm
over 25–500 MHz [3]. Distinguishes 1T from harmonic: **yes**. Complexity:
medium. Note its published threshold (1.5T) differs from our behavioral basin
(≈1.95T) — thresholds must be re-derived for our topology.

### 5.2 E2 — Replica VCDL PLL-assisted coarse control
A replica VCDL is configured as a VCO and PLL-locked to the input; the
resulting control voltage sets the main VCDL close to T. Area/power roughly
doubles [1]. Distinguishes 1T from harmonic indirectly. Complexity: high.

### 5.3 E3 — Stopwatch / N-detector
A pulse is sent through a replica delay model while a counter measures how
many reference periods it takes; the captured count sets coarse delay [2].
Requires replica delay model and counter, and accurate tracking between model
and real VCDL across PVT. Distinguishes 1T from harmonic: **yes**. Complexity:
medium.

### 5.4 E4 — Binary search on phase-error polarity
A SAR controller searches the coarse code [5]. Caution: our frozen PFD
transfer is **one-sided**, so phase-error polarity alone does not indicate
direction; the comparison signal would have to be edge-count based, reducing
this to Option A with a different search algorithm. Complexity: medium.

### 5.5 E5 — Second loop with VCO (patent)
A second PFD/CP/VCO loop detects harmonic lock and forces main delay down [7].
High complexity and area; included for completeness.

### 5.6 Summary
All E options require additional hardware. E1 and E3 are the most practical;
E2 is the most robust but costly.

---

## 6. Important technical questions

**Q1 — How can hardware determine the input period without already being locked?**
It does not need T numerically. Counting REF edges until the first FB edge
gives `k = floor(D/T)` directly (§0.1b). That is a dimensionless basin index,
sufficient to steer. Absolute period measurement (E2/E3) is an alternative but
adds hardware.

**Q2 — Can feedback edge counting distinguish 0.68T from 1.68T?**
**Yes, if the count starts at a known reset event**: 0.68T produces one REF
edge before first FB; 1.68T produces two. Counting REF edges *between*
consecutive FB edges does **not** work (both give one, because FB has the same
frequency as REF). UP pulse width also does not work (§0.1c).

**Q3 — What happens if VCDL delay changes while edges are in flight?**
The v4 engine shows older, slower edges can arrive late and even generate DOWN
pulses. For edge counting this corrupts the measurement. Therefore the CP
must be disabled during coarse acquisition and the line flushed between
attempts. This is a Level B design requirement, not yet a verified circuit.

**Q4 — How should the startup controller avoid destabilizing the analog loop?**
Gate the CP off during coarse acquisition; apply coarse delay through a
separate path; hand over once; add hysteresis and a holdoff timer so the FSM
cannot re-trigger the coarse loop during fine settling.

**Q5 — Should the charge pump be disabled during coarse acquisition?**
**Yes.** Otherwise the delay changes during counting and the control voltage
can be driven to a rail by the full-startup UP pulse (the exact failure seen
for starts ≤1.02T in `f2_convergence.csv`).

**Q6 — How should acquisition terminate?**
When the count indicates k = 1 (D in [T, 2T)) for two consecutive measurement
windows, switch to FINE and disable the counter. Termination is by basin
index, not by a guessed period.

**Q7 — What prevents repeated switching between modes?**
FSM with one-way progression ACQUIRE → FINE after a valid handoff; re-entry
only on RESET, DLL_EN toggle, or a verified loss-of-lock / frequency-change
event, with a holdoff counter.

**Q8 — What happens when REF_CLK changes frequency?**
The existing delay no longer equals T; fine lock is lost. A lock detector
monitoring phase error / count must detect this and re-enter ACQUIRE, possibly
with a new RANGE band. This is **not solved** by any option here and is a key
open risk.

**Q9 — How should RESET_N and DLL_EN behave?**
RESET_N: asynchronously reset PFD, CP control, counter and FSM; force coarse
maximum delay and CP disabled. DLL_EN: master enable; when low, CP tri-stated,
coarse held, outputs gated; when high with RESET_N released, start the ACQUIRE
sequence. Exact polarities are not specified here.

**Q10 — How can a lock detector confirm 1T rather than 2T?**
Edge count k = 1 combined with near-zero steady PFD charge; or multiphase
timing: at 1T, PHASE[4] (nominally 180°) is half a reference period after
PHASE[0]; at 2T it is a full period after. A simple tap-relationship detector
can verify this. PFD pulse width alone cannot (§0.1c).

---

## 7. Comparison summary

See `option_comparison.csv`. Ranking against the request criteria:

| Option | Basin placement | 1T vs harmonic | New HW | 25–200 MHz | Overall |
|---|---|---|---|---|---|
| A | Yes (k=1) | Yes | Small-medium | Good | **Best** |
| D | Yes (same observable via PFD) | Yes if counting | Very small | Good | **Second** |
| B | Only with code/period estimate | No alone | Medium-high | Good | Enabler |
| C | No | No | None | Bounds only | Insufficient alone |
| E1/E3 | Yes | Yes | Medium | Literature-supported | Viable alternative |
| E2 | Yes | Indirect | High (~2x) | Good | Robust but costly |

---

## 8. Conclusions

### 8.1 Best acquisition approach
**Option A — digital cycle-counting acquisition.** It uses a directly
measurable, period-independent observable (`floor(D/T)`) that this
investigation verified in the validated v4 engine, it distinguishes the 1T
basin from both the min-delay rail and 2T/3T harmonics, and it needs only a
small digital block plus a coarse delay actuator. It is the only option that
both solves the startup placement problem and requires no prior knowledge of
the input period.

### 8.2 Second-best alternative
**Option D — startup control from existing PFD signals.** It is essentially
Option A implemented with the PFD's own UP/DOWN and reset-state signals,
minimizing new hardware. Its critical constraint is that it must count edges;
using UP pulse width alone is provably ambiguous in our model.

### 8.3 Recommended conceptual architecture
Combine A (or D) with a minimal coarse/fine split:

1. RESET_N → CP disabled, coarse VCDL at maximum delay, counter and FSM reset.
2. Count REF edges to first FB edge → k = floor(D/T).
3. If k ≠ 1, step coarse delay in the indicated direction; flush and repeat.
4. When k = 1 is stable, hold coarse code, enable the behaviorally validated
   fine PFD/CP loop, which acquires 1T from above.
5. A tap-based 1T lock detector verifies D ≈ T (not 2T) before asserting LOCK.
6. FSM progresses one way; re-acquire only on RESET, DLL_EN, or verified
   loss of lock / frequency change.

Diagram: `block_diagrams/recommended.png`. **This is a proposal only; nothing
was implemented and no architecture file was changed.**

### 8.4 Key risks
- Coarse delay changes while edges are in flight corrupt the count → CP must
  be off and the line flushed.
- Basin boundary is a single-corner, single-frequency Level B result
  (≈1.02T–1.05T at 100 MHz); PVT margin unknown.
- Frequency changes during operation are not solved by any option.
- 1T lock detector thresholds are unverified.
- Coarse actuator step size and hysteresis are not designed.

### 8.5 What must be simulated next (Level B)
1. Behavioral model of the edge counter + FSM + coarse steering, driven by the
   v4 engine, over all 11 frequencies and multiple starting codes.
2. Coarse-step sweep to find a step that lands reliably in (1.02T, 1.95T)
   without overshoot to k=0 or k≥2.
3. Frequency-change mid-lock test.
4. Tap-based 1T lock detector model distinguishing 1T from 2T.
5. Only after that: transistor-level PFD/CP polarity and coarse delay element
   verification (separate phase, requires approval).

### 8.6 What cannot yet be claimed
- That any option achieves lock time ≤100/400 cycles with acquisition overhead.
- That the basin or count thresholds hold across PVT or in silicon.
- That harmonic lock is eliminated — only that it is detectable and steerable
  in the Level B model.
- That the recommended architecture is area/power compliant.
- Any transistor-level or post-layout result.

---

## STATUS

- Verification of supplied context: **PASS**
- Option comparison complete: **PASS**
- Technical questions answered: **PASS**
- Best approach identified (Level B): **PASS — Option A**
- Circuit implementation: **NOT STARTED** (out of scope)
- Transistor / PVT feasibility: **UNVERIFIED**

---

## ISSUES

1. No architecture or specification change was made; the current official
   startup (minimum-delay forcing) remains incompatible with the 1T basin.
2. The coarse delay actuator, FSM timing and lock-detector thresholds are
   conceptual only — no sizing or timing margin established.
3. Literature thresholds (0.5T/1.5T) differ from our behavioral basin
   (≈1.02T–1.95T); they must not be substituted for project evidence.
4. Frequency-change handling is an open problem.
5. No fabricated numeric area/power figures are given; all such statements
   are qualitative.

---

## NEXT STEP

Present this comparison to the user for a decision. No implementation, no
architecture edit, and no Problem 2 work may proceed without explicit
approval of a specific option. Stopping here after presenting the comparison
and recommendation.
