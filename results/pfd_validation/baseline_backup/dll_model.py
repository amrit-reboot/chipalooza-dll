"""
Level B behavioral model of an 8-phase Delay-Locked Loop (DLL).

MODELING LEVEL
--------------
This module is LEVEL B (behavioral). It contains NO transistors, NO Sky130 models
and NO parasitic extraction. It is a cycle-by-cycle numerical model of the control
loop plus an algebraic delay-cell characteristic. Every number it produces must be
labelled behavioral in the report; none of it is transistor-level evidence.

WHAT IS MODELLED
----------------
1. Current-starved delay line: 8 identical stages, total delay = 8 * t_stage(u),
   where u = VCTRL / VDD is the normalised control voltage.
2. Delay-cell characteristic: hyperbolic in u.

       t_stage(u) = t_hi / (1 + r*u),      r = t_hi/t_lo - 1

   t_lo is the minimum stage delay (u = 1, maximum control voltage) and
   t_hi is the maximum stage delay (u = 0, control voltage at the positive rail
   where the starving devices are off).
   The hyperbolic form is chosen because current-starved delay is approximately
   inversely proportional to the starving current, and the current of a MOS in
   strong inversion is approximately quadratic in overdrive. It has a non-zero
   slope everywhere, so Kd never collapses to zero at the end of the range.

3. PFD: edge-triggered phase-frequency detector. The correction pulse magnitude
   saturates at T/2 while its SIGN is preserved for large errors, representing
   the PFD's frequency-detection behaviour. An alternative wrapping "xor"
   detector mode is provided for comparison only: a wrapping detector drives the
   loop the wrong way whenever the initial delay error exceeds T/2, which is a
   genuine acquisition limit for mixer-style phase detectors but not for a PFD.
4. Charge pump + loop capacitor: voltage ramp during the UP/DOWN pulse.

       t_stage decreases as u increases, therefore:
       error > 0  (feedback edge late  -> delay too long)  -> charge UP   (u up)
       error < 0  (feedback edge early -> delay too short) -> discharge DOWN (u down)

       du = (Icp / (C * VDD)) * pulse_width

5. Dead zone: corrections smaller than `dead_zone` are ignored, which produces a
   non-zero static phase error exactly as a real PFD/CP does.
6. Startup: the loop is initialised at minimum delay (u = u0 = 1.0), the standard
   "force minimum delay" startup. Whether that is sufficient to avoid false lock
   is tested explicitly in the startup experiments, not assumed.

ASSUMPTIONS (all must be stated in any report that quotes these results)
------------------------------------------------------------------------
A1. All 8 stages are identical until mismatch is explicitly injected.
A2. Each stage contributes an even number of inversions, so a rising input edge
    produces a rising edge at every tap. This is what makes the duty-cycle
    corrector immune to the input duty cycle.
A3. The delay characteristic is hyperbolic with the band endpoints given in
    BANDS; these endpoints are PROPOSED planning values, not measured silicon.
A4. The loop is ideal apart from dead zone and optional CP mismatch: no charge
    injection, no leakage, no supply noise inside the loop model itself.
A5. jitter_estimate() is an analytical/statistical ESTIMATE driven by an assumed
    supply sensitivity, not a noise simulation.
"""

from __future__ import annotations

import numpy as np

# ----------------------------------------------------------------------------
# Baseline constants (from AGENTS.md baseline specification)
# ----------------------------------------------------------------------------
VDD_NOM = 1.8

# Per-band delay-cell planning ranges.
#   t_lo = minimum stage delay, reached at u = 1 (max control voltage)
#   t_hi = maximum stage delay, reached at u = 0 (control voltage at rail)
# Ranges include roughly 1.5-2x margin around the required T/8 of each band.
BANDS = {
    0: {"f_lo": 25e6, "f_hi": 60e6, "t_lo": 1.70e-9, "t_hi": 7.00e-9},
    1: {"f_lo": 50e6, "f_hi": 120e6, "t_lo": 0.85e-9, "t_hi": 3.50e-9},
    2: {"f_lo": 100e6, "f_hi": 200e6, "t_lo": 0.50e-9, "t_hi": 1.75e-9},
}

N_STAGES = 8


# ----------------------------------------------------------------------------
# Delay cell
# ----------------------------------------------------------------------------
def stage_delay(u, band: int) -> float:
    """Stage propagation delay [s] at normalised control u in [0, 1]."""
    u = min(max(float(u), 0.0), 1.0)
    b = BANDS[band]
    r = b["t_hi"] / b["t_lo"] - 1.0
    return b["t_hi"] / (1.0 + r * u)


def stage_kd(u, band: int) -> float:
    """Delay sensitivity dt_stage/du [s per unit u]. Always negative."""
    u = min(max(float(u), 0.0), 1.0)
    b = BANDS[band]
    r = b["t_hi"] / b["t_lo"] - 1.0
    return -b["t_hi"] * r / (1.0 + r * u) ** 2


