# Phase 0 — Repository and Environment Audit

**Project:** Chipalooza Challenge #4 — 8-Phase DLL feasibility study
**Date of audit:** 2026-11-21
**Auditor:** OpenCode engineering team (Role 4 Verification / Role 5 Automation)
**Status:** **BLOCKED — the simulation environment is not operational.**
**Scope:** Read-only inspection. Nothing was installed, downloaded, or modified. Only new empty directories and this report were created.

---

## 1. Objective

Establish, from direct observation, whether this machine can run the open-source
Sky130 simulation flow required for the feasibility study (xschem + ngspice +
Sky130 PDK), before any circuit work begins.

Per `AGENTS.md` §7 Phase 0 and §6, circuit design must not start until this audit
is reviewed and approved.

---

## 2. Host platform

| Item | Observed value |
|---|---|
| Host OS | Windows (`win32`) |
| Repository path | `C:\Chipalooza\chipalooza-dll` |
| Git repository | **No** (`Is directory a git repo: false`) |

---

## 3. Windows-side tooling

| Tool | Result | Evidence |
|---|---|---|
| `xschem` | **MISSING** | not on `PATH`; no `C:\Program Files\xschem` |
| `ngspice` | **MISSING** | not on `PATH`; no `C:\Program Files\ngspice` |
| `python` | FOUND — **3.12.4** | local user Programs directory, path redacted |
| `python3` | Present but a 0.0.0.0-version Microsoft Store shim | not usable as an interpreter |
| `docker` | **MISSING** | not on `PATH` |
| PDK environment variables (`PDK`, `PDK_ROOT`, `SKY130*`, `IIC*`, `OSIC*`) | **NONE SET** | `Get-ChildItem Env:` filtered on those patterns returned nothing |
| PDK install locations checked | all absent | `C:\eda`, `C:\tools`, `C:\openlane`, `C:\sky130`, `<user-home>\eda`, `<user-home>\.volare`, `<user-home>\AppData\Local\ngspice` |

Windows Python packages present (relevant to Role 5 automation):

| Package | Version |
|---|---|
| numpy | 2.2.4 |
| scipy | 1.16.0 |
| matplotlib | 3.10.1 |
| plotly | 6.0.1 |
| pandas | **not installed** (would be needed for some tabulation workflows; not yet required) |

---

## 4. WSL side

A WSL2 distribution exists and was inspected.

| Item | Observed value |
|---|---|
| `wsl --list --verbose` | `* Ubuntu  Stopped  2` (default distro, WSL **version 2**) |
| Distro | Ubuntu **24.04.4 LTS** |
| Kernel/report | via `uname -a` in probe (see `logs/` when re-run) |

Tooling inside Ubuntu 24.04:

| Tool | Result |
|---|---|
| `xschem` | **MISSING** |
| `ngspice` | **MISSING** |
| `magic` | **MISSING** |
| `netgen` | **MISSING** |
| `klayout` | **MISSING** |
| `docker` | **MISSING** |
| `iverilog` | FOUND (`/usr/bin/iverilog`) — digital only, not sufficient for analog DLL work |
| `python3` | FOUND — **3.12.3**, with numpy 1.26.4 / scipy 1.11.4 / matplotlib 3.6.3 (pandas absent) |
| Free disk space on `/` | 949 GB available of 1007 GB |

apt candidates (queried with `apt-cache policy`, **nothing installed**):

| Package | Installed | Candidate |
|---|---|---|
| `ngspice` | none | `42+ds-3build1` |
| `xschem` | none | `3.4.4-1` |

---

## 5. Sky130 PDK audit

| Check | Result |
|---|---|
| `PDK` / `PDK_ROOT` environment variable | **NOT SET** (Windows and WSL) |
| `/usr/share/pdk`, `/opt/pdk`, `/usr/local/pdk`, `/usr/local/share/pdk` | absent |
| `/opt/sky130`, `/usr/share/sky130`, `/usr/local/share/sky130` | absent |
| `$HOME/pdk`, `$HOME/.volare` | absent |
| `libs.tech` directories anywhere in the Linux filesystem | **none found** |
| `*.lib` model files anywhere in the Linux filesystem | **none found** |
| Any `*sky130*` model file | **none found** |

### Conclusion on PDK

**No Sky130 PDK is installed anywhere on this machine.** Consequently the
following Phase 0 items **cannot be completed and are recorded as UNVERIFIED**:

