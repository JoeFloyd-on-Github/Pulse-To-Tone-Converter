# Pulse-to-Tone Converter — rev V2 (LDO supply, low-loop-current)

A redesign of the power front-end of the BRD170127 pulse-to-tone converter to
work reliably on **IP/VoIP phone systems that supply low loop current and low
line voltage**, where the original shunt-only design is marginal. Same board
form factor and the same DTMF/ATtiny signal section; only the supply is reworked,
plus the firmware/analog fixes that the project's own history already proved out.

This builds directly on the development history of the upstream project
(LieBtrau / Christoph Tack,
[Hackaday 28557](https://hackaday.io/project/28557-pulse-to-tone-converter)) and
on the [engineering analysis](../ANALYSIS.md) of the as-built board. **Read those
first** — the design choices here are responses to specific pitfalls found there.

> **Status / scope of this deliverable.** This folder contains the **circuit
> design, the bill of materials, the preserved form factor, and a full supply
> simulation**. It does **not** contain a routed PCB: there is no KiCad/EasyEDA
> available in this environment to lay out and route copper, and I won't hand-
> fabricate Gerbers by hand (that would be unverifiable). See
> [§6](#6-what-is-and-isnt-here-and-how-to-finish-the-pcb).

---

## 1. Why the original struggles on IP phone systems

From the analysis and the upstream logs, the original front-end is: a BAT46WH
Schottky **bridge** → a **TLV431 shunt** that sets VCC ≈ 4.66 V directly →
a **series Schottky D5** → VDD ≈ 4.25 V → the ATtiny85 and an **MCP6022 active
filter**. The failure modes on a low-current/low-voltage FXS port:

- **A shunt that *sets the rail* needs the loop to supply more current than the
  load.** On a VoIP FXS current-limited to ~20 mA with ~6–7 mA already consumed
  (the MCP6022 alone is ~2 mA, always on), there may be nothing left to shunt, so
  VCC never reaches its clamp.
- **A series diode cannot regulate.** During each rotary pulse the loop is open
  ~70 ms of every 100 ms; the reservoir discharges and VDD tracks it straight
  down through D5. The upstream logs measured VCC sagging to **3.08 V** (active)
  / **3.57 V** (idle-sleep).
- **Startup:** the 470 µF took ~60 ms to charge; with BOD disabled the board
  "ran in bursts or not at all" on a VoIP FXS.

## 2. The key constraint: a 2-terminal loop device still needs a shunt

The converter sits **in series with the loop** (a 2-terminal device). The SLIC/ATA
sets the loop current and pushes **all of it** through the converter, but the
electronics only want a few mA. **A pure series LDO has nowhere to send the
excess current**, so an LDO alone cannot replace the shunt. The correct "LDO
approach" for a loop-powered device is **two stages**:

```
  line ─► BAT46WH bridge ─► [ SHUNT CLAMP ~6.5V ] ─► [ 680µF ] ─► [ LDO 3.3V ] ─► VDD
          (D1..D4)          absorbs excess loop        reservoir    MCP1702      ATtiny +
                            current, survives ringing  on LDO       (Iq 2µA)     passive filter
```

- **Stage 1 — shunt clamp (~6.5 V).** Still absorbs the loop current the
  electronics don't use and clamps ringing/transients, but it only has to hold a
  *loose* clamp well above the rail — not define the MCU rail precisely. Built
  from a **TL431 + small NPN/MOSFET shunt** (or a 6.2 V zener + NPN), with the
  reference **deliberately biased above its minimum operating current** so lot-
  to-lot spread no longer decides pass/fail (this fixes the "same batch, some
  work some fail" TLV431 problem from the analysis).
- **Stage 2 — low-Iq LDO to 3.3 V.** An **MCP1702-3302** (Vin ≤ 13.2 V so it
  tolerates the 6.5 V clamp and ringing, **Iq ≈ 2 µA**, dropout tens of mV at our
  mA currents) produces a clean, regulated **3.3 V**. Because the **680 µF
  reservoir sits on the LDO *input***, the LDO holds VDD flat at 3.3 V while its
  input cap droops during pulse gaps — the thing a bare diode cannot do.

### Proven fixes carried over (from the upstream history)

- **Passive RC DTMF filter instead of the MCP6022** — removes the ~2 mA
  always-on quiescent draw (Joris van Rantwijk's 2024 VoIP fix). This is the
  single biggest current saving and is what makes low-loop-current operation
  possible.
- **3.3 V rail** (vs 4.25 V) — the ATtiny85V runs to 1.8 V; 3.3 V cuts MCU
  current ~30 % and lowers the voltage the device must develop across the loop.
- **ATtiny 2.7 V BOD enabled** + **idle-sleep during dialing** (Timer0 wake) —
  the upstream-chosen startup/brown-out fix, kept.
- **680 µF reservoir on the LDO input** (Joris's value), for ride-through.

## 3. Simulation — does it hold up as loop current and line voltage fall?

`sim/supply_sim.py` (numpy/scipy, first-order device models with datasheet-ish
numbers) compares the original and proposed supplies across the three stresses
that matter. Result:

![supply simulation](sim/supply_sim.png)

| Metric | Original | **Proposed** |
|---|---|---|
| Min **loop current** to hold the MCU rail | 6.0 mA | **0.6 mA** |
| Min **terminal voltage** across the converter to hold the rail | 5.21 V | **3.88 V** |
| Pulse-dial transient **min VDD** (dial "0", 10 pulses @10 pps) | 3.37 V (sawtooth) | **3.30 V (flat)** |
| Margin over 2.7 V BOD in the transient | +0.67 V | **+0.60 V, and ripple-free** |

Reading the panels:

1. **Rail vs loop current** — the proposed LDO rail stays at 3.3 V down to
   **~0.6 mA** of loop current; the original needs **~6 mA** before its shunt can
   define the rail. This is the headline win for current-limited VoIP FXS ports.
2. **Rail vs voltage across the converter** — the proposed design regulates
   3.3 V down to **~3.9 V** across the device; the original needs **~5.3 V**. On a
   Bbox2-class VoIP port that only develops ~10 V off-hook (and shares it with the
   phone), that ~1.4 V of recovered headroom is the difference between working and
   browning out.
3. **Pulse-dial transient** — because the reservoir feeds the **LDO input**, VDD
   stays **flat at 3.3 V** through the whole dialed digit (the input cap droops
   ~0.1 V/pulse but stays far above the LDO's dropout), versus the original's
   sawtooth down toward the BOD. A flat rail is also better for DTMF tone
   amplitude/accuracy.

The simulation is behavioural, not SPICE-exact (no `ngspice` here), so treat the
numbers as the *comparison and the margins*, not lab values — but the physics
(shunt-needs-excess-current, diode-can't-regulate, LDO-rejects-input-droop) is
what drives the result and is robust to the exact device constants. Re-run with
your own measured ATtiny current / FXS numbers:

```sh
cd hardware_v2/sim && python3 supply_sim.py   # writes supply_sim.png + a summary
```

## 4. Bill of materials — changed/added parts (power front-end)

| Ref | Part | Note |
|---|---|---|
| D1–D4 | BAT46WH (SOD-123) | Schottky bridge — unchanged |
| U_shunt | TL431A + MMBT3904 (or 6.2 V zener + MMBT3904) | **new** shunt clamp ~6.5 V; bias the ref ≥ its I_min(max) |
| R_bias | ~2.2 k (clamp→ref) | guarantees TL431 bias current (removes batch sensitivity) |
| U_ldo | **MCP1702-3302 (SOT-23)** | **new** LDO, Vin≤13.2 V, Iq≈2 µA, 3.3 V out |
| C_in / C_out | 1 µF / 1 µF ceramic | LDO decoupling |
| C1 | **680 µF** electrolytic | reservoir, on the **LDO input** |
| U4 (MCP6022) | **removed** | replaced by a passive RC DTMF filter |
| R/C filter | passive RC (values from the DTMF band) | **new** low-pass + AC-couple to line |
| U1 | ATtiny85V-10SU | unchanged; **enable 2.7 V BOD**, keep external 8 MHz |

The shunt transistor dissipates up to ~`Vclamp × (I_loop,max − I_load)` ≈ 6.5 V ×
~35 mA ≈ **0.23 W** at the high end — size it (SOT-89 / SOT-23 at the edge) and
keep copper under it.

## 5. Form factor (preserved)

From the rev-R2 Gerbers (`../Gerber_BRD170127_R2.zip`):

- **Board outline: 49.0 mm × 34.0 mm**, 2-layer.
- **Three RJ11 (6P6C) jacks** on the left edge (to rotary phone / to DTMF phone /
  to FXS) — their 0.8 mm mounting-pin clusters are at roughly X≈5.3–7.8 mm,
  Y≈6–11 mm and Y≈22–27 mm; keep these footprints and positions fixed.
- Mounting/fiducial holes preserved.

The new supply parts (two SOT-23s, a few passives, the 680 µF and 1 µF caps)
replace the removed MCP6022 and the TLV431/divider cluster and fit the same
area; net passive count is similar.

## 6. What is (and isn't) here, and how to finish the PCB

**Here:** the circuit design and rationale, the BOM deltas, the preserved form
factor, and a runnable supply simulation with results.

**Not here:** a routed board / new Gerbers. Laying out and routing copper needs an
EDA tool (KiCad/EasyEDA), which isn't available in this environment, and
hand-writing Gerbers would be unverifiable.

**To finish it** (any of):
- Open the original **EasyEDA** project (the upstream board was done in EasyEDA
  v6.1.52), swap the supply section per §2/§4, and re-route the small changed
  area — the signal section and connectors stay put.
- Or recreate it in **KiCad**: I can generate a KiCad **schematic** (`.kicad_sch`)
  and a board **outline** at 49×34 mm with the RJ11 footprints placed, for you to
  route — say the word and I'll produce those files.
- Either way, **validate on hardware** against a real VoIP FXS (and a low-current
  SLIC setting) — the sim predicts the margins, the bench confirms them.
