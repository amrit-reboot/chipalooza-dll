# Proposal v1 Submission: 8-Phase Delay-Locked Loop for Chipalooza Challenge #4

## 1. Project Title

**Eight-Phase Delay-Locked Loop With Cycle-Counting Coarse Acquisition for Sky130 SoCs**

| Field | Value |
|---|---|
| Document status | Final submission proposal v1. Prepared from v0.4 with targeted submission-specific documentation corrections. No architecture, baseline, or numerical-result changes |
| Date | 2026-11-22 |
| Submission type | Individual designer. Designer details are provided in the separate CV attachment |
| IP type | Analog and mixed-signal eight-phase DLL IP block for SoC timing, pre-layout proposal |
| Evidence level | Level A analytical and Level B behavioral only |
| Circuit evidence | No Level C transistor-level or Level D post-layout result |
| Baseline specifications | Preserved from `AGENTS.md`; no target relaxed in this revision |
| Architecture authority | `proposal/architecture_decisions_v0.1.md`, decisions D1 through D8 |

---

## 2. Abstract

The proposed block is an analog and mixed-signal eight-phase delay-locked loop (DLL). It accepts a 25 MHz to 200 MHz reference clock and generates eight nominally 45 degree spaced phase taps plus a duty-cycle-corrected clock. The intended use is SoC timing alignment where multiple phases of the same clock are needed without frequency synthesis.

The provisional architecture uses an eight-stage fine delay line, a phase-frequency detector (PFD), a charge pump, a loop capacitor, and a proposed coarse acquisition subsystem. The main acquisition problem is basin selection. A two-latch PFD cannot distinguish an aligned total line delay of `T` from `2T` or `3T`, and the Level B behavioral model shows that a minimum-delay start rails instead of reaching the desired 1T equilibrium under the tested conditions.

The proposal therefore adopts cycle-counting coarse acquisition as the provisional direction. A controller measures `k = floor(D/T)` from observable reference and feedback edges and steers the coarse delay toward the `k = 1` region. This count is a coarse classification only. It does not guarantee that the fine loop is inside its acquisition basin. The strongest evidence is Level B behavioral evidence from an event-driven PFD model tested under the reported behavioral conditions and from controller sweeps. No transistor-level, Sky130, extracted, or silicon result is claimed.

---

## 3. Motivation and Applications

An eight-phase DLL creates eight time-interleaved versions of a reference clock. With a 1T locked delay line, adjacent taps are separated by `T/8`, which is 45 degrees of the reference period. The block is useful for:

- multiphase clock generation for digital and mixed-signal blocks;
- timing alignment and deskew at the block or chip level;
- interleaved sampling systems that need staggered sampling edges;
- ADC timing, including sample-and-hold or comparator phase distribution;
- clock distribution where several local phases reduce routing sensitivity;
- interface timing where transmit, receive, or sampling edges must be placed within a clock period.

A DLL delays and aligns clock phases. It does not frequency-multiply like a phase-locked loop (PLL). If a new output frequency is required, a PLL or another synthesis architecture is needed.

The critical design question is not whether the fine loop has a 1T equilibrium. Analytical and behavioral work indicates that it does with correct PFD and charge-pump polarity. The difficult questions are whether the startup sequence reliably reaches the 1T basin, whether the physical delay cell covers the required range, and whether the phase, jitter, power, and area targets can be met in Sky130.

---

## 4. Functional Specifications

The following targets are the existing project baseline from `AGENTS.md`. They remain the proposal targets even where current evidence is incomplete. Status labels distinguish proposed targets from analytical estimates, behavioral evidence, and unverified items.

