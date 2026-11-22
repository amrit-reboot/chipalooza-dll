# Chipalooza Challenge #4 — 8-Phase DLL Feasibility Study

## 1. Project Identity

**Project:** 8-Phase Multiphase Delay-Locked Loop (DLL)  
**Technology:** Sky130 Open-Source PDK  
**Challenge:** Chipalooza Challenge #4 — Open Circuit Design  
**Deadline:** November 23, 2026  
**Project Type:** Pre-layout, simulation-only feasibility study  
**Tools:** xschem, ngspice, Python, Sky130 PDK, IIC-OSIC-TOOLS

## 2. Mission

Evaluate whether an 8-phase analog/mixed-signal DLL can realistically meet its proposed specifications in Sky130.

The study must establish feasibility using reproducible open-source simulation and analysis.

The objective is NOT to assume that the proposed architecture works.

The objective is to:

1. Verify delay-cell tuning range across frequency bands and PVT corners.
2. Determine whether the DLL locks within the specified cycle budget.
3. Identify harmonic locks, false locks, startup failures and unstable operating conditions.
4. Evaluate phase accuracy and tap-spacing mismatch.
5. Verify duty-cycle correction.
6. Estimate power, jitter and area realistically.
7. Identify specifications that cannot be achieved and recommend evidence-based revisions before proposal submission.

All conclusions must be supported by calculations, simulation data, plots or explicitly identified estimates.

---

# 3. Proposed Architecture

The DLL is intended to accept a clock and produce eight evenly spaced clock phases.

### Inputs

- CLK_IN
- RANGE[1:0]
- CP_CUR
- TAP_SEL[2:0]
- MON_DIV[1:0]
- Reset/startup control

### Main circuit blocks

1. Eight-stage current-starved delay line
2. Switchable capacitive loads for frequency-range selection
3. Matched dummy loads
4. Phase-frequency detector (PFD)
5. Dead-zone mitigation
6. Charge pump with selectable current
7. Loop capacitor
8. Startup reset / minimum-delay forcing mechanism
9. Lock detector
10. VC_LOW and VC_HIGH limit indicators
11. Duty-cycle corrector (CLK50)
12. TAP_MON multiplexer
13. MON_DIV
14. Buffered VCTRL_MON

### Intended outputs

- PHASE[0:7] — eight phases separated by approximately 45 degrees
- CLK50 — corrected 50% duty-cycle clock
- TAP_MON — selectable monitored phase
- VCTRL_MON — buffered control voltage
- LOCK
- VC_LOW
- VC_HIGH

The precise feedback topology, PFD implementation, startup sequence and duty-corrector circuit must be verified before they are considered finalized.

---

# 4. Baseline Specifications

These specifications are the initial proposal and must never be changed silently.

## 4.1 Supply and operating conditions

| Parameter | Minimum | Typical | Maximum |
|---|---:|---:|---:|
| Supply voltage | 1.62 V | 1.80 V | 1.98 V |
| Temperature | -40°C | 27°C | +110°C |

Process corners:

- TT
- SS
- FF
- SF
- FS

## 4.2 Input clock

| Parameter | Specification |
|---|---|
| Frequency | 25–200 MHz |
| Input duty cycle | 30–70% |
| Input edge time | ≤1 ns |
| Frequency band 0 | 25–60 MHz |
| Frequency band 1 | 50–120 MHz |
| Frequency band 2 | 100–200 MHz |

Bands overlap intentionally.

## 4.3 DLL performance

| Metric | Typical | Maximum / Required Limit |
|---|---:|---:|
| Lock time | 100 cycles | 400 cycles |
| Static phase error | ±2% of T | ±5% of T |
| Tap spacing DNL | ±8% of T/8 | ±15% of T/8 |
| CLK50 duty cycle | 50% | 45–55% |
| Period jitter at 100 MHz | 25 ps RMS | 60 ps RMS |
| Supply current at 100 MHz | 1 mA | — |
| Supply current at 200 MHz | — | 2 mA |
| Phase output load | — | ≥100 fF each |
| False locks | 0 | 0 in startup tests |
| Area | — | ≤0.05 mm² |

