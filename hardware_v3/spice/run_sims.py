#!/usr/bin/env python3
"""
run_sims.py - ngspice test benches for the pulse-to-tone converter.

Compares the ORIGINAL board (conv_orig.sub) with rev V3 (conv_v3.sub) using the
generic, datasheet-fitted models in models.lib. Writes CSV/PNG results and a
summary.json to ./results/.

    cd hardware_v3/spice && python3 run_sims.py          # everything
    python3 run_sims.py dc spread dial dtmf onhook ring   # a subset

Benches
  dc      converter voltage drop, rails and shunt currents vs loop current
  spread  TLV431 Vref / Imin spread (incl. a TL431 fitted by mistake) at low loop current
  dial    pulse-dialing a "0" on POTS / normal ATA / weak ATA, with and without the cell
  dtmf    DTMF level, twist and PWM carrier at the FXS terminals (600 ohm)
  onhook  hang-up: cell disarm, VDD collapse, on-hook cell drain, firmware-failure case
  ring    ringing current through the converter while on-hook
"""
import json, os, subprocess, sys, itertools
import numpy as np
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "results")
os.makedirs(OUT, exist_ok=True)
SUMMARY_FILE = os.path.join(OUT, "summary.json")
summary = json.load(open(SUMMARY_FILE)) if os.path.exists(SUMMARY_FILE) else {}

HDR = (".include models.lib\n.include conv_orig.sub\n.include conv_v3.sub\n"
       ".options method=gear reltol=1e-3 vntol=1e-5 abstol=1e-10 itl4=50\n")
BOD = 2.7


def run(name, body, cols):
    """Write <name>.cir, run ngspice, return dict of numpy columns from wrdata."""
    cir = os.path.join(OUT, name + ".cir")
    dat = os.path.join(OUT, name + ".dat")
    with open(cir, "w") as f:
        f.write(f"* {name}\n" + HDR + body.replace("@DAT@", dat) + "\n.end\n")
    r = subprocess.run(["ngspice", "-b", cir], cwd=HERE, capture_output=True, text=True)
    if not os.path.exists(dat) or "aborted" in r.stdout + r.stderr or "too small" in r.stdout + r.stderr:
        print(r.stdout[-3000:], r.stderr[-2000:])
        raise RuntimeError(name + " failed")
    a = np.loadtxt(dat)
    os.remove(dat)
    a = np.atleast_2d(a)
    # wrdata writes (x, y) pairs per vector
    d = {"x": a[:, 0]}
    for i, c in enumerate(cols):
        d[c] = a[:, 2 * i + 1]
    return d


def conv(kind, inst, a, b, tone, arm, **p):
    sub = "CONV_V3" if kind == "v3" else "CONV_ORIG"
    p.setdefault("tsaw", "1")          # PWM ramp only needed by the dtmf bench
    if kind != "v3":
        for k in ("voc", "ri", "cell", "roff"):
            p.pop(k, None)
    ps = " ".join(f"{k}={v}" for k, v in p.items())
    return f"X{inst} {a} {b} 0 {tone} {arm} {sub} {ps}\n"


