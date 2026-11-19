#!/usr/bin/env python3
"""
supply_sim.py - ride-through of the pulse-to-tone converter supply during pulse
dialing, comparing three MCU-supply topologies. The ONLY hard requirement during
a pulse gap is VDD > BOD (keep the MCU alive); the ATtiny tolerates a wide rail.

  ORIGINAL : reservoir on VCC (shunt ~4.66V), series Schottky D5 -> VDD=Vcap-0.4
  LDO      : reservoir on an LDO INPUT (clamp 6.5V) -> LDO 3.3V -> VDD
  DIRECT   : reservoir DIRECTLY on VDD (shunt clamp ~5.0V, MCU-safe) -> VDD=Vcap
             (the correct topology: nothing lossy between the drooping cap and
              the MCU; the full charge from Vclamp down to BOD is usable)

Key point this quantifies: ANY series element (LDO dropout, or the original's
series diode) subtracts from the usable droop budget and trips BOD sooner. A
series regulator only "wins" if it lets the reservoir charge ABOVE the MCU's safe
max (needs a strong line) - which is not the low-voltage VoIP case we care about.

Outputs: supply_sim.png and a printed summary.
"""
import numpy as np
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt

VF_SCHOTTKY = 0.30
V_BRIDGE    = 2*VF_SCHOTTKY
BOD         = 2.70
LDO_DROPOUT = 0.20          # at our mA-level currents

# load currents (passive RC filter in both new designs -> the MCP6022's ~2mA is gone;
# during pulse DIALING the MCU idle-sleeps between 1ms timer wakes)
I_DIAL_ORIG = 2.2e-3        # original still has the op-amp powered during dialing
I_DIAL_NEW  = 1.0e-3        # passive filter + idle-sleep

designs = {
 "Original (shunt 4.66V + series D5, op-amp on)":
    dict(color="r", vfull=4.66, series=0.40, ldo=None, iload=I_DIAL_ORIG, C=470e-6, clampmax=4.66),
 "LDO after cap (clamp 6.5V -> LDO 3.3V)":
    dict(color="orange", vfull=6.5, series=0.0, ldo=3.30, iload=I_DIAL_NEW, C=680e-6, clampmax=6.5),
 "DIRECT drive (clamp 5.0V, cap on VDD)":
    dict(color="g", vfull=5.0, series=0.0, ldo=None, iload=I_DIAL_NEW, C=680e-6, clampmax=5.0),
}

def vdd_of(d, vcap):
    if d["ldo"] is not None:
        return min(d["ldo"], vcap - LDO_DROPOUT)
    return vcap - d["series"]

def bod_trip_vcap(d):
    """cap voltage at which VDD hits BOD (series/dropout pushes this UP)."""
    if d["ldo"] is not None:
        return BOD + LDO_DROPOUT        # 2.90
    return BOD + d["series"]            # direct: 2.70 ; original: 3.10

# ---- transient at a WEAK line (cap charges only to Vavail; weak recharge) ----
def transient(d, vavail, recharge_I, pps=10, npulses=12, open_frac=0.70, dt=1e-4):
    C = d["C"]; vfull = min(d["vfull"], vavail)
    T, t_open = 1.0/pps, open_frac/pps
    vcap = vfull; ts=[]; vs=[]; t=0.0
    for _ in range(npulses):
        tend=t+t_open
        while t<tend:
            vcap -= (d["iload"]/C)*dt; ts.append(t); vs.append(vdd_of(d,vcap)); t+=dt
        tend=t+(T-t_open)
        while t<tend:
            vcap=min(vfull, vcap+((recharge_I-d["iload"])/C)*dt); ts.append(t); vs.append(vdd_of(d,vcap)); t+=dt
    return np.array(ts), np.array(vs)

fig, ax = plt.subplots(1, 3, figsize=(16,5))

# Panel 1: ride-through budget vs reservoir charge voltage (the crossover)
vc = np.linspace(3.0, 6.8, 300)
for name,d in designs.items():
    trip = bod_trip_vcap(d)
    budget = np.clip(vc - trip, 0, None)
    budget = np.where(vc <= d["clampmax"]+1e-9, budget, np.nan)   # can't charge above clamp
    ax[0].plot(vc, budget, color=d["color"], lw=2.2, label=name.split(" (")[0])
