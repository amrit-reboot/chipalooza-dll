"""
Behavioral (Level B) DLL experiment runner for the Chipalooza #4 feasibility study.

Runs the six proposal-relevant experiments against scripts/dll_model.py and writes
CSV tables to results/tables/ and PNG plots to results/plots/.

Every result produced here is BEHAVIORAL (Level B). No transistor-level or
post-layout claim is made anywhere in this file.

Usage:
    python scripts/run_behavioral.py
"""

from __future__ import annotations

import csv
import os
import sys

import numpy as np

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dll_model as m  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PLOT_DIR = os.path.join(ROOT, "results", "plots")
TABLE_DIR = os.path.join(ROOT, "results", "tables")

VDD = m.VDD_NOM
ICP = 300e-6
C_LOOP = 25e-12

BAND_MIDPOINT = {0: 42.5e6, 1: 85e6, 2: 150e6}


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
def ensure_dirs():
    os.makedirs(PLOT_DIR, exist_ok=True)
    os.makedirs(TABLE_DIR, exist_ok=True)


def write_csv(name, header, rows):
    path = os.path.join(TABLE_DIR, name)
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(header)
        w.writerows(rows)
    return path


def loop_gain(u, band, icp=ICP, c=m.C_LOOP if hasattr(m, "C_LOOP") else 25e-12, vdd=VDD):
    """Per-cycle loop gain G = Icp * |dT_line/du| / (C*VDD). Must be < 1 for stability."""
    return icp * abs(m.line_kd(u, band)) / (c * vdd)


# ---------------------------------------------------------------------------
# E1: lock transient and band-midpoint lock table
# ---------------------------------------------------------------------------
def exp_lock_transient():
    res = m.simulate_lock(100e6, band=m.band_for_freq(100e6), cycles=1200, icp=ICP, c_loop=C_LOOP)

    fig, ax = plt.subplots(2, 1, figsize=(8, 6), sharex=True)
    cyc = np.arange(len(res["u_hist"]))
    ax[0].plot(cyc, res["err_hist"] * 1e12, lw=1.2)
    ax[0].axhline(0.02 * res["T"] * 1e12, color="k", ls="--", lw=0.8, label="+2% T")
    ax[0].axhline(-0.02 * res["T"] * 1e12, color="k", ls="--", lw=0.8, label="-2% T")
    ax[0].set_ylabel("phase error (ps)")
    ax[0].set_title(
        f"Behavioral DLL lock transient @ 100 MHz, band {res['band']} "
        f"(lock at cycle {res['lock_cycle']})"
    )
    ax[0].legend(fontsize=8)
    ax[0].grid(alpha=0.3)
    ax[1].plot(cyc, res["u_hist"], lw=1.5, color="tab:red")
    ax[1].set_xlabel("reference cycle")
    ax[1].set_ylabel("VCTRL/VDD (normalised)")
    ax[1].grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(os.path.join(PLOT_DIR, "lock_transient_100MHz.png"), dpi=150)
    plt.close(fig)

    rows = []
    for band, f in BAND_MIDPOINT.items():
        r = m.simulate_lock(f, band=band, cycles=1200, icp=ICP, c_loop=C_LOOP)
        rows.append([
            f"{f/1e6:.1f}", band,
            "" if r["lock_cycle"] is None else r["lock_cycle"],
            f"{r['static_err_ps']:.3f}",
            f"{100*r['static_err_frac_T']:.3f}",
            f"{r['u_final']:.4f}",
            f"{r['delay_over_T']:.4f}",
            r["harmonic_index"],
            "PASS" if r["locked"] else "FAIL",
        ])
    write_csv(
        "lock_band_midpoints.csv",
        ["f_MHz", "band", "lock_cycle", "static_err_ps", "static_err_pct_T",
         "u_final", "delay_over_T", "harmonic_index", "status"],
        rows,
    )
    return res, rows