# --------------------------------------------------------------------------- dc
def bench_dc():
    res = {}
    fig, ax = plt.subplots(1, 3, figsize=(15, 4.2))
    for kind, col in (("orig", "tab:red"), ("v3", "tab:blue")):
        # one operating-point solve per current (a .dc sweep of this floating,
        # current-driven circuit can continue onto a non-physical branch)
        currents = [x / 2 for x in range(2, 101)]          # 1 .. 50 mA
        body = "IL T B DC 20m\nRT T A 1\nRG B 0 1e8\nVTN TN 0 0\nVARM ARM 0 1\n"
        body += conv(kind, "1", "A", "B", "TN", "ARM", cell=0)   # loop power only
        tmp = os.path.join(OUT, f"dcop_{kind}")
        body += (".control\nforeach il " + " ".join(f"{c}m" for c in currents) + "\n"
                 "alter IL dc = $il\nop\n"
                 + (f"print v(B,A) v(x1.vcc) v(x1.vdd) v(x1.vee) v(x1.q4b) v(x1.u3k) v(x1.q2b) v(x1.u2k) > {tmp}.$il\nend\n.endc\n"
                    if kind == "v3" else
                    f"print v(B,A) v(x1.vcc) v(x1.vdd) v(x1.vee) > {tmp}.$il\nend\n.endc\n"))
        cir = os.path.join(OUT, f"dc_{kind}.cir")
        open(cir, "w").write(f"* dc {kind}\n" + HDR + body + "\n.end\n")
        subprocess.run(["ngspice", "-b", cir], cwd=HERE, capture_output=True, text=True)
        rows = []
        for c in currents:
            fn = f"{tmp}.{c}m"
            vals = {l.split("=")[0].strip(): float(l.split("=")[1]) for l in open(fn) if "=" in l}
            os.remove(fn)
            if kind == "v3":   # TLV431 cathode currents through R20 / R16 (the PNPs take the rest)
                iu3 = (vals["v(x1.q4b)"] - vals["v(x1.u3k)"]) / 220 * 1e3
                iu2 = (vals["v(x1.q2b)"] - vals["v(x1.u2k)"]) / 220 * 1e3
            else:              # original: U3 alone carries the loop current (minus ~0.1 mA in R5/R7)
                iu3 = c - 0.13
                iu2 = float("nan")
            rows.append((c, vals["v(b,a)"], vals["v(x1.vcc)"], vals["v(x1.vdd)"], -vals["v(x1.vee)"], iu3, iu2))
        rows = np.array(rows)
        il = rows[:, 0]
        d = {"vdrop": rows[:, 1], "vcc": rows[:, 2], "vdd": rows[:, 3], "vlo": rows[:, 4], "iu3": rows[:, 5]}
        np.savetxt(os.path.join(OUT, f"dc_{kind}.csv"), rows, delimiter=",",
                   header="loop_mA,Vdrop,VCC,VDD,V_GND_VEE,I_U3_mA,I_U2_mA", fmt="%.4f")
        lab = "original" if kind == "orig" else "rev V3"
        ax[0].plot(il, d["vdrop"], col, label=lab)
        ax[1].plot(il, d["vdd"], col, label=f"{lab} VDD")
        ax[1].plot(il, d["vcc"], col, ls=":", label=f"{lab} VCC")
        ax[2].plot(il, d["vlo"], col, label=lab)
        ok = il[np.argmax(d["vdd"] > BOD)]
        res[kind] = {
            "drop_at_20mA_V": float(np.interp(20, il, d["vdrop"])),
            "drop_at_40mA_V": float(np.interp(40, il, d["vdrop"])),
            "vdd_at_20mA_V": float(np.interp(20, il, d["vdd"])),
            "min_loop_mA_for_VDD_above_BOD": float(ok),
            "lower_shunt_V_at_20mA": float(np.interp(20, il, d["vlo"])),
            "lower_shunt_power_mW_at_40mA": float(np.interp(40, il, d["vlo"]) * 40),
            "U3_TLV431_current_mA_at_25mA": float(np.interp(25, il, d["iu3"])),
            "U3_TLV431_current_mA_at_40mA": float(np.interp(40, il, d["iu3"])),
        }
    ax[0].set(title="Converter voltage drop (idle, no tone)", xlabel="loop current [mA]", ylabel="V(line)")
    ax[1].axhline(BOD, color="k", ls="--", lw=0.8)
    ax[1].set(title="Rails vs loop current", xlabel="loop current [mA]", ylabel="V")
    ax[2].set(title="Lower shunt (line modulator) voltage, idle", xlabel="loop current [mA]", ylabel="V(GND-VEE)")
    for a in ax:
        a.grid(alpha=.3); a.legend(fontsize=8)
    fig.tight_layout(); fig.savefig(os.path.join(OUT, "dc.png"), dpi=110)
    summary["dc"] = res
    print("dc", json.dumps(res, indent=1))