| Parameter | Target | Status | Basis and limitation |
|---|---|---|---|
| Reference frequency | 25 MHz to 200 MHz | Proposed target; Level B behavioral evidence at 7 acquisition frequencies and 36 frequency sweep points; Unverified across all intermediate frequencies | Seven frequencies were tested in acquisition sweeps and 36 points were tested in the 5 MHz behavioral sweep. Continuous physical coverage is not established. |
| Supply voltage | 1.62 V minimum, 1.80 V typical, 1.98 V maximum | Proposed target; Unverified | No transistor-level supply sweep has been performed. |
| Temperature | -40 C, 27 C, +110 C | Proposed target; Unverified | No transistor-level temperature sweep has been performed. |
| Process corners | TT, SS, FF, SF, FS | Proposed target; Unverified | No Sky130 corner models have been used. |
| Input clock duty cycle | 30 percent to 70 percent | Proposed target; Level B behavioral evidence; Unverified in circuits | Duty correction was tested in a behavioral model only. |
| Input edge time | 1 ns or less | Proposed target; Unverified | No input buffer or pad model has been simulated. |
| Frequency band 0 | 25 MHz to 60 MHz | Proposed target; Level B behavioral evidence at sampled points; Unverified physically | Planning band used in behavioral model. |
| Frequency band 1 | 50 MHz to 120 MHz | Proposed target; Level B behavioral evidence at sampled points; Unverified physically | Planning band used in behavioral model. |
| Frequency band 2 | 100 MHz to 200 MHz | Proposed target; Level B behavioral evidence at sampled points; Unverified physically | Planning band used in behavioral model. |
| Number of phases | 8 | Proposed target; Level B behavioral evidence | Eight taps exist in the behavioral model. No transistor delay line has been built. |
| Phase spacing | Nominal 45 degrees at 1T lock | Proposed target; Level B behavioral evidence; Unverified physically | Tap spacing depends on real device mismatch and layout. |
| Derived stage delay | 5 ns at 25 MHz, 3.125 ns at 40 MHz, 2.5 ns at 50 MHz, 2.083 ns at 60 MHz, 1.25 ns at 100 MHz, 1.042 ns at 120 MHz, 625 ps at 200 MHz | Level A derivation; Unverified physically | Calculated as `T/8`. Physical delay-cell range is the largest open risk. |
| Charge pump current | 200 uA behavioral target | Proposed design target; Level B behavioral evidence | Best fixed current in the tested behavioral robustness sweep. Not a finalized transistor current. |
| Fine loop capacitor | 25 pF behavioral model value | Level B model condition; proposed study value | Used in the reported behavioral sweeps. Not selected from transistor-level noise or area data. |
| Lock behavior | 1T DLL lock; 100 cycles typical, 400 cycles maximum | Proposed target; Level B behavioral evidence for cycle counts; Unverified hardware lock indication | At 200 uA, detected lock time was median 26 cycles and maximum 158 cycles in the tested sweep. |
| Static phase error | 2 percent of T typical, 5 percent of T maximum | Proposed target; Level B behavioral evidence only; Unverified physically | Behavioral floor is a dead-zone artifact, not silicon evidence. |
| Tap-spacing DNL | 8 percent of T/8 typical, 15 percent of T/8 maximum | Proposed target; Level B behavioral evidence with assumed mismatch; Unverified | Requires real Sky130 mismatch and post-layout Monte Carlo for a compliance claim. |
| CLK50 duty cycle | 50 percent target, 45 percent to 55 percent allowed | Proposed target; Level B behavioral evidence; Unverified physically | Behavioral duty correction used ideal timing and an even-inversion assumption. |
| Period jitter at 100 MHz | 25 ps RMS typical, 60 ps RMS maximum | Proposed target; Level A estimate; Unverified | Supply sensitivity dominates the estimate. No ngspice noise simulation exists. |
| Supply current | 1 mA typical at 100 MHz, 2 mA maximum at 200 MHz | Proposed target; Level A estimate; Unverified | Rough analytical estimate only. No transistor operating-point or transient current exists. |
| Phase output load | 100 fF or more per phase | Proposed target; Unverified | Output buffers are not designed. |
| False locks | 0 in startup tests | Proposed target; limited Level B behavioral observation; hardware lock detector not implemented | Limited Level B behavioral observation: no false LOCK assertions were observed in the tested controller scenarios. This does not establish a zero false-lock rate or validate a hardware lock detector. Unaided fine-loop sweeps did show harmonic settles. |
| Area | 0.05 mm2 or less | Proposed target; Unverified | No sizing, layout, or credible area estimate exists. |

The three proposed bands overlap: 25 MHz to 60 MHz, 50 MHz to 120 MHz, and 100 MHz to 200 MHz. These ranges are provisional. Overlap may provide placement flexibility, but no band-selection policy is established. Selection in overlap regions, automatic versus externally selected band operation, wrong-band behavior in hardware, and physical band implementation remain unresolved or unverified. No selection algorithm is proposed here.

No ESTIMATE or UNVERIFIED item in this table is converted into a pass.

Where the baseline provides minimum, typical, and maximum values, this section preserves them. Absolute limits are the maximum or required-limit values for lock time, phase error, tap DNL, jitter, supply current, output load, false locks, and area. Where the baseline gives no average value, no average is invented.

### 4.1 Evidence status separation

| Category | Meaning in this proposal | Examples |
|---|---|---|
| Target specifications | Baseline goals retained from `AGENTS.md`. These are not claims of achievement | 25 MHz to 200 MHz, 100 cycle typical lock, 60 ps maximum jitter, 0.05 mm2 area |
| Analytically estimated performance | Calculations based on stated assumptions. No circuit measurement is implied | Stage delay `T/8`, 25 ps and 60 ps supply sensitivity limits, 0.1 mA to 0.5 mA current estimate |
| Behaviorally demonstrated results | Results from Python event driven and behavioral models under tested conditions only | 406 run controller study, 728 run robustness sweep, 91/91 acquisitions at 200 uA, median 26 and maximum 158 cycles |
| Unverified claims | Items that require Sky130 transistor, post layout, or hardware evidence | Hardware lock detector, physical delay range, PVT coverage, output load drive, jitter and power compliance, area |
| Future implementation goals | Work required after proposal acceptance | Toolchain enablement, delay cell characterization, transistor loop validation, layout, DRC, LVS, extracted Monte Carlo |

---

## 5. Proposed Architecture

This section describes the intended architecture, not a completed transistor implementation. No block in this proposal has a Sky130 transistor-level schematic in the current repository.

1. **Reference input.** The functional input is `CLK_IN`, retained from the baseline. Acquisition reports may call the same signal `REF_CLK`. The proposal uses `CLK_IN` as the baseline name and treats `REF_CLK` as an alias only.

2. **Phase-frequency detector.** A two-latch PFD compares the reference with the last delay-line tap. **Status:** existing Level B event-driven model. Transistor-level PFD polarity, reset behavior, and dead zone are not implemented or verified.

3. **Charge pump.** The charge pump converts PFD UP and DOWN pulses into loop-capacitor charge. The behavioral operating point is `Icp = 200 uA`. **Status:** existing Level B model and proposed design target. A transistor-level charge pump is not implemented.

