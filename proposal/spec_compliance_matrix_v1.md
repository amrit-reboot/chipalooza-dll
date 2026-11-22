# Baseline Specification Compliance Matrix v1

## 1. Purpose and scope

This matrix maps every baseline specification in `AGENTS.md` Sections 3 and 4 to the evidence currently available in the repository. It is a documentation artifact for submission preparation only. No simulation was run and no baseline target was changed.

Status categories are limited to those allowed in `AGENTS.md`: **PASS**, **WITHIN 20%**, **FAIL**, **UNVERIFIED**, **ESTIMATE**, **NOT APPLICABLE**.

Evidence levels follow `AGENTS.md`: **A** analytical, **B** behavioral/model, **C** Sky130 transistor-level, **D** post-layout/extracted. Where no evidence exists, the required level is identified but no A-D evidence is claimed.

No estimate or behavioral result is marked as transistor-level or physical-design compliance.

---

## 2. Baseline operating conditions and interface

| Specification | Target | Available evidence | Evidence level (A/B/C/D) | Status | Source file | Limitation/next action |
|---|---|---|---|---|---|---|
| Supply voltage | 1.62 V minimum, 1.80 V typical, 1.98 V maximum | Proposal states target only; no transistor supply sweep | None; Level C required | UNVERIFIED | `AGENTS.md:86`; `proposal/proposal_v0.4.md:52` | Characterize delay cell and full loop at all three supplies with Sky130 models. |
| Temperature | -40 C minimum, 27 C typical, +110 C maximum | Proposal states target only; no transistor temperature sweep | None; Level C required | UNVERIFIED | `AGENTS.md:87`; `proposal/proposal_v0.4.md:53` | Run Sky130 PVT temperature sweep. |
| Process corners | TT, SS, FF, SF, FS | No Sky130 model files or corner simulations exist | None; Level C required | UNVERIFIED | `AGENTS.md:89-95`; `proposal/proposal_v0.4.md:54`; `results/environment_report.md:89-113` | Enable Sky130 PDK and verify exact model section names before simulation. |
| Input clock frequency | 25 MHz to 200 MHz | Behavioral frequency sweep at 5 MHz steps, 36/36 points; acquisition studies at 7 sampled frequencies | B | UNVERIFIED | `AGENTS.md:101`; `results/tables/frequency_sweep.csv`; `results/pfd_validation/acquisition_controller/run_summary.json` | Behavioral continuity does not establish physical or PVT-verified coverage. Test real circuit across range and band edges. |
| Input clock duty cycle | 30 percent to 70 percent | Behavioral duty-correction model at 30, 50, and 70 percent; 50-sample MC per point | B | UNVERIFIED | `AGENTS.md:102`; `results/tables/duty_correction.csv`; `proposal/proposal_v0.4.md:55,267` | Verify with transistor input buffer, real phase skew, output load, supply, and temperature. |
| Input edge time | 1 ns or less | No input buffer or pad model simulated | None; Level C required | UNVERIFIED | `AGENTS.md:103`; `proposal/proposal_v0.4.md:56` | Define source edge rate and simulate input/pad behavior. |
| Frequency band 0 | 25 MHz to 60 MHz | Planning band in behavioral model; sampled points only | B | UNVERIFIED | `AGENTS.md:104`; `proposal/proposal_v0.4.md:57`; `results/tables/frequency_sweep.csv` | Physical band implementation and band-selection policy remain unresolved. |
| Frequency band 1 | 50 MHz to 120 MHz | Planning band in behavioral model; sampled points only | B | UNVERIFIED | `AGENTS.md:105`; `proposal/proposal_v0.4.md:58`; `results/tables/frequency_sweep.csv` | Physical band implementation and band-selection policy remain unresolved. |
| Frequency band 2 | 100 MHz to 200 MHz | Planning band in behavioral model; sampled points only | B | UNVERIFIED | `AGENTS.md:106`; `proposal/proposal_v0.4.md:59`; `results/tables/frequency_sweep.csv` | Physical 200 MHz delay/buffer feasibility remains unverified. |
| Bands overlap intentionally | 25-60, 50-120, and 100-200 MHz overlap | Proposal discusses overlap and states no selection policy is established | A/B documentation | UNVERIFIED | `AGENTS.md:108`; `proposal/proposal_v0.4.md:75` | Define overlap-region selection policy or state no automatic selection is implemented. |
| Baseline input signals | `CLK_IN`, `RANGE[1:0]`, `CP_CUR`, `TAP_SEL[2:0]`, `MON_DIV[1:0]`, reset/startup control | Signal inventory reconciled in proposal documentation; no RTL, schematic, pad map, or harness mapping | A/B documentation | UNVERIFIED | `AGENTS.md:42-48`; `proposal/proposal_v0.4.md:188-210`; `proposal/architecture_decisions_v0.1.md:52` | Resolve aliases, widths, polarity, electrical characteristics, and official pin budget. |
| Intended output signals | `PHASE[0:7]`, `CLK50`, `TAP_MON`, `VCTRL_MON`, `LOCK`, `VC_LOW`, `VC_HIGH` | Signal inventory reconciled in proposal documentation; no implemented circuit outputs | A/B documentation | UNVERIFIED | `AGENTS.md:56-72`; `proposal/proposal_v0.4.md:188-210`; `proposal/architecture_decisions_v0.1.md:52` | Implement and verify all baseline outputs; do not omit `PHASE[0:7]`. |
| Topology verification requirement | Precise feedback topology, PFD implementation, startup sequence, and duty-corrector circuit must be verified before being finalized | Conceptual architecture and behavioral models only; hardware blocks not implemented | B | UNVERIFIED | `AGENTS.md:74`; `proposal/proposal_v0.4.md:83-104,297-303` | Verify each block with Sky130 transistor-level simulation before finalizing. |

