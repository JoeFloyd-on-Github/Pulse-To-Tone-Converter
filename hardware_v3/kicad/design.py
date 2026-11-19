"""
design.py - single source of truth for BRD170127 rev V3 (pulse-to-tone converter
with CR1632 backup). gen_pcb.py and gen_sch.py both build from this file, so the
schematic, the PCB and the SPICE model (../spice/conv_v3.sub) share reference
designators and nets.

Coordinates are in mm on the 49 x 34 mm rev-R2 outline, origin at the board's
bottom-left corner, Y up (as in the R2 Gerbers). gen_pcb.py flips Y for KiCad.
"""

BOARD_W, BOARD_H = 49.0, 34.0

# ref: (value, footprint, symbol, mpn, lcsc, {pad: net}, (x, y, rot_deg))
# rot is KiCad rotation (counter-clockwise, degrees) of the footprint.
R = "Resistor_SMD:R_0805_2012Metric"
C = "Capacitor_SMD:C_0805_2012Metric"
D = "Diode_SMD:D_SOD-123"
SOT23 = "Package_TO_SOT_SMD:SOT-23"
SOT89 = "Package_TO_SOT_SMD:SOT-89-3"

PARTS = {
    # ---------------------------------------------------------------- line side
    "CN1": ("RJ11 to DTMF phone", "BRD170127:RJ11_6P6C_BRD170127", "Connector:6P6C",
            "6P6C side-entry, as rev R2", "", {"3": "LINE_B", "4": "LINE_T"}, (3.0, 25.0, 0)),
    "CN2": ("RJ11 to FXS", "BRD170127:RJ11_6P6C_BRD170127", "Connector:6P6C",
            "6P6C side-entry, as rev R2", "", {"3": "LINE_B", "4": "LINE_T"}, (3.0, 9.0, 0)),
    "CN3": ("RJ11 to rotary phone", "BRD170127:RJ11_6P6C_BRD170127", "Connector:6P6C",
            "6P6C side-entry, as rev R2", "", {"3": "LINE_A", "4": "LINE_T"}, (46.0, 17.0, 180)),
    "D1": ("BAT46WH", D, "Device:D_Schottky", "BAT46WH", "C127989", {"1": "VCC", "2": "LINE_A"}, (13.2, 23.0, 90)),
    "D2": ("BAT46WH", D, "Device:D_Schottky", "BAT46WH", "C127989", {"1": "VCC", "2": "LINE_B"}, (15.6, 23.0, 90)),
    "D3": ("BAT46WH", D, "Device:D_Schottky", "BAT46WH", "C127989", {"1": "LINE_A", "2": "VEE"}, (13.2, 11.0, 90)),
    "D4": ("BAT46WH", D, "Device:D_Schottky", "BAT46WH", "C127989", {"1": "LINE_B", "2": "VEE"}, (15.6, 11.0, 90)),
    # ------------------------------------------------- upper shunt, VCC = 5.0 V
    "U2": ("TLV431A", SOT23, "BRD170127:TLV431_SOT23_RKA", "TLV431ASN1T1G", "C56765",
           {"1": "U2_REF", "2": "U2_K", "3": "GND"}, (24.0, 27.6, 0)),
    "Q2": ("BCX53-16", SOT89, "Transistor_BJT:BCX53", "BCX53-16", "",
           {"1": "Q2_B", "2": "GND", "3": "VCC"}, (19.6, 28.6, 0)),
    "R1": ("100k", R, "Device:R", "", "", {"1": "VCC", "2": "U2_REF"}, (27.6, 31.4, 0)),
    "R6": ("33k", R, "Device:R", "", "", {"1": "U2_REF", "2": "GND"}, (27.6, 27.6, 90)),
    "R15": ("470", R, "Device:R", "", "", {"1": "VCC", "2": "Q2_B"}, (19.0, 32.0, 0)),
    "R16": ("220", R, "Device:R", "", "", {"1": "Q2_B", "2": "U2_K"}, (23.0, 32.0, 0)),
    "C12": ("1n", C, "Device:C", "", "", {"1": "U2_K", "2": "U2_REF"}, (24.0, 24.6, 0)),
    "C10": ("100n", C, "Device:C", "", "", {"1": "VCC", "2": "GND"}, (19.0, 24.6, 0)),
    "R17": ("22k", R, "Device:R", "", "", {"1": "VCC", "2": "GND"}, (19.0, 22.4, 0)),
    # ------------------------------------- lower shunt / line modulator (U3)
    "U3": ("TLV431A", SOT23, "BRD170127:TLV431_SOT23_RKA", "TLV431ASN1T1G", "C56765",
           {"1": "U3_REF", "2": "U3_K", "3": "VEE"}, (24.0, 6.4, 0)),
    "Q4": ("BCX53-16", SOT89, "Transistor_BJT:BCX53", "BCX53-16", "",
           {"1": "Q4_B", "2": "VEE", "3": "GND"}, (19.6, 5.4, 0)),
    "R5": ("47k", R, "Device:R", "", "", {"1": "GND", "2": "U3_REF"}, (27.6, 9.4, 0)),
    "R7": ("10k", R, "Device:R", "", "", {"1": "U3_REF", "2": "VEE"}, (27.6, 6.4, 90)),
    "R19": ("470", R, "Device:R", "", "", {"1": "GND", "2": "Q4_B"}, (19.0, 2.0, 0)),
    "R20": ("220", R, "Device:R", "", "", {"1": "Q4_B", "2": "U3_K"}, (23.0, 2.0, 0)),
    "C11": ("10n", C, "Device:C", "", "", {"1": "GND", "2": "VEE"}, (19.0, 9.4, 0)),
    # ------------------------------------------ DTMF filter + modulator Q1
    "Q1": ("BC856B", SOT23, "Transistor_BJT:BC856", "BC856B", "C181144",
           {"1": "Q1_B", "2": "Q1_E", "3": "U3_REF"}, (30.6, 11.0, 0)),
    "R2": ("39k", R, "Device:R", "", "", {"1": "VDD", "2": "Q1_E"}, (34.0, 11.0, 90)),
    "R12": ("10k", R, "Device:R", "", "", {"1": "PB1", "2": "FLT1"}, (34.0, 17.2, 90)),
    "R13": ("160k", R, "Device:R", "", "", {"1": "FLT1", "2": "GND"}, (36.2, 14.6, 90)),
    "C8": ("4.7n", C, "Device:C", "", "", {"1": "FLT1", "2": "GND"}, (31.8, 17.2, 90)),
    "R10": ("10k", R, "Device:R", "", "", {"1": "FLT1", "2": "Q1_B"}, (29.6, 17.2, 90)),
    "C9": ("4.7n", C, "Device:C", "", "", {"1": "Q1_B", "2": "GND"}, (27.4, 13.6, 90)),
    # ---------------------------------------------------------- pulse sense
    "R3": ("56k", R, "Device:R", "", "", {"1": "VCC", "2": "SENSE"}, (22.0, 20.0, 0)),
    "C5": ("100n", C, "Device:C", "", "", {"1": "SENSE", "2": "GND"}, (22.0, 17.8, 0)),
    "R14": ("10k", R, "Device:R", "", "", {"1": "SENSE", "2": "PB0"}, (25.8, 17.8, 0)),
    # ------------------------------------------------------------------- MCU
    "U1": ("ATtiny85V-10SU", "Package_SO:SOIC-8_5.3x5.3mm_P1.27mm", "MCU_Microchip_ATtiny:ATtiny85V-10S",
           "ATTINY85V-10SU", "C152192",
           {"1": "RESET", "2": "XTAL1", "3": "XTAL2", "4": "GND", "5": "PB0", "6": "PB1",
            "7": "BATT_EN", "8": "VDD"}, (31.0, 23.0, 0)),
    "R11": ("10k", R, "Device:R", "", "", {"1": "VDD", "2": "RESET"}, (36.8, 21.0, 90)),
    "C4": ("100n", C, "Device:C", "", "", {"1": "VDD", "2": "GND"}, (35.2, 26.4, 0)),
    "C7": ("100n", C, "Device:C", "", "", {"1": "VDD", "2": "GND"}, (23.6, 14.6, 0)),
    "X1": ("8MHz", "Crystal:Crystal_SMD_HC49-SD", "Device:Crystal", "HC-49/US SMD 8.000 MHz 18 pF", "C108703",
           {"1": "XTAL1", "2": "XTAL2"}, (31.0, 30.6, 0)),
    "C2": ("18p", C, "Device:C", "", "", {"1": "XTAL1", "2": "GND"}, (24.8, 21.0, 90)),
    "C3": ("18p", C, "Device:C", "", "", {"1": "XTAL2", "2": "GND"}, (36.8, 28.6, 90)),
    # ------------------------------------------- supply, reservoir, coin cell
    "D5": ("BAT46WH", D, "Device:D_Schottky", "BAT46WH", "C127989", {"1": "VDD", "2": "VCC"}, (37.0, 31.8, 0)),
    "C1": ("470u 6.3V", "Capacitor_THT:CP_Radial_D8.0mm_P3.50mm", "Device:C_Polarized",
           "470uF 6.3V radial 8 mm, 3.5 mm pitch", "", {"1": "VDD", "2": "GND"}, (44.0, 27.25, 90)),
    "Q3": ("DMG2301L", SOT23, "Transistor_FET:DMG2301L", "DMG2301L-7", "",
           {"1": "BATT_EN", "2": "BATT_P", "3": "CELL"}, (40.4, 6.0, 0)),
    "R18": ("1M", R, "Device:R", "", "", {"1": "BATT_EN", "2": "BATT_P"}, (37.0, 4.0, 90)),
    "D6": ("BAT46WH", D, "Device:D_Schottky", "BAT46WH", "C127989", {"1": "VDD", "2": "CELL"}, (37.0, 8.4, 90)),
    "BT1": ("CR1632 (off-board holder)", "BRD170127:CELL_LEADS_2PAD", "Device:Battery_Cell",
            "CR1632 + wire-lead holder", "", {"1": "BATT_P", "2": "GND"}, (44.0, 3.2, 0)),
    # ------------------------------------------------------------ test points
    "TP1": ("VCC", "TestPoint:TestPoint_Pad_D1.5mm", "Connector:TestPoint", "", "", {"1": "VCC"}, (16.8, 26.8, 0)),
    "TP2": ("VDD", "TestPoint:TestPoint_Pad_D1.5mm", "Connector:TestPoint", "", "", {"1": "VDD"}, (38.6, 25.0, 0)),
    "TP3": ("BATT+", "TestPoint:TestPoint_Pad_D1.5mm", "Connector:TestPoint", "", "", {"1": "BATT_P"}, (40.0, 2.0, 0)),
    "TP4": ("BATT_EN", "TestPoint:TestPoint_Pad_D1.5mm", "Connector:TestPoint", "", "", {"1": "BATT_EN"}, (37.0, 1.6, 0)),
    "TP5": ("CELL", "TestPoint:TestPoint_Pad_D1.5mm", "Connector:TestPoint", "", "", {"1": "CELL"}, (40.4, 9.0, 0)),
    "TP6": ("GND", "TestPoint:TestPoint_Pad_D1.5mm", "Connector:TestPoint", "", "", {"1": "GND"}, (16.8, 17.0, 0)),
    # ------------------------------------------------------------- fiducials
    "FID1": ("Fiducial", "Fiducial:Fiducial_1mm_Mask2mm", "Mechanical:Fiducial", "", "", {}, (11.6, 32.4, 0)),
    "FID2": ("Fiducial", "Fiducial:Fiducial_1mm_Mask2mm", "Mechanical:Fiducial", "", "", {}, (11.6, 1.6, 0)),
}