4. **Fine delay control.** The loop capacitor voltage controls the fine delay stages. The behavioral model assumes a monotonic control law and a 25 pF capacitor. **Status:** existing Level B model. Control sensitivity `Kd` is unmeasured.

5. **Delay chain.** Eight current-starved stages produce a total delay near `T` and eight taps near 45 degree spacing. Switchable capacitive loads and matched dummy loads are part of the intended baseline concept. **Status:** studied concept and behavioral model. No transistor delay cell has been simulated.

6. **Feedback path.** The last tap feeds the PFD. The same edge is proposed as an observable for coarse acquisition. **Status:** existing in the behavioral model. Real synchronizers and input behavior are not designed.

7. **Eight phase taps.** `PHASE[0:7]` are functional outputs. **Status:** behavioral model only. Output buffers and load drive are not designed.

8. **Duty-cycle correction.** The baseline concept uses phase 0 and phase 4 rising edges to generate alternating set and reset events for `CLK50`. **Status:** Level B behavioral model and proposed block. It depends on an even number of inversions per stage and has not been verified in circuits.

9. **Coarse acquisition subsystem.** This includes a cycle-counting controller, a coarse actuator, a fine-loop handoff whose qualification method remains open, observable lock qualification, and timeout handling. **Status:** behavioral controller prototype exists; hardware FSM, coarse actuator, and hardware lock detector are not implemented.

10. **Lock detector and status.** The future detector should qualify `D ≈ T` using observable signals such as edge count, PFD pulse qualification, selected tap relationships including phase 4, coarse code, supply-limit indicators, and timeout state. **Status:** proposed block. Simulator-only fields such as `final_ratio`, `harmonic_index`, and `settled_pp` are not hardware signals and must not be used as such.

### Proposed block diagram

Solid green blocks are existing Level B models. Dashed orange blocks are proposed or unimplemented hardware.

```mermaid
flowchart LR
    REF["Reference input<br/>CLK_IN"] --> PFD["PFD event model<br/>Level B"]
    PFD --> CP["Charge pump and C_loop model<br/>Level B"]
    CP --> CTRL["VCTRL node<br/>model only"]
    CTRL --> VCDL["Eight-stage delay model<br/>Level B"]
    VCDL --> PHASE["PHASE[0:7] and FB<br/>Level B"]
    PHASE --> PFD
    PHASE --> DCC["Duty corrector model<br/>Level B"]
    PHASE --> LOCKOBS["Observable tap and edge signals<br/>definition open"]

    BEHCTL["Cycle-counting controller prototype<br/>Level B"] -.tested in Level B model.-> PFD
    HWFSM["Hardware acquisition FSM<br/>not implemented"] --> ACT["DAC plus MUX coarse actuator<br/>candidate, not implemented"]
    SYNCH["Synchronizers and reset logic<br/>not implemented"] --> HWFSM
    ACT --> CTRL
    HWFSM -->|CP gate and handoff| CP
    LOCKDET["Hardware lock detector<br/>not implemented"] --> STATUS["LOCK, FAIL, TIMEOUT<br/>FAIL and TIMEOUT are proposed"]
    LOCKOBS --> LOCKDET
    HWFSM --> LOCKDET

    classDef existing fill:#e8f5e9,stroke:#2e7d32,stroke-width:1px;
    classDef proposed fill:#fff3e0,stroke:#ef6c00,stroke-width:1px,stroke-dasharray:5 5;
    class PFD,CP,CTRL,VCDL,PHASE,DCC,BEHCTL,LOCKOBS existing;
    class HWFSM,ACT,SYNCH,LOCKDET,STATUS proposed;
```

---

## 6. Acquisition Strategy

Minimum-delay startup is not retained as the preferred proposal architecture. The Level B PFD model tested under the stated conditions shows that starts below the lower 1T basin edge converge to the minimum-delay rail and do not recover to 1T. In the exact-event study, all tested starts from `0.90T` through `1.02T` ended at the rail, while starts from `1.05T` through `1.95T` locked at 100 MHz, band 1, and `Icp = 300 uA`. The old minimum-delay forcing mechanism is therefore kept only as historical baseline context, not as a claimed working acquisition method.

Cycle counting identifies a coarse delay region:

`k = floor(D/T)`

| Count | Condition | Coarse interpretation | Conceptual coarse action |
|---:|---|---|---|
| `k = 0` | `D < T` | Below one reference period; associated with the minimum-delay rail basin in the tested model | Increase delay and remeasure |
| `k = 1` | `T <= D < 2T` | One-reference-period coarse region only; not a fine-acquisition guarantee | Proceed to handoff qualification; do not hand off on the count alone |
| `k >= 2` | `D >= 2T` | Two or more reference periods; harmonic region | Decrease delay and remeasure |

The reported Level B fine-loop basin is approximately `1.02T` to `1.95T` at the tested 100 MHz, band 1, and `Icp = 300 uA` condition. The robustness study also showed that the fine-loop basin varies with frequency and charge-pump current. Therefore, `k = 1` alone is a coarse classification and **is not sufficient** to guarantee successful fine acquisition. The lower and upper handoff boundaries need guard bands. A guard-band strategy, additional measurement, calibrated coarse target, or other qualification method remains to be selected and validated. No guard-band values are proposed here. The reported basin is specific to the tested behavioral conditions and must not be generalized across frequencies, PVT corners, or physical circuits. Hardware acquisition success is not established.

