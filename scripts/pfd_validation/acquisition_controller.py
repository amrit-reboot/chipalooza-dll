"""
Behavioral startup/acquisition controller prototype for the 8-phase DLL (LEVEL B).

This is a PROTOTYPE investigation only. It does NOT modify the official
architecture or specifications. It drives the validated v4 exact-event engine
(pfd_model_v4_final.py) and uses ONLY observable edge-count information to
place the VCDL delay in the 1T fine-lock basin.

OBSERVABLE
----------
With the charge pump disabled (probe current ~ 0), the number of reference
edges that arrive while the first PFD UP pulse is still asserted equals
floor(D/T) -- the "startup ignored-REF count" verified in the acquisition
investigation. No numerical value of T, and no forced delay preset, is used.

COARSE ACTUATOR
---------------
The prototype actuator is the normalized VCDL control u in [0, 1] used by the
v4/dll_model delay model (u = 0 -> maximum delay, u = 1 -> minimum delay).
The controller only increments/decrements this control by fixed steps; it never
computes or assigns a target delay from T. Mapping this to real hardware
(DAC / switched loads) is described in the report.

STATE MACHINE
-------------
RESET -> INITIALIZE -> COARSE_ACQUIRE -> BASIN_CHECK -> FINE_LOCK
      -> LOCK_VERIFY -> LOCKED
with TIMEOUT and FAIL terminal states, and a re-entry path from LOCK_VERIFY
back to COARSE_ACQUIRE when fine locking fails.

No transistors, no Sky130, no Docker, no installation.
"""
from __future__ import annotations

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "scripts"))
sys.path.insert(0, HERE)

import dll_model as m                       # noqa: E402
import pfd_model_v4_final as v4             # noqa: E402


STATES = (
    "RESET", "INITIALIZE", "COARSE_ACQUIRE", "BASIN_CHECK",
    "FINE_LOCK", "LOCK_VERIFY", "LOCKED", "TIMEOUT", "FAIL",
)

# Fine-lock outcome labels (derived from final_ratio, NOT from v4's
# mislabeled rail_min/rail_max flags -- see report).
OUTCOME_1T = "1T_LOCK"
OUTCOME_RMIN = "MIN_DELAY_RAIL"
OUTCOME_RMAX = "MAX_DELAY_RAIL"
OUTCOME_HARM = "HARMONIC_LOCK"
OUTCOME_UNSET = "UNSETTLED"


