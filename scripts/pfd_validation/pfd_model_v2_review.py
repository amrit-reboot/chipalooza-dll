"""
REVIEW / AUDIT model — Level B behavioral.

Preserves the v1 event-driven PFD semantics exactly (pfd_event_model.py is NOT
modified) and adds:

  1. Charge accounting, so the net charge per reference period can be measured
     directly instead of inferred from the control voltage.
  2. Two alternative detectors for comparison:
        "pfd"       : two-latch PFD, reset when both outputs are high (v1 behaviour)
        "pd_linear" : phase detector with a zero at every multiple of T
  3. A cycle-accurate trace of reference edges, feedback edges, UP and DOWN.

The point of this file is to answer, with evidence, whether the v1 railing
behaviour is (a) a coding bug, (b) a property of the two-latch PFD, or (c) a
fundamental limit of DLL topology. Those three possibilities have very different
consequences for the architecture.

LEVEL B. No transistors, no Sky130, no parasitics.
"""

from __future__ import annotations

import heapq
import os
import sys

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(_HERE))
import dll_model as base  # noqa: E402

N_STAGES = base.N_STAGES
BANDS = base.BANDS
VDD_NOM = base.VDD_NOM
line_delay = base.line_delay
line_kd = base.line_kd
band_for_freq = base.band_for_freq
u_for_delay = base.u_for_delay


# ===========================================================================
# 1. Event-driven two-latch PFD with charge accounting (v1 semantics)
# ===========================================================================
def simulate_pfd(
    f: float,
    band: int | None = None,
    u0: float = 1.0,
    cycles: int = 200,
    icp: float = 300e-6,
    c_loop: float = 25e-12,
    vdd: float = VDD_NOM,
    t_dead: float = 10e-12,
    t_reset: float = 5e-12,
    up_direction: int = -1,
    fixed_delay: float | None = None,
    freeze: bool = False,
    freeze_delay: bool = False,
    record_trace: bool = False,
) -> dict:
    """Two-latch PFD. Identical edge policy to v1, plus charge accounting.

    Charge is accumulated as signed current*time so that the net charge per
    period can be compared against the theoretical sawtooth directly.
    """
    if band is None:
        band = band_for_freq(f)
    T = 1.0 / f
    u = float(np.clip(u0, 0.0, 1.0))
    u_seed = u

    if freeze:
        icp = 0.0

    up = down = False
    reset_pending = False
    seq = 0
    heap: list = []
    t_start = max(0.0, -(fixed_delay or 0.0))

    def push(t, typ):
        nonlocal seq
        heapq.heappush(heap, (t, seq, typ))
        seq += 1

    push(t_start, "ref")
    if fixed_delay is not None and fixed_delay < 0:
        push(t_start + fixed_delay, "fb")

    t_now = 0.0
    ref_seen = 0
    q_net = 0.0            # signed charge into the loop capacitor [C]
    q_up = 0.0             # charge delivered while UP only
    q_down = 0.0
    trace = []
    per_period_q = []
    period_q = 0.0

    u_hist, d_hist = [], []

    def integrate(t0, t1):
        nonlocal u, q_net, q_up, q_down, period_q
        dt = t1 - t0
        if dt <= 0.0 or up == down:
            return
        if dt < t_dead:
            return
        if up:
            dq = icp * dt
            q_up += dq
        else:
            dq = -icp * dt
            q_down += dq
        q_net += dq
        period_q += dq
        if not freeze and not freeze_delay:
            u = min(max(u + (dq / (c_loop * vdd)) * up_direction, 0.0), 1.0)

    while ref_seen < cycles and heap:
        t, _, typ = heapq.heappop(heap)
        integrate(t_now, t)
        t_now = t

        if typ == "ref":
            ref_seen += 1
            d_now = float(fixed_delay) if fixed_delay is not None else line_delay(u, band)
            u_hist.append(u)
            d_hist.append(d_now)
            per_period_q.append(period_q)
            period_q = 0.0
            push(t + d_now, "fb")
            push(t + T, "ref")
            if not up:
                up = True
                if record_trace:
                    trace.append((t, "UP"))
            if up and down and not reset_pending:
                reset_pending = True
                push(t + t_reset, "rst")
        elif typ == "fb":
            if not down:
                down = True
                if record_trace:
                    trace.append((t, "DOWN"))
            if up and down and not reset_pending:
                reset_pending = True
                push(t + t_reset, "rst")
        else:
            if record_trace:
                trace.append((t, "RESET"))
            up = down = False
            reset_pending = False

    # The first UP pulse is truncated only when the first feedback edge arrives,
    # which is ceil(D/T) periods for D > T. Discard that startup transient plus
    # the empty interval before the first reference edge.
    d_seed = fixed_delay if fixed_delay is not None else line_delay(u_seed, band)
    n_skip = int(np.ceil(d_seed / T)) + 1
    steady_q = per_period_q[n_skip:] if len(per_period_q) > n_skip + 4 else per_period_q
    n = max(1, len(steady_q))
    avg_q = float(np.sum(steady_q) / n)     # steady-state charge per reference period

    return {
        "T": T, "f": f, "band": band,
        "q_per_period": avg_q,
        "q_per_period_over_icpT": avg_q / (icp * T) if icp else 0.0,
        "q_per_period_hist": np.asarray(per_period_q),
        "q_up": q_up, "q_down": q_down, "q_net": q_net,
        "u_hist": np.asarray(u_hist),
        "ratio_hist": np.asarray(d_hist) / T,
        "d_hist": np.asarray(d_hist),
        "final_u": float(u_hist[-1]) if u_hist else u0,
        "final_ratio": float(d_hist[-1] / T) if d_hist else float("nan"),
        "trace": trace if record_trace else None,
    }