The conceptual measurement sequence is not a finalized hardware algorithm:

1. Reset the PFD, controller, and charge-pump gating. Place the delay line toward a known coarse starting condition.
2. Hold the coarse and fine controls and allow the delay line to settle before measuring.
3. Define a measurement window using a start event and a stop event that remain to be selected. Select the reference and feedback edges associated with that window.
4. Derive the count from the observed edges. Treat the result as coarse information only.
5. If coarse adjustment is indicated, step the coarse actuator, flush the delay line of in-flight edges, allow it to settle, and remeasure.
6. Qualify the handoff using guard bands or another method to be selected. Do not enable the fine loop on `k = 1` alone.
7. Enable the fine PFD and charge pump only after handoff qualification. Assert LOCK only after observable-signal hardware lock validation confirms the 1T condition and rejects rail and harmonic states.
8. If step, attempt, or time limits are reached, report FAIL or TIMEOUT and keep LOCK deasserted.

The implementation definition remains open, including the measurement start event, measurement stop event, reference and feedback edge selection, synchronizer latency compensation, metastability handling, coincident-edge handling, exact boundary behavior at `D = T` and `D = 2T`, delay-line flushing after coarse-code changes, and measurement stability or qualification. This is a conceptual method pending hardware design and verification. No circuitry or timing values are specified here.

Conceptual state and control table. This table is proposed and unimplemented.

| State | Coarse actuator | Charge pump and fine loop | Delay-line flush or settling | Measurement | Lock qualification |
|---|---|---|---|---|---|
| Reset | Force or hold a known coarse condition | Disabled | Flush and settle before Measure | Disabled | Cleared |
| Measure | Hold | Disabled | Settled and unchanged | Enabled | LOCK not asserted |
| Coarse adjust | Step as indicated | Disabled | Flush after each code change and settle before remeasure | Disabled until settled | LOCK not asserted |
| Qualification | Hold | Disabled | Settled | Enabled or repeated as required | Evaluate handoff using a method not yet selected |
| Fine acquisition | Hold and isolate | Enabled | Settled | Disabled | Observe 1T evidence; LOCK not asserted until qualified |
| Locked | Hold | Enabled | Stable | Disabled | LOCK asserted by a future detector |
| Fail or timeout | Hold | Disabled | Settled or not applicable | Stopped | LOCK withheld; FAIL or TIMEOUT reported |

This table is a functional concept only. The electrical implementation of the DAC/MUX and `VCTRL` interaction, isolation, hold behavior, and handoff has not been designed. A DAC implementation is not proven or selected. Switched capacitive loads and a separate coarse delay section remain alternatives. A 4-bit coarse control is only an initial study point and is not claimed to be sufficient or optimal.

Known limitations carried forward are:

- no implemented coarse actuator or electrical handoff;
- no implemented hardware lock detector;
- no demonstrated hardware acquisition across PVT, mismatch, or frequency changes during operation.

---

## 7. Interface and Testability

The baseline functional interface remains the reference. Acquisition and debug signals are proposed additions requiring review. The signal inventory is a working proposal. It is not a finalized top-level declaration, pinout, or pad assignment. Names, widths, polarity, electrical characteristics, and pin allocation must be verified against the official challenge interface and harness.

### A. Functional interface, baseline reference

| Direction | Signal | Name reconciliation | Purpose |
|---|---|---|---|
| Input | `CLK_IN` | Also called `REF_CLK` in acquisition reports | Reference clock |
| Input | Reset and startup control | Proposed local name `RESET_N`; polarity and timing remain undefined | Known startup state |
| Input | `RANGE[1:0]` | Also called `BAND[1:0]` in acquisition reports | Frequency-band selection; policy in overlap regions remains unresolved |
| Input | `CP_CUR` | Baseline control input; `CP_CUR_CODE` is a provisional descriptive label only | Charge-pump current setting. Encoding remains undefined in the baseline; no width or encoding is finalized here |
| Input | `TAP_SEL[2:0]` | Also called `PHASE_SEL[2:0]` in earlier candidate material | Mux-control input that selects the monitored tap |
| Input | `MON_DIV[1:0]` | No alias | Divider setting for tap monitor path |
| Output | `PHASE[0:7]` | No alias | Eight phase outputs |
| Output | `CLK50` | No alias | Duty-cycle-corrected clock |
| Output | `TAP_MON` | Also called `PHASE_MON` in earlier candidate material | Selected phase tap for observation |
| Output | `VCTRL_MON` | No alias | Buffered control-voltage monitor |
| Output | `LOCK` | No alias | Baseline lock indication |
| Output | `VC_LOW` | No alias | Control voltage low-limit indicator |
| Output | `VC_HIGH` | No alias | Control voltage high-limit indicator |

The earlier candidate interface listed `PHASE_SEL[2:0]` as an output. That is corrected here. A tap selector is a mux-control input. `PHASE[0:7]`, `CP_CUR`, `MON_DIV[1:0]`, `VC_LOW`, and `VC_HIGH` are restored because they are part of the baseline interface.

### B. Configuration and control, proposed wrapper additions

| Direction | Signal | Status | Purpose |
|---|---|---|---|
| Input | `DLL_EN` | Proposed | Master enable and charge-pump gating |
| Input | `ACQ_EN` | Proposed | Enables coarse acquisition without changing functional phase outputs |
| Input | `COARSE_CODE[3:0]` | Proposed study interface | Four-bit coarse control; initial study point only |
| Input | `Icp code` | Proposed, encoding TBD | Provisional descriptive label for a charge-pump current selection; not a baseline pin |