# ---------------------------------------------------------------------------
# E2: frequency sweep across the full specified 25-200 MHz range
# ---------------------------------------------------------------------------
def exp_frequency_sweep():
    freqs = np.arange(25e6, 200e6 + 1, 5e6)
    rows, lock_times, static_errs, locked_flags = [], [], [], []

    for f in freqs:
        band = m.band_for_freq(f)
        r = m.simulate_lock(f, band=band, cycles=1500, icp=ICP, c_loop=C_LOOP)
        lock_times.append(np.nan if r["lock_cycle"] is None else r["lock_cycle"])
        static_errs.append(abs(r["static_err_frac_T"]) * 100)
        locked_flags.append(1 if r["locked"] else 0)
        rows.append([
            f"{f/1e6:.1f}", band,
            "" if r["lock_cycle"] is None else r["lock_cycle"],
            f"{r['static_err_ps']:.3f}",
            f"{100*r['static_err_frac_T']:.3f}",
            f"{r['u_final']:.4f}",
            r["harmonic_index"],
            "PASS" if r["locked"] else "FAIL",
        ])

    write_csv(
        "frequency_sweep.csv",
        ["f_MHz", "band", "lock_cycle", "static_err_ps", "static_err_pct_T",
         "u_final", "harmonic_index", "status"],
        rows,
    )

    lock_times = np.array(lock_times, dtype=float)
    fig, ax = plt.subplots(2, 1, figsize=(9, 6), sharex=True)
    ax[0].plot(freqs / 1e6, lock_times, "o-", ms=3)
    ax[0].axhline(100, color="g", ls="--", lw=0.8, label="spec typical 100 cycles")
    ax[0].axhline(400, color="r", ls="--", lw=0.8, label="spec max 400 cycles")
    ax[0].set_ylabel("lock time (cycles)")
    ax[0].set_title("Behavioral DLL frequency sweep, 25-200 MHz")
    ax[0].legend(fontsize=8)
    ax[0].grid(alpha=0.3)
    ax[1].plot(freqs / 1e6, static_errs, "s-", ms=3, color="tab:orange")
    ax[1].axhline(2, color="g", ls="--", lw=0.8, label="spec typical 2% T")
    ax[1].axhline(5, color="r", ls="--", lw=0.8, label="spec max 5% T")
    ax[1].set_xlabel("input frequency (MHz)")
    ax[1].set_ylabel("static phase error (% T)")
    ax[1].legend(fontsize=8)
    ax[1].grid(alpha=0.3)
    for b, mid in BAND_MIDPOINT.items():
        for axis in ax:
            axis.axvline(mid / 1e6, color="gray", ls=":", lw=0.7)
    fig.tight_layout()
    fig.savefig(os.path.join(PLOT_DIR, "frequency_sweep.png"), dpi=150)
    plt.close(fig)

    return freqs, lock_times, static_errs, locked_flags


