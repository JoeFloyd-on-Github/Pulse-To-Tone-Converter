#!/usr/bin/env python3
"""
gen_sch.py - build BRD170127_V3.kicad_sch from design.py.

Every symbol pin gets a global net label, so connectivity comes from the labels
(no hand-drawn wires). Symbols are grouped by function with a heading per group.
Library symbols are flattened (KiCad's "extends" resolved) and embedded.

    python3 gen_sch.py && kicad-cli sch erc BRD170127_V3.kicad_sch
"""
import os, re, sys, uuid
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from design import PARTS

HERE = os.path.dirname(os.path.abspath(__file__))
SYMDIR = "/usr/share/kicad/symbols"
OUT = os.path.join(HERE, "BRD170127_V3.kicad_sch")
ROOT_UUID = "6a1e3c52-7d6b-4c1e-9b8e-170127000003"


# ------------------------------------------------------------ tiny s-expr I/O
def parse(s):
    tok = re.findall(r'\(|\)|"(?:\\.|[^"\\])*"|[^\s()]+', s)
    stack, cur = [], []
    for t in tok:
        if t == "(":
            stack.append(cur); cur = []
        elif t == ")":
            done = cur; cur = stack.pop(); cur.append(done)
        else:
            cur.append(t)
    return cur


def dump(x, ind=0):
    if not isinstance(x, list):
        return x
    if all(not isinstance(e, list) for e in x):
        return "(" + " ".join(x) + ")"
    out = "(" + " ".join(e for e in x if not isinstance(e, list) and x.index(e) == 0)
    head = []
    for e in x:
        if isinstance(e, list):
            break
        head.append(e)
    out = "(" + " ".join(head)
    for e in x[len(head):]:
        out += "\n" + "\t" * (ind + 1) + (dump(e, ind + 1) if isinstance(e, list) else e)
    return out + "\n" + "\t" * ind + ")"


def q(s):
    return '"' + s.replace('"', '\\"') + '"'


def uq(s):
    return s[1:-1] if s.startswith('"') else s


_libs = {}


def lib_symbols(lib):
    if lib not in _libs:
        path = os.path.join(HERE, "BRD170127.kicad_sym") if lib == "BRD170127" else os.path.join(SYMDIR, lib + ".kicad_sym")
        tree = parse(open(path).read())[0]
        _libs[lib] = {uq(e[1]): e for e in tree if isinstance(e, list) and e[0] == "symbol"}
    return _libs[lib]


def flatten(lib, name):
    """Return the symbol s-expr for lib:name with 'extends' resolved."""
    syms = lib_symbols(lib)
    child = syms[name]
    ext = [e for e in child if isinstance(e, list) and e[0] == "extends"]
    if not ext:
        sym = [e for e in child]
    else:
        parent = flatten(lib, uq(ext[0][1]))
        pname = uq(parent[1])
        sym = ["symbol", q(name)]
        cprops = {uq(e[1]): e for e in child if isinstance(e, list) and e[0] == "property"}
        for e in parent[2:]:
            if isinstance(e, list) and e[0] == "property" and uq(e[1]) in cprops:
                sym.append(cprops.pop(uq(e[1])))
            elif isinstance(e, list) and e[0] == "symbol":
                sub = list(e)
                sub[1] = q(uq(e[1]).replace(pname, name, 1))
                sym.append(sub)
            else:
                sym.append(e)
        for p in cprops.values():
            sym.insert(2, p)
    return sym


def pins_of(sym):
    """{pin_number: (x, y, angle)} in library coordinates (Y up)."""
    res = {}
    def walk(x):
        for e in x:
            if isinstance(e, list):
                if e[0] == "pin":
                    at = next(a for a in e if isinstance(a, list) and a[0] == "at")
                    num = next(a for a in e if isinstance(a, list) and a[0] == "number")
                    res[uq(num[1])] = (float(at[1]), float(at[2]), float(at[3]) if len(at) > 3 else 0.0)
                else:
                    walk(e)
    walk(sym)
    return res