The newly proposed wrapper and test signals in Sections 7B and 7C are not baseline pins. Section 7D contains two baseline monitors, `TAP_MON` and `VCTRL_MON`, plus proposed debug signals. No proposed signal is assigned to a pad, and no dedicated or low resistance pad request is made at this stage. The official FAQ asks proposals to list the I/O pins used and to state where pins may not be multiplexed; those determinations remain TBD until the harness wrapper and pin map are published.

### C. Status outputs, baseline and proposed

| Signal | Status | Purpose |
|---|---|---|
| `LOCK` | Baseline | Indicates qualified 1T lock after lock-detector implementation |
| `VC_LOW` | Baseline | Indicates low control-voltage limit |
| `VC_HIGH` | Baseline | Indicates high control-voltage limit |
| `FAIL` | Proposed addition | Acquisition attempt failed without valid lock |
| `TIMEOUT` | Proposed addition | Acquisition watchdog expired |

`FAIL` and `TIMEOUT` are not baseline requirements. Their polarity, timing, persistence, and recovery behavior are not finalized.

### D. Proposed monitor and test interface

| Signal | Status | Purpose |
|---|---|---|
| `TAP_MON` / `PHASE_MON` | Baseline monitor with naming reconciliation | Sequential tap observation; mux skew must be de-embedded |
| `VCTRL_MON` | Baseline monitor | Bring-up and loop-voltage observation |
| `ACQ_STATE` | Proposed, width TBD | Acquisition FSM state visibility |
| `ACQ_K` | Proposed, width TBD | Observed coarse count for debug only |
| `COARSE_CODE_MON[3:0]` | Proposed study monitor | Coarse-code observation; width follows D6 study point only |

Official Challenge #4 rules state that the harness uses a 1.8 V logic library with the standard Sky130 dual 1.8 V core and 3.3 V periphery pad library, and provide up to 24 digital controls, 12 digital test signals, 4 shared analog signal lines, and 3 dedicated pins per project; exceptions require approval. The same official rules state that slot size and I/O configuration are TBD and that the harness repository and wrapper template will be posted later. The 1.8 V signals brought to periphery pads would require overvoltage protection. The candidate signal inventory in this proposal has not been mapped to those limits or to specific pad types, no low-resistance or dedicated-pin request has been approved, and no pad assignment exists. Pin-budget and official-interface compliance are therefore UNVERIFIED. Shared analog buses should not be assumed suitable for high-frequency phase measurement.

---

## 8. Simulation and Verification Evidence

### Level A: analytical

- Loop gain and PFD charge scaling were derived for the behavioral model: `Q_cycle ≈ Icp * frac(D/T) * T`, with per-cycle gain dependent on delay sensitivity and loop capacitance.
- Analytical work establishes that the PFD transfer has zeros at integer multiples of `T`, and that the 1T equilibrium is attracting from above for the modeled polarity and loop gain range.
- Jitter sensitivity was estimated from `dT/T = S * dVDD/VDD` and a 20 mVrms supply-noise assumption. The 60 ps maximum requires `S` below approximately 0.382 in that estimate. The metric is period jitter RMS from a sqrt(2) edge-difference model with independent edge noise, not cycle-to-cycle jitter or ngspice noise output. This is not a measured cell sensitivity.
- Supply current was roughly estimated as 0.1 mA to 0.5 mA at 100 MHz using an assumed 30 fF per-stage load. This is not a circuit measurement.
- Required stage delay was calculated as `T/8`.

### Level B: behavioral

| Study | Scope | Main result within the tested model | Boundary |
|---|---|---|---|
| Final PFD validation | Exact-event engine, 50 to 5000 substeps per period | Within the behavioral engine: no lost edges; exact 5 ps reset timing; identical basin boundaries across timestep; 1T basin from roughly `1.02T` to `1.95T` at 100 MHz, band 1, `Icp = 300 uA` | Single frequency, current, and nominal PVT condition; basin varies with frequency and current |
| Phase 3 acquisition controller, `Icp = 300 uA` | 406 runs: main matrix, randomized, deterministic, boundary | Within the behavioral controller model: 239 total 1T acquisitions; 76/91 correct-band acquisitions; no false LOCK assertions observed | 25 MHz failed all correct-band cases at 300 uA; in the wrong-band main matrix, 52/182 cases reached 1T_LOCK and 130/182 failed in the behavioral model because modeled band delay ranges overlap; simulator-based classification only |
| Phase 4 fixed-current robustness sweep | 7 frequencies x 8 currents x 13 initial conditions = 728 controller runs | Within the behavioral model: fixed `Icp = 200 uA` achieved 91/91 correct-band acquisitions | Single PVT point; wrong-band cases from Phase 3 were not re-swept |
| Tap-spacing model | 30-sample behavioral Monte Carlo with assumed 1 percent per-stage delay sigma | Mean worst-tap DNL 1.43 percent of `T/8`; 99.7th percentile 2.63 percent of `T/8` | Assumption is not Sky130 mismatch data; 30 samples do not establish 3-sigma yield |
| Duty-cycle model | 50-sample behavioral Monte Carlo per input duty point | Corrected means: 49.99 percent at 30 percent input duty, 49.99 percent at 50 percent, and 49.96 percent at 70 percent | Assumes even inversion count and ideal timing |

