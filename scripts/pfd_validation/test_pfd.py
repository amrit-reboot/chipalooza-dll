"""
Automated tests for the event-driven PFD (scripts/pfd_validation/pfd_event_model.py).

Runs without pytest:  python scripts/pfd_validation/test_pfd.py

Each test states the physical property it protects. A failure means the detector
model no longer represents edge-triggered PFD behaviour.
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pfd_event_model as ev  # noqa: E402

T = 1e-8
F = 100e6


def pulses(delay, cycles=8):
    """Return [(up_width, down_width)] per completed comparison, in seconds."""
    tr = ev.measure_pulses(delay, F, band=1, cycles=cycles)
    up_t = dn_t = None
    out = []
    for t, kind, val in tr:
        if kind == "UP" and val:
            up_t = t
        elif kind == "DOWN" and val:
            dn_t = t
        elif kind == "RESET":
            out.append(((t - up_t) if up_t is not None else 0.0,
                        (t - dn_t) if dn_t is not None else 0.0))
            up_t = dn_t = None
    return out


def steady(delay, cycles=12):
    p = pulses(delay, cycles=cycles)
    assert p, "detector produced no comparisons"
    tail = p[-3:]
    return (sum(x[0] for x in tail) / len(tail),
            sum(x[1] for x in tail) / len(tail))


# ---------------------------------------------------------------------------
def test_reference_leads_feedback_asserts_up():
    """fb arrives after ref -> reference leads -> UP must be the asserted output."""
    up, down = steady(0.25 * T)
    assert up > 0.20 * T, f"UP too short for a 0.25T delay: {up/T:.3f}T"
    assert down < 0.01 * T, f"DOWN should be ~0, got {down/T:.3f}T"


def test_up_pulse_width_tracks_phase_error():
    """With D < T the UP width must equal the delay (proportional response)."""
    for frac in (0.05, 0.2, 0.5, 0.9):
        up, _ = steady(frac * T)
        assert abs(up / T - frac) < 0.01, (
            f"UP width {up/T:.4f}T does not match delay {frac}T"
        )


def test_feedback_leading_reference_asserts_down():
    """When the feedback edge arrives before the reference, DOWN must dominate."""
    # A negative delay is unphysical for a delay line, but the detector must still
    # behave correctly: present fb one quarter period EARLY.
    tr = ev.simulate_event_pfd(
        F, band=1, cycles=8, freeze_control=True, record_transitions=True,
        fixed_delay=-0.25 * T,
    )["transitions"]
    up_t = dn_t = None
    ups, downs = [], []
    for t, kind, val in tr:
        if kind == "UP" and val:
            up_t = t
        elif kind == "DOWN" and val:
            dn_t = t
        elif kind == "RESET":
            ups.append((t - up_t) if up_t is not None else 0.0)
            downs.append((t - dn_t) if dn_t is not None else 0.0)
            up_t = dn_t = None
    assert downs, "no comparisons produced"
    assert max(downs) > 0.1 * T, f"DOWN never asserted substantially: {downs}"
    assert min(ups) < 0.05 * T, f"UP should be ~0 when fb leads: {ups}"


def test_exact_alignment_produces_no_net_charge():
    """At D = kT the two edges coincide; neither output may dominate."""
    up, down = steady(1.0 * T, cycles=10)
    assert up < 0.02 * T and down < 0.02 * T, (
        f"residual pulse at alignment: up={up/T:.4f}T down={down/T:.4f}T"
    )


def test_harmonic_ambiguity_is_present():
    """The detector must NOT distinguish 1T from 2T. Identical edges -> identical output."""
    for k in (1.0, 2.0, 3.0):
        up, down = steady(k * T, cycles=14)
        assert up < 0.05 * T and down < 0.05 * T, (
            f"D={k}T should look like alignment, got up={up/T:.4f}T"
        )


def test_up_width_is_fractional_part_above_one_period():
    """For D > T the steady-state UP width equals frac(D/T), evidencing the ambiguity."""
    for frac, total in ((1.01, "1.01"), (1.10, "1.10"), (1.50, "1.50")):
        up, _ = steady(frac * T, cycles=16)
        expect = frac - int(frac)
        assert abs(up / T - expect) < 0.02, (
            f"D={total}T gave UP={up/T:.4f}T, expected {expect:.4f}T"
        )


def test_control_polarity_is_negative_feedback():
    """UP must move the delay toward the target, i.e. increase delay when short."""
    r = ev.simulate_event_pfd(F, band=1, u0=0.6, cycles=400, icp=300e-6,
                              c_loop=25e-12, up_direction=-1)
    assert r["final_ratio"] > 0.6, (
        "with up_direction=-1 the delay should rise, got "
        f"{r['final_ratio']:.3f}T"
    )


def test_charge_pump_dead_zone_blocks_tiny_pulses():
    """Intervals shorter than t_dead must deliver no charge."""
    small = ev.simulate_event_pfd(F, band=1, u0=0.5, cycles=300, icp=300e-6,
                                  c_loop=25e-12, up_direction=-1,
                                  fixed_delay=1e-12, t_dead=10e-12)
    assert abs(small["final_u"] - 0.5) < 1e-9, (
        f"dead zone did not block charge, u={small['final_u']}"
    )


def test_rail_saturation_is_reported():
    """A persistent one-sided drive must rail the control and be flagged."""
    r = ev.simulate_event_pfd(F, band=1, u0=1.0, cycles=4000, icp=300e-6,
                              c_loop=25e-12, up_direction=-1)
    assert r["rail_saturated"], (
        f"expected rail saturation, got u={r['final_u']:.3f} "
        f"ratio={r['final_ratio']:.3f}"
    )


# ---------------------------------------------------------------------------
def main():
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    failures = 0
    print(f"Running {len(tests)} PFD detector tests\n")
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