- actual model-library file paths
- actual process-corner model section names (TT/SS/FF/SF/FS)
- available device flavours (`nfet_01v8`, `pfet_01v8`, etc.) and their parameters
- MiM capacitor availability for the loop filter
- mismatch parameter support in the Sky130 models

No corner names have been assumed or invented. They must be read from the real
model files once a PDK is present.

---

## 6. IIC-OSIC-TOOLS audit

| Check | Result |
|---|---|
| `/etc/iic-osic-tools-release` | absent |
| IIC-OSIC-TOOLS launcher script | absent |
| Docker engine available to host the container | **not installed** (neither Windows nor WSL) |

**This machine is not an IIC-OSIC-TOOLS environment.** The tool container image
is not present and there is no Docker runtime to launch it.

---

## 7. Basic Sky130 NMOS simulation

**Status: NOT SIMULATED.**

Reason: no ngspice binary and no Sky130 model files exist, so a basic NMOS
DC/operating-point testbench cannot be executed. No simulation output was
produced or inferred. Per `AGENTS.md` Rule 3, no result is reported here.

---

## 8. Feature verification (transient noise, Monte Carlo)

**Status: UNVERIFIED — cannot be tested without an installed ngspice.**

Notes recorded for the record, to be confirmed empirically after installation.
These are *expectations about the tool*, not measurements:

- Upstream `ngspice` has supported `.noise` analysis for many releases, and
  transient noise via `noise`/`trnoise`-style sources exists in modern versions.
  The Debian/Ubuntu `ngspice 42` package *should* include `.noise`; whether the
  build exposes transient-noise analysis in the packaged binary must be verified
  by `ngspice --version` feature flags and a trial deck.
- Monte Carlo in ngspice is normally driven from `.control` blocks with
  `while`/`agauss`/`sgauss` parameter perturbation loops rather than a single
  `.mc` card. Availability and behaviour must be verified on the installed build.

Both items are recorded as **UNVERIFIED**, not as available.

---

## 9. Repository state

Before any change the repository contained exactly one file:

```
AGENTS.md
```

It was **not** a git repository, and no other files existed, so no file could be
overwritten. The directory skeleton from `AGENTS.md` §8 was then created.

Created (empty directories):

```
spec/
design/{delay_cell,pfd,charge_pump,loop_filter,duty_corrector,top}/
sim/{delay_cell,pfd,charge_pump,loop_filter,full_loop,startup,duty,jitter,monte_carlo}/
scripts/
results/{plots,raw,tables}/
logs/{simulation,analysis}/
```

Created (files):

```
scripts/env_audit.sh        # read-only re-runnable environment probe
results/environment_report.md  # this report
```

Duplicated probe scripts were kept outside the repository in the session temp
directory and are not part of the project.

---

## 10. Assessment summary

| Phase 0 requirement | Result |
|---|---|
| Repository inspected | **DONE** |
| xschem version | **NOT AVAILABLE** |
| ngspice version | **NOT AVAILABLE** |
| Python available | **DONE** — 3.12.4 (Windows), 3.12.3 (WSL) |
| Sky130 PDK availability | **ABSENT** |
| IIC-OSIC-TOOLS environment | **ABSENT** |
| Model library paths | **UNVERIFIED** (no PDK) |
| Process corner names | **UNVERIFIED** (no PDK) |
| Supply/temperature sweep capability | **UNVERIFIED** (no simulator) |
| Basic NMOS simulation | **NOT SIMULATED** |
| Transient noise support | **UNVERIFIED** |
| Monte Carlo support | **UNVERIFIED** |
| Directory structure created | **DONE** |
| Environment report written | **DONE** |

### Gate decision

