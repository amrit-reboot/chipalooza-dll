# Feasibility of a 1.3T Coarse Preset Without Prior Knowledge of T

**Level B analytical / behavioral. Proposal only — no architecture change applied.**

---

## 1. The problem

The exact-event engine shows that 1T acquisition requires the initial line delay
to lie in the basin:

\[
1.02\,T \;\lesssim\; D_{\text{start}} \;\lesssim\; 1.95\,T
\]

Starting below this range rails to minimum delay (`k=0` basin); starting above
it locks at `2T`. The current architecture forces **minimum delay** at startup,
which is *always* outside the basin.

A "1.3T preset" therefore means: set the initial delay to ~1.3 input periods
**without knowing the input period in advance**. This is not a simple constant
voltage — it requires a period-dependent mechanism.

---

## 2. What the band plan permits

Maximum available delay relative to T (from `dll_model.py` BANDS):

| Frequency | Band | D_max / T | D_min / T | Max-delay startup lands in |
|---:|---:|---:|---:|---|
| 25 MHz | 0 | 1.40 | 0.34 | 1T basin ✓ |
| 30 MHz | 0 | 1.68 | 0.41 | 1T basin ✓ |
| 42.5 MHz | 0 | 2.38 | 0.58 | 2T basin |
| 50 MHz | 0 | 2.80 | 0.68 | 2T basin |
| 60 MHz | 0 | 3.36 | 0.82 | 3T basin |
| 85 MHz | 1 | 2.38 | 0.58 | 2T basin |
| 100 MHz | 1 | 2.80 | 0.68 | 2T basin |
| 120 MHz | 1 | 3.36 | 0.82 | 3T basin |
| 150 MHz | 2 | 2.80 | 0.60 | 2T basin |
| 200 MHz | 2 | 2.80 | 0.60 | 2T basin |

At 25–30 MHz, maximum-delay startup already lands in the 1T basin. Above
~42 MHz it does not. A universal mechanism must work across the full 25–200 MHz
range.

---

## 3. Implementable acquisition mechanisms (proposals only)

### Option A — Cycle-counting coarse acquisition (recommended candidate)

**Principle:** With the delay line near maximum, the number of reference edges
that occur between consecutive feedback edges equals \(k = \lfloor D/T \rfloor\).
A small state machine can count these edges:

1. Force maximum delay at reset.
2. Count reference edges between two consecutive feedback edges → gives `k`.
3. If `k ≥ 2`, assert a coarse DOWN current (or a faster CP setting) until `k = 1`.
4. Once `k = 1` (i.e. `T < D < 2T`), switch to the normal PFD; it locks at 1T.

**Hardware needed:** a 2–3 bit counter clocked by reference edges, reset by
feedback edges; a mode signal selecting coarse/fine CP current; a state machine.
All are standard digital/analog blocks in Sky130.

**Advantage:** The measured quantity (`k`) is *digital* and requires no analog
period-to-voltage conversion. It directly detects which basin the loop is in.

**Limitation:** Adds state and area; the `k` transition edge cases (D near 2T)
need hysteresis; coarse DOWN step size must be chosen to avoid overshooting into
`k=0`. This is Level B analysis; transistor-level verification required.

### Option B — Period-to-voltage preset

**Principle:** Charge a capacitor with a known current `I_ref` for exactly one
reference period: `V = I_ref·T/C`. Use this voltage (scaled) as the initial
VCTRL such that `D(V) ≈ 1.3T`. Since `D(V)` is approximately hyperbolic, the
scaling requires knowledge of the delay transfer function.

**Hardware needed:** a switched-current source, timing gate, sample-and-hold.

**Limitation:** Accuracy depends on `I_ref·C` PVT tracking against the delay
cell's `t_lo/t_hi` PVT. Without ratio-metric design, corners could shift the
preset out of the basin. Not demonstrated here.

### Option C — Successive-approximation / binary search

**Principle:** Set VCTRL to mid-scale, observe whether the first feedback edge
arrives before or after the second reference edge (i.e. whether `D<T` or
`D>T`), then binary-search VCTRL over a few cycles.

**Advantage:** Converges geometrically; needs only a comparator and a SAR state
machine.

**Limitation:** The PFD's frozen transfer is one-sided, so phase alone does not
give direction; the search must use *edge-count* (`k`) as the comparison signal,
making it essentially Option A with a different search algorithm.

### Option D — Accept 2T lock (specification change)

**Principle:** Loosen the lock detector to accept `D = kT` for any integer k.

**Status:** This is a **specification change** and requires explicit user
approval. It would also change the phase-output spacing (45° at 1T becomes
90° at 2T relative to input), which may be unacceptable.

---

## 4. Strongest honest statement

A 1.3T preset is **not trivially generatable** without period information.
Option A (cycle-counting coarse acquisition) is the most directly implementable
from the evidence gathered here: it uses only digital edge counting and a
coarse/fine CP mode switch, and it directly targets the measured basin
(`1T < D < 2T`). However:

- It is **not in the current architecture**.
- Its coarse-DOWN step size and `k`-transition hysteresis are **not designed**
  in this study.
- It needs transistor-level verification before any claim of silicon
  feasibility.

---

## 5. What startup architecture would be necessary

For a defensible proposal, the startup section must specify:

1. **Initial state:** maximum delay (not minimum) — verified here to land in
   `k≥1` basins at all frequencies.
2. **Basin detector:** a cycle-counting mechanism that determines `k` before
   fine acquisition begins.
3. **Coarse correction:** a controllable path to reduce delay from `k≥2` into
   `k=1` without overshooting to `k=0`.
4. **Fine acquisition:** the normal two-latch PFD with the verified polarity
   (`UP raises VCTRL → delay falls`).
5. **Lock verification:** a detector that confirms `D ≈ T` (not merely
   "edges aligned"), distinguishing 1T from 2T/3T harmonics.

None of these are applied. This section is a proposal for user review.
