"""
Testbench for the behavioral acquisition controller prototype (LEVEL B).

Runs:
  * 7 frequencies x 3 bands x 13 initial conditions  (main matrix)
  * randomized initial conditions in each functional band
  * deterministic INITIALIZE tests (max / mid) in each functional band

Writes all results to results/pfd_validation/acquisition_controller/.
No transistor simulation, no architecture/spec edits.
"""
from __future__ import annotations

import csv
import json
import os
import random
import sys
import time

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "scripts"))

import dll_model as m                                   # noqa: E402
from acquisition_controller import AcquisitionController, STATES  # noqa: E402

OUT = os.path.join(ROOT, "results", "pfd_validation", "acquisition_controller")
os.makedirs(OUT, exist_ok=True)

FREQS = [25e6, 30e6, 50e6, 75e6, 100e6, 150e6, 200e6]
BANDS = [0, 1, 2]
RATIO_ICS = [0.68, 0.90, 1.00, 1.02, 1.05, 1.10, 1.30, 1.50, 1.95, 2.10, 2.50]
N_RANDOM = 5
SEED = 20261121

RESULT_FIELDS = [
    "test_id", "test_set", "f_MHz", "band", "functional_band",
    "initial_label", "start_ratio", "effective_start_ratio", "u_start",
    "success", "final_state", "outcome", "failure_reason",
    "final_ratio", "harmonic_index",
    "cycles_to_basin", "fine_lock_cycle", "effective_lock_cycles", "total_cycles",
    "coarse_adjustments", "fine_attempts", "basin_count",
    "count_sequence", "u_sequence", "d_sequence",
]


def row_for(tid, tset, res, label, start_ratio):
    f = res["f"]
    return {
        "test_id": tid,
        "test_set": tset,
        "f_MHz": f / 1e6,
        "band": res["band"],
        "functional_band": m.band_for_freq(f),
        "initial_label": label,
        "start_ratio": "" if start_ratio is None else round(start_ratio, 4),
        "effective_start_ratio": round(res["effective_start_ratio"], 4),
        "u_start": round(res["u_start"], 4),
        "success": int(res["success"]),
        "final_state": res["final_state"],
        "outcome": res["outcome"],
        "failure_reason": res["failure_reason"],
        "final_ratio": round(res["final_ratio"], 4),
        "harmonic_index": "" if res["harmonic_index"] is None else res["harmonic_index"],
        "cycles_to_basin": "" if res["cycles_to_basin"] is None else res["cycles_to_basin"],
        "fine_lock_cycle": "" if res["fine_lock_cycle"] is None else res["fine_lock_cycle"],
        "effective_lock_cycles": (
            "" if res["effective_lock_cycles"] is None else res["effective_lock_cycles"]
        ),
        "total_cycles": res["total_cycles"],
        "coarse_adjustments": res["coarse_adjustments"],
        "fine_attempts": res["fine_attempts"],
        "basin_count": "" if res["basin_count"] is None else res["basin_count"],
        "count_sequence": "|".join(str(x) for x in res["count_traj"]),
        "u_sequence": "|".join(f"{x:.3f}" for x in res["u_traj"]),
        "d_sequence": "|".join(f"{x:.3f}" for x in res["d_traj"]),
    }


def write_csv(path, fields, rows):
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


