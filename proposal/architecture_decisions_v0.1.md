# Architecture Decisions v0.1 — 8-Phase DLL

| Field | Value |
|---|---|
| Decision date | 2026-11-22 |
| Scope | Record the approved working architecture decisions and the related documentation corrections for the pre-layout DLL feasibility study. |
| Status | Decision log only. No proposal drafting, implementation, simulation, installation, or toolchain setup was performed in this task. |
| Baseline specifications | Unchanged. This log does not relax, replace, or reinterpret any baseline specification in `AGENTS.md`. |
| Proposal v0.1 | Preserved untouched. This log does not modify `proposal/proposal_v0.1.md` or `proposal/proposal_audit_v0.1.md`. |
| Evidence levels | Level A analytical, Level B behavioral, Level C transistor-level, Level D post-layout. Only Levels A and B exist in the current evidence base. |

---

## 1. Purpose

This file records the user-approved working decisions needed before Proposal v0.2 is prepared. The decisions are proposals for the next proposal revision and future investigation. They are not evidence that the circuit has been implemented, simulated at transistor level, or validated in hardware.

No new simulation or circuit validation was run for this task. Quantitative statements below were rechecked against existing raw CSVs, and documentation statements were traced to existing reports, with evidence level stated explicitly.

---

## 2. Counting convention

The implemented behavioral controller convention is:

`k = floor(D/T)`

Classification:

| Count | Condition | Interpretation |
|---:|---|---|
| `k = 0` | `D < T` | Minimum-delay rail basin |
| `k = 1` | `T ≤ D < 2T` | Desired coarse acquisition region |
| `k ≥ 2` | `D ≥ 2T` | Harmonic region requiring investigation or rejection |

An alternative `ceil(D/T)` convention, with desired count 2, appears in historical material. It is not the implemented controller convention. `option_comparison.csv` retains that historical wording as raw data and was not modified.

The following remain unresolved implementation issues: boundary ambiguity near `D ≈ T` and `D ≈ 2T`, coincident REF/FB edges, synchronizer latency, metastability, and measurement-window flush discipline before each new count.

---

## 3. Decision table

| ID | Approved working decision | Rationale and evidence level | Limitations / implementation status |
|---|---|---|---|
| **D1** | Adopt **digital cycle-counting coarse acquisition followed by fine DLL acquisition** as the provisional proposal architecture. | **Level B:** v4 PFD basin validation, 406-run controller study, and 728-run robustness sweep support the acquisition concept in a behavioral model. | Not a transistor-level implementation. Coarse actuator, hardware FSM, synchronizers, and lock detector remain unimplemented. The original minimum-delay-startup baseline is retained as historical architecture only; existing behavioral evidence contradicts its acquisition success and it must not be claimed as working. |
| **D2** | Carry `Icp = 200 µA` as the **behavioral operating point and proposed design target**. | **Level B:** 91/91 successful correct-band acquisitions; median effective lock time 26 cycles; maximum 158 cycles; 85/91 cases within 100 cycles. These values were recomputed from the raw robustness CSVs. | Not a finalized transistor-level current. No transistor charge pump has been designed, matched, or validated. Current mismatch, leakage, compliance, switching transients, and PVT behavior are unverified. |
| **D3** | Retain the **25–200 MHz baseline target**. Do not relax the specification. | **Level A:** required stage delay ranges from 5 ns at 25 MHz to 625 ps at 200 MHz. **Level B:** seven sampled frequencies were tested in the controller studies. | Intermediate frequencies were not exhaustively tested. Physical delay-cell feasibility across the range is **UNVERIFIED**. 25/30 MHz boundary behavior is a known behavioral risk. 200 MHz physical speed feasibility is also unverified. |
| **D4** | Investigate **DAC + MUX driving VCTRL** as the leading coarse actuator candidate. | **Level B:** the behavioral control `u` maps most directly to a DAC-controlled VCTRL with break-before-make handoff. | Candidate only. No implementation, sizing, linearity, monotonicity, charge-injection, leakage, or PVT validation exists. Switched-capacitive loading and a separate coarse delay section remain alternatives. |
| **D5** | Adopt an **observable-signal lock detector** as a future design target. | **Level B/A:** controller and PFD studies show that simulator-only success variables cannot be used in hardware and that edge-count plus phase evidence is needed to distinguish harmonic states. | Not implemented or validated. Candidate observables: REF/FB edge-count classification, PFD UP/DOWN qualification, selected phase relationships including PHASE[4], coarse code, VC_LOW/VC_HIGH, timeout, and failure status. Do not use `final_ratio`, `harmonic_index`, or `settled_pp` as hardware signals. |
| **D6** | Use **4-bit coarse control** only as an initial study point. | **Level B:** the controller prototype used coarse steps in a normalized control domain; no circuit-level resolution requirement was measured. | Do not claim four bits is sufficient, optimal, or physically validated. The required resolution depends on the unimplemented actuator transfer function and PVT behavior. |
| **D7** | Preserve the **baseline functional interface** as the reference. Treat acquisition-controller, coarse-control, and additional status signals as a proposed wrapper/test interface pending reconciliation. | Baseline `AGENTS.md` defines the functional interface. Existing proposal material contains an inconsistent candidate list. **Level A/B documentation review only.** | `PHASE_SEL`/`TAP_SEL` is an input when selecting a mux. `PHASE[0:7]` are functional outputs and must not be silently omitted. Reconcile `CLK_IN`/`REF_CLK`, `RANGE`/`BAND`, and `PHASE_MON`/`TAP_MON`. Address `CP_CUR`, `MON_DIV`, `VC_LOW`, and `VC_HIGH`. `FAIL`/`TIMEOUT` are proposed additions, not baseline requirements. No pad assignments are finalized. |
| **D8** | Authorize a **future Level C toolchain investigation and feasibility study**. | The current environment report records ngspice, xschem, Sky130 PDK, and IIC-OSIC-TOOLS as unavailable or not validated. | This decision does **not** authorize software installation, large PDK downloads, system configuration changes, or transistor-level design in this task. The next technical milestone after proposal preparation is environment enablement followed by one Sky130 delay-cell characterization. |

