# CLAUDE.md — Pulse-to-Tone Converter

**Before doing anything in this repo, read [`PROJECT_CONTEXT.md`](PROJECT_CONTEXT.md).**
It holds the goals, history, key decisions, concerns and open items from earlier
sessions — the things that are not obvious from the code or the git log.

## Quick orientation

- An ATtiny85 board (BRD170127 rev R2) that sits inside a rotary phone and turns
  pulse dialing into DTMF. Derived from LieBtrau's (Christoph Tack) Hackaday
  project 28557 / github.com/LieBtrau/pulse-dtmf-converter.
- `ANALYSIS.md` — engineering review of the original (power, regulator, firmware).
- `hardware_v2/` — direct-drive supply redesign for low-current VoIP lines.
- `hardware_v3/` — V2 plus a CR1632 coin-cell backup (the current design).
- `firmware/` — upstream source verbatim (GPL v3) plus our `battery_control.ino`.

## Working conventions

- **Licensing matters here.** `firmware/` is GPL v3 (© 2018 Christoph Tack); keep
  upstream files verbatim apart from minimal, clearly described changes, and keep
  the credit in README/ANALYSIS. ATTinyCore and Bounce2 keep their own licenses.
- The V2/V3 folders are **designs + simulations, not routed PCBs.** Don't describe
  them as fabricated or bench-tested.
- Sim scripts (`hardware_v*/sim/*.py`) regenerate the PNGs next to them; update
  both together.
- Commit or push only when asked. As of 2026-11-18 the `origin` remote points at a
  GitHub repo that does not exist yet — nothing has been pushed.
