"""
Investigation D: 30 MHz lower acquisition-basin boundary (LEVEL B).

Fine-resolution sweep around D/T = 1.00-1.10, across all Icp values, using
the unmodified v4 engine and unmodified Phase-3 controller.
"""
from __future__ import annotations

import csv
import json
import os
import time

from robustness_common import (
    FREQS_HZ, ICPS_A, OUT_1T, OUT_RMIN, classify, d_limits, init_u,
)
from acquisition_controller import AcquisitionController
import dll_model as m
import pfd_model_v4_final as v4
from robustness_common import ROOT

OUT = os.path.join(ROOT, "results", "pfd_validation", "acquisition_robustness")
os.makedirs(OUT, exist_ok=True)


def fine_sweep(f, band, icp, ratios, cycles=150, substeps=150):
    dmin, dmax = d_limits(f, band)
    out = []
    for rr in ratios:
        r = v4.simulate_v4(f, band=band, start_ratio=rr, cycles=cycles,
                           substeps=substeps, icp=icp)
        out.append({
            "f_MHz": f / 1e6, "band": band, "Icp_uA": icp * 1e6,
            "start_ratio": round(rr, 4),
            "final_ratio": round(r["final_ratio"], 4),
            "harmonic_index": r["harmonic_index"],
            "outcome": classify(r, dmin, dmax),
            "lock_cycle": "" if r["lock_cycle"] is None else r["lock_cycle"],
            "settled_pp": round(r["settled_pp"], 5),
        })
    return out


def main():
    t0 = time.time()
    # Fine grid 0.980 .. 1.120 step 0.002 (71 points); also upper edge 1.90..2.10
    ratios = [round(0.980 + 0.002 * i, 4) for i in range(71)]
    ratios += [round(1.90 + 0.01 * i, 4) for i in range(21)]
    rows = []
    summary = []

    for icp in ICPS_A:
        for f in (30e6, 25e6):
            band = m.band_for_freq(f)
            rows.extend(fine_sweep(f, band, icp, ratios))

        # 30 MHz recovery test with the baseline controller at failing points
        ctrl = AcquisitionController(30e6, 0, icp=icp)
        rec = []
        for sr in (1.00, 1.01, 1.02, 1.03, 1.04):
            res = ctrl.run(start_ratio=sr, init_mode="preserve")
            rec.append({
                "f_MHz": 30, "Icp_uA": icp * 1e6, "start_ratio": sr,
                "success": int(res["success"]),
                "count_sequence": "|".join(str(x) for x in res["count_traj"]),
                "d_sequence": "|".join(f"{x:.3f}" for x in res["d_traj"]),
                "coarse_adjustments": res["coarse_adjustments"],
                "fine_attempts": res["fine_attempts"],
                "final_ratio": round(res["final_ratio"], 4),
                "outcome": res["outcome"],
                "effective_lock_cycles": (
                    "" if res["effective_lock_cycles"] is None else res["effective_lock_cycles"]
                ),
            })

        # lower edge from fine grid at 30 MHz
        s30 = [r for r in rows if r["f_MHz"] == 30 and r["Icp_uA"] == icp * 1e6
               and r["start_ratio"] <= 1.120]
        ok30 = [r["start_ratio"] for r in s30 if r["outcome"] == OUT_1T]
        s25 = [r for r in rows if r["f_MHz"] == 25 and r["Icp_uA"] == icp * 1e6
               and r["start_ratio"] <= 1.120]
        ok25 = [r["start_ratio"] for r in s25 if r["outcome"] == OUT_1T]
        summary.append({
            "Icp_uA": icp * 1e6,
            "f30_lower_edge": min(ok30) if ok30 else "",
            "f30_1T_points": len(ok30),
            "f30_rail_points": sum(r["outcome"] == OUT_RMIN for r in s30),
            "f30_recovery_success": sum(x["success"] for x in rec),
            "f30_recovery_total": len(rec),
            "f25_lower_edge": min(ok25) if ok25 else "",
            "f25_1T_points": len(ok25),
        })
        print(f"Icp={icp*1e6:3.0f}uA  30MHz lower edge={min(ok30) if ok30 else 'NONE'} "
              f"(n={len(ok30):2d})  recovery={sum(x['success'] for x in rec)}/5  "
              f"25MHz lower edge={min(ok25) if ok25 else 'NONE'} "
              f"({time.time()-t0:.1f}s)", flush=True)

        if icp == ICPS_A[0]:
            recovery_all = []
        recovery_all.extend(rec)

    def dump(name, data):
        with open(os.path.join(OUT, name), "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=list(data[0].keys()))
            w.writeheader(); w.writerows(data)

    dump("boundary_fine.csv", rows)
    dump("boundary_summary.csv", summary)
    dump("boundary_recovery.csv", recovery_all)
    with open(os.path.join(OUT, "boundary_meta.json"), "w", encoding="utf-8") as fh:
        json.dump({
            "grid": "0.980..1.120 step 0.002; 1.90..2.10 step 0.01",
            "fine_sim_cycles": 150, "fine_substeps": 150,
            "controller": "Phase-3 AcquisitionController, unmodified",
            "elapsed_s": round(time.time() - t0, 1),
        }, fh, indent=2)
    print(f"DONE {time.time()-t0:.1f}s")


if __name__ == "__main__":
    main()
