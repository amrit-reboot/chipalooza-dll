# Proposed Coarse Actuator — Behavioral Requirement Description (LEVEL B)

**This is a requirement description, not a designed circuit.** No transistor sizing, no schematic, no area/power number is claimed. Any decision to add this block to the official architecture requires explicit user approval.

---

## 1. What the prototype assumes

The v4/DLL model exposes a normalized VCDL control `u ∈ [0, 1]`:

- `u = 0` → maximum cell delay (`t_hi`), `u = 1` → minimum cell delay (`t_lo`)
- `line_delay(u) = 8 · t_hi / (1 + (t_hi/t_lo − 1) · u)` — monotonic decreasing in `u`
- The controller changes `u` only by fixed steps: `Δu = 0.10` coarse, `Δu = 0.05` nudge

The controller never computes a target `u` from `T`; it only steps in the direction indicated by the measured count `k = floor(D/T)`.

---

## 2. Monotonicity check

From the model (`dll_model.py` stage_delay), `dD/du < 0` for all `u ∈ [0, 1]` and all bands. Therefore:

- "increase delay when FB too early" → decrease `u` ✔
- "decrease delay when FB too late" → increase `u` ✔
- No non-monotonic region exists in the planning model ✔

**Qualification:** this is the model's analytic monotonicity, not a measured Sky130 transfer curve. Real switched-cap loading may introduce non-monotonic step behaviour if load steps overlap poorly with the fine control range.

---

## 3. Range and resolution requirements

For each functional band, the `u` interval that yields `1 ≤ D/T < 2` (count = 1):

| f (MHz) | band | D/T range | u at D/T = 2 | u at D/T = 1 | Window width |
|---:|---:|---:|---:|---:|---:|
| 25 | 0 | 0.34 – 1.40 | 0.000 | 0.128 | **0.128** |
| 30 | 0 | 0.41 – 1.68 | 0.000 | 0.218 | 0.218 |
| 50 | 0 | 0.68 – 2.80 | 0.128 | 0.577 | 0.449 |
| 75 | 1 | 0.51 – 2.10 | 0.016 | 0.353 | 0.337 |
| 100 | 1 | 0.68 – 2.80 | 0.128 | 0.577 | 0.449 |
| 150 | 2 | 0.60 – 2.10 | 0.020 | 0.440 | 0.420 |
| 200 | 2 | 0.80 – 2.80 | 0.160 | 0.720 | 0.560 |

**Requirements derived:**
1. The actuator must span the full `u ∈ [0, 1]` range (or at least cover every window above) — otherwise some initial conditions cannot be corrected.
2. Step size must be smaller than the narrowest window (0.128 at 25 MHz) to avoid skipping count = 1. The prototype's `Δu = 0.10` satisfies this.
3. A 3-bit uniform code (`Δu = 0.125`) would be marginal at 25 MHz. A 4-bit code (`Δu ≈ 0.067`) gives ≈2× margin and is the **qualitative** recommendation.
4. Fine resolution near the basin should be ≤0.05 in `u` to support the nudge step used by LOCK_VERIFY recovery.

No numeric area, power or switching-speed claim is made. These are control-domain requirements only.

---

## 4. Candidate hardware structures (conceptual)

| Candidate | Principle | Pros | Cons / open issues |
|---|---|---|---|
| **Switched capacitive loads** on each delay stage (extend existing RANGE mux) | Digital code adds/removes load caps → stepwise delay | Reuses existing band-select concept; monotonic if weighted correctly | Extra load and duty-cycle distortion on PHASE outputs; step quantization; must not disturb fine cell |
| **Coarse DAC driving the same VCTRL node through a MUX** | DAC sets approximate VCTRL during ACQUIRE; CP drives it during FINE | Fine and coarse share one control node; simple handoff | Requires break-before-make MUX; DAC must hold voltage during handoff; leakage during fine lock |
| **Separate coarse control on a series delay section** | Digital coarse stages before the existing analog fine line | Clean separation of acquisition from fine loop | Adds delay elements, buffering and area; tap phase outputs move; coarse/fine PVT mismatch |
| **Replica VCDL PLL-assisted coarse voltage** (literature Option E2) | Second loop generates coarse VCTRL | Robust across wide range | ~2× area/power reported in literature; far beyond this prototype's scope |

**Prototype mapping:** the behavioral `u` most directly corresponds to the second candidate (DAC + MUX on the existing control node). The first candidate corresponds to extending the existing RANGE mechanism. Neither has been designed.

---

## 5. Interaction with PFD / CP / filter / VCDL

- Coarse acquisition requires CP disabled; otherwise delay changes while edges are in flight and the count is corrupted (documented in the acquisition investigation).
- The coarse actuator must not inject charge into the loop capacitor during handoff; a MUX or tri-state is required.
- Handoff is one-way within an acquisition attempt: COARSE → FINE only after `k = 1`. Re-entry requires a verified failure or RESET.
- The loop capacitor value (25 pF in the model) is unchanged by the coarse path.

---

## 6. What is NOT established

- No transistor-level monotonicity or step-size verification.
- No area/power estimate.
- No proof that a DAC/MUX on VCTRL preserves fine-lock jitter.
- No proof that switched loads meet the tap-spacing spec.
- No PVT or Monte Carlo data.
- No approval to change the architecture has been given.
