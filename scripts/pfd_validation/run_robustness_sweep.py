"""
Investigation A + B data collection: Icp sweep across 25-200 MHz (LEVEL B).

Uses the validated v4 engine and the UNMODIFIED Phase-3 AcquisitionController.
Writes current_sweep.csv, basin_map.csv, lock_time.csv, loop_gain.csv.
"""
from __future__ import annotations

import csv
import json
import os
import sys
import time

from robustness_common import (
    FREQS_HZ, ICPS_A, INITIAL_LABELS, OUT_1T, OUT_RMIN, OUT_RMAX, OUT_UNSET,
    classify, d_limits, init_u, loop_gain_metrics,
)
from acquisition_controller import AcquisitionController
import dll_model as m
import pfd_model_v4_final as v4
from robustness_common import ROOT

OUT = os.path.join(ROOT, "results", "pfd_validation", "acquisition_robustness")
os.makedirs(OUT, exist_ok=True)
BASIN_STEP = 0.05
BASIN_MIN, BASIN_MAX = 0.50, 3.00


def basin_edges(ratios, outcomes):
    """Contiguous 1T_LOCK run containing the point nearest 1.3T."""
    idxs = [i for i, o in enumerate(outcomes) if o == OUT_1T]
    if not idxs:
        return None, None, 0
    anchor = min(range(len(ratios)), key=lambda i: abs(ratios[i] - 1.3))
    # find contiguous run around anchor if it is a 1T point, else nearest run
    runs = []
    cur = []
    for i in idxs:
        if cur and i != cur[-1] + 1:
            runs.append(cur); cur = []
        cur.append(i)
    if cur:
        runs.append(cur)
    run = min(runs, key=lambda rr: min(abs(i - anchor) for i in rr))
    return ratios[run[0]], ratios[run[-1]], len(idxs)