# ------------------------------------------------------------------ spread
def bench_spread():
    """Vary each TLV431's Vref and Imin; report VDD and shunt regulation at low loop current."""
    vrefs = [1.222, 1.240, 1.258]                      # TLV431A +/-1.5 %
    imins = [55e-6, 100e-6, 400e-6, 1e-3]              # TLV431 typ/max, TL431 typ/max
    loops = [4e-3, 6e-3, 8e-3, 10e-3, 15e-3]
    res = {}
    rows = []
    for kind in ("orig", "v3"):
        body = "IL T B DC 10m\nRT T A 1\nRG B 0 1e8\nVTN TN 0 0\nVARM ARM 0 1\n"
        lines = []
        n = 0
        combos = list(itertools.product(vrefs, imins))
        for (vr, im) in combos:
            n += 1
            lines.append(conv(kind, str(n), f"A{n}", f"B{n}", "TN", "ARM",
                              vref2=vr, imin2=f"{im}", vref3=vr, imin3=f"{im}")
                         .replace(f"X{n} ", f"X{n} "))
            lines.append(f"IL{n} T{n} B{n} DC 10m\nRT{n} T{n} A{n} 1\nRG{n} B{n} 0 1e8\n")
        body = "VTN TN 0 0\nVARM ARM 0 1\n" + "".join(lines)
        probes = " ".join(f"v(x{i}.vcc) v(x{i}.vdd)" for i in range(1, n + 1))
        sweep = "\n".join(
            [f"alter IL{i} dc = $&il" for i in range(1, n + 1)])
        ctl = ".control\nforeach il " + " ".join(f"{x}" for x in loops) + "\n"
        ctl += "".join(f"alter IL{i} dc = $il\n" for i in range(1, n + 1))
        ctl += f"op\nprint {probes} > @DAT@.$il\nend\n.endc\n"
        cir_body = body + ctl
        cir = os.path.join(OUT, f"spread_{kind}.cir")
        with open(cir, "w") as f:
            f.write(f"* spread {kind}\n" + HDR + cir_body.replace("@DAT@", os.path.join(OUT, f"sp_{kind}")) + "\n.end\n")
        subprocess.run(["ngspice", "-b", cir], cwd=HERE, capture_output=True, text=True)
        res[kind] = {}
        for il in loops:
            fn = os.path.join(OUT, f"sp_{kind}.{il}")
            txt = open(fn).read()
            os.remove(fn)
            vals = {}
            for line in txt.splitlines():
                if "=" in line:
                    k, v = line.split("=")
                    vals[k.strip()] = float(v)
            for i, (vr, im) in enumerate(combos, 1):
                vcc = vals[f"v(x{i}.vcc)"]; vdd = vals[f"v(x{i}.vdd)"]
                rows.append((kind, il * 1e3, vr, im * 1e6, vcc, vdd))
            vdds = [vals[f"v(x{i}.vdd)"] for i in range(1, n + 1)]
            vccs = [vals[f"v(x{i}.vcc)"] for i in range(1, n + 1)]
            res[kind][f"{il*1e3:.0f}mA"] = {"VDD_min": min(vdds), "VDD_max": max(vdds),
                                            "VCC_min": min(vccs), "VCC_max": max(vccs)}
    with open(os.path.join(OUT, "spread.csv"), "w") as f:
        f.write("board,loop_mA,vref,imin_uA,VCC,VDD\n")
        for r in rows:
            f.write(",".join(f"{x}" if isinstance(x, str) else f"{x:.4g}" for x in r) + "\n")
    # plot: VCC spread band vs loop current
    fig, ax = plt.subplots(figsize=(7, 4.2))
    for kind, col in (("orig", "tab:red"), ("v3", "tab:blue")):
        lo = [res[kind][f"{x*1e3:.0f}mA"]["VCC_min"] for x in loops]
        hi = [res[kind][f"{x*1e3:.0f}mA"]["VCC_max"] for x in loops]
        ax.fill_between([x * 1e3 for x in loops], lo, hi, color=col, alpha=.3,
                        label=("original" if kind == "orig" else "rev V3") + " VCC (all parts)")
    ax.set(title="Upper-shunt rail across TLV431/TL431 spread", xlabel="loop current [mA]", ylabel="VCC [V]")
    ax.grid(alpha=.3); ax.legend()
    fig.tight_layout(); fig.savefig(os.path.join(OUT, "spread.png"), dpi=110)
    summary["spread"] = res
    print("spread", json.dumps(res, indent=1))