ax[0].axvspan(3.4, 4.6, color='gray', alpha=0.12)
ax[0].text(3.45, 0.15, "weak VoIP line\n(cap can't charge high)", fontsize=8, color='dimgray')
ax[0].axvline(5.5, color='b', ls=':', lw=1); ax[0].text(5.55, 2.6, "MCU 5.5V\nabs max", fontsize=8, color='b')
ax[0].set_title("1) Usable droop budget vs reservoir charge voltage\n(higher = more pulse ride-through before BOD)")
ax[0].set_xlabel("voltage the reservoir can charge to (V)"); ax[0].set_ylabel("VDD droop budget before BOD (V)")
ax[0].grid(alpha=.3); ax[0].legend(fontsize=8, loc="upper left")

# Panel 2: VDD vs voltage across the converter (low line voltage)
vdev = np.linspace(2.8, 11, 300)
for name,d in designs.items():
    avail = vdev - V_BRIDGE
    if d["ldo"] is not None:
        rail = np.minimum(d["ldo"], np.clip(avail - LDO_DROPOUT, 0, None))
    else:
        rail = np.minimum(d["clampmax"], np.clip(avail - d["series"], 0, None))
    ax[1].plot(vdev, rail, color=d["color"], lw=2.2, label=name.split(" (")[0])
ax[1].axhline(BOD, color='k', ls='--', lw=1); ax[1].text(8.5, BOD+0.05, "BOD 2.7V", fontsize=9)
ax[1].axvline(10.0, color='b', ls=':', lw=1); ax[1].text(9.0, 0.3, "VoIP off-hook ~10V", fontsize=8, color='b')
ax[1].set_title("2) MCU rail vs voltage across the converter")
ax[1].set_xlabel("terminal voltage across converter (V)"); ax[1].set_ylabel("VDD (V)")
ax[1].set_ylim(0,5.5); ax[1].grid(alpha=.3); ax[1].legend(fontsize=8, loc="lower right")

# Panel 3: transient, weak corner (cap charges to 4.3V, weak 2.5mA recharge)
VAVAIL, RECHG = 4.3, 2.5e-3
for name,d in designs.items():
    t,v = transient(d, VAVAIL, RECHG)
    ax[2].plot(t*1e3, v, color=d["color"], lw=2, label=f"{name.split(' (')[0]} (min {v.min():.2f}V)")
ax[2].axhline(BOD, color='k', ls='--', lw=1); ax[2].text(850, BOD+0.03, "BOD 2.7V", fontsize=9)
ax[2].set_title("3) Pulse-dial ride-through, WEAK line\n(reservoir charges to 4.3V, ~2.5mA recharge)")
ax[2].set_xlabel("time (ms)"); ax[2].set_ylabel("VDD (V)")
ax[2].set_ylim(2.3,4.6); ax[2].grid(alpha=.3); ax[2].legend(fontsize=8, loc="lower left")

fig.suptitle("A series regulator in the MCU power path subtracts from the droop budget — direct drive keeps BOD from tripping", fontsize=12)
fig.tight_layout(rect=[0,0,1,0.94])
fig.savefig(__import__("os").path.join(__import__("os").path.dirname(__import__("os").path.abspath(__file__)), "supply_sim.png"), dpi=110)

print("=== BOD-trip cap voltage (lower is better; series/dropout raises it) ===")
for name,d in designs.items():
    print(f"  {name:48s} trips BOD when Vcap = {bod_trip_vcap(d):.2f} V "
          f"| budget at Vcap={d['clampmax']:.1f}: {d['clampmax']-bod_trip_vcap(d):+.2f} V")
print("\n=== weak-line transient (charge 4.3V, recharge 2.5mA) minimum VDD ===")
for name,d in designs.items():
    _,v = transient(d, VAVAIL, RECHG)
    print(f"  {name:48s} min VDD {v.min():.2f} V  (margin {v.min()-BOD:+.2f} V)")
print("\nwrote supply_sim.png")
