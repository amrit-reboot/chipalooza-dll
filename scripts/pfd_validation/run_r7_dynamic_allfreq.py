"""R7: independent dynamic engine across all required frequencies.

Compares the quasi-static event engine with the 8-stage dynamic engine at the
same coarse delay preset, and records the 25 MHz low-Icp remedy as a proposal
(not applied to the architecture).
"""
import os, sys, csv
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(ROOT, "scripts"))
import pfd_model_v3 as v3

OUT = os.path.join(ROOT, "results", "pfd_validation", "review", "tables")
FREQS = [25, 30, 42.5, 50, 60, 85, 100, 120, 150, 180, 200]
rows = []
for fmhz in FREQS:
    f = fmhz * 1e6
    band = v3.band_for_freq(f)
    d = v3.simulate_dynamic(f, band=band, start_ratio=1.3, cycles=1500,
                            substeps=100)
    e = v3.simulate_event(f, band=band, coarse_preset=1.3, cycles=3000)
    rows.append([f"{fmhz:g}", band, "300", f"{d['final_ratio']:.3f}",
                 f"{e['final_ratio']:.3f}",
                 "LOCK_1T" if abs(d["final_ratio"] - 1.0) < 0.03 else "NO_LOCK"])

for fmhz in (25, 30):
    f = fmhz * 1e6
    for icp in (50e-6, 100e-6, 150e-6):
        d = v3.simulate_dynamic(f, band=0, start_ratio=1.3, cycles=1500,
                                substeps=100, icp=icp)
        e = v3.simulate_event(f, band=0, coarse_preset=1.3, cycles=3000, icp=icp)
        rows.append([f"{fmhz:g}", 0, f"{icp*1e6:.0f}", f"{d['final_ratio']:.3f}",
                     f"{e['final_ratio']:.3f}",
                     "LOCK_1T" if abs(d["final_ratio"] - 1.0) < 0.03 else "NO_LOCK"])

path = os.path.join(OUT, "r7_dynamic_preset_1p3.csv")
with open(path, "w", newline="", encoding="utf-8") as fh:
    w = csv.writer(fh)
    w.writerow(["f_MHz", "band", "Icp_uA", "dynamic_final_D_over_T",
                "event_final_D_over_T", "result"])
    w.writerows(rows)
for r in rows:
    print("  ".join(map(str, r)))
main = [r for r in rows if r[2] == "300"]
print(f"preset 1.3 T, Icp=300 uA: dynamic 1T locks "
      f"{sum(1 for r in main if r[5] == 'LOCK_1T')}/{len(main)}")
