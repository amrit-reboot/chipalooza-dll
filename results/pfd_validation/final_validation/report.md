# Final Validation — Problem 1: PFD and DLL Acquisition (LEVEL B)

**Date:** 2026-11-21
**Level:** **B — behavioral only.** No transistors, no Sky130, no parasitics.
**Scope:** Problem 1 only. No architecture/specification file modified. No Problem 2 work.
**Preservation:** All previous files, reports, tables and plots retained unchanged.

---

## TASK

Final validation of the event-driven PFD and DLL acquisition model, specifically:

1. Audit dynamic-engine timestep and event handling.
2. Convergence study: 50–5000 substeps/period.
3. Acquisition outcomes for 14 initial delays (0.90T–1.95T).
4. Parameter sweeps: Icp, reset delay, dead time.
5. Determine whether timestep changes basin boundaries.
6. Verify edge propagation, reset timing, pulse quantization, charge integration.
7. Distinguish below-1T, above-1T, sub-1T excursion, harmonics, rails, oscillation, artifacts.
8. Investigate 1.3T preset feasibility without prior period knowledge.
9. Establish the strongest honest conclusion.
10. Add a separate final-validation report with tables and plots.

---

## CHANGES

**New files only** (previous files preserved):

| File | Purpose |
|---|---|
| `scripts/pfd_validation/pfd_model_v4_final.py` | Exact sub-step event timing engine |
| `scripts/pfd_validation/run_final_validation.py` | F1–F5 runner |
| `results/pfd_validation/final_validation/report.md` | this report |
| `results/pfd_validation/final_validation/preset_feasibility.md` | requirement 8 analysis |
| `tables/f1–f4*.csv` | audit, convergence, sweeps, event trace |
| `plots/f2_convergence.png`, `f2_outcome_map.png`, `f3_icp_sweep.png` | new plots |
| `logs/final_validation.log` | full run log |

No official architecture, spec, or earlier result file modified. No Docker, install, or transistor simulation.

---

## METHOD

### v4 exact-event engine

The v3 dynamic engine advanced edges and processed PFD events only on a coarse
integration grid. At 100 MHz / 100 substeps, `dt = 100 ps` while `t_reset = 5 ps`
and `t_dead = 10 ps` — reset was late by up to 100 ps, edge arrivals were
quantized to the grid, and charge was computed from whole grid intervals.

**v4 inserts exact event times within each integration step:**

- reference edges at exact `nT`;
- in-flight edges propagate continuously; exit time solved from current stage delay;
- reset at exactly `t_event + t_reset` (including zero);
- charge integrated from `assertion + t_dead` to exact event time;
- UP/DOWN assertion times recorded for measurement.

Two independent checks were used: (a) edge accounting balance
`launched − completed − in_flight = 0`; (b) reset-delay measurement from the
event trace.

---

## RESULT

### 1. Timestep and event handling audit — PASS

`tables/f1_timestep_audit.csv`, all 7 substeps at D=1.35T:

| substeps | dt (ps) | launched | completed | in-flight | balance | ignored ref | resets | final D/T |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 50 | 200 | 300 | 299 | 1 | **0** | 1 | 299 | 1.001 |
| 100 | 100 | 300 | 299 | 1 | **0** | 1 | 299 | 1.001 |
| 200 | 50 | 300 | 299 | 1 | **0** | 1 | 299 | 1.001 |
| 500 | 20 | 300 | 299 | 1 | **0** | 1 | 299 | 1.001 |
| 1000 | 10 | 300 | 299 | 1 | **0** | 1 | 299 | 1.001 |
| 2000 | 5 | 300 | 299 | 1 | **0** | 1 | 299 | 1.001 |
| 5000 | 2 | 300 | 299 | 1 | **0** | 1 | 299 | 1.001 |

- **No edges lost** at any timestep.
- One ignored reference edge per run: correct PFD behavior — the reference
  edge at t=T arrives while UP is already asserted from startup.
- No ignored feedback edges.
- Reset delays measured from trace: **exactly 5.000 ps** at every event
  (`tables/f4_reset_delays.csv`).
- Event trace (`tables/f4_event_trace_1p35.csv`) shows the correct sequence:
  UP@0, DOWN@1.269T, RESET@+5ps, UP@2.0T, DOWN@2.199T, RESET@+5ps, …
- Charge is computed from exact assertion times, not quantized intervals.

**Conclusion:** The timestep-resolution concern is resolved by v4. The v3
grid-resolution limitation was real but does not affect the v4 outcomes.

### 2. Convergence study — timestep does NOT change basin boundaries

`tables/f2_convergence.csv`, 14 starts × 7 substeps = 98 runs.
**Every start gives the same outcome at all 7 substep values:**