CSV-checked Phase 4 numbers at `Icp = 200 uA`:

| Metric | Result from raw CSVs |
|---|---:|
| Successful correct-band acquisitions within the Level B model | 91/91 |
| Minimum effective lock cycles among successes | 7 |
| Median effective lock cycles among successes | 26 |
| Maximum effective lock cycles among successes | 158 |
| Cases at or below 100 cycles | 85/91 |
| Frequencies sampled | 25, 30, 50, 75, 100, 150, 200 MHz |

Source-of-truth note: `results/pfd_validation/acquisition_robustness/lock_time.csv` is authoritative for lock-time statistics. Five median discrepancies exist in `results/pfd_validation/acquisition_robustness/current_sweep.csv`: (25 MHz, 100 uA) 15.0 vs 14.5; (100 MHz, 50 uA) 117.0 vs 97.5; (150 MHz, 75 uA) 87.0 vs 80.0; (200 MHz, 125 uA) 57.0 vs 53.0; (200 MHz, 150 uA) 87.0 vs 65.0. The raw CSVs are unchanged. The 200 uA statistics and the global worst case quoted here were verified from `lock_time.csv`.

Global worst case in the 728-run Phase 4 robustness matrix:

| Field | Value |
|---|---|
| Effective lock cycles | 197 |
| Frequency | 200 MHz |
| Charge-pump current | 150 uA |
| Initial condition | 2.50 |
| Coarse cycles | 18 |
| Fine lock cycle | 179 |
| Final outcome | 1T lock |
| Final ratio | 1.0199 |

These results apply only to the tested behavioral conditions, including the stated model delay curves, `C_loop = 25 pF`, nominal supply and temperature, and the model reset and dead-time settings. The 197-cycle result belongs to the Phase 4 robustness sweep and is not the worst case at the proposed 200 uA operating point. These Level B outcomes do not establish hardware acquisition success, a hardware lock detector, or a zero false-lock rate.

The following earlier claims remain withdrawn and are not used as evidence: that a DLL cannot lock with a PFD, that `D_min < T/2` makes acquisition impossible, that the 1T basin extends below 1T, and that the old 55/55 startup sweep proves zero false locks.

### Level C: transistor-level

Not performed. No Sky130 MOSFET simulation, delay-cell characterization, transistor PFD, transistor charge pump, or full-loop transistor transient exists.

### Level D: post-layout

Not performed. No layout, extraction, DRC, LVS, or post-layout Monte Carlo exists.

---

## 9. Proposed Verification Plan

| Area | Method | Exit criterion or recorded result |
|---|---|---|
| Functional | Simulate reference, reset, band selection, eight phase outputs, and `CLK50` behavior in the selected flow | Correct output relationships and no undefined startup state |
| Acquisition | Re-run count-based acquisition with real delay and charge-pump models over multiple initial control states and bands | Classify every outcome as 1T lock, rail, harmonic, unsettled, timeout, or failure |
| Coarse-to-fine handoff | Test `k = 1` near the lower and upper basin edges, flush behavior after coarse-code changes, and a qualification method to be selected using real circuit models | Select and document a qualification method; no handoff based on `k = 1` alone |
| Lock detector | Stimulate true 1T, 2T, rail, coincident-edge, and noisy cases using observable signals only | LOCK asserted for qualified 1T only; no LOCK on rail or harmonic; report tested scenarios rather than inferring a zero false-lock rate |
| Frequency range | Test 25, 30, 50, 60, 75, 85, 100, 120, 150, 180, and 200 MHz in applicable bands, with additional points near band edges | Baseline frequency range met or exact failures reported |
| Band selection | Test overlap regions, externally selected bands, and wrong-band cases; test automatic selection only if it is later implemented | Record the selection policy or the observed failure; no policy assumed |
| Phase spacing | Measure all tap delays after lock; compute `T/8` spacing, DNL, and INL | Compare with 8 percent typical and 15 percent maximum targets |
| Duty cycle | Sweep input duty at 30, 50, and 70 percent across corners and output load | `CLK50` within 45 percent to 55 percent |
| Jitter | Verify ngspice noise capability before use; inject defined supply noise and measure period jitter; if unavailable, keep the analytical estimate labeled as such | Compare with 25 ps typical and 60 ps maximum at 100 MHz |
| Power | Measure average supply current in transient and operating-point simulations at 100 MHz and 200 MHz | Compare with 1 mA typical and 2 mA maximum targets |
| Area | Estimate device area first, then report actual layout core area | Compare with 0.05 mm2 limit only after layout exists |
| PVT | Sweep TT, SS, FF, SF, FS at 1.62 V, 1.80 V, and 1.98 V at -40 C, 27 C, and +110 C | Record delay range, lock, phase error, duty cycle, current, and jitter per corner |
| Mismatch | Use Sky130 mismatch parameters if supported; otherwise perturb parameters externally and state the method | Report mean, sigma, and extremes without claiming strong yield from small samples |
| Output loading | Simulate each phase output with at least 100 fF load and intended buffer behavior | Phase spacing and duty remain within targets |
| Reset and startup | Sweep reset polarity cases, release timing, and initial control states | Known state and repeatable acquisition or reported failure |
| Failure and timeout | Force wrong band, insufficient actuator range, low and high control limits, and frequency change | FAIL and TIMEOUT behave as specified and LOCK is not falsely asserted |

