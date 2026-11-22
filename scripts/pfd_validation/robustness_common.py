"""
Shared helpers for the Phase-4 acquisition-robustness investigation (LEVEL B).

This module is INVESTIGATION ONLY. It does not modify any validated model or
the Phase-3 controller. All outcomes are derived from measured v4 results.
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

FREQS_HZ = [25e6, 30e6, 50e6, 75e6, 100e6, 150e6, 200e6]
ICPS_A = [50e-6, 75e-6, 100e-6, 125e-6, 150e-6, 200e-6, 250e-6, 300e-6]
INITIAL_LABELS = ["min", "max", "0.68", "0.90", "1.00", "1.02", "1.05",
                  "1.10", "1.30", "1.50", "1.95", "2.10", "2.50"]

OUT_1T = "1T_LOCK"
OUT_RMIN = "MIN_DELAY_RAIL"
OUT_RMAX = "MAX_DELAY_RAIL"
OUT_UNSET = "UNSETTLED"


def classify(r: dict, dmin: float, dmax: float, tol: float = 0.02) -> str:
    """Classify a v4 result from measured ratio/index/ripple."""
    ratio = r["final_ratio"]
    k = r["harmonic_index"]
    if k == 1 and abs(ratio - 1.0) <= tol and r["settled_pp"] <= 0.05:
        return OUT_1T
    if ratio <= dmin + 0.03:
        return OUT_RMIN
    if ratio >= dmax - 0.03:
        return OUT_RMAX
    if k >= 2 and abs(ratio - k) <= tol:
        return f"HARMONIC_{k}T_LOCK"
    return OUT_UNSET


def d_limits(f: float, band: int):
    T = 1.0 / f
    return m.line_delay(1.0, band) / T, m.line_delay(0.0, band) / T


def u_for_ratio(ratio: float, f: float, band: int) -> float:
    dmin, dmax = d_limits(f, band)
    if ratio >= dmax:
        return 0.0
    if ratio <= dmin:
        return 1.0
    return m.u_for_delay(ratio / f, band)


def init_u(label: str, f: float, band: int):
    if label == "min":
        return 1.0
    if label == "max":
        return 0.0
    return u_for_ratio(float(label), f, band)


def loop_gain_metrics(f: float, band: int, icp: float, c_loop: float = 25e-12,
                      vdd: float = 1.8) -> dict:
    """First-order analytical loop-gain metrics at the D=T operating point.

    Q per cycle      = Icp * frac(D/T) * T
    dD/du            = line_kd(u, band)
    du per cycle     = Icp * T * frac / (C * VDD)
    d(D/T) per cycle = |line_kd| * Icp * frac / (C * VDD)   (T cancels EXCEPT
                       through line_kd(u at D=T), which differs per band)
    """
    T = 1.0 / f
    u1 = u_for_ratio(1.0, f, band)
    kd = abs(m.line_kd(u1, band))
    g_abs = kd * icp / (c_loop * vdd)                 # d(D/T)/cycle per unit frac
    frac_step = 0.05
    return {
        "u_at_1T": u1,
        "line_kd_s_per_u": kd,
        "charge_per_cycle_per_frac_C": icp * T,
        "du_per_cycle_per_frac": icp * T / (c_loop * vdd),
        "d_D_over_T_per_cycle_per_frac": g_abs,
        "d_D_over_T_per_cycle_frac005": g_abs * frac_step,
        "T_ns": T * 1e9,
    }
