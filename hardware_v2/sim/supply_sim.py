#!/usr/bin/env python3
"""
supply_sim.py - behavioural simulation of the pulse-to-tone converter power
front-end, comparing the ORIGINAL shunt-only design (BRD170127) with the
proposed TWO-STAGE "shunt clamp + low-Iq LDO" design, as loop current and line
voltage are reduced and through the pulse-dial transient.

The converter is a 2-TERMINAL device in series with the subscriber loop. The
SLIC/ATA sets the loop current; the device develops a terminal voltage and must
power its electronics from it. A shunt element is unavoidable (it absorbs the
loop current the electronics don't use and clamps ringing); the question is what
produces the clean MCU rail. Original: a TLV431 shunt sets ~4.66 V directly and
a series Schottky drops it to VDD. Proposed: a shunt CLAMPS to ~6.5 V, and a
low-Iq LDO regulates a stable 3.3 V from it.

Models are first-order but use real datasheet-ish numbers; the goal is the
*comparison and the margins*, not SPICE-exact nodes.

Outputs: hardware_v2/sim/supply_sim.png and a printed summary.
"""
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# ---- shared constants -------------------------------------------------------
VF_SCHOTTKY = 0.30     # BAT46WH forward drop at a few mA
V_BRIDGE    = 2 * VF_SCHOTTKY   # two diodes in the rectifier path
BOD         = 2.70     # ATtiny85V brown-out threshold (enabled in both designs)

# ---- ORIGINAL design (shunt sets the rail) ----------------------------------
ORIG = dict(
    name       = "Original (TLV431 shunt @4.66V + D5, MCP6022 active filter)",
    v_rail     = 4.66,          # shunt clamp -> VCC
    v_series   = 0.40,          # series Schottky D5 drop VCC->VDD
    i_active   = 6.0e-3,        # ATtiny@4.25V ~4mA + MCP6022 ~2.1mA
    i_idle     = 2.2e-3,        # idle-sleep + op-amp still on
    C_res      = 470e-6,        # C1
)
ORIG["v_vdd_reg"] = ORIG["v_rail"] - ORIG["v_series"]   # ~4.26 V

# ---- PROPOSED design (shunt clamp -> low-Iq LDO 3.3V, passive RC filter) -----
#   LDO ~ MCP1702-3302: Vin up to 13.2V, Iq ~2uA, pass impedance a few ohms,
#   so dropout at our mA-level currents is tens of mV.
NEW = dict(
    name       = "Proposed (shunt clamp @6.5V -> MCP1702 LDO 3.3V, passive filter)",
    v_clamp    = 6.5,           # shunt clamp (absorbs excess loop current)
    v_ldo      = 3.30,          # LDO output rail
    ldo_iq     = 2e-6,          # LDO quiescent current
    ldo_rpass  = 2.6,           # effective pass resistance -> dropout = I*rpass
    ldo_do_min = 0.020,         # dropout floor
    i_active   = 4.0e-3,        # ATtiny@3.3V ~4mA (no op-amp; passive filter)
    i_idle     = 1.0e-3,        # idle-sleep, passive filter ~0
    C_res      = 680e-6,        # Joris's value
)
def ldo_dropout(i):
    return max(NEW["ldo_do_min"], i * NEW["ldo_rpass"])

# =============================================================================
# 1. VDD vs LOOP CURRENT  (ample line voltage; does the rail hold as I_loop falls?)
# =============================================================================
i_loop = np.linspace(0.3e-3, 40e-3, 400)

def vdd_vs_iloop_orig(i):
    # shunt can only clamp while the loop supplies at least the load current;
    # below that the electronics discharge the rail.
    il = ORIG["i_active"]
    out = np.where(i >= il, ORIG["v_vdd_reg"],
                   ORIG["v_rail"] * (i / il) - ORIG["v_series"])
    return np.clip(out, 0, None)