---

## 3. DLL performance specifications

| Specification | Target | Available evidence | Evidence level (A/B/C/D) | Status | Source file | Limitation/next action |
|---|---|---|---|---|---|---|
| Lock time, typical | 100 cycles | At 200 uA behavioral target: median effective lock 26 cycles in tested Phase 4 sweep | B | UNVERIFIED | `AGENTS.md:114`; `results/pfd_validation/acquisition_robustness/lock_time.csv`; `proposal/proposal_v0.4.md:65,273-277` | Behavioral result only; no hardware lock indication or transistor loop. |
| Lock time, maximum/required limit | 400 cycles | At 200 uA: max 158 cycles; global matrix worst 197 cycles at 200 MHz and 150 uA | B | UNVERIFIED | `AGENTS.md:114`; `results/pfd_validation/acquisition_robustness/lock_time.csv`; `proposal/proposal_v0.4.md:280-293` | `lock_time.csv` is authoritative; `current_sweep.csv` has five median summary discrepancies. Physical timing remains unverified. |
| Static phase error, typical | +/-2 percent of T | Behavioral sweep static error 0.003 to 0.039 percent T; midpoint results 0.007 to 0.029 percent T | B | UNVERIFIED | `AGENTS.md:115`; `results/tables/frequency_sweep.csv`; `results/tables/lock_band_midpoints.csv` | Behavioral dead-zone result is not silicon evidence. |
| Static phase error, maximum/required limit | +/-5 percent of T | Same behavioral sweep; no transistor phase error | B | UNVERIFIED | `AGENTS.md:115`; `proposal/proposal_v0.4.md:66` | Measure phase error after lock with real devices, mismatch, load, and PVT. |
| Tap spacing DNL, typical | +/-8 percent of T/8 | 30-sample behavioral MC with assumed 1 percent per-stage sigma; mean worst-tap DNL 1.43 percent T/8 | B/ASSUMED | UNVERIFIED | `AGENTS.md:116`; `scripts/run_behavioral.py:199-239`; `proposal/proposal_v0.4.md:67,266` | Assumption is not Sky130 mismatch data. |
| Tap spacing DNL, maximum/required limit | +/-15 percent of T/8, post-layout MC 3-sigma | Behavioral 99.7th percentile 2.63 percent T/8 from 30 samples | B/ASSUMED | UNVERIFIED | `AGENTS.md:116,125`; `results/behavioral_dll.md`; `proposal/proposal_v0.4.md:67,266` | A 30-sample 99.7th percentile is descriptive only, not 3-sigma yield evidence. Post-layout MC required. |
| CLK50 duty cycle, typical | 50 percent | Behavioral corrected mean 49.96 to 49.99 percent for 30/50/70 percent input | B | UNVERIFIED | `AGENTS.md:117`; `results/tables/duty_correction.csv`; `proposal/proposal_v0.4.md:68,267` | Assumes even inversion count and ideal timing. |
| CLK50 duty cycle, allowed range | 45 percent to 55 percent | Same behavioral data | B | UNVERIFIED | `AGENTS.md:117`; `proposal/proposal_v0.4.md:68,267` | Verify across corners, load, phase skew, and real duty-corrector circuit. |
| Period jitter at 100 MHz, typical | 25 ps RMS | Analytical supply-noise model; 25 ps corresponds to S <= 0.159099 at 20 mVrms | A | ESTIMATE | `AGENTS.md:118`; `results/tables/jitter_sensitivity.csv`; `scripts/dll_model.py` | Not a noise simulation or measurement. S is assumed/unmeasured. |
| Period jitter at 100 MHz, maximum | 60 ps RMS | Analytical supply-noise model; 60 ps corresponds to S <= 0.381838 at 20 mVrms | A | ESTIMATE | `AGENTS.md:118`; `results/tables/jitter_sensitivity.csv`; `proposal/proposal_v0.4.md:69,255,319` | Verify ngspice noise capability and measure supply sensitivity with real devices. |
| Supply current at 100 MHz, typical | 1 mA | Rough analytical estimate 0.1 to 0.5 mA; 8-stage dynamic term 43.2 uA from assumed 30 fF/stage | A/ASSUMED | ESTIMATE | `AGENTS.md:119`; `results/behavioral_dll.md`; `proposal/proposal_v0.4.md:70,256,320` | No transistor operating-point or transient current exists. |
| Supply current at 200 MHz, maximum | 2 mA | No measured or simulated circuit current | A/ASSUMED | ESTIMATE | `AGENTS.md:120`; `proposal/proposal_v0.4.md:70,320` | Measure after transistor design; present value is not compliance evidence. |
| Phase output load | At least 100 fF each | No output buffer or load simulation | None; Level C required | UNVERIFIED | `AGENTS.md:121`; `proposal/proposal_v0.4.md:71,324` | Design buffers and simulate each phase with 100 fF load. |
| False locks, typical | 0 | No false LOCK assertions observed in tested Level B controller scenarios | B | UNVERIFIED | `AGENTS.md:122`; `acquisition_controller/acquisition_results.csv`; `acquisition_robustness/lock_time.csv` | Scoped observation only; not a hardware false-lock rate. |
| False locks, required in startup tests | 0 in startup tests | No hardware lock detector implemented; old 55/55 startup claim withdrawn | B/documentation | UNVERIFIED | `AGENTS.md:122`; `results/behavioral_dll.md`; `proposal/proposal_v0.4.md:72,295,314` | Implement observable-signal lock detector and test true 1T, harmonic, rail, and coincident-edge cases. |
| Area | 0.05 mm2 or less | No sizing, layout, or credible area estimate | None; Level D required | UNVERIFIED | `AGENTS.md:123`; `proposal/proposal_v0.4.md:73,321` | Produce device-area estimate then layout area after design exists. |