# ---------------------------------------------------------------- placement
GROUPS = [
    ("Line interface / bridge", ["CN1", "CN2", "CN3", "D1", "D2", "D3", "D4"]),
    ("Upper shunt  VCC = 5.0 V", ["U2", "Q2", "R1", "R6", "R15", "R16", "C12", "C10", "R17", "TP1"]),
    ("Lower shunt / line modulator", ["U3", "Q4", "R5", "R7", "R19", "R20", "C11", "TP6"]),
    ("DTMF filter + V-to-I (Q1)", ["R12", "R13", "C8", "R10", "C9", "Q1", "R2"]),
    ("Pulse sense", ["R3", "C5", "R14"]),
    ("MCU", ["U1", "R11", "C4", "C7", "X1", "C2", "C3"]),
    ("Supply + CR1632 backup", ["D5", "C1", "TP2", "BT1", "Q3", "R18", "D6", "TP3", "TP4", "TP5"]),
    ("Fiducials", ["FID1", "FID2"]),
]
# group origin (mm) on an A3 sheet, column pitch, items per row
G_ORIGIN = {0: (25, 35), 1: (25, 95), 2: (25, 150), 3: (215, 35), 4: (215, 95), 5: (215, 135), 6: (215, 205), 7: (25, 260)}
PITCH_X, PITCH_Y, PER_ROW = 30.48, 27.94, 5


def U():
    return q(str(uuid.uuid4()))


def glabel(net, x, y, ang, just):
    """global label, so schematic net names equal the PCB's (no '/' prefix)"""
    return (f'(global_label {q(net)} (shape passive) (at {x:.2f} {y:.2f} {ang}) (fields_autoplaced yes) '
            f'(effects (font (size 1.0 1.0)) (justify {just})) (uuid {U()}) '
            f'(property "Intersheetrefs" "${{INTERSHEET_REFS}}" (at {x:.2f} {y:.2f} 0) '
            f'(effects (font (size 1.27 1.27)) (hide yes))))')