# -------------------------------------------------------------------- dial
LINES = {
    # name: (Vbat [V], Rfeed [ohm], current limit [A])
    "POTS (48 V, 2x200 ohm + 1 km)": (48, 600, 1.0),
    "ATA (25 mA, 40 V)": (40, 200, 0.025),
    "weak ATA (15 mA, 18 V)": (18, 200, 0.015),
    "very weak (10 mA, 15 V)": (15, 300, 0.010),
    "starved (7 mA, 15 V)": (15, 300, 0.007),
    "starved (3 mA, 15 V)": (15, 300, 0.003),
}
CELLS = {"no cell": (3.2, 15, 0), "fresh 3.2V/15R": (3.2, 15, 1),
         "mid 3.0V/40R": (3.0, 40, 1), "EOL 2.7V/120R": (2.7, 120, 1)}


def fxs(vbat, rfeed, ilim, n=""):
    """FXS port. POTS = battery + feed resistance (Thevenin). ATA = constant-current
    feed (Norton) whose open-circuit voltage is clamped at its compliance voltage.
    Both have a 600-ohm AC termination (220 uF + 600 ohm)."""
    if ilim >= 0.05:
        s = f"VB{n} TPX{n} RG{n} {vbat}\nRF{n} TPX{n} TP{n} {rfeed}\n"
    else:
        s = (f"IFX{n} RG{n} TP{n} DC {ilim}\nRPAR{n} TP{n} RG{n} 100k\n"
             f"DCL{n} RG{n} TP{n} DCLAMP{n}\n.model DCLAMP{n} D(IS=1e-12 BV={vbat} IBV=1m RS=5)\n")
    return s + (f"CFX{n} TP{n} FX{n} 220u\nRFX{n} FX{n} RG{n} 600\nRGND{n} RG{n} 0 1e7\n")


def phone(n="", dial=None):
    # rotary phone: 230 ohm DC, ~600 ohm AC (speech network), dial contacts in series
    s = f"RPH{n} TP{n} P1{n} 230\nLPH{n} P1{n} P2{n} 10\nRPHA{n} P1{n} P2{n} 370\n"
    if dial is None:
        s += f"RDIAL{n} P2{n} A{n} 0.1\n"
    else:
        s += f"SDIAL{n} P2{n} A{n} DC{n} 0 SWD\nVDC{n} DC{n} 0 PWL({dial})\n"
        s += ".model SWD SW(VT=0.5 VH=0.1 RON=0.1 ROFF=1e9)\n"
    return s


def dial_pwl(t0=1.0, pulses=10, pps=10.0, brk=0.6):
    T = 1 / pps
    pts = [(0, 1), (t0, 1)]
    t = t0
    for _ in range(pulses):
        pts += [(t + 1e-4, 0), (t + brk * T, 0), (t + brk * T + 1e-4, 1), (t + T, 1)]
        t += T
    pts.append((t + 1.0, 1))
    return " ".join(f"{a:.5f} {b}" for a, b in pts), t