# ---------------------------------------------------------------------------
# E3: eight phases, tap spacing, DNL/INL with mismatch Monte Carlo
# ---------------------------------------------------------------------------
def exp_phase_spacing():
    f = 100e6
    band = m.band_for_freq(f)
    r = m.simulate_lock(f, band=band, cycles=1200, icp=ICP, c_loop=C_LOOP)
    if not r["locked"]:
        raise RuntimeError(
            f"tap-spacing experiment requires a locked point, got "
            f"{r['harmonic_index']}T at u={r['u_final']:.3f}"
        )
    u = r["u_final"]
    T = r["T"]

    ideal = m.tap_dnl(u, band)
    rows = []
    for i in range(m.N_STAGES):
        rows.append([
            i,
            f"{ideal['taps'][i]*1e12:.3f}",
            f"{(i+1)*90:.1f}",
            f"{ideal['spacing'][i]*1e12:.3f}",
            f"{100*ideal['dnl'][i]:.4f}",
            f"{100*ideal['inl'][i]:.4f}",
        ])
    write_csv(
        "tap_spacing_100MHz.csv",
        ["tap", "delay_ps", "phase_deg", "spacing_ps", "DNL_pct_T8", "INL_pct_T8"],
        rows,
    )

    # Monte Carlo tap mismatch: 30 samples, 1% per-stage sigma (behavioral assumption).
    rng = np.random.default_rng(7)
    n_mc, sigma = 30, 0.01
    mc_dnl_max, mc_dnl_rms, mc_duty = [], [], []
    for _ in range(n_mc):
        eps = rng.normal(0.0, sigma, m.N_STAGES)
        d = m.tap_dnl(u, band, mismatch_eps=eps)
        dty = m.duty_corrector(0.5, u, band, mismatch_eps=eps)
        mc_dnl_max.append(d["dnl_max"])
        mc_dnl_rms.append(d["dnl_rms"])
        mc_duty.append(dty["corrected_duty"])

    mc_dnl_max = np.array(mc_dnl_max)
    mc_duty = np.array(mc_duty)

    fig, ax = plt.subplots(2, 1, figsize=(9, 6))
    x = np.arange(m.N_STAGES)
    ax[0].bar(x, ideal["dnl"] * 100, color="tab:blue")
    ax[0].axhline(8, color="k", ls="--", lw=0.8, label="spec typical +/-8% of T/8")
    ax[0].axhline(-8, color="k", ls="--", lw=0.8)
    ax[0].axhline(15, color="r", ls=":", lw=0.9, label="spec max +/-15% of T/8")
    ax[0].axhline(-15, color="r", ls=":", lw=0.9)
    ax[0].set_xticks(x)
    ax[0].set_xticklabels([f"PH{i}" for i in range(m.N_STAGES)], fontsize=8)
    ax[0].set_ylabel("DNL (% of T/8)")
    ax[0].set_title("Tap spacing DNL, ideal matched line @ 100 MHz")
    ax[0].legend(fontsize=8)
    ax[0].grid(alpha=0.3, axis="y")

    ax[1].hist(mc_dnl_max * 100, bins=12, color="tab:purple", edgecolor="k")
    ax[1].axvline(15, color="r", ls=":", lw=1.2, label="spec max 15%")
    ax[1].axvline(np.percentile(mc_dnl_max * 100, 99.7), color="k", ls="--", lw=1.0,
                  label=f"99.7% = {np.percentile(mc_dnl_max*100, 99.7):.1f}%")
    ax[1].set_xlabel("worst-tap |DNL| (% of T/8)")
    ax[1].set_ylabel("samples")
    ax[1].set_title(f"Monte Carlo tap mismatch, {n_mc} samples, {sigma*100:.0f}% per-stage sigma (Level B)")
    ax[1].legend(fontsize=8)
    ax[1].grid(alpha=0.3, axis="y")
    fig.tight_layout()
    fig.savefig(os.path.join(PLOT_DIR, "tap_dnl.png"), dpi=150)
    plt.close(fig)

    # Phase waveform timing diagram at lock.
    taps = m.tap_delays(u, band)
    t = np.linspace(0, 2.5 * T, 5000)
    fig, ax = plt.subplots(figsize=(10, 5))
    for i in range(m.N_STAGES):
        high = ((t - taps[i]) % T) < 0.5 * T
        ax.plot(t * 1e9, high + (m.N_STAGES - 1 - i) * 1.4, lw=1.0,
                label=f"PHASE[{i}] = {i*45} deg")
    ax.set_xlabel("time (ns)")
    ax.set_ylabel("PHASE[7] ... PHASE[0]")
    ax.set_yticks([])
    ax.set_title(f"Eight output phases at lock, 100 MHz, band {band} (T = {T*1e9:.1f} ns)")
    ax.legend(fontsize=7, ncol=4, loc="upper right")
    ax.grid(alpha=0.2)
    fig.tight_layout()
    fig.savefig(os.path.join(PLOT_DIR, "phase_waveforms_100MHz.png"), dpi=150)
    plt.close(fig)

    return {
        "u": u, "T": T, "ideal": ideal,
        "mc_dnl_max_pct": mc_dnl_max * 100,
        "mc_dnl_rms_pct": np.array(mc_dnl_rms) * 100,
        "mc_duty": mc_duty,
    }


# ---------------------------------------------------------------------------
# E4: duty-cycle correction
# ---------------------------------------------------------------------------
def exp_duty():
    f = 100e6
    band = m.band_for_freq(f)
    r = m.simulate_lock(f, band=band, cycles=1200, icp=ICP, c_loop=C_LOOP)
    if not r["locked"]:
        raise RuntimeError("duty experiment requires a locked point")
    u = r["u_final"]

    rng = np.random.default_rng(11)
    rows = []
    for din in (0.30, 0.50, 0.70):
        d = m.duty_corrector(din, u, band)
        samples = np.array([
            m.duty_corrector(din, u, band, mismatch_eps=rng.normal(0, 0.01, m.N_STAGES))["corrected_duty"]
            for _ in range(50)
        ])
        rows.append([
            f"{din*100:.0f}",
            f"{d['uncorrected_duty']*100:.2f}",
            f"{d['corrected_duty']*100:.2f}",
            f"{samples.mean()*100:.2f}",
            f"{samples.std()*100:.2f}",
            "PASS" if 0.45 <= samples.mean() <= 0.55 else "FAIL",
        ])

    write_csv(
        "duty_correction.csv",
        ["input_duty_pct", "uncorrected_pct", "corrected_ideal_pct",
         "corrected_mean_pct", "sigma_pct", "status_45_55"],
        rows,
    )

    fig, ax = plt.subplots(figsize=(8, 4.5))
    labels = [f"input {r[0]}%" for r in rows]
    x = np.arange(len(rows))
    ax.bar(x - 0.2, [float(r[1]) for r in rows], 0.4, label="uncorrected (pass-through)", color="tab:gray")
    ax.bar(x + 0.2, [float(r[3]) for r in rows], 0.4, label="CLK50 corrected (mean of 50 MC)", color="tab:green")
    ax.axhspan(45, 55, color="tab:green", alpha=0.12, label="spec 45-55%")
    ax.axhline(50, color="k", ls="--", lw=0.8)
    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    ax.set_ylabel("duty cycle (%)")
    ax.set_ylim(0, 80)
    ax.set_title("Duty-cycle correction, behavioral model @ 100 MHz")
    ax.legend(fontsize=8)
    ax.grid(alpha=0.3, axis="y")
    fig.tight_layout()
    fig.savefig(os.path.join(PLOT_DIR, "duty_correction.png"), dpi=150)
    plt.close(fig)

    return rows