---

## 4. Hardware implementation status

| Item | Status |
|---|---|
| Digital cycle-counting acquisition FSM | Not implemented in RTL or transistors; behavioral prototype only. |
| Coarse actuator | Not implemented. DAC/MUX is a candidate; switched loads and a separate coarse section remain alternatives. |
| Hardware synchronizers | Not implemented or analyzed for MTBF. |
| Hardware lock detector | Not implemented or validated. |
| Charge pump at 200 µA | Not implemented at transistor level. 200 µA is a behavioral target only. |
| Full-loop transistor-level simulation | Not performed. |
| PVT / Monte Carlo transistor-level validation | Not performed. |
| Pad interface / pin assignments | Not finalized. |

---

## 5. Unresolved questions

1. What coarse actuator transfer function and step size are achievable in Sky130 across PVT?
2. How should boundary counts near `D ≈ T` and `D ≈ 2T` be resolved without false handoff?
3. What synchronizer structure and MTBF target are required for REF/FB and counter crossings?
4. What watchdog, timeout, and recovery policy should the FSM use?
5. Which observable signals are required for a hardware lock detector, and what thresholds are safe across PVT?
6. Does `PHASE[4]` midpoint verification reliably reject the harmonic states of interest with real tap skew and mismatch?
7. How should frequency changes during operation trigger reacquisition?
8. Which interface signals belong in the functional core versus the wrapper/test harness?
9. Is the candidate full interface compatible with the Chipalooza harness pin budget?
10. Can the delay cell cover 5 ns to 625 ps across the required corners? This remains the largest physical feasibility risk.
11. Can jitter, power, area, duty-cycle, and tap-DNL targets be met with real devices and parasitics?

---

## 6. Evidence qualification to carry into Proposal v0.2

The following are Level B behavioral results, not physical measurements:

- 91/91 acquisitions at `Icp = 200 µA`.
- Median 26-cycle and maximum 158-cycle effective lock times at 200 µA.
- 85/91 cases within 100 cycles at 200 µA.
- 406-run controller study and 728-run robustness study.
- PFD basin results, including the approximately `(1.02T, 1.95T)` behavioral 1T region at 100 MHz.
- Tap-spacing and DNL results based on assumed mismatch statistics.
- Duty-cycle correction results from the ideal/behavioral model.

The following are Level A estimates, not verified circuit performance:

- Supply-noise sensitivity and jitter estimates.
- Supply-current estimates.

Area remains UNVERIFIED; no sizing or layout estimate exists in this evidence
base. No Level C transistor-level or Level D post-layout result exists in the
repository.

---

## 7. Documentation corrections made in this task

| File | Correction |
|---|---|
| `results/pfd_validation/acquisition_robustness/report.md` | Corrected the two prose/table locations that identified the 197-cycle global worst case as 150 MHz. The raw CSV identifies 200 MHz, 150 µA, initial condition 2.50. Added explicit Level B qualification around lock-time and acquisition statistics. Correct tables were preserved. |
| `results/behavioral_dll.md` | Marked the stale §10 false-lock row **WITHDRAWN / INVALID FOR EVIDENCE** with a reference to §0.1. Historical numbers were retained only inside the withdrawn row. Added a note that §10 results are Level A analytical or Level B behavioral and that “PASS (behavioral)” is not a hardware claim. |
| `results/pfd_validation/acquisition_investigation/report.md` | Standardized the documented controller convention to `k = floor(D/T)` with desired `k = 1`. Distinguished the historical `ceil(D/T)` convention as a separate definition retained in raw `option_comparison.csv`. Recorded unresolved boundary, coincident-edge, synchronizer-latency, and measurement-window issues as implementation risks. |

No raw CSV, simulation script, proposal v0.1 file, proposal audit file, or specification file was modified.

---

## 8. Authorization boundary

This log records decisions only. It does not authorize:

- relaxing any baseline specification;
- starting Proposal v0.2 drafting;
- repository cleanup or reorganization;
- installing software or packages;
- downloading a PDK;
- changing system configuration;
- running simulations;
- starting transistor-level design;
- finalizing pad assignments.

The exact next task is a separate documentation task to prepare Proposal v0.2 from the preserved v0.1 draft and this decision log, with all evidence levels and unresolved risks carried forward.
