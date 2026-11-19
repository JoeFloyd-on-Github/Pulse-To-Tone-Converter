#pragma once

#include "Arduino.h"

// ATtiny85 pin map for BRD170127 rev V3 (see ../README.md).
//   pin 1  PB5  RESET (R11 10k pull-up)
//   pin 2  PB3  crystal X1 (8 MHz)
//   pin 3  PB4  crystal X1
//   pin 5  PB0  loop/pulse sense (VCC -> R3/C5 -> R14): LOW = loop open
//   pin 6  PB1  DTMF PWM output OC1A (hard-coded in dtmfgenerator.cpp)
//   pin 7  PB2  BATT_EN: LOW = coin cell connected; input (high-Z) = cell off
//               (R18 1M pulls Q3's gate to BATT+). On the R2 board this was the
//               unused "mode select" input.
const int PIN_LOOP_SENSE = 0;   // upstream name: PIN_DTMF_OUT (it was always the pulse input)
const int PIN_BATT_EN    = 2;   // upstream: PIN_MODE_SELECT