Pre-silicon work uses simulation. Physical measurement requires fabricated silicon and is outside the current project scope. A future bench plan should include reference clock generation, multichannel phase measurement, low-noise supplies, supply-noise injection, temperature control, and current measurement. That equipment is proposed, not confirmed available.

---

## 10. Implementation Plan

1. **Establish and verify the Sky130 and ngspice toolchain.** Confirm model files, process corners, and required simulation capability before circuit work.
2. **Characterize one Sky130 delay cell.** Simulate a current-starved cell only after the toolchain is operational.
3. **Determine whether the required delay range is plausible.** Measure delay versus `VCTRL`, `Kd`, monotonicity, and usable control range against the 5 ns to 625 ps baseline requirement.
4. **Characterize the PFD and charge pump.** Verify polarity, reset, dead zone, current matching, leakage, and rail behavior with circuit models.
5. **Establish fine-loop behavior using circuit models.** Determine the fine-loop basin and handoff constraints before committing to coarse acquisition hardware.
6. **Investigate and design the coarse actuator and handoff.** Compare DAC plus MUX, switched loads, and a separate coarse section using measured circuit behavior.
7. **Develop a hardware-realizable lock detector.** Use observable signals only and test against 1T, rail, and harmonic states.
8. **Integrate the complete DLL.** Combine the delay line, fine loop, coarse acquisition, phase taps, `CLK50`, monitors, and status outputs.
9. **Run PVT, mismatch, load, jitter, power, and area verification.** Record exact failures or pass evidence against the preserved baseline targets.
10. **Perform layout and post-layout verification.** Add extraction, DRC, LVS, and post-layout Monte Carlo only after earlier stages provide a credible design.

Interface reconciliation and pin-budget review remain prerequisites to top-level integration. This is a proposed dependency-aware roadmap, not a declaration that any work has begun.

---

## 11. Risks and Open Issues

| Priority | Risk | Current position | Investigation |
|---:|---|---|---|
| 1 | Physical delay-cell range and linearity | 5 ns to 625 ps stage delay is only a baseline derivation; no Sky130 cell exists | Characterize one cell across `VCTRL`, supply, temperature, and all corners |
| 2 | Coarse-to-fine handoff qualification | `k = 1` is a coarse region only; the tested Level B basin was approximately `1.02T` to `1.95T` under one tested condition; guard bands and qualification method are open | Select a qualification method and test lower and upper boundaries with real circuit models across frequency, PVT, and band conditions |
| 3 | 25 MHz lower boundary behavior | At 200 uA, the tested controller succeeded at 25 MHz, but boundary and rail pockets exist at other currents | Re-run acquisition with real delay and charge-pump models; sweep fine grid near `D/T = 1` |
| 4 | 200 MHz upper boundary feasibility | Behavioral success exists; physical speed and delay range are unverified | Simulate band 2 cell and buffers at FF, low voltage, high temperature, and maximum load |
| 5 | Coarse actuator and electrical handoff | DAC plus MUX is only a candidate; VCTRL interaction, isolation, hold behavior, monotonicity, charge injection, leakage, and PVT behavior are not designed | Design and simulate candidate actuators and handoff; compare step size and qualification behavior |
| 6 | Hardware-realizable lock detector | No hardware detector exists; no false-lock rate has been measured; simulator-only classification fields are invalid | Define observable threshold logic and test against 1T, 2T, rail, and coincident-edge cases |
| 7 | Jitter sensitivity | Estimate shows the 60 ps limit depends on supply sensitivity below approximately 0.382 at 20 mVrms | Verify noise tools, measure supply sensitivity, and simulate injected supply noise |
| 8 | Duty-cycle correction | Behavioral result depends on even inversion count and ideal edge behavior | Confirm stage polarity and simulate 30, 50, and 70 percent input duty across corners and load |
| 9 | PVT and mismatch | All acquisition and timing evidence is nominal and behavioral | Run full PVT and a documented mismatch study; state statistical limits |
| 10 | Power and area | Current estimate is coarse; area is unverified | Measure simulated current and produce device-based and layout area estimates |
| 11 | Output load | Buffers are not designed; 100 fF load compliance is unknown | Design buffers and simulate phase outputs with the required load |
| 12 | Interface and pad budget | Baseline and proposed signals are reconciled in this draft but not finalized; no pad assignments exist | Review wrapper split, pin budget, pad types, and high-frequency monitor access |
| 13 | Frequency-band selection | Bands overlap; no selection policy is established; wrong-band behavior in hardware and physical band implementation are unverified | Test overlap regions and wrong-band cases; compare automatic and external selection and record any decision separately |

Additional open issues are frequency-change reacquisition, exact reset polarity and timing, synchronizer MTBF, measurement start and stop definitions, exact boundary behavior at `D = T` and `D = 2T`, and the statistical strength of any future Monte Carlo result.

---

## 12. Toolchain and Equipment

### Current behavioral environment

| Item | Status |
|---|---|
| Python | Available, version 3.12.4 on Windows |
| NumPy | Available, version 2.2.4 on Windows |
| SciPy | Available, version 1.16.0 on Windows |
| Matplotlib | Available, version 3.10.1 on Windows |
| pandas | Not installed; analysis has used standard library CSV tooling |
| ngspice | Not available |
| xschem | Not available |
| Sky130 PDK | Not available |
| IIC-OSIC-TOOLS | Not available; image pull was not completed |
| Level C simulation | Blocked |