def line_delay(u, band: int) -> float:
    """Total delay of the 8-stage line [s]."""
    return N_STAGES * stage_delay(u, band)


def line_kd(u, band: int) -> float:
    """Total delay sensitivity dT_line/du [s per unit u]."""
    return N_STAGES * stage_kd(u, band)


def u_for_delay(t_total: float, band: int) -> float:
    """Inverse of line_delay(): control value that produces t_total."""
    b = BANDS[band]
    r = b["t_hi"] / b["t_lo"] - 1.0
    t_stage = t_total / N_STAGES
    if t_stage >= b["t_hi"]:
        return 0.0
    if t_stage <= b["t_lo"]:
        return 1.0
    return (b["t_hi"] / t_stage - 1.0) / r


def band_for_freq(f: float) -> int:
    """Functional band selection following the specified band edges."""
    if f <= BANDS[0]["f_hi"]:
        return 0
    if f <= BANDS[1]["f_hi"]:
        return 1
    return 2


def delay_range(band: int):
    """(min, max) total line delay [s] for a band."""
    b = BANDS[band]
    return N_STAGES * b["t_lo"], N_STAGES * b["t_hi"]


# ----------------------------------------------------------------------------
# Closed-loop DLL simulation
# ----------------------------------------------------------------------------
def simulate_lock(
    f: float,
    band: int | None = None,
    cycles: int = 1200,
    u0: float = 1.0,
    icp: float = 300e-6,
    c_loop: float = 25e-12,
    vdd: float = VDD_NOM,
    dead_zone: float = 2e-12,
    cp_mismatch: float = 0.0,
    mismatch_eps: np.ndarray | None = None,
    lock_tol_frac: float = 0.02,
    lock_hold_cycles: int = 5,
    detector: str = "pfd",
) -> dict:
    """Run one closed-loop lock transient.

    Returns a dict with histories and lock metrics. Note that `locked` means the
    phase error is inside tolerance AND the line delay settled at 1xT, i.e. a
    true first-harmonic lock. A harmonic lock is reported separately.

    `detector` selects the phase-detector behaviour, which materially changes
    acquisition:

    "pfd" (default) — edge-triggered PFD as specified in the architecture. The
        correction pulse saturates at T/2 and the SIGN of the error is preserved
        for large errors. This is the PFD's frequency-detection behaviour: if the
        feedback edge is a long way early the loop keeps slowing the line down.
    "xor" — mixer/XOR-style phase detector. The error wraps modulo T into
        [-T/2, +T/2]. Provided only for comparison, because a wrapping detector
        drives the loop the WRONG WAY when the initial delay error exceeds T/2.
    """
    if detector not in ("pfd", "xor"):
        raise ValueError("detector must be 'pfd' or 'xor'")
    if band is None:
        band = band_for_freq(f)

    T = 1.0 / f
    u = float(u0)
    eps = np.zeros(N_STAGES) if mismatch_eps is None else np.asarray(mismatch_eps, float)

    u_hist = np.empty(cycles)
    err_hist = np.empty(cycles)
    delay_hist = np.empty(cycles)

    inside = 0
    lock_cycle = None

    for n in range(cycles):
        t_line = float(np.sum(_stage_vec(u, band) * (1.0 + eps)))
        # Raw timing error of the feedback edge versus the reference edge.
        err_raw = t_line - T
        if detector == "pfd":
            # Saturating PFD: magnitude capped at T/2, sign preserved.
            err = float(np.clip(err_raw, -T / 2.0, T / 2.0))
        else:
            # Wrapping XOR/mixer detector: error folded modulo T.
            err = _wrap_to_pm_half(err_raw, T)

        u_hist[n] = u
        err_hist[n] = err
        delay_hist[n] = t_line

        if abs(err) > lock_tol_frac * T:
            inside = 0
        else:
            inside += 1
            if inside >= lock_hold_cycles and lock_cycle is None:
                lock_cycle = n + 1

        # Charge pump correction for this cycle.
        if abs(err) > dead_zone:
            icp_eff = icp * (1.0 + 0.5 * cp_mismatch) if err > 0 else icp * (1.0 - 0.5 * cp_mismatch)
            du = (icp_eff / (c_loop * vdd)) * abs(err) * np.sign(err)
            u = min(max(u + du, 0.0), 1.0)

    t_final = delay_hist[-1]
    harmonic = int(round(t_final / T))
    settled_err = float(err_hist[-1])

    return {
        "f": f,
        "band": band,
        "T": T,
        "u_hist": u_hist,
        "err_hist": err_hist,
        "delay_hist": delay_hist,
        "lock_cycle": lock_cycle,
        "locked": bool(lock_cycle is not None and harmonic == 1),
        "harmonic_index": harmonic,
        "u_final": float(u_hist[-1]),
        "t_final": float(t_final),
        "static_err_ps": settled_err * 1e12,
        "static_err_frac_T": settled_err / T,
        "delay_over_T": t_final / T,
    }