def main():
    t0 = time.time()
    basin_rows, lock_rows, sweep_rows, gain_rows = [], [], [], []
    n = 0

    for f in FREQS_HZ:
        band = m.band_for_freq(f)
        dmin, dmax = d_limits(f, band)
        for icp in ICPS_A:
            n += 1
            # ---- fine-loop basin sweep ----------------------------------
            ratios = []
            outcomes = []
            final_ratios = []
            lock_cycles = []
            rr = BASIN_MIN
            while rr <= BASIN_MAX + 1e-9:
                r = v4.simulate_v4(f, band=band, start_ratio=rr, cycles=150,
                                   substeps=150, icp=icp)
                o = classify(r, dmin, dmax)
                ratios.append(round(rr, 4))
                outcomes.append(o)
                final_ratios.append(round(r["final_ratio"], 4))
                lock_cycles.append(r["lock_cycle"])
                basin_rows.append({
                    "f_MHz": f / 1e6, "band": band, "Icp_uA": icp * 1e6,
                    "start_ratio": round(rr, 4),
                    "effective_start_ratio": round(min(rr, dmax), 4),
                    "final_ratio": round(r["final_ratio"], 4),
                    "harmonic_index": r["harmonic_index"],
                    "outcome": o,
                    "lock_cycle": "" if r["lock_cycle"] is None else r["lock_cycle"],
                    "settled_pp": round(r["settled_pp"], 5),
                })
                rr += BASIN_STEP
            lo, hi, n1t = basin_edges(ratios, outcomes)
            n_rail = sum(o == OUT_RMIN for o in outcomes)
            n_harm = sum(o.startswith("HARMONIC") for o in outcomes)
            n_unset = sum(o == OUT_UNSET for o in outcomes)

            # ---- controller success across initial conditions -----------
            ctrl = AcquisitionController(f, band, icp=icp)
            successes = 0
            eff_locks = []
            coarse = []
            fine = []
            for label in INITIAL_LABELS:
                res = ctrl.run(u0=init_u(label, f, band), init_mode="preserve")
                successes += int(res["success"])
                if res["success"] and res["effective_lock_cycles"] is not None:
                    eff_locks.append(res["effective_lock_cycles"])
                coarse.append(res["coarse_adjustments"])
                fine.append(res["fine_attempts"])
                lock_rows.append({
                    "f_MHz": f / 1e6, "band": band, "Icp_uA": icp * 1e6,
                    "init": label,
                    "success": int(res["success"]),
                    "final_outcome": res["outcome"],
                    "count_sequence": "|".join(str(x) for x in res["count_traj"]),
                    "coarse_adjustments": res["coarse_adjustments"],
                    "fine_attempts": res["fine_attempts"],
                    "cycles_to_basin": "" if res["cycles_to_basin"] is None else res["cycles_to_basin"],
                    "fine_lock_cycle": "" if res["fine_lock_cycle"] is None else res["fine_lock_cycle"],
                    "effective_lock_cycles": (
                        "" if res["effective_lock_cycles"] is None else res["effective_lock_cycles"]
                    ),
                    "final_ratio": round(res["final_ratio"], 4),
                })

            gm = loop_gain_metrics(f, band, icp)
            gain_rows.append({
                "f_MHz": f / 1e6, "band": band, "Icp_uA": icp * 1e6,
                **{k: round(v, 8) for k, v in gm.items()},
            })

            sweep_rows.append({
                "f_MHz": f / 1e6, "band": band, "Icp_uA": icp * 1e6,
                "Dmin_over_T": round(dmin, 4), "Dmax_over_T": round(dmax, 4),
                "basin_lo": "" if lo is None else lo,
                "basin_hi": "" if hi is None else hi,
                "n_1T_points": n1t,
                "n_min_rail": n_rail,
                "n_harmonic": n_harm,
                "n_unsettled": n_unset,
                "controller_success": successes,
                "controller_total": len(INITIAL_LABELS),
                "success_pct": round(100 * successes / len(INITIAL_LABELS), 1),
                "lock_median": "" if not eff_locks else round(sorted(eff_locks)[len(eff_locks)//2], 2),
                "lock_max": "" if not eff_locks else max(eff_locks),
                "coarse_adj_max": max(coarse),
                "fine_attempts_max": max(fine),
                "g_norm_per_frac": round(gm["d_D_over_T_per_cycle_per_frac"], 6),
                "d_DT_per_cycle_frac005": round(gm["d_D_over_T_per_cycle_frac005"], 6),
            })
            print(f"[{n:2d}/56] {f/1e6:5.0f} MHz Icp={icp*1e6:3.0f}uA "
                  f"basin={lo}-{hi} 1Tpts={n1t:2d} rail={n_rail:2d} harm={n_harm:2d} "
                  f"ctrl={successes:2d}/13 med={sweep_rows[-1]['lock_median']} "
                  f"G={gm['d_D_over_T_per_cycle_per_frac']:.3f} "
                  f"({time.time()-t0:.1f}s)", flush=True)

    def dump(name, fields, rows):
        with open(os.path.join(OUT, name), "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=fields)
            w.writeheader(); w.writerows(rows)

    dump("current_sweep.csv", list(sweep_rows[0].keys()), sweep_rows)
    dump("basin_map.csv", list(basin_rows[0].keys()), basin_rows)
    dump("lock_time.csv", list(lock_rows[0].keys()), lock_rows)
    dump("loop_gain.csv", list(gain_rows[0].keys()), gain_rows)
    with open(os.path.join(OUT, "sweep_meta.json"), "w", encoding="utf-8") as fh:
        json.dump({
            "basin_step": BASIN_STEP, "basin_range": [BASIN_MIN, BASIN_MAX],
            "fine_sim_cycles": 150, "fine_substeps": 150,
            "controller": "Phase-3 AcquisitionController, unmodified",
            "total_combinations": n, "elapsed_s": round(time.time() - t0, 1),
        }, fh, indent=2)
    print(f"DONE {time.time()-t0:.1f}s")


if __name__ == "__main__":
    main()
