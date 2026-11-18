#!/usr/bin/env python3
"""
battery_backup_sim.py - rev V3: CR1632 coin-cell backup that carries the ATtiny
through pulse dialing (option B). Simulates the dialing transient with and
without the cell, the cell's usable life (fresh -> end-of-life), and reports the
TEST-POINT voltages for bench verification.

Power section modelled (see ../schematic.svg):
    Vc (loop clamp ~5V) --[D_loop Schottky]--> VDD
    CR1632 (+) --[Q_batt P-FET, MCU BATT_EN]--[D_rev Schottky]--> VDD
    VDD: ATtiny + 100uF decoupling
The two paths OR into VDD: whichever source is higher supplies the MCU. The loop
wins between pulses; during the ~70ms loop-open gap the loop rail collapses and
the cell holds VDD. Q_batt gives on-hook disconnect; D_rev blocks back-charge.

On a WEAK VoIP line the loop can only charge Vc low and can't refill the small
100uF between pulses, so WITHOUT the cell VDD walks down through BOD over a digit;
WITH the cell VDD is floored at the cell voltage.
"""
import numpy as np
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt

BOD      = 2.70          # ATtiny85V 2.7V BOD (8 MHz needs >=2.7V)
VF_DLOOP = 0.30          # loop-path Schottky
VF_DREV  = 0.15          # cell-path low-Vf Schottky (PMEG), reverse-charge block
C_VC     = 100e-6        # small loop reservoir on Vc (cell does the ride-through now)
I_DIAL   = 1.0e-3        # ATtiny idle-sleep while counting pulses (passive filter)

# weak VoIP line: loop only develops ~4.0V across the converter, weak recharge
V_AVAIL  = 4.0
RECHARGE = 2.5e-3

# CR1632 across life: (open-circuit V, internal resistance)
CELL = {"fresh (new)":      (3.20, 15),
        "mid-life":         (3.00, 40),
        "near end-of-life": (2.70, 120)}

def cell_vdd(ocv, ri, iload=I_DIAL):
    """VDD the cell can hold at VDD during a gap, through Q_batt + D_rev."""
    return ocv - iload*ri - VF_DREV

def dial_transient(with_cell, cell=None, pps=10, npulses=12, open_frac=0.70, dt=5e-4):
    """VDD over a dialed digit. Loop reservoir (C_VC) feeds VDD via D_loop;
       the cell floors VDD when armed."""
    T, t_open = 1.0/pps, open_frac/pps
    vc = V_AVAIL                      # loop reservoir voltage
    vfloor = cell_vdd(*cell) if with_cell else 0.0
    ts, vs, t = [], [], 0.0
    for _ in range(npulses):
        tend = t + t_open            # loop OPEN: Vc (100uF) discharges into the MCU
        while t < tend:
            vc -= (I_DIAL/C_VC)*dt
            vdd = max(vc - VF_DLOOP, vfloor)   # OR of loop path and cell floor
            ts.append(t); vs.append(vdd); t += dt
        tend = t + (T - t_open)      # loop CLOSED: weak recharge of Vc
        while t < tend:
            vc = min(V_AVAIL, vc + ((RECHARGE - I_DIAL)/C_VC)*dt)
            vdd = max(vc - VF_DLOOP, vfloor)
            ts.append(t); vs.append(vdd); t += dt
    return np.array(ts), np.array(vs)

fig, ax = plt.subplots(1, 3, figsize=(16, 5))

# Panel 1: dialing transient, no-cell vs cell(fresh) vs cell(EOL)
t0,v0 = dial_transient(False)
tf,vf = dial_transient(True, CELL["fresh (new)"])
te,ve = dial_transient(True, CELL["near end-of-life"])
ax[0].plot(t0*1e3, v0, 'r-', lw=2, label=f"NO cell (min {v0.min():.2f}V)")
ax[0].plot(tf*1e3, vf, 'g-', lw=2, label=f"CR1632 fresh (min {vf.min():.2f}V)")
ax[0].plot(te*1e3, ve, color='orange', lw=2, label=f"CR1632 EOL (min {ve.min():.2f}V)")
ax[0].axhline(BOD, color='k', ls='--', lw=1); ax[0].text(760, BOD+0.03, "BOD 2.7V", fontsize=9)
ax[0].set_title('1) Dialing "0" on a WEAK line (Vavail 4.0V)\ncell floors VDD above BOD')
ax[0].set_xlabel("time (ms)"); ax[0].set_ylabel("VDD (V)")
ax[0].set_ylim(2.2, 4.0); ax[0].grid(alpha=.3); ax[0].legend(fontsize=8, loc="lower left")

