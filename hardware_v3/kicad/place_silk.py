#!/usr/bin/env python3
"""
place_silk.py - move every reference designator to a spot on the silkscreen
where it does not touch a pad, another footprint's silk, another reference or
the board edge. References that fit nowhere are moved to F.Fab (they still show
on the assembly drawing). Run after routing.
"""
import os
import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
PCB = os.path.join(HERE, "BRD170127_V3.kicad_pcb")
MM = pcbnew.FromMM


def inflate(bb, d):
    b = pcbnew.BOX2I(bb.GetPosition(), bb.GetSize())
    b.Inflate(MM(d))
    return b


def main():
    b = pcbnew.LoadBoard(PCB)
    edge = b.GetBoardEdgesBoundingBox()
    edge_in = inflate(edge, -0.35)

    pads = [inflate(p.GetBoundingBox(), 0.12) for p in b.GetPads()]
    silk = []
    for fp in b.GetFootprints():
        for g in fp.GraphicalItems():
            if g.GetLayer() == pcbnew.F_SilkS and g.GetClass() != "PCB_TEXT":
                silk.append((fp.GetReference(), inflate(g.GetBoundingBox(), 0.1)))
    placed = []
    moved_to_fab = []

    fps = sorted(b.GetFootprints(), key=lambda f: f.GetBoundingBox(False).GetArea())
    for fp in fps:
        ref = fp.Reference()
        if fp.GetReference().startswith("FID"):
            ref.SetLayer(pcbnew.F_Fab)
            continue
        ref.SetLayer(pcbnew.F_SilkS)
        ref.SetTextSize(pcbnew.VECTOR2I(MM(0.8), MM(0.8)))
        ref.SetTextThickness(MM(0.13))
        ref.SetKeepUpright(True)
        bb = fp.GetCourtyard(pcbnew.F_CrtYd).BBox() if fp.GetCourtyard(pcbnew.F_CrtYd).OutlineCount() else fp.GetBoundingBox(False)
        cx, cy = bb.GetCenter().x, bb.GetCenter().y
        hw, hh = bb.GetWidth() // 2, bb.GetHeight() // 2
        cands = []
        for size in (0.8,):
            for dx, dy, ang in ((0, -1, 0), (0, 1, 0), (-1, 0, 90), (1, 0, 90), (-1, 0, 0), (1, 0, 0),
                                (0, -1, 90), (0, 1, 90), (-1, -1, 0), (1, -1, 0), (-1, 1, 0), (1, 1, 0)):
                for extra in (0.45, 0.8, 1.2, 1.7):
                    off = MM(extra)
                    cands.append((cx + dx * (hw + off), cy + dy * (hh + off), ang, size))
                    if dy == 0:      # also slide along the side
                        for sl in (-0.35, 0.35):
                            cands.append((cx + dx * (hw + off), cy + sl * 2 * hh, ang, size))
                    if dx == 0:
                        for sl in (-0.35, 0.35):
                            cands.append((cx + sl * 2 * hw, cy + dy * (hh + off), ang, size))
        ok = False
        for (x, y, ang, size) in cands:
            ref.SetTextSize(pcbnew.VECTOR2I(MM(size), MM(size)))
            ref.SetTextThickness(MM(0.13 if size >= 0.8 else 0.12))
            ref.SetPosition(pcbnew.VECTOR2I(int(x), int(y)))
            ref.SetTextAngleDegrees(ang)
            tb = inflate(ref.GetBoundingBox(), 0.05)
            if not edge_in.Contains(tb):
                continue
            if any(tb.Intersects(p) for p in pads):
                continue
            if any(tb.Intersects(s) for (r, s) in silk):
                continue
            if any(tb.Intersects(p) for p in placed):
                continue
            placed.append(tb)
            ok = True
            break
        if not ok:
            ref.SetLayer(pcbnew.F_Fab)
            moved_to_fab.append(fp.GetReference())
    b.Save(PCB)
    print("references on F.Fab only:", ", ".join(sorted(moved_to_fab)) or "none")


if __name__ == "__main__":
    main()