---

## 4. Delay requirement

| Specification | Target | Available evidence | Evidence level (A/B/C/D) | Status | Source file | Limitation/next action |
|---|---|---|---|---|---|---|
| Stage delay equation | `t_stage = T/8 = 1/(8f)` | Level A derivation used throughout proposal | A | ESTIMATE | `AGENTS.md:127-133`; `proposal/proposal_v0.4.md:62,257` | Correct analytical requirement; physical achievability must be measured. |
| Required stage delay at 25 MHz | 5 ns | Level A derivation from `1/(8f)` | A | ESTIMATE | `AGENTS.md:137`; `proposal/proposal_v0.4.md:62` | Measure actual delay with Sky130 cell. |
| Required stage delay at 40 MHz | 3.125 ns | Level A derivation from `1/(8f)` | A | ESTIMATE | `AGENTS.md:138`; `proposal/proposal_v0.4.md:62` | Measure actual delay with Sky130 cell. |
| Required stage delay at 50 MHz | 2.5 ns | Level A derivation from `1/(8f)` | A | ESTIMATE | `AGENTS.md:139`; `proposal/proposal_v0.4.md:62` | Measure actual delay with Sky130 cell. |
| Required stage delay at 60 MHz | 2.083 ns | Level A derivation; exact value 2.08333 ns | A | ESTIMATE | `AGENTS.md:140`; `proposal/proposal_v0.4.md:62` | Measure actual delay with Sky130 cell. |
| Required stage delay at 100 MHz | 1.25 ns | Level A derivation from `1/(8f)` | A | ESTIMATE | `AGENTS.md:141`; `proposal/proposal_v0.4.md:62` | Measure actual delay with Sky130 cell. |
| Required stage delay at 120 MHz | 1.042 ns | Level A derivation; exact value 1.04167 ns | A | ESTIMATE | `AGENTS.md:142`; `proposal/proposal_v0.4.md:62` | Measure actual delay with Sky130 cell. |
| Required stage delay at 200 MHz | 625 ps | Level A derivation from `1/(8f)` | A | ESTIMATE | `AGENTS.md:143`; `proposal/proposal_v0.4.md:62` | Measure actual delay with Sky130 cell; this is the most severe upper-frequency risk. |
| Initial corner allowance | Approximately +/-30 to 40 percent, planning estimate only | No transistor corner data | A/ASSUMED | ESTIMATE | `AGENTS.md:145`; `proposal/proposal_v0.4.md:62` | Do not convert planning allowance into a verified range. |
| Actual delay range measurement | Must be measured from transistor-level simulation | No Sky130 cell, schematic, netlist, or simulation result | None; Level C required | UNVERIFIED | `AGENTS.md:147`; `results/environment_report.md:130-136,295-311` | Enable Level C flow and characterize delay versus VCTRL, supply, temperature, and corners. |

---

## 5. Summary

- No baseline specification is marked **PASS** on the basis of a behavioral or analytical result.
- All physical feasibility items that require Sky130 transistors, PVT, post-layout extraction, hardware lock detection, or layout area remain **UNVERIFIED**.
- Analytical stage-delay, jitter, current, and corner-allowance values are marked **ESTIMATE**, not PASS.
- The only substantive proposal text changes made in v0.4 were scoped evidence corrections and official-interface clarification; no target or numerical result was changed.