def _stage_vec(u: float, band: int) -> np.ndarray:
    return np.full(N_STAGES, stage_delay(u, band))


def _wrap_to_pm_half(x: float, period: float) -> float:
    return (x + period / 2.0) % period - period / 2.0


# ----------------------------------------------------------------------------
# Phase spacing / tap DNL
# ----------------------------------------------------------------------------
def tap_delays(u: float, band: int, mismatch_eps=None) -> np.ndarray:
    """Arrival time of PHASE[0..7] relative to the input rising edge."""
    eps = np.zeros(N_STAGES) if mismatch_eps is None else np.asarray(mismatch_eps, float)
    stages = _stage_vec(u, band) * (1.0 + eps)
    return np.cumsum(stages)


def tap_dnl(u: float, band: int, mismatch_eps=None) -> dict:
    """DNL/INL of the 8 phase taps normalised to T/8 of the locked period."""
    delays = tap_delays(u, band, mismatch_eps)
    T = N_STAGES * np.mean(_stage_vec(u, band) * (1.0 + (np.zeros(N_STAGES) if mismatch_eps is None else np.asarray(mismatch_eps))))
    ideal = T / N_STAGES
    spacing = np.diff(np.concatenate(([0.0], delays)))
    dnl = (spacing - ideal) / ideal
    inl = (delays - ideal * np.arange(1, N_STAGES + 1)) / ideal
    return {
        "T": T,
        "ideal_step": ideal,
        "taps": delays,
        "spacing": spacing,
        "dnl": dnl,
        "inl": inl,
        "dnl_rms": float(np.sqrt(np.mean(dnl ** 2))),
        "dnl_max": float(np.max(np.abs(dnl))),
        "inl_max": float(np.max(np.abs(inl))),
    }


# ----------------------------------------------------------------------------
# Duty-cycle correction
# ----------------------------------------------------------------------------
def duty_corrector(input_duty: float, u: float, band: int, mismatch_eps=None) -> dict:
    """CLK50 generated as a set/reset latch: set on PHASE0 rise, reset on PHASE4 rise.

    Because every tap is a delayed rising edge, the PHASE0->PHASE4 span is four
    stage delays regardless of the input duty cycle. The input duty distortion is
    therefore removed, leaving only tap-spacing mismatch as the error source.
    """
    delays = tap_delays(u, band, mismatch_eps)
    T = N_STAGES * float(np.mean(_stage_vec(u, band) * (1.0 + (np.zeros(N_STAGES) if mismatch_eps is None else np.asarray(mismatch_eps)))))
    span = delays[3]  # PHASE0 rise -> PHASE4 rise (4 stages)
    duty_corrected = span / T
    return {
        "input_duty": input_duty,
        "uncorrected_duty": input_duty,
        "corrected_duty": duty_corrected,
        "span_ps": span * 1e12,
        "T_ps": T * 1e12,
    }


# ----------------------------------------------------------------------------
# Jitter estimate (analytical / statistical, Level A-B)
# ----------------------------------------------------------------------------
def jitter_estimate(
    f: float,
    supply_noise_vrms: float,
    sensitivity_per_frac: float = 1.2,
    n_cycles: int = 20000,
    seed: int = 1,
) -> dict:
    """Estimate output period jitter caused by supply noise above the loop bandwidth.

    The DLL loop only corrects errors slower than roughly 1/(lock time constant).
    Supply noise at 100 MHz is far above that bandwidth, so it is NOT suppressed:
    the total line delay modulates directly with the supply.

        dT/T = S * dVDD/VDD          S = assumed relative supply sensitivity

    With independent noise samples per clock period the period-to-period jitter
    (first difference of the arrival time) is sqrt(2) * (dT_rms).

    This is an ESTIMATE. S is an assumption, not a simulated transistor result.
    """
    rng = np.random.default_rng(seed)
    T = 1.0 / f
    dT_rms = sensitivity_per_frac * (supply_noise_vrms / VDD_NOM) * T
    noise = rng.normal(0.0, dT_rms, n_cycles)
    periods = T + noise[1:] - noise[:-1]
    pj = periods - np.mean(periods)
    return {
        "f": f,
        "T_ps": T * 1e12,
        "sensitivity_assumed": sensitivity_per_frac,
        "supply_noise_mvrms": supply_noise_vrms * 1e3,
        "dT_rms_ps": dT_rms * 1e12,
        "period_jitter_rms_ps": float(np.std(pj) * 1e12),
        "break_even_sensitivity_25ps": 25e-12 / ((supply_noise_vrms / VDD_NOM) * T * np.sqrt(2.0)),
        "break_even_sensitivity_60ps": 60e-12 / ((supply_noise_vrms / VDD_NOM) * T * np.sqrt(2.0)),
    }
