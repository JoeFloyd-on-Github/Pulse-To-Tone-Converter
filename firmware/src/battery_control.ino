/*
battery_control: rev-V3 coin-cell backup switch control for the pulse-to-tone
converter. Additions to pulse-dtmf-converter.ino (Copyright (C) 2018 Christoph
Tack). As these additions are combined with that GPL program, they are likewise:

    Copyright (C) 2025  (this project)
    This program is free software: you can redistribute it and/or modify it
    under the terms of the GNU General Public License as published by the Free
    Software Foundation, either version 3 of the License, or (at your option)
    any later version. See ../LICENSE.

----------------------------------------------------------------------------
Hardware (see ../../hardware_v3/schematic.svg):
  A CR1632 coin cell feeds VDD through Q_batt (low-leakage P-MOS switch) and
  D_rev (reverse-charge Schottky), OR'd with the loop supply. BATT_EN drives the
  Q_batt gate through a pull-up to BATT+:
      BATT_EN LOW  -> P-MOS ON  (cell armed)
      BATT_EN HIGH -> P-MOS OFF (cell disconnected; on-hook default via pull-up)

Integration with the upstream sketch is tiny, because it already idle-sleeps:
  - the main loop starts with sleepNow() (SLEEP_MODE_IDLE), so during the pulse
    gaps the MCU is already at its low (~1 mA) current - exactly what keeps the
    coin-cell droop small. Nothing to change there.
  - all we add is: pick a FREE pin for BATT_EN, and arm the cell once we are up
    and running on loop power (i.e. off-hook). The hardware OR then lets the cell
    source current only during the ~70 ms loop-open gaps.

Pin choice: PIN_DTMF_OUT = PB0 and PIN_MODE_SELECT = PB2 are taken (see pins.h),
and PB5 is RESET. Use a pin not used by the DTMF R-ladder/filter - verify against
the board; PB1 (pin 6) is a typical free choice. Add to pins.h:
      const int PIN_BATT_EN = 1;   // ATtiny85 PB1 / pin 6
----------------------------------------------------------------------------

Add to pulse-dtmf-converter.ino:

    #include "pins.h"
    static inline void cellArm()     { digitalWrite(PIN_BATT_EN, LOW);  }
    static inline void cellRelease() { digitalWrite(PIN_BATT_EN, HIGH); }

in setup(), AFTER rd.init():

    pinMode(PIN_BATT_EN, OUTPUT);
    cellRelease();      // default off
    cellArm();          // off-hook on loop power now; back up VDD from here on

Nothing else is required: the existing sleepNow() at the top of loop() keeps the
gap current low, DTMF is generated on loop power (loop closed, so the cell sources
nothing then - D_rev is reverse-biased), and on-hook the MCU loses power and the
gate pull-up turns Q_batt off (~0 cell drain -> shelf-life-limited life).

Optional - low-battery flag. NOTE: the upstream reducePower() calls
power_adc_disable(), so re-enable the ADC before using analogRead():

    // bool coinCellLow() {   // measure BATT+ via a divider on a spare ADC pin
    //     power_adc_enable(); ADCSRA |= _BV(ADEN);
    //     uint16_t mv = (uint32_t)analogRead(PIN_VBAT) * VREF_MV * DIV / 1023;
    //     return mv < 2900;  // CR1632: replace below ~2.9 V OCV (see simulation)
    // }
*/
