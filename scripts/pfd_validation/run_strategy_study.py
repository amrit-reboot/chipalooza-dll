"""
Investigations C + E: current strategies and controller improvements (LEVEL B).

INVESTIGATION ONLY. The Phase-3 AcquisitionController and v4 engine are
imported but NEVER modified. All new logic lives in this file.
Reads current_sweep.csv / boundary_summary.csv produced by the other scripts.
"""
from __future__ import annotations

import csv
import json
import os
import sys
import time

from robustness_common import (
    FREQS_HZ, ICPS_A, INITIAL_LABELS, OUT_1T, OUT_RMIN, classify, d_limits,
    init_u,
)
from acquisition_controller import AcquisitionController
from robustness_common import ROOT
import dll_model as m
import pfd_model_v4_final as v4

OUT = os.path.join(ROOT, "results", "pfd_validation", "acquisition_robustness")
os.makedirs(OUT, exist_ok=True)


class ExploreController:
    """Investigation-only variant. NOT the baseline controller.

    Adds: adaptive step, repeated count measurement, bounded hysteresis,
    multiple fine attempts with configurable per-attempt Icp (current
    switching), and explicit coarse re-assert before each fine attempt.
    """

    def __init__(self, f, band, *, fine_icps=(300e-6,), coarse_step=0.10,
                 small_step=0.05, repeated=1, max_coarse=20,
                 reassert_coarse=True):
        self.f = f; self.band = band; self.T = 1.0 / f
        self.fine_icps = tuple(fine_icps)
        self.coarse_step = coarse_step
        self.small_step = small_step
        self.repeated = repeated
        self.max_coarse = max_coarse
        self.reassert_coarse = reassert_coarse
        self.dmin, self.dmax = d_limits(f, band)
        self.base = AcquisitionController(f, band)  # for measure_count only

    def _measure(self, u):
        counts = [self.base.measure_count(u)[0] for _ in range(self.repeated)]
        return counts[-1] if len(set(counts)) == 1 else counts[-1], counts

    def run(self, u0):
        u = u0
        coarse_steps = 0
        fine_attempts = 0
        steps = []
        step_size = self.coarse_step
        while coarse_steps < self.max_coarse:
            k, counts = self._measure(u)
            steps.append((round(u, 4), round(m.line_delay(u, self.band) / self.T, 4), k))
            if k == 0:
                u = max(0.0, u - step_size)
                coarse_steps += 1
                step_size = self.small_step  # adaptive after first correction
                continue
            if k >= 2:
                u = min(1.0, u + step_size)
                coarse_steps += 1
                step_size = self.small_step
                continue
            # k == 1: fine attempts with configurable currents
            for icp in self.fine_icps:
                fine_attempts += 1
                uu = u if self.reassert_coarse else None
                r = v4.simulate_v4(self.f, band=self.band, u0=uu if uu is not None else u,
                                   cycles=200, substeps=300, icp=icp)
                o = classify(r, self.dmin, self.dmax)
                if o == OUT_1T:
                    return {
                        "success": True, "outcome": o, "fine_icp_uA": icp * 1e6,
                        "fine_attempts": fine_attempts, "coarse_steps": coarse_steps,
                        "final_ratio": r["final_ratio"],
                        "lock_cycle": r["lock_cycle"], "steps": steps,
                    }
                if self.reassert_coarse:
                    # coarse re-asserts its code after a failed fine attempt
                    continue
            # all fine currents failed: adaptive smaller step, keep searching
            step_size = self.small_step
            u = max(0.0, u - self.small_step)  # bias toward more delay
            coarse_steps += 1
        return {
            "success": False, "outcome": "FAIL", "fine_icp_uA": None,
            "fine_attempts": fine_attempts, "coarse_steps": coarse_steps,
            "final_ratio": m.line_delay(u, self.band) / self.T,
            "lock_cycle": None, "steps": steps,
        }


