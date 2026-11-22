"""
Final validation of Problem 1 (LEVEL B) — exact-event dynamic engine.

Runs F1–F6 experiments and writes all outputs to
results/pfd_validation/final_validation/.

Run: python scripts/pfd_validation/run_final_validation.py
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

import pfd_model_v4_final as v4  # noqa: E402

OUT = os.path.join(ROOT, "results", "pfd_validation", "final_validation")
TABLES = os.path.join(OUT, "tables")
PLOTS = os.path.join(OUT, "plots")
LOGS = os.path.join(OUT, "logs")
for d in (TABLES, PLOTS, LOGS):
    os.makedirs(d, exist_ok=True)

F = 100e6
BAND = 1
T = 1.0 / F
STARTS = [0.90, 0.95, 0.98, 0.99, 1.00, 1.01, 1.02, 1.05,
          1.10, 1.20, 1.30, 1.50, 1.80, 1.95]
SUBSTEPS_LIST = [50, 100, 200, 500, 1000, 2000, 5000]
ICP_LIST = [50e-6, 100e-6, 150e-6, 300e-6]
RESET_PS_LIST = [0, 5, 10, 25]
DEAD_PS_LIST = [0, 5, 10, 25]
CYCLES = 300


def wcsv(name, header, rows):
    with open(os.path.join(TABLES, name), "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(header)
        w.writerows(rows)


def classify(r, start):
    """Explicit outcome classification per user requirement 7."""
    final = r["final_ratio"]
    k = r["harmonic_index"]
    hist = r["ratio_hist"]
    q_dn = r["q_down"]
    rail = r["rail_min"] or r["rail_max"]
    osc = r["oscillating"]
    pp = r["settled_pp"]

    if osc:
        return "OSCILLATION"
    if rail and k == 0:
        return "RAIL_MIN (k=0 basin)"
    if r["rail_max"]:
        return "RAIL_MAX"
    if k == 0 and final < 0.75:
        return "LOCK_0T / MIN_RAIL"
    if k == 1 and abs(final - 1.0) < 0.03:
        # Did the trajectory cross below 1T after the first comparison?
        post = hist[5:] if len(hist) > 5 else hist
        crossed = bool(np.any(post < 1.0 - 0.005))
        if start < 1.0:
            return "1T_LOCK (from below)" if not crossed else "1T_LOCK (from below, crossed)"
        if crossed:
            return "1T_LOCK (above -> sub-1T excursion -> recover)"
        return "1T_LOCK (from above)"
    if k >= 2 and abs(final - k) < 0.03:
        return f"HARMONIC_{k}T"
    return "UNCLASSIFIED"


# ---------------------------------------------------------------------------
# F1: timestep / event audit
# ---------------------------------------------------------------------------
def f1_timestep_audit():
    rows = []
    for ss in SUBSTEPS_LIST:
        r = v4.simulate_v4(F, band=BAND, start_ratio=1.35, cycles=CYCLES,
                           substeps=ss, record_trace=True)
        launched, completed, in_flight = r["edge_launched"], r["edge_completed"], r["in_flight_end"]
        rows.append([
            ss, f"{r['dt_ps']:.1f}", launched, completed, in_flight,
            launched - completed - in_flight,
            r["ignored_ref"], r["ignored_fb"], len(r["reset_times"]),
            f"{r['final_ratio']:.4f}",
            r["lock_cycle"] if r["lock_cycle"] is not None else "none",
            f"{r['settled_pp']:.5f}",
        ])
    wcsv("f1_timestep_audit.csv",
         ["substeps", "dt_ps", "edges_launched", "edges_completed",
          "in_flight_end", "edge_balance", "ignored_ref", "ignored_fb",
          "resets", "final_D_over_T", "lock_cycle", "settled_pp"], rows)
    return rows


# ---------------------------------------------------------------------------
# F2: convergence study — all starts × all substeps
# ---------------------------------------------------------------------------
def f2_convergence():
    rows = []
    for start in STARTS:
        for ss in SUBSTEPS_LIST:
            r = v4.simulate_v4(F, band=BAND, start_ratio=start, cycles=CYCLES,
                               substeps=ss)
            rows.append([
                f"{start:.2f}", ss, f"{r['dt_ps']:.1f}",
                f"{r['final_ratio']:.4f}", r["harmonic_index"],
                classify(r, start),
                r["lock_cycle"] if r["lock_cycle"] is not None else "none",
                f"{r['settled_pp']:.5f}", f"{r['final_u']:.4f}",
                int(r["rail_min"]), int(r["rail_max"]), int(r["oscillating"]),
                f"{r['q_down']:.3e}",
            ])
    wcsv("f2_convergence.csv",
         ["start_D_over_T", "substeps", "dt_ps", "final_D_over_T",
          "harmonic", "outcome", "lock_cycle", "settled_pp", "final_u",
          "rail_min", "rail_max", "oscillating", "Q_down"], rows)
    return rows


# ---------------------------------------------------------------------------
# F3: parameter sweeps
# ---------------------------------------------------------------------------
def f3_parameter_sweeps():
    # Icp
    rows_i = []
    for start in (0.99, 1.01, 1.05, 1.10, 1.30, 1.95):
        for icp in ICP_LIST:
            r = v4.simulate_v4(F, band=BAND, start_ratio=start, cycles=CYCLES,
                               substeps=1000, icp=icp)
            rows_i.append([f"{start:.2f}", f"{icp*1e6:.0f}",
                           f"{r['final_ratio']:.4f}", classify(r, start),
                           r["lock_cycle"] if r["lock_cycle"] is not None else "none"])
    wcsv("f3_icp_sweep.csv",
         ["start_D_over_T", "Icp_uA", "final_D_over_T", "outcome", "lock_cycle"], rows_i)

    # reset delay
    rows_r = []
    for start in (0.99, 1.01, 1.05, 1.10, 1.30):
        for rst in RESET_PS_LIST:
            r = v4.simulate_v4(F, band=BAND, start_ratio=start, cycles=CYCLES,
                               substeps=1000, t_reset=rst * 1e-12)
            rows_r.append([f"{start:.2f}", rst,
                           f"{r['final_ratio']:.4f}", classify(r, start),
                           r["lock_cycle"] if r["lock_cycle"] is not None else "none"])
    wcsv("f3_reset_sweep.csv",
         ["start_D_over_T", "reset_ps", "final_D_over_T", "outcome", "lock_cycle"], rows_r)

    # dead time
    rows_d = []
    for start in (0.99, 1.01, 1.05, 1.10, 1.30):
        for dead in DEAD_PS_LIST:
            r = v4.simulate_v4(F, band=BAND, start_ratio=start, cycles=CYCLES,
                               substeps=1000, t_dead=dead * 1e-12)
            rows_d.append([f"{start:.2f}", dead,
                           f"{r['final_ratio']:.4f}", classify(r, start),
                           r["lock_cycle"] if r["lock_cycle"] is not None else "none"])
    wcsv("f3_dead_sweep.csv",
         ["start_D_over_T", "dead_ps", "final_D_over_T", "outcome", "lock_cycle"], rows_d)

    # full factorial at critical starts
    rows_f = []
    for start in (1.01, 1.30):
        for icp in ICP_LIST:
            for rst in RESET_PS_LIST:
                for dead in DEAD_PS_LIST:
                    r = v4.simulate_v4(F, band=BAND, start_ratio=start,
                                       cycles=200, substeps=1000,
                                       icp=icp, t_reset=rst * 1e-12,
                                       t_dead=dead * 1e-12)
                    rows_f.append([f"{start:.2f}", f"{icp*1e6:.0f}", rst, dead,
                                   f"{r['final_ratio']:.4f}", classify(r, start)])
    wcsv("f3_full_factorial.csv",
         ["start_D_over_T", "Icp_uA", "reset_ps", "dead_ps",
          "final_D_over_T", "outcome"], rows_f)
    return rows_i, rows_r, rows_d, rows_f


# ---------------------------------------------------------------------------
# F4: feedback edge propagation verification (D=1.35T)
# ---------------------------------------------------------------------------
def f4_edge_propagation():
    r = v4.simulate_v4(F, band=BAND, start_ratio=1.35, cycles=5,
                       substeps=1000, record_trace=True)
    tr = r["trace"]
    rows = []
    for t, kind, up, down in tr:
        rows.append([f"{t/T:.6f}", kind, int(up), int(down)])
    wcsv("f4_event_trace_1p35.csv",
         ["time_over_T", "event", "UP", "DOWN"], rows)

    # Verify reset timing from trace
    resets = []
    pending = None
    for t, kind, up, down in tr:
        if kind in ("UP", "DOWN") and up and down and pending is None:
            pending = t
        if kind == "RESET" and pending is not None:
            resets.append((t - pending) * 1e12)
            pending = None
    wcsv("f4_reset_delays.csv",
         ["reset_delay_ps"], [[f"{x:.3f}"] for x in resets])

    # Edge accounting summary
    summary = {
        "launched": r["edge_launched"], "completed": r["edge_completed"],
        "in_flight": r["in_flight_end"],
        "ignored_ref": r["ignored_ref"], "ignored_fb": r["ignored_fb"],
        "resets": len(r["reset_times"]), "trace_events": len(tr),
    }
    return summary, resets


# ---------------------------------------------------------------------------
# F5: plots
# ---------------------------------------------------------------------------
def f5_plots(conv_rows, icp_rows):
    # Convergence: final ratio vs substeps, colored by start
    fig, ax = plt.subplots(figsize=(10, 6))
    for start in STARTS:
        sub = [r for r in conv_rows if float(r[0]) == start]
        xs = [int(r[1]) for r in sub]
        ys = [float(r[3]) for r in sub]
        ax.plot(xs, ys, "o-", ms=4, label=f"{start:.2f}T")
    ax.axhline(1.0, color="k", ls="--", lw=1)
    ax.set_xscale("log")
    ax.set_xlabel("substeps per period")
    ax.set_ylabel("final D / T")
    ax.set_title("Convergence study — 100 MHz, band 1, 300 cycles")
    ax.legend(ncol=2, fontsize=7)
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(os.path.join(PLOTS, "f2_convergence.png"), dpi=150)
    plt.close(fig)

    # Outcome map: start vs substeps
    fig, ax = plt.subplots(figsize=(10, 6))
    colors = {
        "RAIL_MIN (k=0 basin)": "red",
        "1T_LOCK (from above)": "green",
        "1T_LOCK (from below)": "blue",
        "1T_LOCK (above -> sub-1T excursion -> recover)": "cyan",
        "HARMONIC_2T": "orange",
        "OSCILLATION": "magenta",
    }
    for r in conv_rows:
        x = int(r[1])
        y = float(r[0])
        c = colors.get(r[5], "gray")
        ax.plot(x, y, "s", color=c, ms=6)
    ax.set_xscale("log")
    ax.set_xlabel("substeps per period")
    ax.set_ylabel("start D / T")
    ax.set_title("Outcome map — Exact-event dynamic engine")
    handles = [plt.Line2D([0], [0], marker="s", color="w",
                          markerfacecolor=c, label=k) for k, c in colors.items()]
    ax.legend(handles=handles, fontsize=7, loc="center left", bbox_to_anchor=(1, 0.5))
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(os.path.join(PLOTS, "f2_outcome_map.png"), dpi=150)
    plt.close(fig)

    # Icp sweep
    fig, ax = plt.subplots(figsize=(9, 5))
    for start in (0.99, 1.01, 1.05, 1.10, 1.30, 1.95):
        sub = [r for r in icp_rows if float(r[0]) == start]
        ax.plot([float(r[1]) for r in sub], [float(r[2]) for r in sub],
                "o-", ms=4, label=f"{start:.2f}T")
    ax.axhline(1.0, color="k", ls="--", lw=1)
    ax.set_xlabel("Icp (uA)")
    ax.set_ylabel("final D / T")
    ax.set_title("Charge-pump current sweep (100 MHz, band 1)")
    ax.legend(fontsize=8)
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(os.path.join(PLOTS, "f3_icp_sweep.png"), dpi=150)
    plt.close(fig)


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------
def main():
    log = []

    def p(s=""):
        print(s)
        log.append(s)

    p("=" * 100)
    p("FINAL VALIDATION — PROBLEM 1 (LEVEL B, exact-event engine)")
    p("=" * 100)

    p("\n[F1] Timestep / event audit")
    f1 = f1_timestep_audit()
    for r in f1:
        p("   sub=%5d dt=%6.1fps launched=%3d completed=%3d inflight=%d "
          "balance=%d ign_ref=%d ign_fb=%d final=%.3f" %
          (r[0], float(r[1]), r[2], r[3], r[4], r[5], r[6], r[7], float(r[9])))

    p("\n[F2] Convergence study (14 starts x 7 substeps)")
    conv = f2_convergence()
    # summary: for each start, how many substeps give each outcome
    for start in STARTS:
        sub = [r for r in conv if float(r[0]) == start]
        outcomes = {}
        for r in sub:
            outcomes[r[5]] = outcomes.get(r[5], 0) + 1
        finals = set(f"{float(r[3]):.3f}" for r in sub)
        p(f"   start={start:.2f}T: outcomes={outcomes} finals={sorted(finals)}")

    p("\n[F3] Parameter sweeps")
    ri, rr, rd, rf = f3_parameter_sweeps()
    p("   Icp sweep outcomes:")
    for start in (0.99, 1.01, 1.05, 1.10, 1.30, 1.95):
        sub = [r for r in ri if float(r[0]) == start]
        p(f"     {start:.2f}T: {[(r[1], r[3]) for r in sub]}")
    p("   Reset sweep outcomes:")
    for start in (0.99, 1.01, 1.05, 1.10, 1.30):
        sub = [r for r in rr if float(r[0]) == start]
        p(f"     {start:.2f}T: {[(r[1], r[3]) for r in sub]}")
    p("   Dead sweep outcomes:")
    for start in (0.99, 1.01, 1.05, 1.10, 1.30):
        sub = [r for r in rd if float(r[0]) == start]
        p(f"     {start:.2f}T: {[(r[1], r[3]) for r in sub]}")

    p("\n[F4] Edge propagation verification")
    summary, resets = f4_edge_propagation()
    p(f"   {summary}")
    p(f"   reset delays (ps): min={min(resets):.3f} max={max(resets):.3f} "
      f"mean={np.mean(resets):.3f}" if resets else "   no resets")

    p("\n[F5] Plots written")

    with open(os.path.join(LOGS, "final_validation.log"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(log) + "\n")

    f5_plots(conv, ri)
    return conv, ri, rr, rd, rf


if __name__ == "__main__":
    main()
