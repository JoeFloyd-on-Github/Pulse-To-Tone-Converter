#!/usr/bin/env python3
"""
gen_pcb.py - build BRD170127_V3.kicad_pcb (placement + nets, unrouted) from design.py.

    python3 gen_pcb.py            # writes BRD170127_V3.kicad_pcb (overwrites!)

Routing is done afterwards (Freerouting via DSN/SES, see README.md), so only run
this again if you intend to re-place and re-route the board.
"""
import os, sys, json
import pcbnew
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from design import PARTS, PLACE, BOARD_W, BOARD_H, NET_CLASSES, nets

HERE = os.path.dirname(os.path.abspath(__file__))
SYS_FP = "/usr/share/kicad/footprints"
OX, OY = 100.0, 100.0          # board origin on the KiCad sheet
PCB = os.path.join(HERE, "BRD170127_V3.kicad_pcb")


def P(x, y):
    """design (mm, Y up from bottom-left) -> KiCad internal units (Y down)."""
    return pcbnew.VECTOR2I(pcbnew.FromMM(OX + x), pcbnew.FromMM(OY + BOARD_H - y))


def load_fp(libref):
    lib, name = libref.split(":")
    path = os.path.join(HERE, lib + ".pretty") if lib == "BRD170127" else os.path.join(SYS_FP, lib + ".pretty")
    fp = pcbnew.FootprintLoad(path, name)
    if fp is None:
        raise SystemExit(f"footprint not found: {libref}")
    fp.SetFPID(pcbnew.LIB_ID(lib, name))
    return fp


def main():
    board = pcbnew.BOARD()
    ds = board.GetDesignSettings()
    board.SetCopperLayerCount(2)
    ds.m_TrackMinWidth = pcbnew.FromMM(0.2)
    ds.m_ViasMinSize = pcbnew.FromMM(0.6)
    ds.m_MinThroughDrill = pcbnew.FromMM(0.3)
    ds.m_MinClearance = pcbnew.FromMM(0.2)
    ds.m_CopperEdgeClearance = pcbnew.FromMM(0.3)
    ds.SetAuxOrigin(P(0, 0))
    ds.SetGridOrigin(P(0, 0))

    netinfo = {}
    # unused connector pins get KiCad's "unconnected-(REF-PadN)" nets, as the schematic's no-connects do
    extra = []
    for ref, p in PARTS.items():
        if ref.startswith("CN"):
            for n in ("1", "2", "5", "6"):
                extra.append(f"unconnected-({ref}-Pad{n})")
    for n in nets() + extra:
        ni = pcbnew.NETINFO_ITEM(board, n)
        board.Add(ni)
        netinfo[n] = ni

    # outline
    pts = [(0, 0), (BOARD_W, 0), (BOARD_W, BOARD_H), (0, BOARD_H)]
    for (x1, y1), (x2, y2) in zip(pts, pts[1:] + pts[:1]):
        s = pcbnew.PCB_SHAPE(board)
        s.SetShape(pcbnew.SHAPE_T_SEGMENT)
        s.SetStart(P(x1, y1)); s.SetEnd(P(x2, y2))
        s.SetLayer(pcbnew.Edge_Cuts); s.SetWidth(pcbnew.FromMM(0.1))
        board.Add(s)

    for ref, (val, fpref, sym, mpn, lcsc, pads, _pos) in PARTS.items():
        x, y, rot = PLACE.get(ref, _pos)
        fp = load_fp(fpref)
        fp.SetReference(ref)
        fp.SetValue(val)
        fp.SetPosition(P(x, y))
        fp.SetOrientationDegrees(rot)
        for k, v in (("MPN", mpn), ("LCSC", lcsc)):
            if v:
                fp.SetField(k, v)
                for f in fp.GetFields():
                    if f.GetName() == k:
                        f.SetVisible(False)
        board.Add(fp)
        for pad in fp.Pads():
            n = pads.get(pad.GetNumber())
            if not n and ref.startswith("CN") and pad.GetNumber() in ("1", "2", "5", "6"):
                n = f"unconnected-({ref}-Pad{pad.GetNumber()})"
            if n:
                pad.SetNet(netinfo[n])
        # keep reference text small and on silk
        fp.Reference().SetTextSize(pcbnew.VECTOR2I(pcbnew.FromMM(0.8), pcbnew.FromMM(0.8)))
        fp.Reference().SetTextThickness(pcbnew.FromMM(0.12))

    # GND (circuit common) pours on both layers
    for layer in (pcbnew.F_Cu, pcbnew.B_Cu):
        z = pcbnew.ZONE(board)
        z.SetLayer(layer)
        z.SetNet(netinfo["GND"])
        ol = z.Outline()
        ol.NewOutline()
        for (x, y) in [(0.3, 0.3), (BOARD_W - 0.3, 0.3), (BOARD_W - 0.3, BOARD_H - 0.3), (0.3, BOARD_H - 0.3)]:
            ol.Append(P(x, y))
        z.SetLocalClearance(pcbnew.FromMM(0.3))
        z.SetMinThickness(pcbnew.FromMM(0.25))
        z.SetPadConnection(pcbnew.ZONE_CONNECTION_THERMAL)
        z.SetThermalReliefGap(pcbnew.FromMM(0.3))
        z.SetThermalReliefSpokeWidth(pcbnew.FromMM(0.4))
        z.SetAssignedPriority(0)
        board.Add(z)

    # silkscreen title
    t = pcbnew.PCB_TEXT(board)
    t.SetText("BRD170127/3  pulse>DTMF  V3")
    t.SetPosition(P(24.5, 33.0 - 32.0 + 0.0) if False else P(24.0, 0.0 + 33.2 - 33.2 + 0.0))
    t.SetLayer(pcbnew.B_SilkS)
    t.SetMirrored(True)
    t.SetTextSize(pcbnew.VECTOR2I(pcbnew.FromMM(1.0), pcbnew.FromMM(1.0)))
    t.SetTextThickness(pcbnew.FromMM(0.15))
    t.SetPosition(P(24.5, 17.0))
    board.Add(t)

    # jack labels on the bottom silkscreen, beside each jack's pins
    for txt, (x, y) in (("DTMF PHONE", (9.0, 30.6)), ("FXS / LINE", (9.0, 3.4)), ("ROTARY", (40.0, 26.2))):
        lt = pcbnew.PCB_TEXT(board)
        lt.SetText(txt)
        lt.SetLayer(pcbnew.B_SilkS)
        lt.SetMirrored(True)
        lt.SetTextSize(pcbnew.VECTOR2I(pcbnew.FromMM(0.9), pcbnew.FromMM(0.9)))
        lt.SetTextThickness(pcbnew.FromMM(0.14))
        lt.SetPosition(P(x, y))
        board.Add(lt)

    board.Save(PCB)
    write_project()
    print("wrote", PCB)