**The Phase 0 gate is NOT passed.** The environment cannot execute a single
transistor-level Sky130 simulation. Per `AGENTS.md` §7 Phase 0 ("Do not start
circuit design if the environment is not verified"), Phase 1 must not begin.

Only the Python automation layer (Role 5) is currently usable. That is
sufficient for purely analytical Level A work, but not for the Level C
transistor evidence the study ultimately requires.

---

## 11. Options to unblock (requires user approval — nothing done)

No installation has been performed and none will be performed without explicit
approval (`AGENTS.md` Rule 8).

| # | Option | Provides | Advantages | Disadvantages |
|---|---|---|---|---|
| A | Install **IIC-OSIC-TOOLS** Docker image, run in WSL2 | ngspice + xschem + magic + netgen + Sky130 PDK, pre-integrated, corner-aware | Matches the tool chain named in `AGENTS.md`; PDK + corner setup already correct; reproducible | Requires Docker Desktop/engine + several GB download; needs approval to install Docker |
| B | Install `ngspice`, `xschem`, and Sky130 PDK (**volare** or manual git clone) inside WSL Ubuntu 24.04 | Same core tools, native Linux | Smaller than the full image; apt already offers ngspice 42 / xschem 3.4.4; 949 GB free | Manual PDK fetching and `PDK_ROOT`/`sky130A` setup; corner names must be validated by hand; system package install needs approval |
| C | Install ngspice + Sky130 PDK on **Windows** natively | Runs without WSL | No WSL indirection | xschem builds poorly on Windows; paths and `.spiceinit` handling are fragile; least reproducible |
| D | Proceed with **Level A analytical work only** for now | Unblocks Phase 1 loop math immediately | No install; Python is ready | Cannot support any Level C claim; Phase 2 and later remain blocked |

### Team recommendation (Role 1 + Role 6)

**Option A** is the lowest-risk route to a defensible, reproducible study,
because it delivers the exact tool chain and PDK that `AGENTS.md` assumes, and
avoids hand-built corner definitions. **Option B** is acceptable if avoiding
Docker is a hard constraint. **Option D** is a legitimate parallel step: the
Phase 1 loop-gain mathematics is Level A and does not need ngspice, but its
conclusions must later be re-anchored to measured `K_d` values from Phase 2.

Per `AGENTS.md` Rule 8, installing any tool or PDK requires your explicit
approval.

---

## 12. Reproducibility

The audit can be re-run with:

```powershell
wsl -d Ubuntu -- bash <repository-root>/scripts/env_audit.sh
```

Model-file and `libs.tech` searches are scoped with `-xdev` so the probe does not
traverse the mounted Windows `C:` drive.

---

## 13. Unresolved questions for the user

1. Which unblocking option (A/B/C/D) do you approve?
2. Is Docker acceptable on this machine?
3. Is there an existing PDK installation elsewhere (external drive, network
   share, another machine) not visible to this audit?
4. Should `pandas` be added to the Python toolchain for tabulation/analysis, or
   should analysis stay on numpy + stdlib `csv`?
5. Do you want this directory initialised as a git repository (`git init`) as
   part of Phase 0 housekeeping?

---

## 14. ADDENDUM — scope adjustment and partial Option A attempt (2026-11-21, later)

The user redefined the deliverable as a **lightweight simulation prototype for a
proposal**, not a tapeout-grade transistor study, and directed that the
behavioral prototype be prioritised over toolchain setup.

### 14.1 What was attempted before the scope change

Option A (IIC-OSIC-TOOLS in Docker) was approved and partially executed:

| Step | Result |
|---|---|
| Docker Engine installed in WSL2 Ubuntu 24.04 | **DONE** — Docker 29.1.3, systemd-managed, `active`, overlayfs, `hello-world` verified |
| local user account added to `docker` group | DONE |
| WSL2 path-MTU defect diagnosed and fixed | DONE — 1500-byte frames failed, 1428 passed; `eth0` set to 1400 and persisted via `wsl-mtu.service`; Docker `daemon.json` set to `mtu 1400`, `max-concurrent-downloads 2`, `max-download-attempts 20` |
| `hpretl/iic-osic-tools:latest` pull | **NOT COMPLETED** — repeated registry/CDN `i/o timeout` on large layers; ~11 attempts over two sessions |
| Pull abandoned | **YES**, at the user's direction, to prioritise the behavioral prototype |

### 14.2 Current tool status (actual, not assumed)

| Tool | Status |
|---|---|
| Python 3.12.4 + numpy/scipy/matplotlib | **AVAILABLE and used** |
| ngspice | **STILL NOT AVAILABLE** (Windows and WSL) |
| xschem | **NOT AVAILABLE** |
| Sky130 PDK | **NOT AVAILABLE** |
| IIC-OSIC-TOOLS image | **NOT AVAILABLE** (pull failed, not retried) |
| Docker Engine | AVAILABLE in WSL2, but with no EDA image it is currently useless for this project |

### 14.3 Consequence for evidence levels

- **Level A and Level B work is unblocked** and has been carried out — see
  `results/behavioral_dll.md`.
- **Level C (transistor-level) remains entirely blocked.** Any transistor claim
  still requires ngspice plus the Sky130 PDK.
- A Docker/MITg `mtu` retry, an apt `ngspice` install, or a volare PDK fetch are
  all still possible but each needs fresh user approval per `AGENTS.md` Rule 8.

Nothing from §2–§12 above has been retro-actively changed: the audit recorded the
environment as it was before the Docker install.

