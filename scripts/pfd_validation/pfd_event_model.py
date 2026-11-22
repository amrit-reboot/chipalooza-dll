"""
Event-driven behavioral PFD model (LEVEL B).

WHY THIS EXISTS
---------------
The original model in scripts/dll_model.py computes

    err_raw = t_line - T
    err     = clip(err_raw, -T/2, +T/2)        # sign preserved

and integrates a correction proportional to that number. That is not a phase
detector. It is an ORACLE: the loop is told the exact delay error relative to
exactly ONE reference period. Consequences:

  * The loop can never lock at 2T or 3T, because the error is always measured
    against 1T. Harmonic locking is impossible BY CONSTRUCTION, so the earlier
    "55/55 true lock, zero false locks" result was guaranteed by the model, not
    discovered from it.
  * A delay of 1.2T produces the same error (+0.2T) as a delay of 0.2T would if
    it were not clipped, so the distinction between "slightly late" and "a whole
    period late" is erased.
  * Large errors are silently capped at T/2 instead of producing a saturated
    output, which removes the PFD's frequency-detection behaviour entirely.

WHAT A REAL EDGE-TRIGGERED PFD DOES
-----------------------------------
A classic two-latch PFD only knows EDGE ORDER:

    reference rising edge  -> set UP
    feedback  rising edge  -> set DOWN
    both high              -> reset both after t_reset
    one high, no edge yet  -> output stays asserted (frequency detection)

The information available is the arrival ORDER and the WIDTH of the resulting
pulses. There is no internal notion of "which cycle" the feedback edge belongs
to. If the steady-state feedback clock has the same frequency as the reference,
then a delay of k*T produces perfectly aligned edges for EVERY integer k, and the
PFD cannot tell k = 1 from k = 0 or k = 3. That ambiguity is the physical origin
of harmonic locking and it is represented here by construction, not suppressed.

CHARGE PUMP / CONTROL POLARITY
------------------------------
Two polarities are physically realisable depending on how VCTRL drives the
starving device:

    up_direction = +1 : UP current raises VCTRL  -> delay DECREASES
    up_direction = -1 : UP current lowers VCTRL  -> delay INCREASES

Which one is correct is not an assumption to be waved through: both are run and
the consequence is reported. Only one of them can produce negative feedback for
the intended "start at minimum delay and slow the line down" startup strategy.

LEVEL
-----
Level B behavioral. No transistors, no Sky130 models. The delay characteristic is
still the algebraic one from dll_model.py so that the ONLY thing being changed is
the detector.
"""

from __future__ import annotations

import heapq
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import dll_model as base  # noqa: E402  (delay characteristic reused, unmodified)

N_STAGES = base.N_STAGES
BANDS = base.BANDS
VDD_NOM = base.VDD_NOM

line_delay = base.line_delay
line_kd = base.line_kd
band_for_freq = base.band_for_freq
stage_delay = base.stage_delay
u_for_delay = base.u_for_delay