def make_state_diagram():
    fig, ax = plt.subplots(figsize=(11, 6))
    ax.set_xlim(0, 12); ax.set_ylim(0, 7); ax.axis("off")
    ax.set_title("Option-A Behavioral Acquisition Controller — FSM (LEVEL B prototype)",
                 fontsize=13, fontweight="bold")
    from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
    pos = {
        "RESET": (0.6, 3.2), "INITIALIZE": (2.3, 3.2),
        "COARSE_ACQUIRE": (4.3, 3.2), "BASIN_CHECK": (6.5, 3.2),
        "FINE_LOCK": (8.7, 4.3), "LOCK_VERIFY": (10.4, 4.3),
        "LOCKED": (11.2, 2.2), "TIMEOUT": (8.6, 0.8), "FAIL": (6.3, 0.8),
    }
    cols = {k: "#dbeafe" for k in pos}
    cols["LOCKED"] = "#bbf7d0"; cols["FAIL"] = "#fecaca"; cols["TIMEOUT"] = "#fed7aa"
    for k, (x, y) in pos.items():
        ax.add_patch(FancyBboxPatch((x - 0.75, y - 0.38), 1.5, 0.76,
                     boxstyle="round,pad=0.03", facecolor=cols[k],
                     edgecolor="#1f2937", linewidth=1.2))
        ax.text(x, y, k, ha="center", va="center", fontsize=8.5)
    def arr(a, b, label="", rad=0.0, fs=7.5):
        x1, y1 = pos[a]; x2, y2 = pos[b]
        ax.add_patch(FancyArrowPatch((x1 + 0.7, y1), (x2 - 0.75, y2),
                     connectionstyle=f"arc3,rad={rad}", arrowstyle="-|>",
                     mutation_scale=11, linewidth=1.1, color="#374151"))
        if label:
            ax.text((x1 + x2) / 2, (y1 + y2) / 2 + 0.22 + rad, label,
                    ha="center", fontsize=fs, color="#111827")
    arr("RESET", "INITIALIZE")
    arr("INITIALIZE", "COARSE_ACQUIRE", "CP off")
    arr("COARSE_ACQUIRE", "BASIN_CHECK", "count k")
    arr("BASIN_CHECK", "FINE_LOCK", "k=1", rad=0.12)
    arr("FINE_LOCK", "LOCK_VERIFY")
    arr("LOCK_VERIFY", "LOCKED", "D=T", rad=-0.25)
    arr("LOCK_VERIFY", "COARSE_ACQUIRE", "fail: nudge", rad=0.42)
    arr("BASIN_CHECK", "COARSE_ACQUIRE", "k=0: +delay / k>=2: -delay", rad=0.35)
    arr("BASIN_CHECK", "TIMEOUT", "step/cycle limit", rad=-0.35)
    ax.text(6, 6.4, "Observable = floor(D/T) from REF edges before first FB (CP disabled); "
            "no T value or forced delay preset is used.",
            ha="center", fontsize=9, style="italic")
    ax.text(6, 0.15, "Level B behavioral prototype only — metastability and circuit timing are NOT verified.",
            ha="center", fontsize=8, color="#991b1b")
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "controller_state_diagram.png"), dpi=150)
    plt.close(fig)


def make_trajectory_plots(rows):
    """Delay/count trajectories for representative successful and failed cases."""
    picks = []
    for label in ("max", "min", "1.02", "1.05", "1.30", "2.50"):
        for f in (30e6, 100e6, 200e6):
            for r in rows:
                if (r["initial_label"] == label and r["f_MHz"] == f / 1e6
                        and r["band"] == m.band_for_freq(f)):
                    picks.append(r)
                    break
    n = len(picks)
    cols = 3
    rrn = (n + cols - 1) // cols
    fig, axes = plt.subplots(rrn, cols, figsize=(15, 3.1 * rrn), squeeze=False)
    for ax, r in zip(axes.flat, picks):
        d = [float(x) for x in r["d_sequence"].split("|")]
        c = [int(x) for x in r["count_sequence"].split("|")]
        ax.step(range(1, len(d) + 1), d, where="post", marker="o", ms=3, color="#1d4ed8")
        ax.axhline(1.0, color="#16a34a", ls="--", lw=1, label="D/T = 1")
        ax2 = ax.twinx()
        ax2.step(range(1, len(c) + 1), c, where="post", marker="s", ms=3,
                 color="#dc2626", alpha=0.6)
        ax2.set_ylabel("count floor(D/T)", color="#dc2626", fontsize=7)
        ax.set_title(f"{r['f_MHz']:.0f} MHz b{r['band']} init={r['initial_label']} "
                     f"-> {r['outcome']}", fontsize=8)
        ax.set_xlabel("measurement step", fontsize=7)
        ax.set_ylabel("D/T", fontsize=7)
        ax.set_ylim(0, max(3.0, max(d) + 0.2))
        ax.tick_params(labelsize=7)
        ax2.tick_params(labelsize=7)
    for ax in axes.flat[n:]:
        ax.axis("off")
    fig.suptitle("Coarse acquisition delay trajectories (LEVEL B behavioral)", fontsize=12)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "delay_trajectories.png"), dpi=150)
    plt.close(fig)


def make_summary_plots(rows):
    main = [r for r in rows if r["test_set"] == "main"]
    # success rate by frequency and band
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    freqs = sorted({r["f_MHz"] for r in main})
    for band in BANDS:
        vals = []
        for f in freqs:
            subset = [r for r in main if r["f_MHz"] == f and r["band"] == band]
            vals.append(100 * sum(r["success"] for r in subset) / max(1, len(subset)))
        axes[0].plot(freqs, vals, marker="o", label=f"band {band}")
    axes[0].set_xlabel("frequency (MHz)"); axes[0].set_ylabel("acquisition success (%)")
    axes[0].set_title("Success by frequency and band"); axes[0].legend(); axes[0].grid(alpha=0.3)
    axes[0].set_ylim(-5, 105)

    ok = [r for r in main if r["success"]]
    if ok:
        axes[1].hist([r["total_cycles"] for r in ok], bins=30, color="#16a34a", alpha=0.75)
    axes[1].set_xlabel("total cycles (coarse + fine)")
    axes[1].set_ylabel("count")
    axes[1].set_title("Total lock cycles — successful cases")
    axes[1].grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "summary_success.png"), dpi=150)
    plt.close(fig)