Tap-spacing requirement refers to post-layout Monte Carlo 3-sigma performance. Since this study is pre-layout, it cannot conclusively establish post-layout compliance.

## 4.4 Delay requirement

For an eight-stage delay line:

\[
t_{\text{stage}}=\frac{T}{8}=\frac{1}{8f}
\]

| Frequency | Required nominal stage delay |
|---:|---:|
| 25 MHz | 5 ns |
| 40 MHz | 3.125 ns |
| 50 MHz | 2.5 ns |
| 60 MHz | 2.083 ns |
| 100 MHz | 1.25 ns |
| 120 MHz | 1.042 ns |
| 200 MHz | 625 ps |

Initial corner allowance: approximately ±30–40%. This is a planning estimate only, not an established Sky130 result.

The actual delay range must be measured from transistor-level simulation.

---

# 5. Prototype Scope

The prototype is PRE-LAYOUT.

No layout, pad ring, DRC, LVS or extracted parasitics are included.

The prototype will include:

- Loop gain analysis
- One transistor-level delay cell
- PVT characterization of delay cell
- PFD
- Charge pump
- Loop capacitor
- Eight-stage delay line
- Full-loop lock simulation
- Startup behavior
- False-lock investigation
- Duty-cycle correction
- Tap-spacing analysis
- Supply-noise sensitivity
- Monte Carlo mismatch exploration where supported

## Modeling hierarchy

Every block must be labeled as one of:

**LEVEL A — Analytical**

Mathematical calculations, theoretical estimates, simplified equations.

**LEVEL B — Behavioral**

Behavioral Verilog-A, SPICE controlled sources, idealized timing models or simplified circuit representations.

**LEVEL C — Transistor-level**

Sky130 MOSFET models and actual transistor-level circuits.

**LEVEL D — Post-layout**

Extracted parasitic simulation. Not included in this prototype.

Never present Level A or B results as transistor-level evidence.

---

# 6. Roles and Responsibilities

OpenCode must use the following role structure. These are engineering responsibilities, not permission to make independent architectural decisions.

## ROLE 1 — Lead Analog/Mixed-Signal Architect

Responsibilities:

- Maintain architecture consistency.
- Check feasibility of proposed topology.
- Identify critical risks.
- Review all subsystem interfaces.
- Ensure all specifications are traceable.
- Review conclusions from other roles.

Authority:

- Can recommend architecture changes.
- Cannot modify the baseline specifications without explicit user approval.
- Cannot claim a design is feasible without supporting evidence.

## ROLE 2 — Analog Circuit Designer

Responsibilities:

- Design current-starved inverter delay cells.
- Design load-cap switching.
- Evaluate dummy loads.
- Design PFD.
- Design charge pump.
- Propose loop capacitor.
- Design control-voltage startup/reset circuitry.
- Evaluate output buffers.
- Use xschem for schematics and ngspice for simulation.

Every circuit proposal must include:

- Schematic
- Device sizing
- Bias conditions
- Expected operation
- Simulation testbench
- Measured results
- Known limitations

## ROLE 3 — Control Systems Engineer

Responsibilities:

- Derive DLL loop equations.
- Calculate gain and stability.
- Study delay sensitivity.
- Evaluate lock convergence.
- Estimate settling time.
- Investigate harmonic-lock conditions.
- Study loop behavior across delay-cell gain variation.
- Recommend loop-capacitor and charge-pump ranges.

All analytical models must state their assumptions.

## ROLE 4 — Verification and Test Engineer

Responsibilities:

- Develop simulation testbenches.
- Create PVT sweeps.
- Create startup tests.
- Create false-lock tests.
- Create frequency sweeps.
- Create duty-cycle sweeps.
- Define automated pass/fail criteria.
- Verify that simulation results are reproducible.

Never modify a design to pass a test without recording the change.

## ROLE 5 — Python Data and Automation Engineer