def vdd_vs_iloop_new(i):
    # LDO needs load+Iq; the rail is set by the LDO, not by the shunt current.
    il = NEW["i_active"] + NEW["ldo_iq"]
    reg = NEW["v_ldo"]
    # below il the clamp input cap can't hold 6.5V, but the LDO keeps regulating
    # until its input falls below Vout+dropout; model graceful sag only well below il.
    out = np.where(i >= 0.6e-3, reg, reg * (i / 0.6e-3))
    return out

# =============================================================================
# 2. VDD vs DEVICE TERMINAL VOLTAGE (low line voltage / phone takes the rest)
# =============================================================================
v_dev = np.linspace(3.0, 12.0, 400)   # voltage available across the converter

def vdd_vs_vdev_orig(v):
    avail = v - V_BRIDGE - ORIG["v_series"]
    return np.minimum(ORIG["v_vdd_reg"], np.clip(avail, 0, None))

def vdd_vs_vdev_new(v):
    avail = v - V_BRIDGE - ldo_dropout(NEW["i_active"])
    return np.minimum(NEW["v_ldo"], np.clip(avail, 0, None))

# =============================================================================
# 3. PULSE-DIAL TRANSIENT (dial "0" = 10 pulses, 10 pps, ~70ms open / 30ms closed)
#    During loop-open the reservoir powers the MCU; during closed it recharges.
# =============================================================================
def transient(design, i_load, recharge_I=25e-3, pps=10, npulses=10,
              open_frac=0.70, dt=1e-4):
    """Return (t, VDD). Two architectures:
       ORIGINAL: reservoir sits on VCC, VDD = Vcap - series Schottky drop, so
                 VDD tracks the cap down (a diode cannot regulate).
       PROPOSED: reservoir sits on the LDO INPUT; VDD = min(Vldo, Vcap-dropout),
                 so the LDO holds the rail flat while its input cap droops."""
    C    = design["C_res"]
    is_ldo = "v_ldo" in design
    vcap = design["v_clamp"] if is_ldo else design["v_rail"]   # cap starts charged
    T, t_open = 1.0 / pps, open_frac / pps
    ts, vs, t = [], [], 0.0
    def vdd_of(vc):
        if is_ldo:
            return min(design["v_ldo"], vc - ldo_dropout(i_load))
        return vc - design["v_series"]
    for _ in range(npulses):
        tend = t + t_open                       # loop OPEN: cap discharges
        while t < tend:
            vcap -= (i_load / C) * dt
            ts.append(t); vs.append(vdd_of(vcap)); t += dt
        tend = t + (T - t_open)                  # loop CLOSED: cap recharges
        vfull = design["v_clamp"] if is_ldo else design["v_rail"]
        while t < tend:
            vcap = min(vfull, vcap + ((recharge_I - i_load) / C) * dt)
            ts.append(t); vs.append(vdd_of(vcap)); t += dt
    return np.array(ts), np.array(vs)

# =============================================================================
# PLOT
# =============================================================================
fig, ax = plt.subplots(1, 3, figsize=(16, 5))

ax[0].plot(i_loop*1e3, vdd_vs_iloop_orig(i_loop), 'r-', lw=2, label="Original 4.26V rail")
ax[0].plot(i_loop*1e3, vdd_vs_iloop_new(i_loop),  'g-', lw=2, label="Proposed 3.3V LDO rail")
ax[0].axhline(BOD, color='k', ls='--', lw=1); ax[0].text(27, BOD+0.05, "BOD 2.7V", fontsize=9)
ax[0].set_title("1) MCU rail vs loop current\n(ample line voltage)")
ax[0].set_xlabel("loop current (mA)"); ax[0].set_ylabel("VDD (V)")
ax[0].set_ylim(0, 5); ax[0].grid(alpha=.3); ax[0].legend(fontsize=8, loc="lower right")