def main():
    t_start = time.time()
    random.seed(SEED)
    ctrl_cache = {}
    rows = []
    tid = 0

    # ---- main matrix ---------------------------------------------------
    for f in FREQS:
        for band in BANDS:
            key = (f, band)
            if key not in ctrl_cache:
                ctrl_cache[key] = AcquisitionController(f, band)
            c = ctrl_cache[key]
            for label in ["min", "max"] + [f"{x:.2f}" for x in RATIO_ICS]:
                if label == "min":
                    u0, sr = 1.0, None
                elif label == "max":
                    u0, sr = 0.0, None
                else:
                    u0, sr = None, float(label)
                tid += 1
                res = c.run(start_ratio=sr, u0=u0, init_mode="preserve")
                rows.append(row_for(f"M{tid:04d}", "main", res, label, sr))
        print(f"main matrix done through {f/1e6:.0f} MHz; {time.time()-t_start:.1f}s", flush=True)

    # ---- randomized initial conditions (functional band only) ----------
    for f in FREQS:
        band = m.band_for_freq(f)
        c = ctrl_cache[(f, band)]
        for i in range(N_RANDOM):
            u0 = round(random.uniform(0.0, 1.0), 4)
            tid += 1
            res = c.run(u0=u0, init_mode="preserve")
            rows.append(row_for(f"R{tid:04d}", "random", res, f"rand{i+1}", None))

    # ---- deterministic INITIALIZE tests (functional band only) ---------
    for f in FREQS:
        band = m.band_for_freq(f)
        c = ctrl_cache[(f, band)]
        for im in ("max", "mid"):
            tid += 1
            res = c.run(u0=0.77, init_mode=im)  # arbitrary physical start
            rows.append(row_for(f"I{tid:04d}", "deterministic_init", res, f"init_{im}", None))

    # ---- edge-count boundary tests (functional band only) --------------
    # These deliberately probe the exact D/T = 1 and D/T = 2 boundaries.
    boundary_ratios = [0.99, 1.00, 1.01, 1.02, 1.03, 1.04,
                       1.95, 1.98, 1.99, 2.00, 2.01, 2.05]
    for f in FREQS:
        band = m.band_for_freq(f)
        c = ctrl_cache[(f, band)]
        for br in boundary_ratios:
            tid += 1
            res = c.run(start_ratio=br, init_mode="preserve")
            rows.append(row_for(f"B{tid:04d}", "boundary", res, f"{br:.2f}", br))

    # ---- write outputs --------------------------------------------------
    write_csv(os.path.join(OUT, "acquisition_results.csv"), RESULT_FIELDS, rows)

    lock_fields = [
        "test_id", "test_set", "f_MHz", "band", "initial_label",
        "success", "cycles_to_basin", "fine_lock_cycle", "effective_lock_cycles",
        "total_cycles", "coarse_adjustments", "fine_attempts", "basin_count", "outcome",
    ]
    write_csv(os.path.join(OUT, "lock_time.csv"), lock_fields,
              [{k: r[k] for k in lock_fields} for r in rows])

    traj_fields = ["test_id", "f_MHz", "band", "initial_label", "step",
                   "count", "u", "d_over_t"]
    traj_rows = []
    for r in rows:
        cs = r["count_sequence"].split("|")
        us = r["u_sequence"].split("|")
        ds = r["d_sequence"].split("|")
        for i, (cc, uu, dd) in enumerate(zip(cs, us, ds), 1):
            traj_rows.append({
                "test_id": r["test_id"], "f_MHz": r["f_MHz"], "band": r["band"],
                "initial_label": r["initial_label"], "step": i,
                "count": cc, "u": uu, "d_over_t": dd,
            })
    write_csv(os.path.join(OUT, "delay_trajectory.csv"), traj_fields, traj_rows)

    make_state_diagram()
    make_trajectory_plots(rows)
    make_summary_plots(rows)

    summary = {
        "total_tests": len(rows),
        "main_tests": sum(r["test_set"] == "main" for r in rows),
        "success_total": sum(r["success"] for r in rows),
        "success_main": sum(r["success"] for r in rows if r["test_set"] == "main"),
        "elapsed_s": round(time.time() - t_start, 1),
        "frequencies_MHz": [f / 1e6 for f in FREQS],
        "bands": BANDS,
        "initial_conditions": ["min", "max"] + [f"{x:.2f}" for x in RATIO_ICS],
        "random_samples_per_freq": N_RANDOM,
        "random_seed": SEED,
    }
    with open(os.path.join(OUT, "run_summary.json"), "w", encoding="utf-8") as fh:
        json.dump(summary, fh, indent=2)
    print(json.dumps(summary, indent=2))
    print(f"DONE in {time.time()-t_start:.1f}s")


if __name__ == "__main__":
    main()