def write_project():
    pro = os.path.join(HERE, "BRD170127_V3.kicad_pro")
    classes = [{
        "name": "Default", "clearance": 0.2, "track_width": 0.25, "via_diameter": 0.6, "via_drill": 0.3,
        "diff_pair_gap": 0.25, "diff_pair_width": 0.2, "diff_pair_via_gap": 0.25,
        "microvia_diameter": 0.3, "microvia_drill": 0.1, "line_style": 0, "priority": 2147483647,
        "pcb_color": "rgba(0, 0, 0, 0.000)", "schematic_color": "rgba(0, 0, 0, 0.000)",
        "wire_width": 6, "bus_width": 12,
    }, {
        "name": "Line", "clearance": 0.25, "track_width": 0.5, "via_diameter": 0.8, "via_drill": 0.4,
        "diff_pair_gap": 0.25, "diff_pair_width": 0.2, "diff_pair_via_gap": 0.25,
        "microvia_diameter": 0.3, "microvia_drill": 0.1, "line_style": 0, "priority": 0,
        "pcb_color": "rgba(0, 0, 0, 0.000)", "schematic_color": "rgba(0, 0, 0, 0.000)",
        "wire_width": 6, "bus_width": 12,
    }]
    data = {
        "board": {"design_settings": {"rules": {
            "min_clearance": 0.2, "min_track_width": 0.2, "min_via_diameter": 0.6, "min_through_hole_diameter": 0.3,
            "min_copper_edge_clearance": 0.3, "min_hole_clearance": 0.25, "min_hole_to_hole": 0.25,
            "min_silk_clearance": 0.0, "min_text_height": 0.8, "min_text_thickness": 0.08}}},
        "meta": {"filename": "BRD170127_V3.kicad_pro", "version": 3},
        "net_settings": {
            "classes": classes,
            "meta": {"version": 4},
            "netclass_patterns": [{"netclass": "Line", "pattern": n} for n in NET_CLASSES["Line"]["nets"]],
        },
        "schematic": {"legacy_lib_dir": "", "legacy_lib_list": []},
    }
    json.dump(data, open(pro, "w"), indent=2)
    for fn, body in (("fp-lib-table", '(fp_lib_table\n  (version 7)\n  (lib (name "BRD170127")(type "KiCad")(uri "${KIPRJMOD}/BRD170127.pretty")(options "")(descr "project footprints"))\n)\n'),
                     ("sym-lib-table", '(sym_lib_table\n  (version 7)\n  (lib (name "BRD170127")(type "KiCad")(uri "${KIPRJMOD}/BRD170127.kicad_sym")(options "")(descr "project symbols"))\n)\n')):
        open(os.path.join(HERE, fn), "w").write(body)


if __name__ == "__main__":
    main()