def main():
    used = {}
    for ref, p in PARTS.items():
        lib, name = p[2].split(":")
        used[p[2]] = (lib, name)
    used["power:PWR_FLAG"] = ("power", "PWR_FLAG")

    libsyms = []
    pinmap = {}
    for lid, (lib, name) in sorted(used.items()):
        sym = flatten(lib, name)
        pinmap[lid] = pins_of(sym)
        s = list(sym)
        s[1] = q(lid)
        libsyms.append(s)

    items = []
    for gi, (title, refs) in enumerate(GROUPS):
        gx, gy = G_ORIGIN[gi]
        items.append(f'(text {q(title)} (exclude_from_sim no) (at {gx - 10} {gy - 14} 0) '
                     f'(effects (font (size 2 2) (bold yes)) (justify left bottom)) (uuid {U()}))')
        for k, ref in enumerate(refs):
            val, fp, lid, mpn, lcsc, pads, _ = PARTS[ref]
            x = gx + (k % PER_ROW) * PITCH_X
            y = gy + (k // PER_ROW) * PITCH_Y
            if ref.startswith("CN"):
                x = gx + (k % 3) * 45.72
                y = gy + (k // 3) * 30.48 if k < 3 else gy + 30.48 + ((k - 3) // 2) * PITCH_Y
                if k >= 3:
                    x = gx + ((k - 3) % 2) * PITCH_X
            x, y = round(x / 2.54) * 2.54, round(y / 2.54) * 2.54
            props = [("Reference", ref, (x + 3.0, y - 4.0), False), ("Value", val, (x + 3.0, y + 4.5), False),
                     ("Footprint", fp, (x, y), True), ("Datasheet", "", (x, y), True)]
            if mpn:
                props.append(("MPN", mpn, (x, y), True))
            if lcsc:
                props.append(("LCSC", lcsc, (x, y), True))
            pr = "".join(f'(property {q(k_)} {q(v)} (at {px:.2f} {py:.2f} 0) (effects (font (size 1.27 1.27)) '
                         f'(justify left){" (hide yes)" if h else ""}))' for k_, v, (px, py), h in props)
            pins = pinmap[lid]
            pr += "".join(f'(pin {q(n)} (uuid {U()}))' for n in pins)
            items.append(f'(symbol (lib_id {q(lid)}) (at {x:.2f} {y:.2f} 0) (unit 1) (exclude_from_sim no) '
                         f'(in_bom {"no" if ref.startswith(("TP", "FID")) else "yes"}) (on_board yes) (dnp no) (uuid {U()}) {pr}'
                         f'(instances (project "BRD170127_V3" (path "/{uq(q(ROOT_UUID))}" (reference {q(ref)}) (unit 1)))))')
            # a net label on every connected pin, pointing away from the body
            for n, (px, py, ang) in pins.items():
                net = pads.get(n)
                if not net:
                    items.append(f'(no_connect (at {x + px:.2f} {y - py:.2f}) (uuid {U()}))')
                    continue
                la = (ang + 180) % 360
                just = "left" if la in (0, 90) else "right"
                items.append(glabel(net, x + px, y - py, int(la), just))

    # PWR_FLAGs: rails fed only by passive parts (bridge diodes, shunts, cell)
    fx, fy = 119.38, 269.24
    for k, net in enumerate(["GND", "VCC", "VEE", "VDD", "BATT_P"]):
        x, y = fx + k * 20.32, fy
        (px, py, ang) = pinmap["power:PWR_FLAG"]["1"]
        items.append(f'(symbol (lib_id "power:PWR_FLAG") (at {x:.2f} {y:.2f} 0) (unit 1) (exclude_from_sim no) '
                     f'(in_bom yes) (on_board yes) (dnp no) (uuid {U()}) '
                     f'(property "Reference" "#FLG0{k + 1}" (at {x:.2f} {y - 6:.2f} 0) (effects (font (size 1.27 1.27)) (hide yes)))'
                     f'(property "Value" "PWR_FLAG" (at {x:.2f} {y - 4:.2f} 0) (effects (font (size 1.0 1.0))))'
                     f'(property "Footprint" "" (at {x:.2f} {y:.2f} 0) (effects (font (size 1.27 1.27)) (hide yes)))'
                     f'(property "Datasheet" "" (at {x:.2f} {y:.2f} 0) (effects (font (size 1.27 1.27)) (hide yes)))'
                     f'(pin "1" (uuid {U()}))'
                     f'(instances (project "BRD170127_V3" (path "/{ROOT_UUID}" (reference "#FLG0{k + 1}") (unit 1)))))')
        items.append(glabel(net, x + px, y - py, 270, "right"))

    notes = [
        "BRD170127 rev V3 - pulse-to-tone converter (ATtiny85), derived from LieBtrau's open design (Hackaday 28557).",
        "Generated by gen_sch.py from design.py. Connectivity is by net label; the PCB is generated from the same data.",
        "Simulation of this exact circuit: ../spice (conv_v3.sub, run_sims.py, REPORT.md).",
        "PB2 (pin 7) is BATT_EN: PB1 is the DTMF PWM (OC1A) and PB3/PB4 the crystal, so the old mode jumper is dropped (mode fixed in firmware).",
    ]
    for k, t in enumerate(notes):
        items.append(f'(text {q(t)} (exclude_from_sim no) (at 25 {282 + k * 4} 0) (effects (font (size 1.5 1.5)) (justify left bottom)) (uuid {U()}))')

    head = ('(kicad_sch\n\t(version 20250114)\n\t(generator "eeschema")\n\t(generator_version "9.0")\n'
            f'\t(uuid {q(ROOT_UUID)})\n\t(paper "A3")\n'
            '\t(title_block\n\t\t(title "Pulse-to-Tone Converter rev V3")\n\t\t(rev "V3")\n'
            '\t\t(company "BRD170127")\n\t\t(comment 1 "Original design: LieBtrau / Christoph Tack (Hackaday 28557)")\n\t)\n')
    body = "\t(lib_symbols\n" + "\n".join("\t\t" + dump(s, 2) for s in libsyms) + "\n\t)\n"
    body += "\n".join("\t" + it for it in items) + "\n"
    tail = '\t(sheet_instances\n\t\t(path "/" (page "1"))\n\t)\n\t(embedded_fonts no)\n)\n'
    open(OUT, "w").write(head + body + tail)
    print("wrote", OUT)


if __name__ == "__main__":
    main()