def read_csv(name):
    path = os.path.join(OUT, name)
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def dump(name, rows):
    if not rows:
        return
    with open(os.path.join(OUT, name), "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader(); w.writerows(rows)


def strategy_from_sweep(sweep):
    """Strategies 1 and 2 evaluated from measured controller sweep data."""
    rows = []
    by_fi = {(float(r["f_MHz"]), float(r["Icp_uA"])): r for r in sweep}
    # Strategy 1: single fixed Icp for all frequencies
    for icp in ICPS_A:
        succ = 0; total = 0; locks = []
        worst = ""
        for f in FREQS_HZ:
            r = by_fi.get((f / 1e6, icp * 1e6))
            if r is None:
                continue
            succ += int(r["controller_success"]); total += int(r["controller_total"])
            if r["lock_max"] != "":
                locks.append(int(r["lock_max"]))
        rows.append({
            "strategy": "1_fixed",
            "detail": f"Icp={icp*1e6:.0f}uA all frequencies",
            "success": succ, "total": total,
            "success_pct": round(100 * succ / total, 1) if total else "",
            "worst_lock_cycles": max(locks) if locks else "",
            "notes": "one current setting; no band logic",
        })
    # Strategy 2: best per-band Icp (max success, then shortest worst lock)
    band_best = {}
    for b in (0, 1, 2):
        cands = [r for r in sweep if int(r["band"]) == b]
        cands.sort(key=lambda r: (-int(r["controller_success"]),
                                  int(r["lock_max"]) if r["lock_max"] != "" else 10**6))
        if cands:
            band_best[b] = float(cands[0]["Icp_uA"])
    succ = 0; total = 0; locks = []
    for f in FREQS_HZ:
        b = m.band_for_freq(f)
        icp_u = band_best.get(b, 300)
        r = by_fi.get((f / 1e6, icp_u))
        if r is None:
            continue
        succ += int(r["controller_success"]); total += int(r["controller_total"])
        if r["lock_max"] != "":
            locks.append(int(r["lock_max"]))
    rows.append({
        "strategy": "2_band_dependent",
        "detail": "band0=%s, band1=%s, band2=%s uA" % tuple(band_best.get(b, "") for b in (0,1,2)),
        "success": succ, "total": total,
        "success_pct": round(100 * succ / total, 1) if total else "",
        "worst_lock_cycles": max(locks) if locks else "",
        "notes": "requires RANGE-based Icp selection",
    })
    return rows, band_best


def improvement_study():
    """Investigation E + strategy 4: current switching on hard cases."""
    rows = []
    configs = [
        ("baseline", dict(fine_icps=(300e-6,))),
        ("small_step_only", dict(fine_icps=(300e-6,), coarse_step=0.05)),
        ("repeated_count_x3", dict(fine_icps=(300e-6,), repeated=3)),
        ("fine_current_150", dict(fine_icps=(150e-6,))),
        ("fine_current_50", dict(fine_icps=(50e-6,))),
        ("switch_300_then_150", dict(fine_icps=(300e-6, 150e-6))),
        ("switch_300_then_50", dict(fine_icps=(300e-6, 50e-6))),
        ("switch_300_150_50", dict(fine_icps=(300e-6, 150e-6, 50e-6))),
    ]
    cases = []
    for label in INITIAL_LABELS:
        cases.append((25e6, m.band_for_freq(25e6), label))
    for lab in ("1.00", "1.02", "1.05", "min", "max"):
        cases.append((30e6, m.band_for_freq(30e6), lab))
    for f in (50e6, 100e6, 200e6):
        for lab in ("min", "1.00", "1.30"):
            cases.append((f, m.band_for_freq(f), lab))

    t0 = time.time()
    for cname, kw in configs:
        for f, band, lab in cases:
            c = ExploreController(f, band, **kw)
            r = c.run(init_u(lab, f, band))
            rows.append({
                "config": cname, "f_MHz": f / 1e6, "band": band, "init": lab,
                "success": int(r["success"]), "outcome": r["outcome"],
                "fine_icp_used_uA": "" if r["fine_icp_uA"] is None else r["fine_icp_uA"],
                "coarse_steps": r["coarse_steps"], "fine_attempts": r["fine_attempts"],
                "final_ratio": round(r["final_ratio"], 4),
                "lock_cycle": "" if r["lock_cycle"] is None else r["lock_cycle"],
            })
        print(f"config {cname:22s} done ({time.time()-t0:.1f}s)", flush=True)
    return rows


def main():
    sweep = read_csv("current_sweep.csv")
    if not sweep:
        print("current_sweep.csv not found - strategy table skipped", flush=True)
        strategy_rows, band_best = [], {}
    else:
        strategy_rows, band_best = strategy_from_sweep(sweep)

    imp_rows = improvement_study()
    dump("strategy_comparison.csv", strategy_rows + [
        {
            "strategy": "3_fine_current_adjust",
            "detail": "descending Icp on fine failure (see improvement_comparison.csv)",
            "success": sum(r["success"] for r in imp_rows if r["config"].startswith("switch_")),
            "total": sum(1 for r in imp_rows if r["config"].startswith("switch_")),
            "success_pct": round(100 * sum(r["success"] for r in imp_rows
                                           if r["config"].startswith("switch_")) /
                                 max(1, sum(1 for r in imp_rows
                                            if r["config"].startswith("switch_"))), 1),
            "worst_lock_cycles": "",
            "notes": "investigation-only ExploreController",
        },
        {
            "strategy": "4_separate_acq_fine",
            "detail": "acq CP off (baseline already), fine Icp selectable",
            "success": sum(r["success"] for r in imp_rows if r["config"] == "fine_current_50"),
            "total": sum(1 for r in imp_rows if r["config"] == "fine_current_50"),
            "success_pct": round(100 * sum(r["success"] for r in imp_rows
                                           if r["config"] == "fine_current_50") /
                                 max(1, sum(1 for r in imp_rows
                                            if r["config"] == "fine_current_50")), 1),
            "worst_lock_cycles": "",
            "notes": "coarse counting already CP-disabled in baseline",
        },
    ])
    dump("improvement_comparison.csv", imp_rows)
    with open(os.path.join(OUT, "strategy_meta.json"), "w", encoding="utf-8") as fh:
        json.dump({"band_best_icp_uA": band_best}, fh, indent=2)
    print("DONE")


if __name__ == "__main__":
    main()
