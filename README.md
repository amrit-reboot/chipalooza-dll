# Chipalooza Challenge #4 — Eight-Phase DLL

A pre-layout feasibility study for an eight-phase analog/mixed-signal delay-locked loop (DLL) targeting the Sky130 process.

**Canonical proposal:** [`proposal/proposal_v1_submission.md](proposal/proposal_v1_submission.md)  
**Evidence status:** Level A analytical + Level B behavioral only. No transistor-level, post-layout, or silicon validation is claimed.

## Project at a glance

- **Goal:** Generate eight nominally 45°-spaced clock phases with total delay locked to one reference period.
- **Target reference range:** 25–200 MHz.
- **Target process:** Sky130.
- **Architecture under investigation:** eight-stage fine delay line, PFD/charge-pump fine loop, and digitally assisted coarse acquisition.
- **Current focus:** understand the fine-loop acquisition basin and evaluate cycle-counting coarse acquisition before committing to a hardware implementation.

This repository is a technical record of feasibility work. Specifications remain targets unless explicitly marked as demonstrated.

## Status

| Work area | Status |
|---|---|
| Baseline specification | Preserved in `AGENTS.md` |
| Architecture and design decisions | Documented |
| Analytical calculations | Completed for the stated assumptions |
| Behavioral fine-loop validation | Completed for reported model conditions |
| Acquisition-controller and robustness studies | Completed for reported model conditions |
| Sky130 transistor-level DLL | Not implemented or validated |
| Physical design, DRC/LVS, extraction | Not performed |
| Silicon/hardware measurements | Not performed |

**Key unresolved technical risk:** reliable coarse-to-fine handoff into the fine loop's one-period acquisition region. A cycle count of `k = 1` is only a coarse classification; it does not by itself guarantee fine-loop acquisition.

## Selected behavioral evidence

Results below are limited to the models and conditions documented in the reports. They are not physical circuit performance claims.

- **Fine-loop validation:** 98 convergence runs; the tested one-period basin was approximately 1.02T–1.95T at 100 MHz, band 1, and 300 µA.
- **Acquisition-controller study:** 406 runs; 239 one-period acquisitions; 76/91 correct-band acquisitions; 0/13 at 25 MHz with 300 µA.
- **Robustness sweep:** 728 runs, 664 successes. At 200 µA, 91/91 tested cases succeeded, with 7/26/158 cycles (minimum/median/maximum).
- **Frequency sweep:** 36 points from 25 to 200 MHz; 15–97 behavioral lock cycles.
- **Duty-cycle correction model:** corrected mean duty values of 49.99%, 49.99%, and 49.96% for 30%, 50%, and 70% input duty.
- **Tap-spacing mismatch model:** assumed mismatch only; no Sky130 device mismatch or post-layout result.

See the detailed reports and raw tables under `results/`. Interpret each result using its report's conditions and limitations.

## Repository guide

| Path | Contents |
|---|---|
| `AGENTS.md` | Original baseline, constraints, and project plan |
| `proposal/proposal_v1_submission.md` | **Single canonical proposal** |
| `proposal/architecture_decisions_v0.1.md` | Decision record |
| `proposal/spec_compliance_matrix_v1.md` | Target-by-target evidence and compliance status |
| `scripts/` | Behavioral models, validation scripts, and runners |
| `results/` | Reports, plots, raw tables, metadata, and logs |
| `docs/` | Publication/reproducibility notes |

Intermediate proposal drafts are not maintained in the public proposal folder. The final proposal is the authoritative submission document.

## Reproduction

Use Python with NumPy, SciPy, and Matplotlib. Run commands from the repository root. Scripts may rewrite files in `results/`; reproduce from a clean copy if you need to preserve the committed outputs.

```bash
python --version
python -c "import numpy, scipy, matplotlib; print(numpy.__version__, scipy.__version__, matplotlib.__version__)"
python scripts/run_behavioral.py
python scripts/pfd_validation/run_acquisition_tests.py
python scripts/pfd_validation/run_robustness_sweep.py
python scripts/pfd_validation/run_final_validation.py
```

Optional detector checks:

```bash
python scripts/pfd_validation/test_pfd.py
python scripts/pfd_validation/test_pfd_v3.py
```

The scripts and reports document the fixed random seeds and test conditions.

## Limitations

- No Sky130 PDK transistor-level DLL simulation is included.
- Physical delay-cell range, PVT coverage, mismatch, output loading, and circuit lock detector are unverified.
- No layout, DRC, LVS, extraction, post-layout analysis, or silicon measurements have been performed.
- Area, power, jitter, and hardware compliance remain targets or analytical estimates—not demonstrated passes.
- Coarse acquisition hardware, its actuator, and handoff qualification remain to be designed and validated.

## License

Apache-2.0. See [LICENSE](LICENSE) and [NOTICE](NOTICE).

## Author

Amrit Tiwari
