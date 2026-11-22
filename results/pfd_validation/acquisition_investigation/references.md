# References — Startup Acquisition Investigation

These are literature references identified during this investigation. They are
**background reading only**; no transistor-level result from them is claimed as
evidence for this project. All project evidence in the accompanying report is
**Level B behavioral** and comes from this repository.

---

## 1. DLL false lock / harmonic lock — general

**Razavi, B., "The Delay-Locked Loop [A Circuit for All Seasons]," IEEE
Solid-State Circuits Magazine, Vol. 10, No. 3, 2018.**
`http://www.seas.ucla.edu/brweb/papers/Journals/BR_SSCM_3_2018.pdf`

Relevant points from the accessible abstract/text:
- A DLL designed for total delay = TCK at TT can falsely lock at 2TCK in a
  slow corner; phase spacing becomes 2T/N instead of T/N.
- Avoiding false lock generally "requires substantial added complexity,
  especially if the DLL must operate across a wide frequency range."
- One published solution uses a **replica VCDL configured as a ring oscillator
  in a PLL** locked to the input, generating a coarse control voltage; the main
  DLL then only needs fine adjustment. Reported cost: approximately **2x area
  and power**.

Relevance: direct support for Option E2 and for the general difficulty of
Option C.

---

## 2. Stopwatch / N-detector initialization

**Baker, R. J. (major professor), "Wide Range, Low Jitter Delay-Locked Loop
Using a Graduated Digital Delay Line and Phase Interpolator" (thesis).**
`https://cmosedu.com/jbaker/students/theses/Wide%20Range,%20Low%20Jitter%20Delay-Locked%20Loop%20Using%20a%20Graduated%20Digital%20Delay%20Line%20and%20Phase%20Interpolator.pdf`

Relevant points:
- Explicitly states that if the DLL resets at **minimum delay** and the phase
  detector wants to remove delay, the DLL will never lock (and the symmetric
  failure at maximum delay).
- Describes a **"stopwatch" / N-detector** fast-initialization method: a pulse
  is sent through a delay model while a counter counts clock cycles; the
  captured count N sets the coarse delay near the lock point.
- DDR SDRAM DLL target: lock within 200 cycles.

Relevance: direct support for Options A/D/E3 and for the minimum-delay rail
problem observed in our v4 model.

---

## 3. Wide-range harmonic lock detector

**"Wide-range harmonic lock detector with real-time delay measurement of
delay-locked loop," IET Electronics Letters, 2015.**
`https://digital-library.theiet.org/doi/pdf/10.1049/el.2014.3749?download=true`

Relevant points:
- Harmonic lock defined as total delay = N·TREF, N ≥ 2.
- States DLL "cannot escape from harmonic lock state by itself without any
  other signals properly indicating whether harmonic locking has occurred."
- Detector monitors total delay using selected multiphase taps (P1, P2, P4,
  P8, P16), initiates harmonic flag above ~1.25–1.5 TREF.
- Demonstrated in 0.13 µm CMOS over 25–500 MHz.

Relevance: direct support for Option E1; also confirms that a lock detector
must verify delay magnitude, not just edge alignment.

---

## 4. Harmonic-free DLL with duty-cycle tolerance

**"Harmonic-free and low cost delay-locked loop with a 20–80% input duty
cycle," IET Electronics Letters, 2017.**
`https://digital-library.theiet.org/doi/pdf/10.1049/el.2016.3032?download=true`

Relevant points:
- States a conventional DLL fails if total delay < 0.5 TREF (zero-trap) or
  > 1.5 TREF (harmonic lock).
- Uses hierarchical delay line with coarse + fine sections and a state
  controller identifying harmonic lock / zero-trap at the coarse stage.

Relevance: supports Options B and E1; also shows the classic 0.5T/1.5T
criterion, which our Level B work did **not** adopt as a hard limit (our
measured basin is approximately 1.02T–1.95T at 100 MHz). The literature
threshold and our behavioral threshold differ and must not be conflated.

---

## 5. Binary search / mixed-mode DLL

**"Fast-Locking and High-Resolution Mixed-Mode DLL with Binary Search and
Clock Failure Detection for Wide Frequency Ranges in 3-nm FinFET CMOS,"
arXiv:2501.13238, 2025.**
`https://arxiv.org/html/2501.13238v2`

Relevant points:
- Binary search over coarse digital code converges in B+1 steps.
- Notes that large first steps can overshoot and cause clock failure;
  includes a toggle detector and clock-failure detection.

Relevance: support for Option E4; cautionary note on coarse-step overshoot.

---

## 6. Frequency division assisted DLL

**"Design of Delay Locked Loop with Frequency Division Technique," WCSE 2016.**
`https://www.wcse.org/WCSE_2016/095.pdf`

Relevant points:
- Uses a start-control signal and transistor to set minimum initial delay,
  claiming false/harmonic lock avoidance.
- Uses frequency dividers to relax PFD operating frequency.

Relevance: background for startup-state control; note that our v4 results
show minimum-delay startup fails in our topology, so this particular
technique is **not** transferable without re-examination.

---

## 7. Harmonic lock / hang prevention patent

**US Patent 7,209,533, "Delay locked loop with harmonic lock and hang
prevention architecture," 2007.**
`https://exa.ai/library/legal/patent/5g8wdk5p0v7`

Relevant points:
- Uses a second loop (PFD + charge pump + filter + VCO) to detect harmonic
  lock and force the main loop delay smaller.
- VCO runs at about 1.4x reference frequency when correctly locked.

Relevance: support for Option E2/E5 alternative loop techniques.

---

## Internal project evidence (not external references)

- `results/pfd_validation/final_validation/report.md` — authoritative
  Level B findings for Problem 1.
- `results/pfd_validation/final_validation/tables/f1_timestep_audit.csv` —
  edge accounting.
- `results/pfd_validation/final_validation/tables/f2_convergence.csv` —
  14 starts × 7 substeps basin map.
- `scripts/dll_model.py` — BANDS delay ranges used for band analysis.
- Diagnostics performed for this investigation (temporary scripts):
  - startup ignored-REF count = floor(D/T) for frozen delay
  - UP pulse width identical for 0.68T, 1.68T, 2.68T
  - band Dmin/T and Dmax/T across 25–200 MHz