def count_pulses(t, pb0, vdd, t0, t1):
    m = (t >= t0) & (t <= t1)
    st, n = 1, 0
    for v, vd in zip(pb0[m], vdd[m]):
        if st == 1 and v < 0.3 * vd:
            st = 0; n += 1
        elif st == 0 and v > 0.6 * vd:
            st = 1
    return n


def bench_dial():
    res = {}
    pwl, tend = dial_pwl()
    fig, axs = plt.subplots(len(LINES), 1, figsize=(11, 3.0 * len(LINES)), sharex=True)
    for ax, (lname, (vb, rf, il)) in zip(axs, LINES.items()):
        res[lname] = {}
        cases = [("orig", "no cell")] + [("v3", c) for c in CELLS]
        for kind, cname in cases:
            voc, ri, cell = CELLS[cname]
            body = fxs(vb, rf, il) + phone(dial=pwl)
            # ARM: firmware arms the cell once the MCU is up (VDD above BOD)
            body += "BARM ARM 0 V = V(x1.vdd) > 2.7 ? 1 : 0\nVTN TN 0 0\n"
            body += conv(kind, "1", "A", "RG", "TN", "ARM", voc=voc, ri=ri, cell=cell)
            body += (f".control\ntran 50u {tend+0.3:.3f} 0 50u\n"
                     "wrdata @DAT@ v(x1.vdd) v(x1.pb0) v(TP,RG) v(x1.vcc)\n.endc\n")
            tag = "".join(ch for ch in lname.split(",")[0] if ch.isalnum())
            d = run(f"dial_{tag}_{kind}_{cname.split()[0]}", body, ["vdd", "pb0", "vline", "vcc"])
            t = d["x"]
            m = (t > 1.0) & (t < tend + 0.2)
            vmin = float(d["vdd"][m].min())
            npulse = count_pulses(t, d["pb0"], d["vdd"], 0.98, tend + 0.2)
            vpre = float(np.interp(0.98, t, d["vdd"]))
            res[lname][f"{kind}/{cname}"] = {"VDD_before_dial": vpre, "VDD_min_during_dial": vmin,
                                             "pulses_seen_of_10": npulse,
                                             "survives_BOD": bool(vmin > BOD)}
            lab = ("original" if kind == "orig" else "V3 " + cname)
            ax.plot(t, d["vdd"], lw=1, label=f"{lab}: min {vmin:.2f} V, {npulse}/10 pulses")
        ax.axhline(BOD, color="k", ls="--", lw=.8)
        ax.set(title=f"Dialing '0' on {lname}", ylabel="VDD [V]", ylim=(0, 5.5))
        ax.grid(alpha=.3); ax.legend(fontsize=7, loc="lower left")
    axs[-1].set(xlabel="time [s]", xlim=(0.8, tend + 0.3))
    fig.tight_layout(); fig.savefig(os.path.join(OUT, "dial.png"), dpi=110)
    summary["dial"] = res
    print("dial", json.dumps(res, indent=1))


# -------------------------------------------------------------------- dtmf
PAIRS = {"1": (697, 1209), "5": (770, 1336), "9": (852, 1477), "D": (941, 1633)}


