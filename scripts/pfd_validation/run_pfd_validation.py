"""
PFD credibility validation for the 8-phase DLL (LEVEL B behavioral).

Runs the event-driven PFD model against the full required acquisition matrix and
compares it with the original oracle-style model in scripts/dll_model.py.

Outputs (all separate from the original results):
    results/pfd_validation/tables/*.csv
    results/pfd_validation/plots/*.png
    results/pfd_validation/logs/*.log

Usage:
    python scripts/pfd_validation/run_pfd_validation.py
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

import dll_model as old_model  # noqa: E402  (original, unmodified)
import pfd_event_model as ev  # noqa: E402

OUT = os.path.join(ROOT, "results", "pfd_validation")
TABLES = os.path.join(OUT, "tables")
PLOTS = os.path.join(OUT, "plots")
LOGS = os.path.join(OUT, "logs")

FREQS_MHZ = [25, 30, 42.5, 50, 60, 85, 100, 120, 150, 180, 200]
U0_LIST = [0.0, 0.1, 0.25, 0.5, 0.75, 0.9, 1.0]

ICP = 300e-6
C_LOOP = 25e-12
CYCLES = 4000


def ensure_dirs():
    for d in (TABLES, PLOTS, LOGS):
        os.makedirs(d, exist_ok=True)


def write_csv(name, header, rows):
    p = os.path.join(TABLES, name)
    with open(p, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(header)
        w.writerows(rows)
    return p


# ---------------------------------------------------------------------------
# E1: detector pulse widths (proves the detector logic)
# ---------------------------------------------------------------------------
def exp_detector_pulses():
    T = 1e-8
    f = 100e6
    rows = []
    for ratio in (0.05, 0.2, 0.5, 0.9, 0.99, 1.0, 1.01, 1.1, 1.5, 2.0, 3.0):
        tr = ev.measure_pulses(ratio * T, f, band=1, cycles=12)
        up_t = dn_t = None
        widths = []
        for t, kind, val in tr:
            if kind == "UP" and val:
                up_t = t
            elif kind == "DOWN" and val:
                dn_t = t
            elif kind == "RESET":
                uw = (t - up_t) / T if up_t is not None else 0.0
                dw = (t - dn_t) / T if dn_t is not None else 0.0
                widths.append((uw, dw))
                up_t = dn_t = None
        # steady-state = last two comparisons
        ss = widths[-2:] if len(widths) >= 2 else widths
        uw = float(np.mean([w[0] for w in ss])) if ss else 0.0
        dw = float(np.mean([w[1] for w in ss])) if ss else 0.0
        rows.append([f"{ratio:.3f}", f"{uw:.4f}", f"{dw:.4f}",
                     f"{(ratio % 1.0):.4f}", "MATCH" if abs(uw - (ratio % 1.0)) < 0.01 else "CHECK"])
    write_csv("detector_pulse_widths.csv",
              ["fixed_D_over_T", "ss_UP_width_over_T", "ss_DOWN_width_over_T",
               "frac_D_over_T", "up_matches_frac"], rows)

    fig, ax = plt.subplots(figsize=(8, 4.5))
    r = [float(x[0]) for x in rows]
    u = [float(x[1]) for x in rows]
    ax.plot(r, u, "o-", label="steady-state UP pulse width")
    ax.plot([0, 3], [0, 0], "k:", lw=0.8)
    ax.set_xlabel("fixed line delay D / T")
    ax.set_ylabel("UP pulse width / T")
    ax.set_title("Event-driven PFD: UP pulse width vs fixed delay (100 MHz, control frozen)")
    ax.grid(alpha=0.3)
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(os.path.join(PLOTS, "detector_pulse_width.png"), dpi=150)
    plt.close(fig)
    return rows


# ---------------------------------------------------------------------------
# E2: acquisition matrix, both polarities
# ---------------------------------------------------------------------------
def exp_acquisition_matrix(up_direction=-1):
    tag = "up_increases_delay" if up_direction == -1 else "up_decreases_delay"
    rows = []
    grid = np.zeros((len(U0_LIST), len(FREQS_MHZ)))
    lock_grid = np.full((len(U0_LIST), len(FREQS_MHZ)), np.nan)

    for i, u0 in enumerate(U0_LIST):
        for j, fmhz in enumerate(FREQS_MHZ):
            f = fmhz * 1e6
            band = ev.band_for_freq(f)
            r = ev.simulate_event_pfd(
                f, band=band, u0=u0, cycles=CYCLES, icp=ICP, c_loop=C_LOOP,
                up_direction=up_direction,
            )
            grid[i, j] = r["harmonic_index"]
            lock_grid[i, j] = np.nan if r["lock_cycle"] is None else r["lock_cycle"]
            if r["locked_1T"]:
                result = "LOCK_1T"
            elif r["oscillating"]:
                result = "OSCILLATION"
            elif r["locked_any"] and r["harmonic_index"] >= 1:
                result = f"HARMONIC_{r['harmonic_index']}T"
            else:
                result = "NO_LOCK"
            rows.append([
                f"{fmhz:g}", band, f"{u0:.2f}", f"{r['T_ps']:.3f}",
                f"{r['final_delay_ps']:.1f}", f"{r['final_ratio']:.4f}",
                f"{r['final_u']:.4f}",
                "" if r["lock_cycle"] is None else r["lock_cycle"],
                r["harmonic_index"], f"{r['settled_pp_frac_T']:.5f}",
                "YES" if r["rail_saturated"] else "no",
                "YES" if r["oscillating"] else "no",
                result,
            ])

    write_csv(f"acquisition_matrix_{tag}.csv",
              ["f_MHz", "band", "u0", "T_ps", "final_delay_ps", "delay_over_T",
               "final_u", "lock_cycle", "harmonic_index", "settled_pp_over_T",
               "rail_saturated", "oscillating", "result"], rows)

    # heatmap of harmonic index
    fig, ax = plt.subplots(figsize=(11, 4.6))
    im = ax.imshow(grid, aspect="auto", cmap="viridis", vmin=0, vmax=max(3, grid.max()))
    ax.set_xticks(range(len(FREQS_MHZ)))
    ax.set_xticklabels([f"{x:g}" for x in FREQS_MHZ], fontsize=8)
    ax.set_yticks(range(len(U0_LIST)))
    ax.set_yticklabels([f"{y:g}" for y in U0_LIST], fontsize=8)
    for i in range(len(U0_LIST)):
        for j in range(len(FREQS_MHZ)):
            ax.text(j, i, f"{int(grid[i, j])}T", ha="center", va="center",
                    fontsize=7, color="w" if grid[i, j] < 2.5 else "k")
    ax.set_xlabel("reference frequency (MHz)")
    ax.set_ylabel("initial control u0")
    ax.set_title(f"Final lock harmonic: 1T = correct, >1T = false lock ({tag})")
    fig.colorbar(im, ax=ax, label="harmonic index")
    fig.tight_layout()
    fig.savefig(os.path.join(PLOTS, f"acquisition_heatmap_{tag}.png"), dpi=150)
    plt.close(fig)
    return rows


# ---------------------------------------------------------------------------
# E3: acquisition basin map (does the loop return to 1T?)
# ---------------------------------------------------------------------------
def exp_basin_map():
    """Sweep the starting delay directly and record where the loop ends up."""
    f = 100e6
    band = ev.band_for_freq(f)
    T = 1e-8
    rows = []
    starts = np.arange(0.05, 3.60, 0.05)
    finals = []
    for s in starts:
        d0 = s * T
        u0 = ev.u_for_delay(d0, band) if d0 <= ev.line_delay(0.0, band) else 0.0
        r = ev.simulate_event_pfd(f, band=band, u0=u0, cycles=CYCLES,
                                  icp=ICP, c_loop=C_LOOP, up_direction=-1)
        finals.append(r["final_ratio"])
        rows.append([f"{s:.2f}", f"{u0:.4f}", f"{r['final_ratio']:.3f}",
                     r["harmonic_index"], f"{r['final_delay_ps']:.1f}",
                     "LOCK_1T" if r["locked_1T"] else "FALSE/NO_LOCK"])
    write_csv("basin_map_100MHz.csv",
              ["start_D_over_T", "u0", "final_D_over_T", "harmonic_index",
               "final_delay_ps", "result"], rows)

    fig, ax = plt.subplots(figsize=(9, 4.5))
    ax.plot(starts, finals, "o-", ms=3)
    ax.plot([0, 3.6], [0, 3.6], "k:", lw=0.8, label="no movement")
    for k in (1, 2, 3):
        ax.axhline(k, color="r", ls="--", lw=0.7)
        ax.text(3.45, k + 0.06, f"{k}T", color="r", fontsize=8)
    ax.set_xlabel("starting line delay D0 / T")
    ax.set_ylabel("final line delay / T")
    ax.set_title("Acquisition basin: where the loop ends up vs where it starts (100 MHz)")
    ax.grid(alpha=0.3)
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(os.path.join(PLOTS, "acquisition_basin_100MHz.png"), dpi=150)
    plt.close(fig)
    return rows


# ---------------------------------------------------------------------------
# E4: old oracle model vs new event model on the same grid
# ---------------------------------------------------------------------------
def exp_compare_models():
    rows = []
    agreed = 0
    total = 0
    for fmhz in FREQS_MHZ:
        f = fmhz * 1e6
        band = ev.band_for_freq(f)
        for u0 in U0_LIST:
            new = ev.simulate_event_pfd(f, band=band, u0=u0, cycles=CYCLES,
                                        icp=ICP, c_loop=C_LOOP, up_direction=-1)
            old = old_model.simulate_lock(f, band=band, u0=u0, cycles=CYCLES,
                                          icp=ICP, c_loop=C_LOOP, detector="pfd")
            total += 1
            same = (new["harmonic_index"] == old["harmonic_index"]) and \
                   (new["locked_1T"] == old["locked"])
            if same:
                agreed += 1
            rows.append([
                f"{fmhz:g}", f"{u0:.2f}",
                old["harmonic_index"], "YES" if old["locked"] else "no",
                f"{old['delay_over_T']:.3f}",
                new["harmonic_index"], "YES" if new["locked_1T"] else "no",
                f"{new['final_ratio']:.3f}",
                "SAME" if same else "DIFFERENT",
            ])
    write_csv("old_vs_new_model.csv",
              ["f_MHz", "u0", "old_harmonic", "old_locked_1T", "old_delay_over_T",
               "new_harmonic", "new_locked_1T", "new_delay_over_T", "verdict"], rows)
    return rows, agreed, total


# ---------------------------------------------------------------------------
# E5: startup strategy - minimum delay vs maximum delay
# ---------------------------------------------------------------------------
def exp_startup_strategy():
    rows = []
    for fmhz in FREQS_MHZ:
        f = fmhz * 1e6
        band = ev.band_for_freq(f)
        T = 1.0 / f
        d_min, d_max = d_min_max(band)
        for label, u0 in (("min_delay", 1.0), ("max_delay", 0.0), ("mid", 0.5)):
            r = ev.simulate_event_pfd(f, band=band, u0=u0, cycles=CYCLES,
                                      icp=ICP, c_loop=C_LOOP, up_direction=-1)
            rows.append([
                f"{fmhz:g}", band, label, f"{u0:.2f}",
                f"{d_min/T:.3f}", f"{d_max/T:.3f}",
                r["harmonic_index"], f"{r['final_ratio']:.3f}",
                "" if r["lock_cycle"] is None else r["lock_cycle"],
                "LOCK_1T" if r["locked_1T"] else ("HARMONIC" if r["locked_any"] else "NO_LOCK"),
            ])
    write_csv("startup_strategy.csv",
              ["f_MHz", "band", "strategy", "u0", "min_D_over_T", "max_D_over_T",
               "final_harmonic", "final_D_over_T", "lock_cycle", "result"], rows)
    return rows


def d_min_max(band):
    b = ev.BANDS[band]
    return ev.N_STAGES * b["t_lo"], ev.N_STAGES * b["t_hi"]


# ---------------------------------------------------------------------------
# E6: capture window of a phase detector (the architectural alternative)
# ---------------------------------------------------------------------------
def exp_capture_window():
    """A phase detector that measures the wrapped error can only acquire if the
    starting delay is within +/-T/2 of the target. Check the band plan against it.
    """
    rows = []
    for fmhz in FREQS_MHZ:
        f = fmhz * 1e6
        band = ev.band_for_freq(f)
        T = 1.0 / f
        d_min, d_max = d_min_max(band)
        lo, hi = d_min / T, d_max / T
        reaches = lo <= 1.0 <= hi
        capturable = 0.5 < lo < 1.5
        rows.append([f"{fmhz:g}", band, f"{lo:.3f}", f"{hi:.3f}",
                     "YES" if reaches else "no",
                     "YES" if capturable else "no",
                     "OK" if (reaches and capturable) else "FAIL"])
    write_csv("capture_window.csv",
              ["f_MHz", "band", "min_D_over_T", "max_D_over_T",
               "range_contains_1T", "capturable_from_min_delay", "verdict"], rows)
    return rows


# ---------------------------------------------------------------------------
# E7: wrapped-phase-detector alternative on the same grid
# ---------------------------------------------------------------------------
def exp_wrap_detector():
    """Original delay characteristic, but with a wrapping phase detector.

    This is NOT the PFD. It is a mixer/XOR-style detector whose output is
    proportional to the wrapped phase error, which does reach equilibrium at 1T.
    Used to show what a workable detector looks like.
    """
    rows = []
    counts = {}
    for fmhz in FREQS_MHZ:
        f = fmhz * 1e6
        band = ev.band_for_freq(f)
        for u0 in U0_LIST:
            r = old_model.simulate_lock(f, band=band, u0=u0, cycles=CYCLES,
                                        icp=ICP, c_loop=C_LOOP, detector="xor")
            res = "LOCK_1T" if r["locked"] else (
                f"HARMONIC_{r['harmonic_index']}T" if r["harmonic_index"] > 1 else "NO_LOCK")
            counts[res] = counts.get(res, 0) + 1
            rows.append([f"{fmhz:g}", band, f"{u0:.2f}", f"{r['delay_over_T']:.3f}",
                         r["harmonic_index"],
                         "" if r["lock_cycle"] is None else r["lock_cycle"], res])
    write_csv("wrap_detector_grid.csv",
              ["f_MHz", "band", "u0", "delay_over_T", "harmonic_index",
               "lock_cycle", "result"], rows)
    return rows, counts


# ---------------------------------------------------------------------------
def main():
    ensure_dirs()
    log_lines = []

    def log(s=""):
        print(s)
        log_lines.append(s)

    log("=" * 96)
    log("PFD CREDIBILITY VALIDATION - LEVEL B behavioral, event-driven PFD")
    log(f"Icp={ICP*1e6:.0f} uA, C_loop={C_LOOP*1e12:.0f} pF, cycles={CYCLES}")
    log("=" * 96)

    log("\n[E1] Detector pulse widths vs fixed delay (control frozen)")
    for r in exp_detector_pulses():
        log(f"   D/T={r[0]:>5}  steady UP={r[1]:>7}  DOWN={r[2]:>7}  frac(D/T)={r[3]:>7}  {r[4]}")

    log("\n[E2] Acquisition matrix (UP increases delay, min-delay startup)")
    rows = exp_acquisition_matrix(up_direction=-1)
    by_result = {}
    for r in rows:
        by_result[r[12]] = by_result.get(r[12], 0) + 1
    log(f"   outcomes: {by_result}")

    rows2 = exp_acquisition_matrix(up_direction=+1)
    by2 = {}
    for r in rows2:
        by2[r[12]] = by2.get(r[12], 0) + 1
    log(f"   opposite polarity (UP decreases delay): {by2}")

    log("\n[E3] Acquisition basin map at 100 MHz")
    basin = exp_basin_map()
    l1 = sum(1 for b in basin if b[5] == "LOCK_1T")
    log(f"   starting points that end at 1T: {l1}/{len(basin)}")

    log("\n[E4] Old oracle model vs new event-driven model")
    comp, agreed, total = exp_compare_models()
    log(f"   identical verdicts: {agreed}/{total}")
    diffs = [c for c in comp if c[8] == "DIFFERENT"]
    for d in diffs[:12]:
        log(f"   DIFF f={d[0]:>5} MHz u0={d[1]:>4}: old {d[2]}T/{d[3]} vs new {d[5]}T/{d[6]}")
    if len(diffs) > 12:
        log(f"   ... {len(diffs)-12} more differing rows in old_vs_new_model.csv")

    log("\n[E5] Startup strategy comparison")
    for r in exp_startup_strategy():
        log(f"   {r[0]:>5} MHz {r[2]:>9}: D_start={r[4]}T..{r[5]}T -> final {r[7]}T  {r[9]}")

    log("\n[E6] Capture window of a wrapped phase detector")
    for r in exp_capture_window():
        log(f"   {r[0]:>5} MHz band {r[1]}: D_min={r[2]}T D_max={r[3]}T "
            f"contains1T={r[4]:>3} capturable={r[5]:>3}  {r[6]}")

    log("\n[E7] Wrapping phase detector (alternative) on the same grid")
    _, wcounts = exp_wrap_detector()
    log(f"   outcomes: {wcounts}")

    with open(os.path.join(LOGS, "pfd_validation_run.log"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(log_lines) + "\n")

    log(f"\nTables: {TABLES}\nPlots : {PLOTS}\nLogs  : {LOGS}")


if __name__ == "__main__":
    main()
