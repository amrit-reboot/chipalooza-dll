"""
v4 FINAL dynamic DLL/PFD engine — exact sub-step event timing (LEVEL B).

WHY v4 EXISTS
-------------
The v3 dynamic engine advanced edges and processed PFD events only on a coarse
integration grid. At 100 MHz / 100 substeps dt = 100 ps, while the modelled
reset delay is 5 ps and dead time 10 ps. That means:

  * reset was applied at the first grid point AFTER t_reset (up to 100 ps late);
  * every feedback edge that crossed the line end within a step was treated as
    arriving at a grid point (up to 100 ps early/late);
  * the dead-zone test compared a whole grid interval against t_dead, so a
    5 ps pulse could be integrated as a 100 ps pulse or dropped entirely;
  * charge was computed from the grid interval, not the true pulse duration.

v4 keeps the same 8-stage propagation physics but inserts EXACT event times
inside every integration step:

  * reference edges remain at exact nT;
  * each in-flight edge is advanced continuously and its line-exit time is
    solved inside the current step from the current stage delay;
  * PFD reset occurs at exactly t_event + t_reset (including t_reset = 0);
  * charge is integrated from the assertion time + t_dead to the exact event
    time, so sub-dead-time pulses deliver zero charge;
  * UP/DOWN assertion times are recorded for measurement.

The integration grid is still used for the slow co-evolution of the control
voltage while edges are in flight; the convergence study in
final_validation/ quantifies the remaining grid sensitivity.

LEVEL B ONLY. No transistors, no Sky130, no parasitics.
"""
from __future__ import annotations

import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "scripts"))
sys.path.insert(0, HERE)

import dll_model as base            # noqa: E402

N_STAGES = base.N_STAGES
BANDS = base.BANDS
VDD = base.VDD_NOM
line_delay = base.line_delay
u_for_delay = base.u_for_delay
band_for_freq = base.band_for_freq