# ---------------------------------------------------------------------------
def simulate_event_pfd(
    f: float,
    band: int | None = None,
    u0: float = 1.0,
    cycles: int = 3000,
    icp: float = 300e-6,
    c_loop: float = 25e-12,
    vdd: float = VDD_NOM,
    t_dead: float = 10e-12,
    t_reset: float = 5e-12,
    updown_mismatch: float = 0.0,
    up_direction: int = -1,
    freeze_control: bool = False,
    fixed_delay: float | None = None,
    record_transitions: bool = False,
    lock_tol_frac: float = 0.02,
    lock_hold_cycles: int = 40,
) -> dict:
    """Simulate the DLL with a genuine edge-triggered PFD.

    Parameters
    ----------
    f : reference frequency [Hz]
    band : delay-line band; defaults to the specified band for f
    u0 : initial normalised control voltage (1.0 = minimum delay)
    cycles : number of reference periods to simulate
    icp : charge-pump current [A]
    c_loop : loop capacitance [F]
    vdd : supply [V]
    t_dead : charge-pump dead zone; charge intervals shorter than this deliver no
             charge (represents PFD/CP response time)
    t_reset : PFD reset delay [s]
    updown_mismatch : fractional UP/DOWN current mismatch (0.02 = 2%)
    up_direction : +1 -> UP raises VCTRL (delay falls); -1 -> UP lowers VCTRL
    freeze_control : if True the charge pump is disconnected (icp effectively 0)
                     so the delay stays fixed; used for detector unit tests
    record_transitions : return the raw UP/DOWN transition list
    fixed_delay : if set, the line delay is held at this exact value and the
                  control voltage is not used. Used by the detector unit tests to
                  present arbitrary delays (including > 1 T) to the PFD.
    """
    if band is None:
        band = band_for_freq(f)
    if up_direction not in (-1, 1):
        raise ValueError("up_direction must be -1 or +1")

    T = 1.0 / f
    u = float(np.clip(u0, 0.0, 1.0))

    i_up = icp * (1.0 + 0.5 * updown_mismatch)
    i_down = icp * (1.0 - 0.5 * updown_mismatch)
    if freeze_control:
        i_up = i_down = 0.0

    # PFD latch state
    up = False
    down = False
    reset_pending = False

    seq = 0
    heap: list = []

    # A negative fixed_delay represents a feedback clock that is phase-advanced
    # relative to the reference. Shift the timeline so the first feedback edge is
    # never scheduled before t = 0.
    t_start = max(0.0, -(fixed_delay or 0.0))

    def push(t, typ):
        nonlocal seq
        heapq.heappush(heap, (t, seq, typ))
        seq += 1

    push(t_start, "ref")

    # Phase-advanced feedback: the edge leaving the line before t_start must be
    # present at t = t_start + fixed_delay, otherwise the very first comparison
    # would be presented out of order.
    if fixed_delay is not None and fixed_delay < 0:
        push(t_start + fixed_delay, "fb")

    t_now = 0.0
    ref_seen = 0
    events = 0
    max_events = 40 * cycles + 1000

    u_hist, d_hist, t_hist = [], [], []
    transitions = []
    rail_low_cycles = 0
    rail_high_cycles = 0

    def integrate(t0, t1):
        """Integrate charge-pump current on the loop capacitor over [t0, t1]."""
        nonlocal u
        dt = t1 - t0
        if dt <= 0.0:
            return
        if up == down:
            return
        if dt < t_dead:
            return
        if up:
            du = (i_up / (c_loop * vdd)) * dt * up_direction
        else:
            du = -(i_down / (c_loop * vdd)) * dt * up_direction
        u = min(max(u + du, 0.0), 1.0)

    while ref_seen < cycles and heap and events < max_events:
        t, _, typ = heapq.heappop(heap)
        events += 1
        integrate(t_now, t)
        t_now = t

        if typ == "ref":
            ref_seen += 1
            d_now = float(fixed_delay) if fixed_delay is not None else float(spatial_delay(u, band))
            u_hist.append(u)
            d_hist.append(d_now)
            t_hist.append(t)
            # This edge emerges from the line d_now later.
            push(t + d_now, "fb")
            push(t + T, "ref")
            if not up:
                up = True
                if record_transitions:
                    transitions.append((t, "UP", True))
                if down and not reset_pending:
                    reset_pending = True
                    push(t + t_reset, "rst")
        elif typ == "fb":
            if not down:
                down = True
                if record_transitions:
                    transitions.append((t, "DOWN", True))
                if up and not reset_pending:
                    reset_pending = True
                    push(t + t_reset, "rst")
        else:  # reset
            up = False
            down = False
            reset_pending = False
            if record_transitions:
                transitions.append((t, "RESET", False))

        if up is False and down is False and u <= 0.0:
            rail_low_cycles += 1
        if u >= 1.0:
            rail_high_cycles += 1

    u_hist = np.asarray(u_hist)
    d_hist = np.asarray(d_hist)
    ratio = d_hist / T

    analysis = _analyse(ratio, u_hist, T, ref_seen, lock_tol_frac, lock_hold_cycles)

    return {
        "f": f,
        "band": band,
        "T": T,
        "T_ps": T * 1e12,
        "u_hist": u_hist,
        "d_hist": d_hist,
        "ratio_hist": ratio,
        "t_hist": np.asarray(t_hist),
        "up_direction": up_direction,
        "cycles_run": ref_seen,
        "transitions": transitions if record_transitions else None,
        "rail_low_events": rail_low_cycles,
        "rail_high_events": rail_high_cycles,
        **analysis,
    }


def spatial_delay(u: float, band: int) -> float:
    """Total line delay for control u. Wrapper kept explicit for clarity."""
    return line_delay(u, band)


def _analyse(ratio, u_hist, T, n, tol_frac, hold):
    """Classify the endpoint: 1T lock, other harmonic, no lock, oscillation."""
    if len(ratio) == 0:
        return {
            "harmonic_index": 0, "locked_1T": False, "locked_any": False,
            "lock_cycle": None, "final_ratio": float("nan"),
            "final_u": float("nan"), "final_delay_ps": float("nan"),
            "settled_pp_frac_T": float("nan"), "oscillating": False,
            "rail_saturated": False, "phase_error_frac_T": float("nan"),
        }

    # Lock at 1T: error inside tolerance sustained for `hold` cycles.
    inside = 0
    lock_cycle = None
    for i, r in enumerate(ratio):
        if abs(r - 1.0) <= tol_frac:
            inside += 1
            if inside >= hold and lock_cycle is None:
                lock_cycle = i + 1
        else:
            inside = 0

    tail = ratio[-max(50, len(ratio) // 5):]
    final_ratio = float(np.mean(tail))
    harmonic = int(round(final_ratio))
    settled_pp = float(np.max(tail) - np.min(tail))
    oscillating = settled_pp > max(0.05, 4 * tol_frac)

    locks_1t = lock_cycle is not None and abs(final_ratio - 1.0) <= tol_frac and not oscillating
    locks_any = harmonic >= 1 and settled_pp <= max(0.05, 4 * tol_frac)

    u_tail = u_hist[-max(50, len(u_hist) // 5):]
    rail = bool(np.mean(u_tail <= 0.0) > 0.5 or np.mean(u_tail >= 1.0) > 0.5)

    return {
        "harmonic_index": harmonic,
        "locked_1T": bool(locks_1t),
        "locked_any": bool(locks_any),
        "lock_cycle": lock_cycle,
        "final_ratio": final_ratio,
        "final_u": float(u_hist[-1]),
        "final_delay_ps": float(final_ratio * T * 1e12),
        "settled_pp_frac_T": settled_pp,
        "oscillating": bool(oscillating),
        "rail_saturated": rail,
        "phase_error_frac_T": float(abs(final_ratio - harmonic)),
    }


# ---------------------------------------------------------------------------
# Detector unit-test helpers
# ---------------------------------------------------------------------------
def measure_pulses(delay: float, f: float, band: int = 1, cycles: int = 6,
                   t_reset: float = 5e-12) -> list:
    """Freeze the control and return the raw transition list for `delay`.

    `delay` is the fixed total line delay in seconds. Used to prove the detector
    responds correctly to reference-leading and feedback-leading edge cases.
    """
    res = simulate_event_pfd(
        f, band=band, cycles=cycles, freeze_control=True,
        t_reset=t_reset, record_transitions=True, fixed_delay=delay,
    )
    return res["transitions"]