# ---------------------------------------------------------------------------
# E5: startup sweep / false-lock investigation
# ---------------------------------------------------------------------------
def exp_startup():
    freqs = [25e6, 60e6, 100e6, 150e6, 200e6]
    u0_list = np.round(np.arange(0.0, 1.0001, 0.1), 2)
    rows = []
    summary = {}

    for f in freqs:
        band = m.band_for_freq(f)
        T = 1.0 / f
        min_delay, max_delay = m.delay_range(band)
        for u0 in u0_list:
            r = m.simulate_lock(f, band=band, cycles=2000, u0=float(u0), icp=ICP, c_loop=C_LOOP)
            rows.append([
                f"{f/1e6:.0f}", band, f"{u0:.1f}", f"{r['T']*1e9:.3f}",
                f"{r['t_final']*1e12:.1f}",
                f"{r['delay_over_T']:.3f}",
                r["harmonic_index"],
                "" if r["lock_cycle"] is None else r["lock_cycle"],
                f"{r['static_err_frac_T']*100:.2f}",
                "TRUE_LOCK" if r["locked"] else ("HARMONIC" if r["harmonic_index"] > 1 else "NO_LOCK"),
            ])
        summary[f] = (min_delay, max_delay, T)

    write_csv(
        "startup_sweep.csv",
        ["f_MHz", "band", "u0", "T_ns", "t_final_ps", "delay_over_T",
         "harmonic_index", "lock_cycle", "static_err_pct_T", "result"],
        rows,
    )

    fig, ax = plt.subplots(figsize=(8, 4.5))
    for f in freqs:
        sub = [r for r in rows if float(r[0]) == f / 1e6]
        xs = [float(r[2]) for r in sub]
        ys = [float(r[6]) for r in sub]
        ax.plot(xs, ys, "o-", label=f"{f/1e6:.0f} MHz (band {m.band_for_freq(f)})")
    ax.axhline(1.0, color="g", ls="--", lw=1.0, label="correct lock (delay = 1T)")
    ax.set_xlabel("initial control value u0 (0 = max delay, 1 = min delay)")
    ax.set_ylabel("final delay / T  (harmonic index)")
    ax.set_title("Startup sweep: which harmonic the loop settles on")
    ax.legend(fontsize=8)
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(os.path.join(PLOT_DIR, "startup_false_lock.png"), dpi=150)
    plt.close(fig)

    return rows, summary


# ---------------------------------------------------------------------------
# E6: loop gain and stability margin
# ---------------------------------------------------------------------------
def exp_loop_gain():
    rows = []
    for band in (0, 1, 2):
        for u in (0.0, 0.25, 0.5, 0.75, 1.0):
            g = loop_gain(u, band)
            rows.append([band, f"{u:.2f}", f"{m.line_delay(u, band)*1e12:.1f}",
                         f"{m.line_kd(u, band)*1e12:.2f}", f"{g:.4f}",
                         "STABLE" if g < 1.0 else "UNSTABLE"])
    write_csv(
        "loop_gain.csv",
        ["band", "u", "t_line_ps", "dT_line_per_du_ps", "per_cycle_gain_G", "status"],
        rows,
    )
    return rows