def simulate_v4(
    f: float,
    band: int | None = None,
    start_ratio: float | None = None,
    u0: float = 1.0,
    cycles: int = 400,
    icp: float = 300e-6,
    c_loop: float = 25e-12,
    substeps: int = 1000,
    t_dead: float = 10e-12,
    t_reset: float = 5e-12,
    record_trace: bool = False,
    lock_tol: float = 0.02,
    lock_hold: int = 20,
) -> dict:
    """Exact-event dynamic simulation of the 8-stage DLL.

    start_ratio : initial D/T (overrides u0 when given).
    substeps    : integration grid points per reference period. Events are
                  placed exactly WITHIN each grid interval.
    """
    if band is None:
        band = band_for_freq(f)
    T = 1.0 / f
    dt = T / substeps
    if start_ratio is not None:
        d0 = start_ratio * T
        u = u_for_delay(d0, band) if d0 <= line_delay(0.0, band) else 0.0
    else:
        u = float(min(max(u0, 0.0), 1.0))
    u_seed = u

    up = down = False
    up_since = down_since = 0.0
    reset_at = None
    edges: list[float] = []            # stage progress of each in-flight edge
    launched = completed = 0
    ignored_ref = ignored_fb = 0

    t = 0.0
    q_up = q_down = 0.0
    u_hist, d_hist, t_hist = [], [], []
    q_hist = []
    trace = []
    reset_times = []

    # sampling: one control/delay value per reference edge
    steps_per_period = substeps

    def charge_over(a: float, b: float) -> float:
        """Exact signed charge over [a,b] using true assertion/dead times."""
        if b <= a:
            return 0.0
        if up == down:
            return 0.0
        if up:
            start = up_since + t_dead
        else:
            start = down_since + t_dead
        lo = max(a, start)
        if b <= lo:
            return 0.0
        return icp * (b - lo) * (1.0 if up else -1.0)

    def apply_charge(a: float, b: float):
        nonlocal u, q_up, q_down
        q = charge_over(a, b)
        if q != 0.0:
            if q > 0:
                q_up += q
            else:
                q_down += q
            u = min(max(u + q / (c_loop * VDD), 0.0), 1.0)
            q_hist.append(q)
            return q
        return 0.0

    def advance_edges(duration: float, u_now: float):
        """Advance all in-flight edges by a time interval at current stage delay."""
        stage_delay = line_delay(u_now, band) / N_STAGES
        dp = duration / stage_delay
        for i in range(len(edges)):
            edges[i] += dp

    total_steps = int(cycles * steps_per_period)
    for step in range(total_steps):
        t0 = step * dt

        # ---- reference edge at exact nT (step boundary) -------------------
        if step % steps_per_period == 0:
            d_hist.append(line_delay(u, band))
            u_hist.append(u)
            t_hist.append(t0)
            launched += 1
            edges.append(0.0)
            if not up:
                up = True
                up_since = t0
                if record_trace:
                    trace.append((t0, "UP", up, down))
            else:
                ignored_ref += 1
            if up and down and reset_at is None:
                reset_at = t0 + t_reset

        cur = t0
        t1 = t0 + dt
        guard = 0

        while guard < 8:
            guard += 1
            # candidate event times strictly after cur and up to t1
            stage_delay = line_delay(u, band) / N_STAGES
            candidates = []
            for p in edges:
                if p < N_STAGES:
                    te = cur + (N_STAGES - p) * stage_delay
                    if cur < te <= t1 + 1e-18:
                        candidates.append((min(te, t1), "fb"))
                    elif te <= cur:
                        candidates.append((cur, "fb"))
            if reset_at is not None and cur < reset_at <= t1 + 1e-18:
                candidates.append((min(reset_at, t1), "rst"))

            if not candidates:
                break
            te = min(x[0] for x in candidates)
            # integrate to the event
            apply_charge(cur, te)
            advance_edges(te - cur, u)
            cur = te

            # process all events at this exact time
            # feedback completions first
            still = []
            fb_now = False
            for p in edges:
                if p >= N_STAGES - 1e-12:
                    fb_now = True
                    completed += 1
                else:
                    still.append(p)
            edges = still
            if fb_now:
                if not down:
                    down = True
                    down_since = te
                    if record_trace:
                        trace.append((te, "DOWN", up, down))
                else:
                    ignored_fb += 1
                if up and down and reset_at is None:
                    reset_at = te + t_reset

            # reset (possibly with zero delay)
            do_reset = reset_at is not None and te >= reset_at - 1e-18
            if do_reset:
                reset_times.append(te)
                up = down = False
                reset_at = None
                if record_trace:
                    trace.append((te, "RESET", up, down))
                if t_reset == 0.0:
                    # immediate reset already applied; continue same interval
                    pass

        # integrate to the end of the grid interval
        apply_charge(cur, t1)
        advance_edges(t1 - cur, u)
        t = t1

    ratio = __import__("numpy").asarray(d_hist) / T
    n = len(ratio)
    tail = ratio[-max(20, n // 5):] if n else ratio
    final = float(tail.mean()) if n else float("nan")
    pp = float(tail.max() - tail.min()) if n else float("nan")
    k = int(round(final)) if final >= 0.75 else 0

    # lock time: first sample entering a sustained tol band around its final k
    lock_cycle = None
    inside = 0
    for i, r in enumerate(ratio):
        if abs(r - k) <= lock_tol:
            inside += 1
            if inside >= lock_hold:
                lock_cycle = i - lock_hold + 1
                break
        else:
            inside = 0

    rail_min = bool(u_hist and min(u_hist[-max(5, n // 20):]) <= 1e-12)
    rail_max = bool(u_hist and max(u_hist[-max(5, n // 20):]) >= 1 - 1e-12)
    oscillating = bool(pp > 0.05)

    return {
        "f": f, "band": band, "T": T, "dt_ps": dt * 1e12,
        "substeps": substeps, "icp": icp, "t_dead": t_dead, "t_reset": t_reset,
        "initial_ratio": float(ratio[0]) if n else float("nan"),
        "final_ratio": final, "harmonic_index": k, "settled_pp": pp,
        "lock_cycle": lock_cycle,
        "locked_1T": bool(k == 1 and abs(final - 1.0) <= lock_tol and not oscillating),
        "locked_harmonic": bool(k >= 1 and abs(final - k) <= lock_tol and not oscillating),
        "rail_min": rail_min, "rail_max": rail_max, "oscillating": oscillating,
        "ratio_hist": ratio, "u_hist": __import__("numpy").asarray(u_hist),
        "t_hist": __import__("numpy").asarray(t_hist),
        "u_seed": u_seed, "final_u": float(u_hist[-1]) if u_hist else u,
        "q_up": q_up, "q_down": q_down, "q_hist": __import__("numpy").asarray(q_hist),
        "edge_launched": launched, "edge_completed": completed,
        "in_flight_end": len(edges),
        "ignored_ref": ignored_ref, "ignored_fb": ignored_fb,
        "reset_times": reset_times, "trace": trace if record_trace else None,
    }
