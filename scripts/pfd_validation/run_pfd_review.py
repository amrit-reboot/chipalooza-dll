"""
Independent review experiments for Problem 1 (LEVEL B behavioral).

Preserves all earlier code/results. Writes only to results/pfd_validation/review/.

Run: python scripts/pfd_validation/run_pfd_review.py
"""
from __future__ import annotations

import csv
import os
import sys

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
sys.path.insert(0, HERE)

import dll_model as base            # noqa: E402
import pfd_event_model as v1        # noqa: E402  (unmodified)
import pfd_model_v2_review as v2    # noqa: E402
import pfd_model_v3 as v3           # noqa: E402

OUT = os.path.join(ROOT, "results", "pfd_validation", "review")
TABLES = os.path.join(OUT, "tables")
PLOTS = os.path.join(OUT, "plots")
LOGS = os.path.join(OUT, "logs")
for d in (TABLES, PLOTS, LOGS):
    os.makedirs(d, exist_ok=True)

FREQS_MHZ = [25, 30, 42.5, 50, 60, 85, 100, 120, 150, 180, 200]
U0_LIST = [0.0, 0.1, 0.25, 0.5, 0.75, 0.9, 1.0]
ICP, C_LOOP = 300e-6, 25e-12
CYCLES = 3000
T = 1e-8