# ===========================================================================
# 2. Phase detector with a zero at every multiple of T
# ===========================================================================
def simulate_pd_linear(
    f: float,
    band: int | None = None,
    u0: float = 1.0,
    cycles: int = 2000,
    icp: float = 300e-6,
    c_loop: float = 25e-12,
    vdd: float = VDD_NOM,
    t_dead: float = 10e-12,
) -> dict:
    """Idealised phase detector: output proportional to the phase error measured
    against the NEAREST multiple of T, with a zero at each of those multiples.

        err = D - k*T,  k = round(D/T)

    Positive err (delay too long) -> increase control -> reduce delay.
    This is the detector characteristic a DLL needs in order to have an
    equilibrium at D = kT. Used as a counterexample to "a DLL cannot lock".
    """
    if band is None:
        band = band_for_freq(f)
    T = 1.0 / f
    u = float(np.clip(u0, 0.0, 1.0))
    u_hist, d_hist, err_hist = [], [], []

    for _ in range(cycles):
        d = line_delay(u, band)
        k = int(round(d / T))
        err = d - k * T
        u_hist.append(u)
        d_hist.append(d)
        err_hist.append(err)
        if abs(err) > t_dead:
            du = (icp / (c_loop * vdd)) * abs(err) * (1.0 if err > 0 else -1.0)
            u = min(max(u + du, 0.0), 1.0)

    d_hist = np.asarray(d_hist)
    ratio = d_hist / T
    tail = ratio[-max(50, len(ratio) // 5):]
    final = float(np.mean(tail))
    harmonic = int(round(final))
    pp = float(np.max(tail) - np.min(tail))
    return {
        "T": T, "final_ratio": final, "harmonic_index": harmonic,
        "final_delay_ps": final * T * 1e12, "final_u": float(u_hist[-1]),
        "settled_pp": pp, "locked_1T": bool(abs(final - 1.0) < 0.02 and pp < 0.02),
        "ratio_hist": ratio,
    }


# ===========================================================================
# 3. Theoretical transfer characteristics
# ===========================================================================
def q_pfd_theory(d_over_t: float) -> float:
    """Net charge per reference period for the two-latch PFD, in units of Icp*T.

    Derived in the report:
        Q(D) = Icp * frac(D/T) * T
    i.e. a sawtooth that rises from 0 to Icp*T across each period and jumps back
    to 0 at every multiple of T.
    """
    return d_over_t % 1.0


def q_pd_linear_theory(d_over_t: float) -> float:
    """Net charge per period for the nearest-multiple phase detector, Icp*T units.

    Q(D) = Icp * (D - k*T) with k = round(D/T): a triangular sawtooth that
    crosses zero at every multiple of T with a NEGATIVE slope (restoring).
    """
    k = round(d_over_t)
    return d_over_t - k
