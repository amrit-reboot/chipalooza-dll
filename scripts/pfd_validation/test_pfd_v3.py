"""
New detector / acquisition tests for the independent review (LEVEL B).

No pytest required:  python scripts/pfd_validation/test_pfd_v3.py

These tests are added alongside the existing test_pfd.py; they do not replace it.
"""
from __future__ import annotations

import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "scripts"))

import pfd_model_v2_review as v2   # noqa: E402
import pfd_model_v3 as v3          # noqa: E402

F = 100e6
T = 1.0 / F
ICP, C = 300e-6, 25e-12


def q_at(ratio):
    r = v2.simulate_pfd(F, band=1, cycles=40, icp=ICP, c_loop=C,
                        fixed_delay=ratio * T, freeze_delay=True, up_direction=+1)
    return r["q_per_period_over_icpT"]


def frozen_around(k, eps_frac):
    """Frozen transfer characteristic immediately either side of kT."""
    return q_at(k - eps_frac), q_at(k), q_at(k + eps_frac)


# ---------------------------------------------------------------------------
def test_charge_transfer_matches_sawtooth_around_T():
    up, mid, down = frozen_around(1.0, 0.02)
    assert abs(up - 0.98) < 0.01, f"Q(0.98T)={up:.3f}"
    assert abs(mid - 0.0) < 0.01, f"Q(1.00T)={mid:.3f}"
    assert abs(down - 0.02) < 0.01, f"Q(1.02T)={down:.3f}"


def test_charge_transfer_matches_sawtooth_around_2T():
    up, mid, down = frozen_around(2.0, 0.02)
    assert abs(up - 0.98) < 0.01, f"Q(1.98T)={up:.3f}"
    assert abs(mid - 0.0) < 0.01, f"Q(2.00T)={mid:.3f}"
    assert abs(down - 0.02) < 0.01, f"Q(2.02T)={down:.3f}"


def test_no_dc_bias_at_exact_lock():
    """At D = kT the net charge per period must vanish, not sit at a DC offset."""
    for k in (1, 2, 3):
        assert abs(q_at(float(k))) < 0.01, f"DC bias at {k}T: {q_at(float(k))}"


def test_correction_direction_does_not_reverse_across_T():
    """Frozen transfer is a sawtooth: magnitude wraps, sign never reverses."""
    for r in np.arange(0.05, 3.01, 0.05):
        assert q_at(float(r)) >= -1e-9, f"negative charge at D/T={r:.2f}"


def test_delay_crossing_clock_boundary_is_modelled():
    """D=1.35T: two reference edges occur before the first feedback edge.

    The scheduler must still emit both reference edges and pair the feedback
    edge with the correct reference edge.
    """
    r = v2.simulate_pfd(F, band=1, cycles=4, icp=ICP, c_loop=C,
                        fixed_delay=1.35 * T, freeze_delay=True,
                        up_direction=+1, record_trace=True)
    tr = r["trace"]
    ups = [t / T for t, k in tr if k == "UP"]
    dns = [t / T for t, k in tr if k == "DOWN"]
    rst = [t / T for t, k in tr if k == "RESET"]
    assert any(1.0 < t < 1.4 for t in dns), f"fb after 1T missing: {dns}"
    assert abs(ups[1] - 2.0) < 1e-9, f"second ref edge missing: {ups}"
    assert abs(dns[1] - 2.35) < 1e-3, f"second fb edge wrong: {dns}"
    assert all(rst[i + 1] - rst[i] > 0.99 for i in range(len(rst) - 1)), rst


def test_dynamic_delay_changes_produce_down_pulses():
    """A decreasing delay puts several feedback edges in flight; an older,
    slower edge can arrive before the next reference edge and assert DOWN.
    This is the mechanism that makes kT attracting from BOTH sides.
    """
    d0 = 1.05 * T
    u0 = v3.u_for_delay(d0, 1)
    r = v2.simulate_pfd(F, band=1, u0=u0, cycles=20, icp=ICP, c_loop=C,
                        up_direction=+1)
    q = r["q_per_period_hist"] / (ICP * T)
    assert np.any(q[2:12] < 0), f"DOWN charge never appeared: {q[:15]}"


def test_correct_polarity_locks_1T_from_above():
    for start in (1.05, 1.2, 1.5, 1.8, 1.9):
        r = v3.simulate_event(F, band=1, coarse_preset=start, cycles=3000)
        assert r["locked_1T"], (
            f"start {start}T ended at {r['final_ratio']:.3f}T"
        )


def test_wrong_polarity_rails_max():
    """This is what the v1 experiments actually used."""
    import pfd_event_model as v1
    r = v1.simulate_event_pfd(F, band=1, u0=0.5, cycles=3000,
                              icp=ICP, c_loop=C, up_direction=-1)
    assert r["final_u"] < 1e-9 and r["final_ratio"] > 2.5, (
        f"expected rail, got u={r['final_u']}, D={r['final_ratio']:.3f}T"
    )


def test_start_above_2T_locks_at_2T_not_1T():
    r = v3.simulate_event(F, band=1, coarse_preset=2.5, cycles=3000)
    assert abs(r["final_ratio"] - 2.0) < 0.02 and not r["locked_1T"], (
        f"expected 2T harmonic, got {r['final_ratio']:.3f}T"
    )


def test_min_delay_startup_does_not_lock_1T():
    r = v3.simulate_event(F, band=1, u0=1.0, cycles=3000)
    assert not r["locked_1T"], (
        f"min-delay startup unexpectedly locked: {r['final_ratio']:.3f}T"
    )


def test_coarse_preset_1p2T_locks_all_required_frequencies():
    for fmhz in (25, 30, 42.5, 50, 60, 85, 100, 120, 150, 180, 200):
        f = fmhz * 1e6
        r = v3.simulate_event(f, band=v3.band_for_freq(f), coarse_preset=1.2,
                              cycles=3000)
        assert r["locked_1T"], (
            f"{fmhz} MHz: final {r['final_ratio']:.3f}T, harmonic "
            f"{r['harmonic_index']}"
        )


def test_dynamic_engine_agrees_at_safe_preset():
    for start, band in ((1.2, 1), (1.5, 1), (1.2, 0), (1.2, 2)):
        e = v3.simulate_event(F, band=band, coarse_preset=start, cycles=2500)
        d = v3.simulate_dynamic(F, band=band, start_ratio=start,
                                cycles=1200, substeps=100)
        assert abs(e["final_ratio"] - d["final_ratio"]) < 0.05, (
            f"band {band}, start {start}T: event {e['final_ratio']:.3f}, "
            f"dynamic {d['final_ratio']:.3f}"
        )


# ---------------------------------------------------------------------------
def main():
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    failures = 0
    print(f"Running {len(tests)} review tests\n")
    for fn in tests:
        try:
            fn()
            print(f"  PASS  {fn.__name__}")
        except AssertionError as exc:
            failures += 1
            print(f"  FAIL  {fn.__name__}\n        {exc}")
        except Exception as exc:  # noqa: BLE001
            failures += 1
            print(f"  ERROR {fn.__name__}\n        {type(exc).__name__}: {exc}")
    print(f"\n{len(tests) - failures}/{len(tests)} passed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