Responsibilities:

- Automate ngspice runs.
- Parse output data.
- Generate plots.
- Calculate phase error.
- Calculate tap spacing and DNL.
- Calculate lock time.
- Create summary tables.
- Automate corner sweeps.
- Manage simulation data.

All scripts must run locally using documented dependencies.

## ROLE 6 — Independent Reviewer / Skeptical Engineer

Responsibilities:

- Independently question claims of feasibility.
- Search for hidden assumptions.
- Examine failed simulations.
- Identify unrealistic specifications.
- Check whether startup testing is sufficient.
- Distinguish true lock from harmonic lock.
- Challenge idealized models.
- Check whether measurements actually support claims.

This role must not simply agree with the designer.

## ROLE 7 — Project Manager and Documentation Engineer

Responsibilities:

- Maintain task tracking.
- Maintain specification tracking.
- Record decisions.
- Record unresolved questions.
- Maintain project milestones.
- Ensure deliverables are completed.
- Prepare the final proposal feasibility summary.

The user is the FINAL DESIGN AUTHORITY.

OpenCode must request approval before:

- Changing architecture
- Relaxing a specification
- Choosing a major component value not established by analysis
- Replacing transistor-level simulation with behavioral modeling for a critical claim
- Removing a feature
- Introducing a new dependency
- Making irreversible repository changes

---

# 7. Execution Plan

## PHASE 0 — Repository and Environment Audit

Goal: Establish that the open-source simulation environment is operational.

Tasks:

1. Inspect repository.
2. Inspect available xschem version.
3. Inspect ngspice version.
4. Verify Sky130 PDK availability.
5. Verify IIC-OSIC-TOOLS environment.
6. Identify available model libraries.
7. Confirm process-corner model names.
8. Confirm temperature and supply sweep capability.
9. Run a basic MOSFET simulation.
10. Record environment versions.

Deliverable:

`results/environment_report.md`

Do not start circuit design if the environment is not verified.

---

## PHASE 1 — Loop Mathematics

Goal: Establish mathematically sensible operating ranges before circuit implementation.

Tasks:

1. Define delay sensitivity:

\[
K_d=\frac{d(t_{\text{delay}})}{dV_{\text{CTRL}}}
\]

2. Evaluate loop-gain model:

\[
G=\frac{I_{CP}K_d}{C}
\]

3. Sweep possible charge-pump currents.
4. Sweep possible loop capacitances.
5. Sweep delay sensitivity.
6. Calculate approximate convergence cycles.
7. Check worst-case gain.
8. Check gain variation across bands.
9. Identify possible instability.
10. Identify assumptions and limitations of the simplified model.

Deliverables:

- Python script
- Loop-gain plots
- Loop-gain table
- Sensitivity analysis
- `results/loop_math.md`

Do not finalize CP_CUR or capacitor values without the results and user review.

---

## PHASE 2 — Single Delay Cell

Goal: Determine whether a current-starved delay cell can cover the required delay range.

Tasks:

1. Build the transistor-level current-starved inverter.
2. Include control-voltage dependence.
3. Add switchable capacitive loading.
4. Add dummy loads.
5. Create xschem schematic.
6. Create ngspice testbench.
7. Measure propagation delay.
8. Sweep VCTRL.
9. Sweep supply voltage.
10. Sweep temperature.
11. Sweep process corners.
12. Measure power/current.
13. Identify linearity and usable control range.
14. Determine minimum and maximum achievable delay.
15. Calculate \(K_d\) over the useful range.

Required tests:

- TT
- SS
- FF
- SF
- FS
- 1.62 V
- 1.80 V
- 1.98 V
- -40°C
- 27°C
- 110°C

Deliverables:

- `design/delay_cell.sch`
- `sim/delay_cell/`
- Delay versus VCTRL plots
- Corner summary
- `results/delay_cell.md`

Pass criteria:

For each frequency band, the usable delay range must include the required nominal delay range under the defined corner allowance.

If it fails:

1. Report exact measured delay limits.
2. Identify which corners fail.
3. Identify which frequency limits fail.
4. Propose a narrower frequency range or revised band.
5. Wait for approval before revising the proposal.

---

## PHASE 3 — PFD and Charge Pump

Goal: Verify phase detection and control-voltage correction.

Tasks:

1. Design PFD.
2. Evaluate dead-zone behavior.
3. Design charge pump.
4. Test UP/DOWN current matching.
5. Test leakage.
6. Test reset behavior.
7. Test pulse-width response.
8. Test extreme phase differences.
9. Verify VCTRL range.
10. Verify behavior near rail limits.

Deliverables:

- PFD schematic
- Charge-pump schematic
- Testbenches
- UP/DOWN timing plots
- Current mismatch measurements
- `results/pfd_chargepump.md`

---

## PHASE 4 — Loop Capacitor and Control System

Goal: Find a workable loop-filter configuration.

Tasks:

1. Begin with an ideal capacitor.
2. Test multiple capacitor values.
3. Test multiple CP currents.
4. Calculate loop gain.
5. Simulate closed-loop settling.
6. Check overshoot.
7. Check oscillation.
8. Check stability across delay-cell sensitivity.
9. Investigate lock-time versus noise tradeoff.
10. Later substitute a Sky130 MiM capacitor model if available.

Target capacitor range initially:

20–30 pF, as proposed.

This is not a finalized value.

Deliverables:

- Gain table
- Lock-time table
- Control-voltage plots
- Stability assessment
- `results/loop_filter.md`

---

## PHASE 5 — Eight-Stage DLL Integration

Goal: Integrate the complete delay line and feedback loop.

Tasks:

1. Integrate eight delay cells.
2. Integrate PFD.
3. Integrate charge pump.
4. Integrate capacitor.
5. Integrate startup reset.
6. Integrate band selection.
7. Simulate at band midpoints.
8. Test TT, SS and FF initially.
9. Expand to all required corners.
10. Record lock time.
11. Record static phase error.
12. Record tap spacing.
13. Record current.
14. Record control voltage.

Frequency midpoint tests:

- Band 0: 42.5 MHz
- Band 1: 85 MHz
- Band 2: 150 MHz

These are initial test points; the user may approve additional points.

Deliverables:

- DLL top-level schematic
- Full-loop testbench
- Lock transient plots
- Phase plots
- Tap-spacing table
- `results/full_loop.md`

---

## PHASE 6 — Startup and False-Lock Testing

Goal: Determine whether startup forces the loop toward the correct lock.

Tasks:

1. Simulate minimum-delay startup.
2. Test 10 or more initial VCTRL values.
3. Test each band.
4. Test multiple input frequencies.
5. Observe phase detector behavior.
6. Check harmonic-lock possibilities.
7. Check VC_LOW.
8. Check VC_HIGH.
9. Check reset timing.
10. Verify lock-detector behavior.

Record:

- Initial VCTRL
- Startup state
- Final VCTRL
- Final phase error
- Lock status
- Lock time
- Failure mode

A successful startup sweep does not prove zero false locks in all possible conditions. State the scope of testing.

Deliverables:

- Startup sweep data
- False-lock plots
- Failure log
- `results/startup.md`

---

## PHASE 7 — Duty-Cycle Corrector

Goal: Generate CLK50 with a 45–55% duty-cycle target.

Proposed concept:

Use rising edges from phase 0 and phase 4 to create alternating set/reset events.

Tasks:

1. Define exact logic.
2. Analyze startup state.
3. Check asynchronous reset.
4. Check glitches.
5. Check phase mismatch sensitivity.
6. Simulate input duty 30%.
7. Simulate input duty 50%.
8. Simulate input duty 70%.
9. Test corners.
10. Measure CLK50 duty cycle.

Deliverables:

- Duty-corrector schematic
- Testbench
- Waveforms
- Duty table
- `results/duty_corrector.md`

Do not assume this architecture achieves 50% duty until simulated.

---

