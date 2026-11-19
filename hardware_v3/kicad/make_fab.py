#!/usr/bin/env python3
"""
make_fab.py - write the manufacturing package to ./fab from BRD170127_V3.kicad_pcb.

    python3 make_fab.py

fab/gerbers/            Gerbers (Protel names) + Excellon drill (PTH/NPTH split)
fab/BRD170127_V3_gerbers.zip
fab/BRD170127_V3_bom.csv        grouped BOM (value, refs, footprint, MPN, LCSC)
fab/BRD170127_V3_bom_jlc.csv    JLCPCB assembly BOM format
fab/BRD170127_V3_cpl_jlc.csv    JLCPCB pick-and-place (top side, SMD only)
fab/BRD170127_V3_schematic.pdf
fab/BRD170127_V3_assembly.pdf   all reference designators (F.Fab) + outline
fab/render_top.png / render_bottom.png
Also runs DRC (+ schematic parity) and ERC and fails if DRC finds anything.
"""
import csv, os, shutil, subprocess, sys, zipfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from design import PARTS

HERE = os.path.dirname(os.path.abspath(__file__))
PCB = os.path.join(HERE, "BRD170127_V3.kicad_pcb")
SCH = os.path.join(HERE, "BRD170127_V3.kicad_sch")
FAB = os.path.join(HERE, "fab")
GER = os.path.join(FAB, "gerbers")
NAME = "BRD170127_V3"


def cli(*a):
    r = subprocess.run(["kicad-cli", *a], capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit(f"kicad-cli {' '.join(a)} failed:\n{r.stdout}\n{r.stderr}")
    return r.stdout


def main():
    shutil.rmtree(FAB, ignore_errors=True)
    os.makedirs(GER)

    # ---- checks
    rpt = os.path.join(FAB, "drc.rpt")
    cli("pcb", "drc", "--severity-all", "--schematic-parity", "--exit-code-violations", "-o", rpt, PCB)
    cli("sch", "erc", "-o", os.path.join(FAB, "erc.rpt"), SCH)

    # ---- gerbers + drill
    layers = "F.Cu,B.Cu,F.Paste,F.SilkS,B.SilkS,F.Mask,B.Mask,Edge.Cuts"
    cli("pcb", "export", "gerbers", "--layers", layers, "--use-drill-file-origin",
        "--subtract-soldermask", "-o", GER + "/", PCB)
    cli("pcb", "export", "drill", "--format", "excellon", "--excellon-separate-th",
        "--excellon-units", "mm", "--drill-origin", "plot", "--generate-map", "--map-format", "gerberx2",
        "-o", GER + "/", PCB)
    z = os.path.join(FAB, NAME + "_gerbers.zip")
    with zipfile.ZipFile(z, "w", zipfile.ZIP_DEFLATED) as zf:
        for f in sorted(os.listdir(GER)):
            zf.write(os.path.join(GER, f), f)

    # ---- position file -> JLC CPL
    pos = os.path.join(FAB, "pos_raw.csv")
    cli("pcb", "export", "pos", "--format", "csv", "--units", "mm", "--side", "front",
        "--smd-only", "--use-drill-file-origin", "--exclude-fp-th", "-o", pos, PCB)
    with open(pos) as f, open(os.path.join(FAB, NAME + "_cpl_jlc.csv"), "w", newline="") as g:
        w = csv.writer(g)
        w.writerow(["Designator", "Mid X", "Mid Y", "Layer", "Rotation"])
        for row in csv.DictReader(f):
            ref = row["Ref"]
            if ref.startswith(("TP", "FID")):
                continue
            w.writerow([ref, row["PosX"] + "mm", row["PosY"] + "mm", "Top", row["Rot"]])
    os.remove(pos)

    # ---- BOM
    groups = {}
    for ref, (val, fp, sym, mpn, lcsc, pads, _) in PARTS.items():
        if ref.startswith(("FID", "TP")):
            continue
        groups.setdefault((val, fp, mpn, lcsc), []).append(ref)
    def keyref(r):
        import re
        m = re.match(r"([A-Z]+)(\d+)", r)
        return (m.group(1), int(m.group(2)))
    rows = sorted(groups.items(), key=lambda kv: keyref(sorted(kv[1], key=keyref)[0]))
    with open(os.path.join(FAB, NAME + "_bom.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["Qty", "Value", "Designators", "Footprint", "MPN / description", "LCSC"])
        for (val, fp, mpn, lcsc), refs in rows:
            refs = sorted(refs, key=keyref)
            w.writerow([len(refs), val, " ".join(refs), fp.split(":")[1], mpn, lcsc])
    with open(os.path.join(FAB, NAME + "_bom_jlc.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["Comment", "Designator", "Footprint", "LCSC Part #"])
        for (val, fp, mpn, lcsc), refs in rows:
            refs = sorted(refs, key=keyref)
            if fp.startswith(("BRD170127:", "Capacitor_THT")):
                continue          # hand-soldered: RJ11 jacks, cell leads, C1 (THT)
            w.writerow([mpn or val, ",".join(refs), fp.split(":")[1], lcsc])

    # ---- documents
    cli("sch", "export", "pdf", "-o", os.path.join(FAB, NAME + "_schematic.pdf"), SCH)
    cli("pcb", "export", "pdf", "--layers", "F.Fab,Edge.Cuts", "--include-border-title",
        "-o", os.path.join(FAB, NAME + "_assembly.pdf"), PCB)
    for side in ("top", "bottom"):
        cli("pcb", "render", "--side", side, "--width", "1600", "--height", "1120", "--quality", "high",
            "-o", os.path.join(FAB, f"render_{side}.png"), PCB)
    print("wrote", FAB)
    for f in sorted(os.listdir(FAB)):
        print("  ", f)


if __name__ == "__main__":
    main()
