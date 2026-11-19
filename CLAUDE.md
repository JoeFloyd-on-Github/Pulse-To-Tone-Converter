# CLAUDE.md — Pulse-to-Tone Converter

**Before doing anything in this repo, read [`PROJECT_CONTEXT.md`](PROJECT_CONTEXT.md).**
It holds the goals, history, key decisions, concerns and open items from earlier
sessions — the things that are not obvious from the code or the git log.

## Quick orientation

- An ATtiny85 board (BRD170127 rev R2) that sits inside a rotary phone and turns
  pulse dialing into DTMF. Derived from LieBtrau's (Christoph Tack) Hackaday
  project 28557 / github.com/LieBtrau/pulse-dtmf-converter.
- `ANALYSIS.md` — engineering review of the original (power, regulator, firmware).
- `hardware_v2/` — the low-loop-current supply/DTMF redesign (V3 without the coin
  cell). Documentation only; it is built on the V3 PCB with the cell parts unfitted.
- `hardware_v3/` — V2 plus a CR1632 coin-cell backup (the current design).
  `hardware_v3/spice/` is the ngspice comparison; `hardware_v3/kicad/` is the routed
  KiCad 9 board, generated from `design.py`. Edit `design.py` and rerun the
  generators rather than editing `.kicad_pcb`/`.kicad_sch` by hand (see its README).
- `firmware/` — upstream source verbatim (GPL v3) plus our `battery_control.ino`.

## Working conventions

- **Licensing matters here.** `firmware/` is GPL v3 (© 2018 Christoph Tack); keep
  upstream files verbatim apart from minimal, clearly described changes, and keep
  the credit in README/ANALYSIS. ATTinyCore and Bounce2 keep their own licenses.
- V2 is a design + simulation only; V3 is routed and DRC-clean but **not built or
  bench-tested**. Don't describe either as proven hardware.
- `hardware_v3/spice` (ngspice) is the reference simulation. The older Python model
  in `hardware_v3/sim/` predates it; `hardware_v2/sim/` was removed.
- Commit or push only when asked. `main` tracks `origin/main` on GitHub
  (`JoeFloyd-on-Github/Pulse-To-Tone-Converter`, first pushed 2026-11-18).