def bench_dtmf():
    res = {}
    fig, axs = plt.subplots(2, 2, figsize=(12, 7))
    vb, rf, il = LINES["ATA (25 mA, 40 V)"]
    for kind in ("orig", "v3"):
        res[kind] = {}
        for key, (f1, f2) in PAIRS.items():
            body = fxs(vb, rf, il) + phone()
            body += "VARM ARM 0 1\nVTN TN 0 PWL(0 0 0.0499 0 0.05 1)\n"
            body += conv(kind, "1", "A", "RG", "TN", "ARM", f1=f1, f2=f2, tsaw="32u")
            # settle the reservoir first (uic + 0.05 s), then 100 ms of tone
            body += (".control\ntran 1u 0.15 0 0.5u\n"
                                          "wrdata @DAT@ v(FX,RG) v(x1.vdd)\n.endc\n")
            d = run(f"dtmf_{kind}_{key}", body, ["vac", "vdd"])
            # resample onto a uniform 1 us grid (ngspice steps are adaptive)
            tu = np.arange(0.0, d["x"][-1], 1e-6)
            t, v = tu, np.interp(tu, d["x"], d["vac"])
            d["vdd"] = np.interp(tu, d["x"], d["vdd"])
            m = t > 0.08
            tt, vv = t[m], v[m] - v[m].mean()
            n = len(tt); dt = tt[1] - tt[0]
            w = np.hanning(n)
            sp = np.abs(np.fft.rfft(vv * w)) * 2 / w.sum()
            fr = np.fft.rfftfreq(n, dt)
            def lvl(f):
                k = np.argmin(abs(fr - f)); a = sp[max(k-3,0):k+4].max()
                return 20 * np.log10(a / np.sqrt(2) / 0.7746 + 1e-12)   # dBm into 600 ohm
            lo, hi = lvl(f1), lvl(f2)
            carrier = lvl(31250)
            band = (fr > 300) & (fr < 3400)
            tot = np.sqrt(np.sum(sp[band] ** 2) / 2)
            res[kind][key] = {"low_dBm": round(lo, 2), "high_dBm": round(hi, 2),
                              "twist_dB": round(hi - lo, 2), "carrier_31k25_dBm": round(carrier, 1),
                              "VDD_min_during_tone": float(d["vdd"][t > 0.05].min())}
            if key == "5":
                axi = 0 if kind == "orig" else 1
                axs[0, axi].plot(tt[:4000] * 1e3, v[m][:4000] - v[m].mean(), lw=.8)
                axs[0, axi].set(title=f"{'original' if kind=='orig' else 'rev V3'}: digit 5 at FXS (600 ohm)",
                                xlabel="ms", ylabel="V")
                axs[1, axi].plot(fr / 1e3, 20 * np.log10(sp / np.sqrt(2) / 0.7746 + 1e-9), lw=.7)
                axs[1, axi].set(xlim=(0, 40), ylim=(-90, 0), xlabel="kHz", ylabel="dBm (600 ohm)",
                                title="spectrum (DTMF pair + 31.25 kHz PWM carrier)")
    for a in axs.flat:
        a.grid(alpha=.3)
    fig.tight_layout(); fig.savefig(os.path.join(OUT, "dtmf.png"), dpi=110)
    summary["dtmf"] = res
    print("dtmf", json.dumps(res, indent=1))