def write_csv(name, header, rows):
    with open(os.path.join(TABLES, name), "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(header)
        w.writerows(rows)


# ---------------------------------------------------------------------------
# R1: 77-point grid, old (wrong) polarity vs correct polarity
# ---------------------------------------------------------------------------
def r1_polarity_grid():
    rows = []
    for fmhz in FREQS_MHZ:
        f = fmhz * 1e6
        band = v3.band_for_freq(f)
        for u0 in U0_LIST:
            wrong = v1.simulate_event_pfd(f, band=band, u0=u0, cycles=CYCLES,
                                          icp=ICP, c_loop=C_LOOP, up_direction=-1)
            right = v3.simulate_event(f, band=band, u0=u0, cycles=CYCLES,
                                      icp=ICP, c_loop=C_LOOP)
            rows.append([f"{fmhz:g}", band, f"{u0:.2f}",
                         f"{wrong['final_ratio']:.3f}",
                         "RAIL_MAX" if wrong["final_u"] < 1e-9 else "other",
                         f"{right['final_ratio']:.3f}",
                         right["harmonic_index"],
                         "LOCK_1T" if right["locked_1T"] else "NO_1T_LOCK"])
    write_csv("r1_polarity_grid.csv",
              ["f_MHz", "band", "u0", "wrong_final_D_over_T", "wrong_state",
               "correct_final_D_over_T", "correct_harmonic", "correct_result"], rows)
    return rows


# ---------------------------------------------------------------------------
# R2: basin maps at 100 MHz, quasi-static event vs dynamic propagation
# ---------------------------------------------------------------------------
def r2_basin_maps():
    f = 100e6
    starts = np.round(np.arange(0.60, 3.01, 0.05), 3)
    rows = []
    ev_finals, dy_finals = [], []
    for s in starts:
        e = v3.simulate_event(f, band=1, coarse_preset=float(s), cycles=2500)
        d = v3.simulate_dynamic(f, band=1, start_ratio=float(s),
                                cycles=1200, substeps=100)
        ev_finals.append(e["final_ratio"])
        dy_finals.append(d["final_ratio"])
        rows.append([f"{s:.2f}", f"{e['final_ratio']:.3f}", e["harmonic_index"],
                     f"{d['final_ratio']:.3f}", d["harmonic_index"]])
    write_csv("r2_basin_maps.csv",
              ["start_D_over_T", "event_final", "event_harmonic",
               "dynamic_final", "dynamic_harmonic"], rows)

    fig, ax = plt.subplots(figsize=(9, 5))
    ax.plot(starts, ev_finals, "o-", ms=3, label="event (delay latched at launch)")
    ax.plot(starts, dy_finals, "s-", ms=3, label="dynamic (8-stage propagation)")
    for k in (1, 2, 3):
        ax.axhline(k, color="r", ls="--", lw=0.8)
        ax.text(2.95, k + 0.04, f"{k}T", color="r", fontsize=9)
    ax.set_xlabel("initial line delay D0 / T")
    ax.set_ylabel("final settled delay / T")
    ax.set_title("Acquisition basins at 100 MHz - corrected CP polarity")
    ax.grid(alpha=0.3)
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(os.path.join(PLOTS, "r2_basin_maps.png"), dpi=150)
    plt.close(fig)
    return rows


# ---------------------------------------------------------------------------
# R3: edge timing diagrams near 0T, 1T, 2T
# ---------------------------------------------------------------------------
def r3_timing_diagrams():
    cases = [(0.90, "D = 0.90 T"), (1.00, "D = 1.00 T"),
             (1.10, "D = 1.10 T"), (2.00, "D = 2.00 T")]
    fig, axes = plt.subplots(len(cases), 1, figsize=(10, 8), sharex=True)
    for ax, (ratio, title) in zip(axes, cases):
        r = v2.simulate_pfd(100e6, band=1, cycles=5, icp=ICP, c_loop=C_LOOP,
                            fixed_delay=ratio * T, freeze_delay=True,
                            up_direction=+1, record_trace=True)
        tr = r["trace"]
        for x in range(4):
            ax.plot([x, x], [1.25, 1.85], color="C0", lw=1.5)
            ax.text(x, 1.88, "ref", color="C0", fontsize=7, ha="center")
        for i in range(4):
            x = i + ratio
            ax.plot([x, x], [0.95, 1.55], color="C1", lw=1.5)
            ax.text(x, 0.90, "fb", color="C1", fontsize=7, ha="center")

        up_t = None
        for t, kind in tr:
            if t / T > 3.2:
                break
            if kind == "UP":
                up_t = t / T
            elif kind == "RESET":
                if up_t is not None:
                    ax.plot([up_t, t / T], [0.55, 0.55], color="C2", lw=4,
                            solid_capstyle="butt")
                    ax.text((up_t + t / T) / 2, 0.40, "UP", color="C2",
                            fontsize=7, ha="center")
                up_t = None
        ax.set_yticks([0.4, 1.25])
        ax.set_yticklabels(["PFD", "clocks"])
        ax.set_ylabel(title, fontsize=9)
        ax.grid(axis="x", alpha=0.2)
    axes[-1].set_xlabel("time / reference period T")
    fig.suptitle("Event timing near 0T, 1T and 2T (frozen delay, Level B)",
                 fontsize=11)
    fig.tight_layout(rect=(0, 0, 1, 0.96))
    fig.savefig(os.path.join(PLOTS, "r3_timing_diagrams.png"), dpi=150)
    plt.close(fig)


# ---------------------------------------------------------------------------
# R4: charge transfer characteristic
# ---------------------------------------------------------------------------
def r4_charge_transfer():
    ratios = np.round(np.arange(0.05, 3.001, 0.05), 3)
    measured = []
    for r in ratios:
        res = v2.simulate_pfd(100e6, band=1, cycles=40, icp=ICP, c_loop=C_LOOP,
                              fixed_delay=float(r) * T, freeze_delay=True,
                              up_direction=+1)
        measured.append(res["q_per_period_over_icpT"])
    theory = [v2.q_pfd_theory(float(r)) for r in ratios]
    write_csv("r4_charge_transfer.csv",
              ["D_over_T", "Q_measured_over_IcpT", "Q_theory_over_IcpT"],
              [[f"{r:.2f}", f"{m:.4f}", f"{t:.4f}"]
               for r, m, t in zip(ratios, measured, theory)])

    fig, ax = plt.subplots(figsize=(9, 4.5))
    ax.plot(ratios, theory, "-", lw=1.5, label="theory Q = Icp frac(D/T) T")
    ax.plot(ratios, measured, "o", ms=3, label="event simulation")
    for k in (1, 2, 3):
        ax.axvline(k, color="r", ls="--", lw=0.8)
    ax.set_xlabel("frozen line delay D / T")
    ax.set_ylabel("net charge per period / Icp*T")
    ax.set_title("Two-latch PFD transfer: non-negative sawtooth, zeros at every kT")
    ax.grid(alpha=0.3)
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(os.path.join(PLOTS, "r4_charge_transfer.png"), dpi=150)
    plt.close(fig)


# ---------------------------------------------------------------------------
# R5: acquisition across all required frequencies from a coarse preset
# ---------------------------------------------------------------------------
def r5_cross_frequency():
    rows = []
    for fmhz in FREQS_MHZ:
        f = fmhz * 1e6
        band = v3.band_for_freq(f)
        Tf = 1.0 / f
        dmin, dmax = v3.d_min_max(band)
        for label, u0 in (("min_delay", 1.0), ("max_delay", 0.0)):
            r = v3.simulate_event(f, band=band, u0=u0, cycles=CYCLES)
            rows.append([f"{fmhz:g}", band, label, f"{dmin/Tf:.3f}", f"{dmax/Tf:.3f}",
                         f"{r['final_ratio']:.3f}", r["harmonic_index"],
                         "LOCK_1T" if r["locked_1T"] else
                         ("HARMONIC" if r["incorrect_harmonic"] else "NO_LOCK")])
        for preset in (1.2, 1.5, 1.8):
            r = v3.simulate_event(f, band=band, coarse_preset=preset, cycles=CYCLES)
            rows.append([f"{fmhz:g}", band, f"preset_{preset}", f"{dmin/Tf:.3f}",
                         f"{dmax/Tf:.3f}", f"{r['final_ratio']:.3f}",
                         r["harmonic_index"],
                         "LOCK_1T" if r["locked_1T"] else
                         ("HARMONIC" if r["incorrect_harmonic"] else "NO_LOCK")])
        d = v3.simulate_dynamic(f, band=band, start_ratio=1.5,
                                cycles=1500, substeps=100)
        rows.append([f"{fmhz:g}", band, "dynamic_preset_1.5", f"{dmin/Tf:.3f}",
                     f"{dmax/Tf:.3f}", f"{d['final_ratio']:.3f}",
                     d["harmonic_index"],
                     "LOCK_1T" if abs(d["final_ratio"] - 1.0) < 0.03 else "NO_LOCK"])
    write_csv("r5_cross_frequency.csv",
              ["f_MHz", "band", "startup", "min_D_over_T", "max_D_over_T",
               "final_D_over_T", "harmonic", "result"], rows)
    return rows


# ---------------------------------------------------------------------------
# R6: local stability around kT (measured per-cycle error recurrence)
# ---------------------------------------------------------------------------
def r6_stability():
    f = 100e6
    rows = []
    for k in (1, 2):
        for sign, start in (("below", k - 0.02), ("above", k + 0.02)):
            r = v3.simulate_event(f, band=1, coarse_preset=start, cycles=400)
            e = r["ratio_hist"][:30] - k
            valid = [(e[i], e[i + 1]) for i in range(len(e) - 1)
                     if abs(e[i]) > 1e-4 and e[i] * e[i + 1] > 0]
            slope = (sum(b / a for a, b in valid) / len(valid)) if valid else float("nan")
            rows.append([k, sign, f"{start:.3f}", f"{slope:.3f}",
                         f"{r['final_ratio']:.3f}",
                         "ATTRACTING" if abs(slope) < 1 else "NOT_ATTRACTING"])
    write_csv("r6_stability.csv",
              ["harmonic_k", "side", "start_D_over_T", "measured_e_ratio",
               "final_D_over_T", "verdict"], rows)
    return rows


# ---------------------------------------------------------------------------
def main():
    log = []

    def p(s=""):
        print(s)
        log.append(s)

    p("=" * 100)
    p("INDEPENDENT REVIEW OF THE v1 PFD CONCLUSION  (LEVEL B)")
    p("=" * 100)

    p("\n[R1] 77-point grid: v1 (wrong CP sign) vs corrected CP sign")
    r1 = r1_polarity_grid()
    for pol, idx in (("wrong", 4), ("correct", 7)):
        counts = {}
        for r in r1:
            counts[r[idx]] = counts.get(r[idx], 0) + 1
        p(f"   {pol:>7}: {counts}")

    p("\n[R2] Basin maps, event vs dynamic propagation")
    r2 = r2_basin_maps()
    for lo, hi in ((0.6, 0.99), (1.0, 1.99), (2.0, 3.0)):
        sub = [r for r in r2 if lo <= float(r[0]) <= hi]
        for col, name in ((2, "event"), (4, "dynamic")):
            counts = {}
            for r in sub:
                counts[r[col]] = counts.get(r[col], 0) + 1
            p(f"   start {lo:.2f}-{hi:.2f}T  {name:>7}: {counts}")

    p("\n[R3/R4] Timing diagrams and charge transfer")
    r3_timing_diagrams()
    r4_charge_transfer()
    p("   wrote r3_timing_diagrams.png and r4_charge_transfer.png")

    p("\n[R5] Acquisition across 11 frequencies")
    r5 = r5_cross_frequency()
    for label in ("min_delay", "max_delay", "preset_1.2", "preset_1.5",
                  "preset_1.8", "dynamic_preset_1.5"):
        sub = [r for r in r5 if r[2] == label]
        l1 = sum(1 for r in sub if r[7] == "LOCK_1T")
        p(f"   {label:>21}: {l1}/{len(sub)} lock 1T; "
          f"others: {[r[7] for r in sub if r[7] != 'LOCK_1T']}")

    p("\n[R6] Local stability around kT")
    for r in r6_stability():
        p("   " + "  ".join(map(str, r)))

    with open(os.path.join(LOGS, "review_run.log"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(log) + "\n")


if __name__ == "__main__":
    main()
