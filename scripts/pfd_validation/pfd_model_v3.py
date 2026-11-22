"""
v3 CORRECTED behavioral DLL / PFD model  (LEVEL B)

This file does NOT modify v1 (pfd_event_model.py) or the earlier audit model.
It fixes the ERROR IN INTERPRETATION that produced the v1 headline:

    v1 experiments used up_direction = -1  ("UP increases the line delay")
    for the whole 77-point acquisition grid. That is the WRONG sign for a DLL
    whose feedback is a delayed copy of the reference:

        A net UP pulse is produced whenever D is not an integer multiple of T.
        With UP increasing D, the loop always moves away from the wrap point,
        so it must end at the maximum-delay rail.  Hence 77/77 rail.

    With the physically correct sign (UP pulse -> VCTRL rises -> current-starved
    delay FALLS), the loop converges to the nearest integer multiple of T from
    ABOVE.  1T is a genuine stable equilibrium, with basin D in (T, 2T).

WHAT v3 ADDS
------------
  * `up_direction=+1` is the documented, physically correct default.
  * `coarse_preset` places the initial delay in a chosen window, so the
    acquisition basin can be explored independently of the delay-band limits.
  * a second, independent `simulate_dynamic()` engine that propagates each
    edge through 8 stages with the control voltage changing WHILE the edge is
    in flight. This audits the quasi-static "delay latched at launch" assumption
    used by the event scheduler.
  * explicit harmonic classification.

LEVEL B ONLY. No transistors, no Sky130, no parasitics.
"""
from __future__ import annotations

import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
sys.path.insert(0, HERE)

import dll_model as base          # noqa: E402
import pfd_event_model as v1      # noqa: E402  (deliberately unmodified)

N_STAGES = base.N_STAGES
BANDS = base.BANDS
VDD_NOM = base.VDD_NOM
line_delay = base.line_delay
line_kd = base.line_kd
band_for_freq = base.band_for_freq
u_for_delay = base.u_for_delay


# ---------------------------------------------------------------------------
# Corrected event-driven acquisition (v1 engine, correct polarity)
# ---------------------------------------------------------------------------
def simulate_event(
    f: float,
    band: int | None = None,
    u0: float = 1.0,
    coarse_preset: float | None = None,
    cycles: int = 4000,
    icp: float = 300e-6,
    c_loop: float = 25e-12,
    t_dead: float = 10e-12,
    t_reset: float = 5e-12,
) -> dict:
    """Event-driven DLL acquisition with the CORRECT charge-pump polarity.

    coarse_preset : initial line delay expressed as a multiple of T. If given,
                    it overrides u0 (this is a proposed startup aid, NOT part of
                    the official architecture).
    """
    if band is None:
        band = band_for_freq(f)
    T = 1.0 / f
    if coarse_preset is not None:
        d0 = coarse_preset * T
        u0 = u_for_delay(d0, band) if d0 <= line_delay(0.0, band) else 0.0

    r = v1.simulate_event_pfd(
        f, band=band, u0=u0, cycles=cycles, icp=icp, c_loop=c_loop,
        t_dead=t_dead, t_reset=t_reset, up_direction=+1,
    )

    ratio = r["ratio_hist"]
    tail = ratio[-max(50, len(ratio) // 5):]
    final = float(np.mean(tail))
    pp = float(np.max(tail) - np.min(tail))
    settled = pp < max(0.02, 3 * 0.02)
    # A delay well below T that ends at the band's minimum is the k=0 basin
    # (the line has ratcheted to its rail), NOT a 1T lock. Do not label 0.68T
    # as "harmonic 1" just because round(0.68) == 1.
    k = int(round(final)) if final >= 0.75 else 0
    r.update({
        "final_ratio": final,
        "harmonic_index": k,
        "settled_pp": pp,
        "locked_1T": bool(abs(final - 1.0) < 0.02 and settled),
        "locked_harmonic": bool(k >= 1 and abs(final - k) < 0.02 and settled),
        "locked_zero": bool(k == 0 and settled),
        "incorrect_harmonic": bool(k > 1 and settled),
        "settled": bool(settled),
        "initial_ratio": float(ratio[0]) if len(ratio) else float("nan"),
    })
    return r


# ---------------------------------------------------------------------------
# Independent dynamic-delay engine (control changes while edges are in flight)
# ---------------------------------------------------------------------------
def simulate_dynamic(
    f: float,
    band: int | None = None,
    start_ratio: float = 1.2,
    cycles: int = 400,
    icp: float = 300e-6,
    c_loop: float = 25e-12,
    substeps: int = 200,
    t_dead: float = 10e-12,
    t_reset: float = 5e-12,
) -> dict:
    """Discrete-time physical model: 8 delay stages, edges advance through the
    line at a rate set by the CURRENT control voltage.

    Each in-flight edge carries a stage position p in [0, N_STAGES). During a
    time step dt, p advances by dt / t_stage(u). If p reaches N_STAGES the edge
    emerges and is presented to the PFD. Both the reference and feedback clocks
    are continuous periodic edge trains.
    """
    if band is None:
        band = band_for_freq(f)
    T = 1.0 / f
    dt = T / substeps
    d0 = start_ratio * T
    u = u_for_delay(d0, band) if d0 <= line_delay(0.0, band) else 0.0
    u_seed = u

    up = down = False
    reset_at = None
    in_flight: list[float] = []      # stage progress of each propagating edge

    u_hist, d_hist = [], []
    q_hist = []
    step = 0
    total_steps = int(cycles * substeps)

    while step < total_steps:
        t = step * dt

        # PFD reset after t_reset
        if reset_at is not None and t >= reset_at:
            up = down = False
            reset_at = None

        # Reference rising edge at every whole period
        if step % substeps == 0:
            d_hist.append(line_delay(u, band))
            u_hist.append(u)
            if not up:
                up = True
            in_flight.append(0.0)
            if up and down and reset_at is None:
                reset_at = t + t_reset

        # Advance edges through the line at the instantaneous stage delay
        stage_delay = line_delay(u, band) / N_STAGES
        remaining = []
        fb_arrived = False
        for p in in_flight:
            p += dt / stage_delay
            if p >= N_STAGES:
                fb_arrived = True
            else:
                remaining.append(p)
        in_flight = remaining
        if fb_arrived:
            if not down:
                down = True
            if up and down and reset_at is None:
                reset_at = t + t_reset

        # Charge pump over this step
        q = 0.0
        if up != down:
            pulse = dt if reset_at is None or t + dt <= reset_at else max(0.0, reset_at - t)
            if pulse >= t_dead:
                q = icp * pulse * (1.0 if up else -1.0)
                q_hist.append(q)
                u = min(max(u + (q / (c_loop * VDD_NOM)), 0.0), 1.0)
        step += 1

    ratio = np.asarray(d_hist) / T
    tail = ratio[-max(20, len(ratio) // 5):]
    final = float(np.mean(tail))
    k = int(round(final)) if final >= 0.75 else 0
    return {
        "band": band, "T": T, "final_ratio": final, "harmonic_index": k,
        "final_u": float(u_hist[-1]) if u_hist else u,
        "settled_pp": float(np.max(tail) - np.min(tail)),
        "initial_ratio": float(ratio[0]) if len(ratio) else float("nan"),
        "ratio_hist": ratio, "u_hist": np.asarray(u_hist),
        "u_seed": u_seed, "q_hist": np.asarray(q_hist),
    }


def d_min_max(band: int) -> tuple[float, float]:
    b = BANDS[band]
    return N_STAGES * b["t_lo"], N_STAGES * b["t_hi"]