## PHASE 8 — Noise and Jitter

Goal: Evaluate supply-noise-induced timing variation.

Tasks:

1. Inject 20 mVrms supply noise at 100 MHz.
2. Use ngspice noise/transient-noise capability only if verified in the installed version.
3. Record exact noise generation method.
4. Measure clock-edge timing.
5. Calculate RMS period jitter.
6. Separate supply-induced jitter from intrinsic jitter.
7. Estimate intrinsic jitter analytically if transistor noise simulation is impractical.
8. Clearly label estimates.

Deliverables:

- Noise simulation method
- Jitter measurements
- Jitter plots
- Assumptions
- `results/jitter.md`

---

## PHASE 9 — Monte Carlo and Mismatch

Goal: Investigate tap-spacing variation.

Tasks:

1. Identify mismatch parameters supported by Sky130 models.
2. Determine whether ngspice Monte Carlo is supported.
3. If necessary, implement parameter perturbation externally using Python.
4. Run approximately 30 samples initially.
5. Record tap-spacing deviations.
6. Calculate mean, standard deviation and observed extremes.
7. Compare observed results with target.
8. Clearly state that 30 samples do not constitute strong statistical validation of a 3-sigma yield claim.

Deliverables:

- Monte Carlo methodology
- Sample data
- Histograms
- Statistical summary
- `results/monte_carlo.md`

---

## PHASE 10 — Final Feasibility Review

For every specification, report:

| Specification | Target | Measured | Method | Status | Evidence |
|---|---|---|---|---|---|
| Delay range | Required | Measured | Transistor simulation | PASS/FAIL | Plot |
| Lock time | ≤400 cycles | Measured | Transient | PASS/FAIL | Plot |
| Phase error | ±5% T | Measured | Transient | PASS/FAIL | Data |
| Tap spacing | ±15% T/8 | Measured | Transient/MC | PASS/FAIL | Data |
| Duty cycle | 45–55% | Measured | Transient | PASS/FAIL | Plot |
| Jitter | ≤60 ps RMS | Measured/estimated | Noise analysis | PASS/FAIL/ESTIMATE | Data |
| Current | ≤2 mA at 200 MHz | Measured | Operating point/transient | PASS/FAIL | Data |
| Area | ≤0.05 mm² | Estimated | Device-area estimate | ESTIMATE | Calculation |
| False locks | Zero in tests | Count | Startup sweep | PASS/FAIL | Logs |

Allowed status categories:

- PASS — verified against the target using the specified methodology.
- WITHIN 20% — misses the target by no more than 20%; not a pass.
- FAIL — misses by more than 20%.
- UNVERIFIED — insufficient evidence.
- ESTIMATE — analytical or approximate result.
- NOT APPLICABLE — explain why.

Do not convert ESTIMATE or UNVERIFIED into PASS.

---

# 8. Repository Structure

Maintain this structure:

```text
chipalooza-dll/
│
├── AGENTS.md
├── README.md
├── .gitignore
│
├── spec/
│   ├── baseline_spec.md
│   ├── architecture.md
│   ├── interfaces.md
│   ├── assumptions.md
│   └── decision_log.md
│
├── design/
│   ├── delay_cell/
│   │   ├── delay_cell.sch
│   │   └── notes.md
│   ├── pfd/
│   ├── charge_pump/
│   ├── loop_filter/
│   ├── duty_corrector/
│   └── top/
│
├── sim/
│   ├── delay_cell/
│   ├── pfd/
│   ├── charge_pump/
│   ├── loop_filter/
│   ├── full_loop/
│   ├── startup/
│   ├── duty/
│   ├── jitter/
│   └── monte_carlo/
│
├── scripts/
│   ├── run_sim.py
│   ├── sweep.py
│   ├── analyze.py
│   └── plot_results.py
│
├── results/
│   ├── plots/
│   ├── raw/
│   ├── tables/
│   ├── environment_report.md
│   ├── loop_math.md
│   ├── delay_cell.md
│   ├── pfd_chargepump.md
│   ├── loop_filter.md
│   ├── full_loop.md
│   ├── startup.md
│   ├── duty_corrector.md
│   ├── jitter.md
│   ├── monte_carlo.md
│   └── summary.md
│
└── logs/
    ├── simulation/
    └── analysis/
```