ax[1].plot(v_dev, vdd_vs_vdev_orig(v_dev), 'r-', lw=2, label="Original (needs ~5.3V)")
ax[1].plot(v_dev, vdd_vs_vdev_new(v_dev),  'g-', lw=2, label="Proposed (works to ~4.0V)")
ax[1].axhline(BOD, color='k', ls='--', lw=1); ax[1].text(9, BOD+0.05, "BOD 2.7V", fontsize=9)
ax[1].axvline(10.0, color='b', ls=':', lw=1); ax[1].text(10.1, 0.3, "Bbox2 VoIP\noff-hook 10V", fontsize=8, color='b')
ax[1].set_title("2) MCU rail vs voltage across the converter\n(low line voltage)")
ax[1].set_xlabel("terminal voltage across converter (V)"); ax[1].set_ylabel("VDD (V)")
ax[1].set_ylim(0, 5); ax[1].grid(alpha=.3); ax[1].legend(fontsize=8, loc="lower right")

# transient: worst case = active load; also show idle-sleep for the proposed
to, vo = transient(ORIG, ORIG["i_active"])
tn, vn = transient(NEW,  NEW["i_active"])
tni, vni = transient(NEW, NEW["i_idle"])
ax[2].plot(to*1e3, vo, 'r-', lw=2, label=f"Original, active ({ORIG['i_active']*1e3:.0f}mA/470µF)")
ax[2].plot(tn*1e3, vn, 'g-', lw=2, label=f"Proposed, active ({NEW['i_active']*1e3:.0f}mA/680µF)")
ax[2].plot(tni*1e3, vni, 'g--', lw=1.5, label=f"Proposed, idle-sleep ({NEW['i_idle']*1e3:.0f}mA/680µF)")
ax[2].axhline(BOD, color='k', ls='--', lw=1); ax[2].text(600, BOD+0.03, "BOD 2.7V", fontsize=9)
ax[2].set_title('3) Pulse-dial transient (dial "0", 10 pulses @10pps)\nreservoir ride-through')
ax[2].set_xlabel("time (ms)"); ax[2].set_ylabel("VDD (V)")
ax[2].set_ylim(2.3, 4.5); ax[2].grid(alpha=.3); ax[2].legend(fontsize=8, loc="lower right")

fig.suptitle("Pulse-to-Tone Converter supply: original shunt vs proposed shunt-clamp+LDO", fontsize=13)
fig.tight_layout(rect=[0,0,1,0.95])
fig.savefig("/home/jfloyd/GitHub/Pulse-To-Tone-Converter/hardware_v2/sim/supply_sim.png", dpi=110)

# ---- printed summary --------------------------------------------------------
def min_iloop(fn, target):
    for i in i_loop:
        if fn(np.array([i]))[0] >= target - 0.05:
            return i*1e3
    return float('nan')
def min_vdev(fn, target):
    for v in v_dev:
        if fn(np.array([v]))[0] >= target - 0.05:
            return v
    return float('nan')

print("=== SUPPLY COMPARISON SUMMARY ===")
print(f"Original rail {ORIG['v_vdd_reg']:.2f}V | Proposed rail {NEW['v_ldo']:.2f}V | BOD {BOD}V\n")
print(f"Min loop current to hold the rail:")
print(f"   original : {min_iloop(vdd_vs_iloop_orig, ORIG['v_vdd_reg']):.1f} mA")
print(f"   proposed : {min_iloop(vdd_vs_iloop_new,  NEW['v_ldo']):.1f} mA")
print(f"Min terminal voltage to hold the rail:")
print(f"   original : {min_vdev(vdd_vs_vdev_orig, ORIG['v_vdd_reg']):.2f} V")
print(f"   proposed : {min_vdev(vdd_vs_vdev_new,  NEW['v_ldo']):.2f} V")
print(f"Pulse-dial transient minimum VDD (active load):")
print(f"   original : {vo.min():.2f} V  (margin over BOD: {vo.min()-BOD:+.2f} V)")
print(f"   proposed : {vn.min():.2f} V  (margin over BOD: {vn.min()-BOD:+.2f} V)")
print(f"   proposed idle-sleep : {vni.min():.2f} V  (margin {vni.min()-BOD:+.2f} V)")
print("\nwrote hardware_v2/sim/supply_sim.png")