def exp_gain_margin():
    """Loop gain at the ACTUAL locked operating points versus charge-pump current.

    Evaluating gain at the rail (u -> 0) is misleading: u = 0 is the clamp
    extreme and is never a settled lock point in range. What matters is G at the
    control value the loop actually settles on for each frequency.
    """
    icps = [50e-6, 75e-6, 100e-6, 150e-6, 200e-6, 300e-6]
    freqs = np.arange(25e6, 200e6 + 1, 12.5e6)
    rows = []
    for icp in icps:
        worst_g = 0.0
        max_lock = 0
        not_locked = 0
        for f in freqs:
            band = m.band_for_freq(f)
            r = m.simulate_lock(f, band=band, cycles=4000, icp=icp, c_loop=C_LOOP)
            if not r["locked"]:
                not_locked += 1
                continue
            worst_g = max(worst_g, loop_gain(r["u_final"], band, icp=icp))
            max_lock = max(max_lock, r["lock_cycle"])
        rows.append([
            f"{icp*1e6:.0f}", f"{worst_g:.4f}", f"{max_lock}", f"{not_locked}",
            "OK" if worst_g < 0.5 else ("MARGINAL" if worst_g < 1.0 else "UNSTABLE"),
            "PASS" if max_lock <= 400 and not_locked == 0 else "FAIL_SPEC",
        ])
    write_csv(
        "gain_vs_icp.csv",
        ["icp_uA", "worst_G_at_locked_points", "max_lock_cycles", "not_locked_count",
         "gain_margin", "lock_spec_400"],
        rows,
    )
    return rows


def exp_detector_comparison():
    """PFD versus wrapping XOR detector: does the detector choice change acquisition?"""
    freqs = [25e6, 40e6, 60e6, 100e6, 150e6, 200e6]
    rows = []
    for f in freqs:
        band = m.band_for_freq(f)
        for det in ("pfd", "xor"):
            r = m.simulate_lock(f, band=band, cycles=2000, icp=ICP, c_loop=C_LOOP, detector=det)
            rows.append([
                f"{f/1e6:.0f}", band, det,
                "" if r["lock_cycle"] is None else r["lock_cycle"],
                r["harmonic_index"],
                f"{r['delay_over_T']:.3f}",
                "LOCK" if r["locked"] else "NO_LOCK",
            ])
    write_csv(
        "detector_comparison.csv",
        ["f_MHz", "band", "detector", "lock_cycle", "harmonic_index", "delay_over_T", "result"],
        rows,
    )
    return rows


# ---------------------------------------------------------------------------
# E7: jitter estimate
# ---------------------------------------------------------------------------
def exp_jitter():
    rows = []
    for s in (0.25, 0.5, 1.0, 1.2, 2.0):
        j = m.jitter_estimate(100e6, 20e-3, sensitivity_per_frac=s)
        rows.append([f"{s:.2f}", f"{j['dT_rms_ps']:.2f}", f"{j['period_jitter_rms_ps']:.2f}",
                     "PASS" if j["period_jitter_rms_ps"] <= 60 else "FAIL"])
    write_csv(
        "jitter_sensitivity.csv",
        ["assumed_supply_sensitivity_S", "dT_rms_ps", "period_jitter_rms_ps",
         "status_60ps_max"],
        rows,
    )

    j = m.jitter_estimate(100e6, 20e-3, sensitivity_per_frac=1.2)
    rng = np.random.default_rng(3)
    T = 1e-8
    dT = 1.2 * (20e-3 / VDD) * T
    noise = rng.normal(0, dT, 20000)
    pj = (noise[1:] - noise[:-1]) * 1e12

    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.hist(pj, bins=60, color="tab:blue", edgecolor="k", alpha=0.8)
    ax.axvline(60, color="r", ls="--", lw=1.0, label="spec max 60 ps RMS")
    ax.axvline(np.std(pj), color="k", ls="-", lw=1.2,
               label=f"RMS = {np.std(pj):.1f} ps")
    ax.set_xlabel("period jitter per cycle (ps)")
    ax.set_ylabel("count")
    ax.set_title("Supply-noise-induced period jitter ESTIMATE, 20 mVrms, S = 1.2 (Level B)")
    ax.legend(fontsize=8)
    ax.grid(alpha=0.3, axis="y")
    fig.tight_layout()
    fig.savefig(os.path.join(PLOT_DIR, "jitter_estimate.png"), dpi=150)
    plt.close(fig)

    return rows, j