# ------------------------------------------------------------------ onhook
def bench_onhook():
    res = {}
    vb, rf, il = LINES["ATA (25 mA, 40 V)"]
    # off-hook 0..1 s, hang up at 1.0 s (dial/hook contacts open for good),
    # firmware disarms 250 ms after the loop opened.
    hook = "0 1 1.0 1 1.0001 0 3 0"
    fig, ax = plt.subplots(figsize=(9, 4))
    for label, t_rel in (("firmware disarms at +250 ms", 1.25), ("firmware never disarms (fault)", 99)):
        body = fxs(vb, rf, il) + phone(dial=hook)
        body += f"BARM ARM 0 V = (V(x1.vdd) > 2.7 && time < {t_rel}) ? 1 : 0\nVTN TN 0 0\n"
        body += conv("v3", "1", "A", "RG", "TN", "ARM")
        body += (".control\ntran 1m 3 0 1m uic\nwrdata @DAT@ v(x1.vdd) i(v.x1.xbt1.vc)\n.endc\n")
        d = run("onhook_" + ("ok" if t_rel < 9 else "fault"), body, ["vdd", "icell"])
        t = d["x"]
        ax.plot(t, d["vdd"], label=label)
        res[label] = {"VDD_at_2.9s": float(np.interp(2.9, t, d["vdd"])),
                      "cell_current_at_2.9s_uA": float(-np.interp(2.9, t, d["icell"]) * 1e6)}
    # steady on-hook drain with the gate pulled up (op point), worst-case leakage
    for roff, tag in (("100meg", "typ"), ("3meg", "worst (1 uA Idss)")):
        body = "VARM ARM 0 0\nVTN TN 0 0\nRL A B 1e9\nRG B 0 1e8\n"
        body += conv("v3", "1", "A", "B", "TN", "ARM", roff=roff)
        body += ".control\nop\nprint i(v.x1.xbt1.vc) > @DAT@.txt\n.endc\n"
        cir = os.path.join(OUT, "onhook_leak.cir")
        open(cir, "w").write("* leak\n" + HDR + body.replace("@DAT@", os.path.join(OUT, "leak")) + "\n.end\n")
        subprocess.run(["ngspice", "-b", cir], cwd=HERE, capture_output=True, text=True)
        txt = open(os.path.join(OUT, "leak.txt")).read(); os.remove(os.path.join(OUT, "leak.txt"))
        i = -float(txt.split("=")[1])
        res[f"on-hook cell drain, {tag}"] = {"uA": i * 1e6, "years_for_100mAh": 0.1 / max(i, 1e-12) / 8766}
    ax.axhline(BOD, color="k", ls="--", lw=.8); ax.axvline(1.0, color="gray", lw=.6)
    ax.set(title="Hang-up at t = 1 s (rev V3, fresh cell)", xlabel="s", ylabel="VDD [V]")
    ax.grid(alpha=.3); ax.legend()
    fig.tight_layout(); fig.savefig(os.path.join(OUT, "onhook.png"), dpi=110)
    summary["onhook"] = res
    print("onhook", json.dumps(res, indent=1))


# -------------------------------------------------------------------- ring
def bench_ring():
    """On-hook ringing: 75 Vrms 25 Hz on 48 V through the ringer (1 uF + 2.5 kohm) and the converter."""
    res = {}
    fig, ax = plt.subplots(figsize=(9, 4))
    for kind in ("orig", "v3"):
        body = ("VRG TP0 RG SIN(48 106 25)\nRS TP0 TP 400\nRGND RG 0 1e7\n"
                "CR TP R1 1u\nRR R1 A 2.5k\n"
                "BARM ARM 0 V = V(x1.vdd) > 2.7 ? 1 : 0\nVTN TN 0 0\n")
        body += conv(kind, "1", "A", "RG", "TN", "ARM")
        # start from the on-hook DC state (ringer cap already charged to the 48 V battery)
        body += ".control\ntran 0.2m 2 0 0.2m\nwrdata @DAT@ v(x1.vdd) v(x1.vcc) v(x1.vee)\n.endc\n"
        d = run(f"ring_{kind}", body, ["vdd", "vcc", "vee"])
        ax.plot(d["x"], d["vdd"], label=f"{'original' if kind=='orig' else 'rev V3'} VDD")
        m = d["x"] > 0.3          # skip the first ring cycle
        res[kind] = {"VCC_max": float(d["vcc"][m].max()), "VDD_max": float(d["vdd"][m].max()),
                     "VDD_at_2s": float(d["vdd"][-1]), "GND_VEE_max": float((-d["vee"][m]).max()),
                     "GND_VEE_max_incl_first_cycle": float((-d["vee"]).max())}
    ax.axhline(BOD, color="k", ls="--", lw=.8)
    ax.set(title="Incoming ring (on-hook): does the MCU wake up?", xlabel="s", ylabel="VDD [V]")
    ax.grid(alpha=.3); ax.legend()
    fig.tight_layout(); fig.savefig(os.path.join(OUT, "ring.png"), dpi=110)
    summary["ring"] = res
    print("ring", json.dumps(res, indent=1))


if __name__ == "__main__":
    which = sys.argv[1:] or ["dc", "spread", "dial", "dtmf", "onhook", "ring"]
    for w in which:
        globals()["bench_" + w]()
        json.dump(summary, open(SUMMARY_FILE, "w"), indent=1)
