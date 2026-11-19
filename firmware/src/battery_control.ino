/*
battery_control: rev-V3 coin-cell backup + on-hook detection for the pulse-to-
tone converter. Additions to pulse-dtmf-converter.ino (Copyright (C) 2018
Christoph Tack). Combined with that GPL program these additions are likewise:

    Copyright (C) 2025  (this project)
    GNU General Public License v3 or later. See ../LICENSE.

----------------------------------------------------------------------------
HARDWARE (see ../../hardware_v3/README.md and the KiCad schematic,
../../hardware_v3/kicad/fab/BRD170127_V3_schematic.pdf):
  BT1 (CR1632) feeds VDD through Q3 (DMG2301L P-MOS switch) and D6 (BAT46WH
  reverse-charge block), OR'd with the loop supply through D5. BATT_EN (PB2)
  drives Q3's gate: LOW = cell armed, HIGH or not driven = cell off (R18 1M
  pulls the gate to BATT+). NO new sense hardware: the existing pulse/loop sense
  on PB0 is reused.

WHY ON-HOOK MUST BE DETECTED IN SOFTWARE:
  Once the cell is armed it holds VDD up through every loop-open, so hanging up
  does NOT remove the MCU's power - the MCU keeps running on the cell. It must
  therefore *detect* on-hook and disarm, or the cell drains.

HOW (reuse the existing loop sense + tune a threshold):
  The RotaryDialer already debounces the loop-sense pin; loop OPEN reads LOW
  (rd.lineIsOpen()==true). A rotary *pulse* break is short (~60-100 ms); a
  *hang-up* holds the loop open indefinitely; between pulses / digits / pauses
  the loop is CLOSED. So: time how long the loop has been continuously open, and
  if it exceeds a threshold well beyond the longest break, it's on-hook.

  ON-HOOK threshold 250 ms  >> ~70-100 ms pulse break  (and > a ~100 ms
  hook-flash, so a register-recall flash is NOT mistaken for on-hook). Tune up
  for slow/worn dials; it only needs to sit between "longest break" and "hang-up".
----------------------------------------------------------------------------

Pin: on the ATtiny85 every pin is already used - PB0 (pin 5) is the loop/pulse
sense (passed to RotaryDialer as PIN_DTMF_OUT, despite the name), PB1 (pin 6) is
the DTMF PWM output OC1A, PB3/PB4 are the 8 MHz crystal and PB5 is RESET. The
only free pin is PB2 (pin 7), which the original sketch reads as the optional
"mode select" jumper (never fitted on the board). The rev-V3 PCB therefore wires
BATT_EN to PB2 (pin 7) - see ../../hardware_v3/kicad.
In pins.h:       const int PIN_BATT_EN = 2;   // ATtiny85 PB2 / pin 7 (rev-V3 PCB)
and in setup():  drop the PIN_MODE_SELECT read and fix the mode in code, e.g.
                 mode = 1;   // 1 = gather all digits, then send (the old default)
Add to rotarydialer.h: the one-line lineIsOpen() accessor (already added here).

Add these globals + helpers to pulse-dtmf-converter.ino:

    #include "pins.h"
    const unsigned long ONHOOK_MS = 250;        // sustained loop-open => on-hook
    unsigned long lastLoopClosedMs = 0;

    static inline void cellArm()     { digitalWrite(PIN_BATT_EN, LOW);  }
    static inline void cellRelease() { digitalWrite(PIN_BATT_EN, HIGH); }

in setup(), AFTER rd.init():

    pinMode(PIN_BATT_EN, OUTPUT);
    cellRelease();                 // default off
    cellArm();                     // off-hook on loop power now; back up VDD
    lastLoopClosedMs = millis();

at the END of loop(), AFTER rd.update():

    if (!rd.lineIsOpen()) {
        lastLoopClosedMs = millis();            // loop closed -> not on-hook
    } else if (millis() - lastLoopClosedMs > ONHOOK_MS) {
        cellRelease();                          // hung up: drop the cell...
        // ...VDD now collapses (loop open + cell off) and the MCU powers down;
        //    the next off-hook re-powers and reboots it.
    }

BATTERY LIFE with this scheme:
  The cell only sources current when VDD falls below its own voltage. The
  ngspice simulation (../../hardware_v3/spice) shows C1 (470 uF) keeps VDD at
  4.4 V or more through dialing on every line down to 3 mA, so the cell does
  not source current during dialing at all. Only the ~250 ms on-hook detection
  window per call draws on it (~1 mA for 0.25 s). On-hook drain with Q3 off is
  about 0.03 uA, so a CR1632 (~120 mAh) is shelf-life-limited. The ONLY way to
  kill it fast is a detection failure that leaves the cell armed while on-hook
  (0.93 mA in SPICE -> flat in ~5 days). So VERIFY ON HARDWARE that the loop
  sense goes (and stays) open on the hook switch, not just on the dial contacts.
*/
