/*
pulse-dtmf-converter-v3: pulse-dialing to DTMF converter, firmware for
BRD170127 rev V3 (CR1632 coin-cell backup).

Based on pulse-dtmf-converter by Christoph Tack (upstream commit 593e746,
2023-02-20, https://github.com/LieBtrau/pulse-dtmf-converter):
    Copyright (C) 2018  Christoph Tack
Rev-V3 changes (see ../README.md for the full description):
    Copyright (C) 2026  BRD170127 rev V3 project

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
*/

/*
Changes from upstream 593e746:
  * PB2 (pin 7) is BATT_EN, the coin-cell switch, instead of the mode-select
    input. The send mode is now the compile-time constant SEND_MODE.
  * Coin-cell control: the cell is connected while the loop is closed and
    released once the loop has been open for ONHOOK_MS (a hang-up). Released
    means the pin is an input (high impedance), so the R18 pull-up holds Q3
    off and no current flows through R18 in either direction.
  * The pulse-sense pin is named PIN_LOOP_SENSE (upstream: PIN_DTMF_OUT).
  * rotarydialer.h: lineIsOpen() accessor for the debounced loop state.
Without the cell parts fitted (BT1, Q3, D6, R18), PB2 drives nothing and the
converter works exactly as with them.
*/

#include <avr/power.h>
#include <avr/sleep.h>
#include "dtmfgenerator.h"
#include "rotarydialer.h"
#include "pins.h"

// ---------------------------------------------------------------- settings
// SEND_MODE 1: collect the whole number, send it DTMF_DELAY_AFTER_LAST_DIALED_DIGIT_ms
//              after the last digit (the only mode R2 boards ever ran).
// SEND_MODE 0: send each digit as soon as it has been dialed.
const int SEND_MODE = 1;
const bool REVERSE_DIAL_MODE = false;                   // true for reverse-dial systems (e.g. New Zealand)
const int DTMF_DELAY_AFTER_LAST_DIALED_DIGIT_ms = 1200; // R2 boards (2019 firmware) used 3000
const int MAX_NR_OF_DIALED_DIGITS = 15;                 // longer numbers are truncated
const unsigned long ONHOOK_MS = 250;                    // loop open this long = hung up
                                                        // (dial break ~60 ms, hook-flash ~100 ms)

DtmfGenerator dtmf;
RotaryDialer rd(PIN_LOOP_SENSE);

unsigned long lastUpdate = 0;
byte pulsesCtr = 0;
byte pulsesBuffer[MAX_NR_OF_DIALED_DIGITS];

// ---------------------------------------------------------------- coin cell
bool cellArmed = false;
unsigned long lastLoopClosedMs = 0;

static void cellArm()
{
    digitalWrite(PIN_BATT_EN, LOW);   // set the level first...
    pinMode(PIN_BATT_EN, OUTPUT);     // ...then drive it: Q3 gate low, cell connected
    cellArmed = true;
}

static void cellRelease()
{
    pinMode(PIN_BATT_EN, INPUT);      // high impedance, no internal pull-up:
    digitalWrite(PIN_BATT_EN, LOW);   // R18 pulls the gate to BATT+, Q3 off
    cellArmed = false;
}

// Called after every rd.update(). The cell follows the hook state:
// loop closed -> armed; loop open for longer than ONHOOK_MS -> released.
static void updateCell()
{
    if (!rd.lineIsOpen())
    {
        lastLoopClosedMs = millis();
        if (!cellArmed)
        {
            cellArm();                // off-hook (again): back up VDD
        }
    }
    else if (cellArmed && (millis() - lastLoopClosedMs > ONHOOK_MS))
    {
        cellRelease();                // hung up: VDD now runs down and the MCU stops
    }
}

// ---------------------------------------------------------------- main
void setup()
{
    cellRelease();                    // cell off until the loop state is known
    reducePower();
    dtmf.init();
    rd.init();
    pulsesCtr = 0;
    lastLoopClosedMs = millis();
}

void pulsesToDtmf(byte nrOfPulses)
{
    byte dtmfDigit;
    if (REVERSE_DIAL_MODE)
    {
        dtmfDigit = 10 - nrOfPulses;
    }
    else
    {
        dtmfDigit = nrOfPulses == 10 ? 0 : nrOfPulses;
    }
    dtmf.generateTone('0' + dtmfDigit);
    delay(80);
    dtmf.stopTone();
}

void loop()
{
    sleepNow();
    rd.update();
    updateCell();
    if (SEND_MODE == 0)
    {
        if (rd.available())
        {
            pulsesToDtmf(rd.readPulses());
        }
    }
    else
    {
        if (rd.available() && pulsesCtr < MAX_NR_OF_DIALED_DIGITS)
        {
            pulsesBuffer[pulsesCtr++] = rd.readPulses();
            lastUpdate = millis() + DTMF_DELAY_AFTER_LAST_DIALED_DIGIT_ms;
        }
        if ((pulsesCtr > 0) && (millis() > lastUpdate))
        {
            for (byte k = 0; k < pulsesCtr; k++)
            {
                pulsesToDtmf(pulsesBuffer[k]);
                delay(80);
            }
            pulsesCtr = 0;
        }
    }
}

void reducePower()
{
#ifdef ARDUINO_AVR_ATTINYX5
    power_usi_disable();
    bitSet(ACSR, ACD);                // disable analog comparator
#endif
    power_adc_disable();
}

void sleepNow()
{
    set_sleep_mode(SLEEP_MODE_IDLE);
    sleep_enable();
    sleep_mode();
    sleep_disable();
}