class AcquisitionController:
    """Behavioral Option-A cycle-counting acquisition controller."""

    def __init__(
        self,
        f: float,
        band: int,
        *,
        icp: float = 300e-6,
        c_loop: float = 25e-12,
        substeps_measure: int = 200,
        substeps_fine: int = 300,
        measure_cycles: int = 6,
        fine_cycles: int = 200,
        coarse_step: float = 0.10,
        nudge_step: float = 0.05,
        max_coarse_steps: int = 20,
        max_fine_attempts: int = 3,
        max_total_cycles: int = 3000,
        lock_tol: float = 0.02,
    ):
        self.f = float(f)
        self.band = int(band)
        self.T = 1.0 / self.f
        self.icp = icp
        self.c_loop = c_loop
        self.substeps_measure = substeps_measure
        self.substeps_fine = substeps_fine
        self.measure_cycles = measure_cycles
        self.fine_cycles = fine_cycles
        self.coarse_step = coarse_step
        self.nudge_step = nudge_step
        self.max_coarse_steps = max_coarse_steps
        self.max_fine_attempts = max_fine_attempts
        self.max_total_cycles = max_total_cycles
        self.lock_tol = lock_tol

        self.dmin_over_t = m.line_delay(1.0, band) / self.T
        self.dmax_over_t = m.line_delay(0.0, band) / self.T

    # ------------------------------------------------------------------
    # Helper: observable edge-count measurement (charge pump disabled)
    # ------------------------------------------------------------------
    def measure_count(self, u: float) -> tuple[int, dict]:
        """Return floor(D/T) from startup ignored-REF count, CP disabled."""
        r = v4.simulate_v4(
            self.f, band=self.band, u0=u,
            cycles=self.measure_cycles, substeps=self.substeps_measure,
            icp=1e-9,  # effectively disabled probe
        )
        return int(r["ignored_ref"]), r

    # ------------------------------------------------------------------
    # Helper: fine PFD/CP lock attempt
    # ------------------------------------------------------------------
    def fine_lock(self, u: float) -> dict:
        return v4.simulate_v4(
            self.f, band=self.band, u0=u,
            cycles=self.fine_cycles, substeps=self.substeps_fine,
            icp=self.icp, c_loop=self.c_loop,
            lock_tol=self.lock_tol,
        )

    def classify_fine(self, r: dict) -> str:
        """Classify a fine-lock result from the measured delay ratio."""
        ratio = r["final_ratio"]
        if abs(ratio - 1.0) <= self.lock_tol and r["harmonic_index"] == 1 \
                and r["settled_pp"] <= 0.05:
            return OUTCOME_1T
        if ratio <= self.dmin_over_t + 0.03:
            return OUTCOME_RMIN
        if ratio >= self.dmax_over_t - 0.03:
            return OUTCOME_RMAX
        if r["harmonic_index"] >= 2 and abs(ratio - r["harmonic_index"]) <= self.lock_tol:
            return OUTCOME_HARM
        return OUTCOME_UNSET

    # ------------------------------------------------------------------
    # Initial condition helper
    # ------------------------------------------------------------------
    def initial_u(self, start_ratio: float | None, u0: float | None) -> float:
        if u0 is not None:
            return min(max(float(u0), 0.0), 1.0)
        if start_ratio is None:
            raise ValueError("provide start_ratio or u0")
        # v4 clamps at max delay when D > Dmax; mirror that here.
        return m.u_for_delay(start_ratio * self.T, self.band)

    # ------------------------------------------------------------------
    # Main FSM
    # ------------------------------------------------------------------
    def run(
        self,
        start_ratio: float | None = None,
        u0: float | None = None,
        init_mode: str = "preserve",
        init_u: float = 0.0,
    ) -> dict:
        """Run one acquisition experiment.

        init_mode = "preserve": INITIALIZE keeps the physical starting delay
                    (unknown power-up state) -- used for robustness tests.
        init_mode = "max"/"mid"/"custom": INITIALIZE loads a deterministic
                    coarse actuator value (init_u for "custom").
        """
        state = "RESET"
        u = self.initial_u(start_ratio, u0)
        trace = []
        u_traj = []
        d_traj = []
        count_traj = []
        coarse_adjustments = 0
        fine_attempts = 0
        total_cycles = 0
        cycles_to_basin = None
        fine_lock_cycle = None
        outcome = OUTCOME_UNSET
        failure_reason = ""
        basin_count = None
        final_fine = None
        init_applied = u

        def log(note: str = ""):
            trace.append({
                "state": state,
                "u": round(u, 6),
                "d_over_t": round(m.line_delay(u, self.band) / self.T, 4),
                "count": count_traj[-1] if count_traj else None,
                "coarse_adjustments": coarse_adjustments,
                "fine_attempts": fine_attempts,
                "cycles": total_cycles,
                "note": note,
            })

        log("reset issued; fine loop disabled")
        state = "INITIALIZE"
        if init_mode == "preserve":
            pass
        elif init_mode == "max":
            u = 0.0
        elif init_mode == "mid":
            u = 0.5
        elif init_mode == "custom":
            u = min(max(float(init_u), 0.0), 1.0)
        else:
            raise ValueError(f"unknown init_mode {init_mode}")
        init_applied = u
        log(f"coarse actuator initialized ({init_mode}); CP disabled")

        # ---- acquisition loop -----------------------------------------
        while True:
            # COARSE_ACQUIRE: measure edge count with CP disabled
            state = "COARSE_ACQUIRE"
            n, meas = self.measure_count(u)
            count_traj.append(n)
            u_traj.append(u)
            d_traj.append(m.line_delay(u, self.band) / self.T)
            total_cycles += self.measure_cycles
            log(f"measured floor(D/T)={n}")

            # BASIN_CHECK: classify by observable count only
            state = "BASIN_CHECK"
            if n == 0:
                log("feedback before next REF -> increase delay")
                u = max(0.0, u - self.coarse_step)
                coarse_adjustments += 1
                outcome = OUTCOME_UNSET
                if coarse_adjustments >= self.max_coarse_steps:
                    state, failure_reason = "FAIL", "coarse step limit (n=0 persisted)"
                    log(failure_reason); break
                if total_cycles >= self.max_total_cycles:
                    state, failure_reason = "TIMEOUT", "cycle budget (n=0)"
                    log(failure_reason); break
                continue
            if n >= 2:
                log(f"feedback after {n} REF edges -> decrease delay")
                u = min(1.0, u + self.coarse_step)
                coarse_adjustments += 1
                outcome = OUTCOME_UNSET
                if coarse_adjustments >= self.max_coarse_steps:
                    state, failure_reason = "FAIL", "coarse step limit (n>=2 persisted)"
                    log(failure_reason); break
                if total_cycles >= self.max_total_cycles:
                    state, failure_reason = "TIMEOUT", "cycle budget (n>=2)"
                    log(failure_reason); break
                continue

            # n == 1: candidate 1T basin
            if cycles_to_basin is None:
                cycles_to_basin = total_cycles
            basin_count = n
            log("count=1 -> candidate 1T basin; enable fine loop")

            # FINE_LOCK
            state = "FINE_LOCK"
            fine_attempts += 1
            fine = self.fine_lock(u)
            final_fine = fine
            total_cycles += self.fine_cycles
            outcome = self.classify_fine(fine)
            log(f"fine attempt {fine_attempts}: {outcome}, final D/T={fine['final_ratio']:.3f}")

            # LOCK_VERIFY
            state = "LOCK_VERIFY"
            if outcome == OUTCOME_1T:
                fine_lock_cycle = fine["lock_cycle"]
                state = "LOCKED"
                log("1T lock verified; assert LOCK")
                break

            if fine_attempts >= self.max_fine_attempts:
                state, failure_reason = "FAIL", f"fine attempts exhausted ({outcome})"
                log(failure_reason); break
            if total_cycles >= self.max_total_cycles:
                state, failure_reason = "TIMEOUT", f"cycle budget ({outcome})"
                log(failure_reason); break

            # Nudge based on the *observed* fine-lock failure direction
            if outcome == OUTCOME_RMIN:
                u = max(0.0, u - self.nudge_step)   # more delay
                note = "min-delay rail -> increase delay"
            elif outcome in (OUTCOME_HARM, OUTCOME_RMAX):
                u = min(1.0, u + self.nudge_step)   # less delay
                note = "harmonic/max rail -> decrease delay"
            else:
                # Unsettled: small alternating dither to leave the boundary
                u = min(1.0, max(0.0, u + (self.nudge_step if fine_attempts % 2 else -self.nudge_step)))
                note = "unsettled -> dither"
            coarse_adjustments += 1
            log(note + "; re-enter COARSE_ACQUIRE")
            # one-way handoff with hysteresis: re-measure before next fine try
            continue

        return {
            "f": self.f, "band": self.band,
            "start_ratio": start_ratio,
            "effective_start_ratio": (
                min(start_ratio, self.dmax_over_t) if start_ratio is not None
                else m.line_delay(init_applied, self.band) / self.T
            ),
            "u_start": init_applied,
            "init_mode": init_mode,
            "success": state == "LOCKED" and outcome == OUTCOME_1T,
            "final_state": state,
            "outcome": outcome,
            "failure_reason": failure_reason,
            "final_u": u,
            "final_ratio": (
                final_fine["final_ratio"] if final_fine is not None
                else m.line_delay(u, self.band) / self.T
            ),
            "harmonic_index": final_fine["harmonic_index"] if final_fine is not None else None,
            "cycles_to_basin": cycles_to_basin,
            "fine_lock_cycle": fine_lock_cycle,
            # Actual detected lock time = coarse measurement cycles actually
            # used to reach the basin + v4's fine lock-cycle detection.
            # total_cycles includes the full fixed fine observation window and
            # is a simulation budget, not the detected lock time.
            "effective_lock_cycles": (
                cycles_to_basin + fine_lock_cycle
                if (cycles_to_basin is not None and fine_lock_cycle is not None)
                else None
            ),
            "total_cycles": total_cycles,
            "coarse_adjustments": coarse_adjustments,
            "fine_attempts": fine_attempts,
            "basin_count": basin_count,
            "u_traj": u_traj,
            "d_traj": d_traj,
            "count_traj": count_traj,
            "trace": trace,
        }


def classify_from_ratio(ratio: float, dmin: float, dmax: float) -> str:
    """Small helper for reporting: classify a settled delay ratio."""
    if abs(ratio - 1.0) <= 0.02:
        return OUTCOME_1T
    if ratio <= dmin + 0.03:
        return OUTCOME_RMIN
    if ratio >= dmax - 0.03:
        return OUTCOME_RMAX
    if abs(ratio - round(ratio)) <= 0.02 and round(ratio) >= 2:
        return OUTCOME_HARM
    return OUTCOME_UNSET