# ---------------------------------------------------------------------------
def main():
    ensure_dirs()

    print("=" * 78)
    print("BEHAVIORAL (LEVEL B) DLL PROTOTYPE — all results below are behavioral")
    print(f"Icp = {ICP*1e6:.0f} uA, C_loop = {C_LOOP*1e12:.0f} pF, VDD = {VDD} V")
    print("=" * 78)

    print("\n[E1] Lock transient and band midpoints")
    res, mid_rows = exp_lock_transient()
    for row in mid_rows:
        print("   f=%s MHz band=%s lock_cycle=%s static_err=%s ps (%s%%T) harmonic=%s %s"
              % (row[0], row[1], row[2] or "none", row[3], row[4], row[7], row[8]))

    print("\n[E2] Frequency sweep 25-200 MHz")
    freqs, lock_times, static_errs, locked = exp_frequency_sweep()
    ok = int(np.sum(locked))
    print(f"   {ok}/{len(freqs)} frequencies true-locked")
    print(f"   lock time: min={np.nanmin(lock_times):.0f} max={np.nanmax(lock_times):.0f} cycles")
    print(f"   static error: max={np.nanmax(static_errs):.3f}% T")
    bad = [(f/1e6, lt) for f, lt, l in zip(freqs, lock_times, locked) if not l]
    if bad:
        print(f"   NOT LOCKED at: {[f'{b[0]:.0f} MHz' for b in bad]}")

    print("\n[E3] Eight phases / tap spacing / Monte Carlo mismatch")
    sp = exp_phase_spacing()
    print(f"   locked u={sp['u']:.4f}, T={sp['T']*1e9:.2f} ns, T/8={sp['T']/8*1e12:.1f} ps")
    print(f"   ideal matched DNL max = {sp['ideal']['dnl_max']*100:.4f}% of T/8")
    print(f"   30-sample MC (1% stage sigma): DNL max mean={sp['mc_dnl_max_pct'].mean():.2f}%"
          f" p99.7={np.percentile(sp['mc_dnl_max_pct'], 99.7):.2f}%")
    print(f"   MC duty (50% input): mean={sp['mc_duty'].mean()*100:.3f}%"
          f" sigma={sp['mc_duty'].std()*100:.3f}%")

    print("\n[E4] Duty-cycle correction")
    for row in exp_duty():
        print(f"   input {row[0]}% -> uncorrected {row[1]}% -> corrected {row[3]}%"
              f" +/- {row[4]}%  {row[5]}")

    print("\n[E5] Startup / false-lock sweep")
    st_rows, st_sum = exp_startup()
    for f, (mind, maxd, T) in st_sum.items():
        print(f"   {f/1e6:5.0f} MHz: T={T*1e9:6.3f} ns, min line delay={mind*1e9:.3f} ns"
              f" ({mind/T:.2f}T), max={maxd*1e9:.3f} ns ({maxd/T:.2f}T)")
    by_result = {}
    for r in st_rows:
        by_result.setdefault(r[9], 0)
        by_result[r[9]] += 1
    print(f"   outcomes over {len(st_rows)} startup trials: {by_result}")

    print("\n[E6] Loop gain / stability")
    lg = exp_loop_gain()
    gains = [float(r[4]) for r in lg]
    print(f"   per-cycle gain G range {min(gains):.4f} .. {max(gains):.4f} (stable if < 1)")
    print("\n[E6b] Gain at actual lock points versus charge-pump current")
    for r in exp_gain_margin():
        print(f"   Icp={r[0]:>4} uA -> worst G={r[1]}  max lock={r[2]:>4} cyc  "
              f"not_locked={r[3]}  gain={r[4]}  {r[5]}")

    print("\n[E6c] Detector comparison (PFD vs wrapping XOR)")
    for r in exp_detector_comparison():
        print(f"   {r[0]:>4} MHz band {r[1]} {r[2]:>3}: {r[6]:<7} "
              f"delay={r[5]}T lock_cycle={r[3] or 'none'}")

    print("\n[E7] Jitter estimate")
    jrows, j = exp_jitter()
    for r in jrows:
        print(f"   S={r[0]}: dT_rms={r[1]} ps, period jitter={r[2]} ps  {r[3]}")
    print(f"   break-even S for 25 ps = {j['break_even_sensitivity_25ps']:.3f}")
    print(f"   break-even S for 60 ps = {j['break_even_sensitivity_60ps']:.3f}")

    print("\n" + "=" * 78)
    print(f"Plots  : {PLOT_DIR}")
    print(f"Tables : {TABLE_DIR}")
    print("All results are LEVEL B (behavioral). Not transistor-level evidence.")
    print("=" * 78)


if __name__ == "__main__":
    main()
