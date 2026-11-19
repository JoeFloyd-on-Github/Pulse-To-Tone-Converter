#!/usr/bin/env python3
"""
route.py - route BRD170127_V3.kicad_pcb and finish it for fabrication.

    python3 gen_pcb.py                 # placement + nets (unrouted)
    python3 route.py                   # import the saved route (route/board.ses), finish
    FREEROUTING_JAR=.../freerouting-2.5.0.jar python3 route.py --autoroute   # route again

--autoroute: export Specctra DSN (pours removed), run Freerouting headless with
analytics disabled and all Java network traffic pointed at a dead proxy, keep
the session in route/board.ses.
Finishing (always): import route/board.ses, widen Freerouting's 0.187 mm
neck-downs to the 0.2 mm minimum, refill the GND pours, place reference labels.
"""
import os, subprocess, sys
import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
PCB = os.path.join(HERE, "BRD170127_V3.kicad_pcb")
RDIR = os.path.join(HERE, "route")
SES = os.path.join(RDIR, "board.ses")
DSN = os.path.join(RDIR, "board.dsn")


def autoroute():
    jar = os.environ.get("FREEROUTING_JAR")
    if not jar or not os.path.exists(jar):
        sys.exit("set FREEROUTING_JAR to freerouting-2.5.0.jar")
    os.makedirs(RDIR, exist_ok=True)
    b = pcbnew.LoadBoard(PCB)
    for z in [z for z in b.Zones()]:
        b.Remove(z)
    if not pcbnew.ExportSpecctraDSN(b, DSN):
        sys.exit("DSN export failed")
    env = dict(os.environ, FREEROUTING__USAGE_AND_DIAGNOSTIC_DATA__DISABLE_ANALYTICS="true",
               FREEROUTING__GUI__ENABLED="false")
    cmd = ["java", "-Dhttp.proxyHost=127.0.0.1", "-Dhttp.proxyPort=9",
           "-Dhttps.proxyHost=127.0.0.1", "-Dhttps.proxyPort=9",
           "-jar", jar, "-de", DSN, "-do", SES, "-mp", os.environ.get("ROUTE_PASSES", "100"),
           "--gui.enabled=false", "--usage_and_diagnostic_data.disable_analytics=true"]
    r = subprocess.run(cmd, env=env, cwd=RDIR, capture_output=True, text=True, timeout=1800)
    open(os.path.join(RDIR, "freerouting.log"), "w").write(r.stdout + r.stderr)
    if not os.path.exists(SES):
        sys.exit("Freerouting produced no session; see route/freerouting.log")


def finish():
    b = pcbnew.LoadBoard(PCB)
    if any(True for _ in b.Tracks()):
        sys.exit("board already has tracks; run gen_pcb.py first")
    if not pcbnew.ImportSpecctraSES(b, SES):
        sys.exit("SES import failed")
    narrow = 0
    for t in b.Tracks():
        if t.GetClass() == "PCB_TRACK" and t.GetWidth() < pcbnew.FromMM(0.2):
            t.SetWidth(pcbnew.FromMM(0.2)); narrow += 1
    pcbnew.ZONE_FILLER(b).Fill(b.Zones())
    b.Save(PCB)
    print(f"imported {sum(1 for _ in b.Tracks())} track/via items, widened {narrow}")
    subprocess.run([sys.executable, os.path.join(HERE, "place_silk.py")], check=True)


if __name__ == "__main__":
    if "--autoroute" in sys.argv:
        autoroute()
    finish()