# Panel 2: cell life - VDD during gap vs cell state
ocv = np.linspace(2.4, 3.3, 200)
ri  = np.interp(ocv, [2.4,2.7,3.0,3.2,3.3],[200,120,40,15,12])   # Ri rises as it depletes
vgap = ocv - I_DIAL*ri - VF_DREV
ax[1].plot(ocv, vgap, 'b-', lw=2)
ax[1].axhline(BOD, color='k', ls='--', lw=1); ax[1].text(3.05, BOD+0.02, "BOD 2.7V", fontsize=9)
# replace threshold: where vgap crosses BOD
xcross = np.interp(BOD, vgap, ocv)
ax[1].axvline(xcross, color='r', ls=':'); ax[1].text(xcross+0.01, 3.3, f"replace cell\n~{xcross:.2f}V OCV", fontsize=8, color='r')
for name,(o,r) in CELL.items():
    g = cell_vdd(o,r)
    ax[1].plot(o, g, 'o', ms=7); ax[1].annotate(f"{name}\n{g:.2f}V", (o,g), textcoords="offset points", xytext=(-10,-28), fontsize=7)
ax[1].set_title("2) Cell life: VDD held during gap vs cell OCV/Ri")
ax[1].set_xlabel("CR1632 open-circuit voltage (V)"); ax[1].set_ylabel("VDD during gap (V)")
ax[1].set_ylim(2.0, 3.4); ax[1].grid(alpha=.3)

# Panel 3: test-point voltage table for bench verification
ax[2].axis("off")
tps = [
 ("TP", "node", "on-hook", "off-hook\nsteady", "during\ngap (dial)"),
 ("TP1","Vc (loop clamp)","0.0 V","~5.0 V","droops"),
 ("TP2","VDD (MCU)","0.0 V","~4.7 V","~2.85 V"),
 ("TP3","BATT+ (CR1632)","~3.0 V","~3.0 V","~3.0 V"),
 ("TP4","BATT_EN (Q_batt gate)","~3 V (off)","~0 V (armed)","~0 V (armed)"),
 ("TP5","cell branch (D_rev anode)","0 V (isol.)","~3.0 V armed","~3.0 V"),
]
tbl = ax[2].table(cellText=tps[1:], colLabels=tps[0], loc="center", cellLoc="center")
tbl.auto_set_font_size(False); tbl.set_fontsize(8); tbl.scale(1, 2.0)
for (r,c),cell in tbl.get_celld().items():
    if r==0: cell.set_facecolor("#1f3a5f"); cell.set_text_props(color="white", weight="bold")
ax[2].set_title("3) Test-point voltages for bench verification", fontsize=11)

fig.suptitle("rev V3: CR1632 backup carries the ATtiny through pulse dialing (option B)", fontsize=13)
fig.tight_layout(rect=[0,0,1,0.94])
fig.savefig("/home/jfloyd/GitHub/Pulse-To-Tone-Converter/hardware_v3/sim/battery_backup_sim.png", dpi=110)

print("=== cell VDD-during-gap (must stay > 2.70V BOD) ===")
for name,(o,r) in CELL.items():
    g = cell_vdd(o,r); print(f"  {name:20s} OCV {o:.2f}V Ri {r:4d}ohm -> VDD_gap {g:.2f}V  {'OK' if g>BOD else 'REPLACE'}")
print(f"  replace-battery threshold ~ {xcross:.2f}V OCV\n")
print("=== dialing transient minima (weak line, Vavail 4.0V) ===")
print(f"  no cell          : {v0.min():.2f} V   ({'BOD TRIP' if v0.min()<BOD else 'ok'})")
print(f"  CR1632 fresh     : {vf.min():.2f} V   ({'BOD TRIP' if vf.min()<BOD else 'ok'})")
print(f"  CR1632 EOL       : {ve.min():.2f} V   ({'BOD TRIP' if ve.min()<BOD else 'ok'})")
print("\n=== cell drain / life ===")
# cell only sources during gaps; cumulative open time per 10-digit number
open_time_per_number = 10*0.7            # ~0.7s open per digit x ~10 digits (worst)
mAh_per_number = I_DIAL*open_time_per_number/3600*1000
print(f"  ~{mAh_per_number*1000:.2f} uAh per 10-digit number; CR1632 ~120mAh -> ~{120/mAh_per_number:,.0f} numbers")
print("  on-hook drain ~0 (Q_batt disconnected) -> life is shelf-life limited (~10 yr)")
print("\nwrote battery_backup_sim.png")