The environment report records that no Sky130 model files, corner definitions, or verified transient-noise and Monte Carlo capabilities are available.

Open-source reproducibility plan: if the proposal is accepted, the design repository will be public, will include all sources needed to regenerate schematic, layout, simulation, and verification views, will use a standard open source license with Apache 2.0 preferred, and will follow the official repository template when published. This is a future obligation, not current evidence of repository readiness.

### Proposed circuit-level environment

The proposed Level C flow is xschem, ngspice, and the Sky130 PDK, preferably through IIC-OSIC-TOOLS if it can be successfully enabled. Tool installation, PDK download, and system configuration are outside this documentation task and require separate authorization.

### Proposed bench equipment

For eventual physical validation, the intended measurements require a programmable reference clock generator, multichannel oscilloscope or equivalent phase measurement setup, low-noise supplies, supply-noise injection hardware, temperature control, current measurement, and suitable probe fixtures. These items are proposed only. No availability or reservation is claimed.

---

## 13. Expected Contribution

The expected contribution is a testable architecture and evidence trail for an eight-phase DLL startup problem, not a claim of a novel DLL topology.

The project can contribute:

- an eight-phase DLL architecture proposal with explicit interface and verification targets;
- investigation of harmonic acquisition and basin-limited startup in a Level B behavioral PFD model tested under the reported conditions;
- a cycle-counting coarse acquisition strategy that does not require numerical knowledge of the input period;
- documented Level B behavioral evidence for acquisition at sampled frequencies and initial conditions;
- a conservative verification plan that separates analytical estimates, behavioral evidence, and future transistor-level proof.

Hardware feasibility remains open. The value of the proposal is that the main risks are identified before circuit implementation and that each target has a stated status.

---

## 14. Conclusion

The proposed block is an eight-phase DLL with a provisional cycle-counting coarse acquisition stage followed by fine analog DLL acquisition. It targets the retained 25 MHz to 200 MHz baseline and the existing supply, phase, duty-cycle, jitter, power, load, and area specifications. Cycle counting identifies a coarse delay region, not a guaranteed fine-lock handoff. The handoff qualification method and hardware implementation remain open.

The proposal is worth investigating because the acquisition problem is concrete and the Level B behavioral evidence supports a specific path forward within the tested conditions. At `Icp = 200 uA`, the Phase 4 fixed-current robustness sweep achieved 91/91 correct-band acquisitions with median 26-cycle and maximum 158-cycle detected lock times. The global worst case in the 728-run matrix was 197 cycles at 200 MHz and 150 uA. These are Level B results only.

Physical evidence is still needed. The most important missing work is a working Sky130 simulation flow, delay-cell characterization, transistor-level PFD and charge pump validation, hardware-realizable acquisition and lock detection, PVT and mismatch verification, output-load testing, jitter measurement, and layout-based area verification. This document is the final proposal text for submission. It is not a hardware-feasibility claim and does not claim Sky130 transistor-level, post-layout, or silicon validation.

---

## References

Project evidence only:

- `AGENTS.md`: baseline specifications and project phases.
- `proposal/architecture_decisions_v0.1.md`: authority for decisions D1 through D8.
- `results/behavioral_dll.md`: Level B DLL prototype and Level A estimates.
- `results/environment_report.md`: toolchain and PDK availability audit.
- `results/pfd_validation/final_validation/report.md`: exact-event PFD validation and basin results.
- `results/pfd_validation/final_validation/preset_feasibility.md`: 1.3T preset and cycle-counting concept study.
- `results/pfd_validation/acquisition_investigation/report.md`: acquisition option comparison.
- `results/pfd_validation/acquisition_controller/report.md`: Phase 3 behavioral controller study.
- `results/pfd_validation/acquisition_controller/failure_analysis.md`: Phase 3 failure taxonomy.
- `results/pfd_validation/acquisition_controller/coarse_actuator.md`: coarse actuator requirements, not a circuit design.
- `results/pfd_validation/acquisition_robustness/report.md`: Phase 4 fixed-current robustness sweep.
- `results/pfd_validation/acquisition_robustness/failure_analysis.md`: Phase 4 failure analysis.
- `results/pfd_validation/acquisition_robustness/current_sweep.csv`: 56 frequency and current combinations.
- `results/pfd_validation/acquisition_robustness/lock_time.csv`: 728-run lock-time source data.
- `results/pfd_validation/acquisition_controller/acquisition_results.csv`: 406-run Phase 3 source data.
- `results/tables/duty_correction.csv`, `results/tables/tap_spacing_100MHz.csv`, and `results/tables/jitter_sensitivity.csv`: behavioral and analytical supporting tables.

External context, rechecked at 2026-11-22 12:48 UTC:

- Open Circuit Design, Chipalooza Challenge #4 Rules & Regulations: `https://opencircuitdesign.com/chipalooza/rules-4.html`.
- Open Circuit Design, Challenge #4 page: `https://opencircuitdesign.com/chipalooza/challenge-4.html`.
- Open Circuit Design, Get Involved: `https://opencircuitdesign.com/chipalooza/get-involved.html`.
- Open Circuit Design, Challenge #4 schedule: `https://opencircuitdesign.com/chipalooza/schedule-4.html`.
- Open Circuit Design, Challenge #4 FAQ: `https://opencircuitdesign.com/chipalooza/faq.html`.

No external academic reference is used as project performance evidence in this revision.