---

# 9. Rules for OpenCode

## Rule 1 — Work incrementally

Do not implement the entire project in one operation.

Work on one phase and one major block at a time.

## Rule 2 — Inspect before editing

Before changing any file:

1. Inspect repository structure.
2. Inspect relevant existing files.
3. Understand the installed environment.
4. Explain what needs to change.
5. Make the smallest appropriate modification.

## Rule 3 — Do not invent results

Never fabricate:

- Simulation output
- PVT results
- Delay measurements
- Lock time
- Jitter
- Power
- Monte Carlo statistics
- Area

If simulation has not run, label it NOT SIMULATED.

## Rule 4 — Preserve baseline specifications

Do not relax the specification because the circuit fails.

Report the failure, explain its cause, and propose revised targets for the user to approve.

## Rule 5 — Reproducibility

Every simulation must have:

- Testbench
- Model/library references
- Parameters
- Corner
- Supply
- Temperature
- Input conditions
- Command used
- Output files
- Analysis script where applicable

## Rule 6 — Prefer open-source tools

Use:

- xschem
- ngspice
- Python
- Sky130 PDK
- Git
- Standard open-source plotting/data tools

Do not require proprietary tools unless explicitly approved.

## Rule 7 — Explain before major design decisions

For every significant decision, provide:

- Problem
- Options
- Advantages
- Disadvantages
- Recommendation
- Evidence
- Required user approval

## Rule 8 — Do not destroy user work

- Do not delete files without asking.
- Do not overwrite uncommitted work without asking.
- Do not reset Git.
- Do not force-push.
- Do not change branches automatically.
- Do not install system dependencies without approval.
- Do not run destructive commands.

## Rule 9 — Report every task

Each completed task must end with:

```text
TASK:
What was attempted.

CHANGES:
Files created or modified.

METHOD:
Analytical / Behavioral / Transistor-level.

RESULT:
Actual measured result or NOT SIMULATED.

STATUS:
PASS / FAIL / WITHIN 20% / UNVERIFIED / ESTIMATE.

ISSUES:
Problems found.

NEXT STEP:
One specific next action.
```

## Rule 10 — User controls the project

The user is the lead designer and decision-maker.

OpenCode is an engineering assistant—not an autonomous authority that can redefine the project.

---

# 10. First Task for OpenCode

Do NOT begin designing the DLL yet.

Start with:

**PHASE 0 — Repository and Environment Audit**

1. Inspect the working directory.
2. Check the installed xschem, ngspice and Python versions.
3. Verify the Sky130 PDK paths.
4. Identify model files and process-corner definitions.
5. Check whether the current environment is IIC-OSIC-TOOLS.
6. Test whether ngspice can simulate a basic Sky130 NMOS.
7. Check available Monte Carlo and transient-noise features.
8. Create the proposed directory structure without deleting existing files.
9. Write `results/environment_report.md`.
10. Summarize findings and STOP.

Do not proceed to Phase 1 until the user reviews the environment audit.

---

# 11. Communication Format

Communicate with the user as an engineering collaborator.

Keep responses:

- Concise but technically complete
- Step-by-step
- Evidence-based
- Explicit about uncertainty
- Clear about what has been simulated versus calculated
- Focused on the current phase

Do not dump huge amounts of code without explaining what it does.

For each phase:

1. State the objective.
2. Explain the engineering reasoning.
3. Show equations where useful.
4. Implement the smallest testable step.
5. Run it.
6. Show the actual output.
7. Interpret it.
8. Identify the next step.
9. Wait for approval at major decision points.

**Final objective:** Produce an honest, reproducible feasibility report that allows the user to submit a technically defensible Chipalooza proposal with realistic specifications and documented risks.