# Final placement (overrides the positions in PARTS). (x, y, KiCad rotation)
PLACE = {
    # bridge (next to the line jacks)
    "D1": (12.3, 19.6, 90), "D2": (14.9, 19.6, 90), "D3": (12.3, 13.4, 90), "D4": (14.9, 13.4, 90),
    # upper shunt, top-left
    "Q2": (13.9, 30.9, 0), "U2": (19.0, 31.8, 0), "R1": (22.6, 31.6, 90), "R15": (13.6, 26.9, 0),
    "R16": (19.0, 28.7, 0), "R6": (22.6, 27.2, 0), "C12": (19.0, 26.4, 0), "C10": (13.6, 24.6, 0),
    "R17": (22.6, 24.9, 0), "TP1": (16.8, 23.4, 0),
    # lower shunt / modulator, bottom-left
    "Q4": (13.9, 3.1, 0), "U3": (19.0, 2.2, 0), "R7": (22.6, 2.4, 90), "R19": (13.6, 7.1, 0),
    "R20": (19.0, 5.3, 0), "R5": (22.6, 6.8, 0), "C11": (19.0, 7.6, 0), "TP6": (15.6, 9.6, 0),
    # pulse sense + loop->VDD diode
    "R3": (20.0, 21.6, 0), "C5": (20.0, 19.2, 0), "R14": (20.0, 16.8, 0), "D5": (23.2, 19.0, 90),
    # MCU + crystal
    "U1": (30.0, 22.4, 0), "X1": (31.4, 30.8, 0), "C2": (26.8, 26.6, 0), "C3": (34.0, 26.6, 0),
    "R11": (30.4, 26.6, 0), "C4": (36.4, 23.4, 90), "C7": (36.4, 19.6, 90), "TP2": (36.8, 15.4, 0),
    # DTMF filter + V-to-I
    "R12": (33.4, 16.6, 90), "R13": (31.2, 16.6, 90), "C8": (29.0, 16.6, 90), "R10": (26.8, 16.6, 90),
    "C9": (26.1, 12.6, 0), "Q1": (30.0, 12.4, 0), "R2": (33.6, 12.4, 90),
    # reservoir (rev-R2 position) and coin-cell backup, right side
    "C1": (44.0, 27.55, 90), "BT1": (44.8, 2.0, 0), "Q3": (41.4, 6.6, 0), "R18": (45.6, 5.6, 0),
    "TP3": (45.6, 8.0, 0), "D6": (36.0, 7.0, 0), "TP5": (38.0, 3.6, 0), "TP4": (34.6, 3.6, 0),
    # fiducials
    "FID1": (12.4, 9.6, 0), "FID2": (31.0, 2.0, 0),
}

# Keep-out zones on the top side (Gerber coords): the RJ11 bodies and C1.
KEEPOUTS = [
    ("CN1/CN2 bodies", (0.0, 0.0, 10.6, 34.0)),
    ("CN3 body", (38.4, 8.4, 49.0, 25.6)),
]

NET_CLASSES = {
    # loop-current carrying nets get wide copper
    "Line": {"nets": ["LINE_A", "LINE_B", "LINE_T", "VCC", "VEE", "GND"], "track": 0.5, "clearance": 0.25},
    "Default": {"track": 0.25, "clearance": 0.2},
}


def nets():
    s = set()
    for p in PARTS.values():
        s.update(p[5].values())
    return sorted(s)