| start D/T | outcome (all 7 substeps) | final D/T |
|---:|---|---|
| 0.90 | RAIL_MIN (k=0 basin) | 0.680 |
| 0.95 | RAIL_MIN | 0.680 |
| 0.98 | RAIL_MIN | 0.680 |
| 0.99 | RAIL_MIN | 0.680 |
| 1.00 | RAIL_MIN | 0.680 |
| 1.01 | RAIL_MIN | 0.680 |
| 1.02 | RAIL_MIN | 0.680 |
| 1.05 | 1T_LOCK (above → sub-1T excursion → recover) | 0.999 |
| 1.10 | 1T_LOCK (from above) | 1.001 |
| 1.20 | 1T_LOCK (from above) | 1.001 |
| 1.30 | 1T_LOCK (from above) | 1.001 |
| 1.50 | 1T_LOCK (from above) | 1.001 |
| 1.80 | 1T_LOCK (from above) | 1.001 |
| 1.95 | 1T_LOCK (from above) | 1.001 |

**Lock times** (1000 substeps; within the ≤100-cycle typical / ≤400-cycle max
spec for all successful locks):

| start | 1.05T | 1.10T | 1.20T | 1.30T | 1.50T | 1.80T | 1.95T |
|---:|---:|---:|---:|---:|---:|---:|---:|
| lock cycle | 6 | 1 | 21 | 27 | 32 | 35 | 36 |

Plots: `plots/f2_convergence.png`, `plots/f2_outcome_map.png`.

**Basin boundary:** between 1.02T and 1.05T at 100 MHz, band 1, Icp=300 µA.
This boundary is **identical** from 50 to 5000 substeps. No timestep artifact
in the basin boundary or the 1T lock result.

Two cases (1.50T/200 substeps, 1.95T/2000 substeps) were labeled
"sub-1T excursion" instead of "from above" only because of a 0.001-unit
difference in the final value (0.999 vs 1.001) at the classification threshold.
Both are 1T locks with settled peak-to-peak = 0.00000 — a label sensitivity,
not an outcome change.

### 3. Parameter sweeps

`tables/f3_icp_sweep.csv`, `f3_reset_sweep.csv`, `f3_dead_sweep.csv`,
`f3_full_factorial.csv`; plot `plots/f3_icp_sweep.png`.

**Icp (µA):**

| start | 50 | 100 | 150 | 300 |
|---:|---|---|---|---|
| 0.99T | RAIL | RAIL | RAIL | RAIL |
| 1.01T | **1T LOCK** | RAIL | RAIL | RAIL |
| 1.05T | 1T | 1T | 1T | 1T (dips below, recovers) |
| 1.10–1.95T | 1T | 1T | 1T | 1T |

Lower Icp widens the basin slightly downward (1.01T locks at 50 µA) because
the first-correction overshoot is smaller. It does not change the fundamental
one-sided character: starting well below 1T always rails.

**Reset delay (0/5/10/25 ps):** no effect on the basin; only at 1.05T with
reset=0 does the loop rail (zero reset delay removes charge integration).
Otherwise all four values give the same outcome.

**Dead time (0/5/10/25 ps):** no effect on any tested outcome.

**Full factorial** (2 starts × 4 Icp × 4 reset × 4 dead, 128 runs):
at start=1.30T, all 128 combinations lock at 1T. At start=1.01T, only
the lowest-Icp cases lock; the rest rail. No oscillation observed anywhere.

### 4. Outcome classification (requirement 7) — explicit distinctions

| Category | Observed? | Evidence |
|---|---|---|
| Starting below 1T → converges to 1T | **NO** | 0.90–0.99T all rail to 0.68T |
| Starting above 1T → converges to 1T | **YES** | 1.10–1.95T, all substeps |
| Starting above 1T → dips below 1T → recovers | **YES** | 1.05T: 1.05→0.974→1.001 |
| Lock at 0T / min rail | **YES** | starts ≤1.02T |
| Lock at 2T or higher harmonic | **YES (earlier studies)** | 25 MHz max-delay → 2T; D0=2.5T → 2T |
| Rail saturation | **YES** | u=1.000, D=0.68T |
| Oscillation | **NO** | settled_pp ≤ 0.00001 in all locking runs |
| Numerical timestep artifact | **NO** | identical outcomes 50–5000 substeps |

**Correction to earlier wording:** The claim in `review/report.md` that
"the true basin extends somewhat below kT" and that in-flight DOWN pulses
"widen the basin below 1T" is **withdrawn**. The v2 engine used in that
evidence latched delay at edge launch (`d_now = line_delay(u)` scheduled at
launch), so it could not propagate in-flight delay changes correctly; its
negative-Q observation was an artifact of that approximation and the `n_skip`
steady-state window. The v4 exact-event engine shows unambiguously:
**starting below 1T never converges to 1T.** A trajectory that *starts above*
1T may dip below and recover — that is a transient excursion, not a basin
extension below 1T. The earlier report text is preserved with this correction.

### 5. Feedback edge propagation verification — PASS

`tables/f4_event_trace_1p35.csv`:

- 5 reference edges launched in 5 cycles; 4 completed and 1 still in flight
  at the final sample — **balance = 0**, no lost edges.
- Reference edge at t=T correctly ignored (UP already asserted) — one ignored
  ref, zero ignored fb.
- Reset occurs exactly 5.000 ps after both UP and DOWN are asserted.
- UP pulse width = time from assertion to DOWN (actual event time), not
  quantized to grid; charge computed from that exact duration minus t_dead.
- Delay changes while edges are in flight are handled by advancing each edge's
  stage progress with the current stage delay at every exact event interval.

### 6. 1.3T preset feasibility

See `preset_feasibility.md`. Summary: a 1.3T preset is **not trivially
generable** without period information. The most implementable candidate is
cycle-counting coarse acquisition (count reference edges between feedback
edges; if k≥2, reduce delay until k=1, then switch to normal PFD). No
architecture change applied.

### 7. Strongest honest conclusion

**Proven mathematically (Level A):**
- Frozen PFD transfer: `Q(D) = Icp·frac(D/T)·T ≥ 0`; zeros at every integer kT.
- Error recurrence near kT from above: `e[n+1] = (1−g)e[n]`, `g = Icp·|dD/du|/(C·VDD)`.
  For `0 < g < 2`, kT is attracting from above.
- With correct CP polarity (UP raises VCTRL, current-starved delay falls), a
  DLL with a two-latch PFD has a stable 1T equilibrium. Frequency integration
  is **not** required — the earlier claim is withdrawn.
- The `D_min < T/2 → acquisition impossible` claim is withdrawn; no T/2 term
  exists in the derivation.

**Demonstrated behaviorally (Level B):**
- Correct-polarity event engine: 1T lock from starts in (1.02T, 1.95T).
- Exact-event engine: identical basin at 50–5000 substeps; no lost edges;
  exact reset timing; charge from true pulse durations.
- Starting below 1T rails to minimum at every tested substep and parameter set.
- 1T acquisition is possible but **basin-limited**; harmonic locks (2T/3T)
  occur for other startup delays.

**Remains unverified:**
- Transistor-level CP polarity and dead-zone behavior (Phase 3).
- PVT corner effects on the basin boundary.
- Mismatch, charge injection, leakage, supply noise.
- Any post-layout result (Level D, out of scope).
- The proposed cycle-counting acquisition mechanism (not designed/verified).

**Startup architecture necessary for a defensible proposal:**
1. Initial state = maximum delay (not minimum).
2. Basin detector (edge-counting) to determine k before fine acquisition.
3. Coarse correction path to move from k≥2 into k=1.
4. Fine PFD with verified polarity.
5. Lock detector verifying `D ≈ T`, distinguishing 1T from harmonics.
None applied — all require user approval.

---

## STATUS

| Item | Status |
|---|---|
| v4 timestep/event audit | **PASS** |
| Edge accounting (no lost edges) | **PASS** |
| Reset timing (5 ps exact) | **PASS** |
| Charge from actual pulse duration | **PASS** |
| Timestep independence of basin (50–5000) | **PASS** |
| 1T acquisition possible (Level B) | **PASS** — from above, basin (1.02T, 1.95T) |
| Starting below 1T → 1T | **FAIL** — rails at every setting |
| Official minimum-delay startup | **FAIL** — 0/14 starts lock 1T |
| "Basin extends below 1T" (earlier claim) | **WITHDRAWN** — v2 artifact |
| 1.3T preset without period knowledge | **UNVERIFIED** — proposal only |
| Transistor-level validity | **UNVERIFIED** — out of scope |

---

## ISSUES

1. The earlier `review/report.md` and `derivation.md` contain the now-withdrawn
   "basin extends below 1T" claim. They are preserved; this report supersedes
   that specific wording. The banner in `../report.md` already flags the
   earlier conclusion as under review.
2. The official architecture's minimum-delay forcing is incompatible with the
   1T basin. Any correction requires user approval; **none applied**.
3. The 1T basin boundary (1.02T–1.05T at 100 MHz) is a single-corner,
   single-frequency Level B result. PVT margin is unknown.
4. Band-0 Icp sensitivity observed earlier (25 MHz) is a separate gain issue
   noted in `review/report.md`, not re-examined here (scope: 100 MHz).
5. Earlier unfavourable results preserved and relabelled, not erased.

---

## NEXT STEP

Your decision before any other work:

- **(a)** approve a proposal to replace minimum-delay forcing with a
  cycle-counting coarse-acquisition mechanism (architecture change — not applied);
- **(b)** approve a harmonic-checking lock detector verifying `D ≈ T`
  (architecture change — not applied);
- **(c)** keep the architecture unchanged and record the basin limitation and
  0/14 min-delay acquisition as explicit proposal risks;
- **(d)** authorize Phase 3 transistor-level verification of CP polarity and
  dead-zone behavior before treating any Level B result as silicon-feasible.

No Problem 2 work started. Stopping here for your review.
