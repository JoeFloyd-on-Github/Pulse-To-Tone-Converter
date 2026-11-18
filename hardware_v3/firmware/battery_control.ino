/*
 * battery_control.ino - rev V3 coin-cell backup control for the pulse-to-tone
 * converter (ATtiny85). Drop these additions into LieBtrau's
 * pulse-dtmf-converter.ino (recover the source from the upstream GitHub repo;
 * only the HEX is in this project folder).
 *
 * Hardware (see ../schematic.svg):
 *   Q_batt = P-channel MOSFET low-leakage switch between the CR1632 and VDD,
 *            with a series D_rev Schottky for reverse-charge protection.
 *   BATT_EN (an MCU GPIO) drives the Q_batt gate through a pull-up to BATT+:
 *            drive LOW  -> P-MOS ON  (cell armed)
 *            drive HIGH -> P-MOS OFF (cell disconnected)
 *   On-hook the MCU is unpowered, the pull-up holds the gate at BATT+, so the
 *   P-MOS is OFF and the cell draws ~0 (shelf-life-limited life).
 *
 * Why "arm, then let the hardware OR do the rest": with Q_batt armed, the cell
 * only actually sources current during the ~70 ms loop-open gaps (D_rev is
 * reverse-biased whenever the loop holds VDD above the cell). So arming for the
 * whole off-hook period costs nothing extra, and the MCU never browns out.
 */

#include <avr/sleep.h>

// ---- pins ----
static const uint8_t PIN_BATT_EN = PB3;   // -> Q_batt gate (active LOW)
static const uint8_t PIN_VBAT_ADC = A1;   // optional: BATT+ via divider for low-batt check

// ---- cell switch helpers ----
static inline void cellArm()     { digitalWrite(PIN_BATT_EN, LOW);  }  // P-MOS ON
static inline void cellRelease() { digitalWrite(PIN_BATT_EN, HIGH); }  // P-MOS OFF

// ---- state ----
static bool     dialing       = false;
static uint32_t lastPulseMs   = 0;
static const uint16_t INTERDIGIT_MS = 1200;   // Patrick's ATA-friendly value

void batterySetup() {
  pinMode(PIN_BATT_EN, OUTPUT);
  cellRelease();                 // default OFF until we are sure we are off-hook
  // Enable BOD at 2.7 V via the ATtiny85V fuses (EXTENDED/HIGH fuse), not here.
  // Arm the cell once we are up and running on loop power (off-hook):
  cellArm();                     // from now on the cell silently backs up VDD
}

// Call from the pulse-dial edge handler (loop open = start of a break).
void onPulseEdge() {
  dialing = true;
  lastPulseMs = millis();
  // (cell is already armed from batterySetup(); nothing to do for power here)
  // ... existing pulse counting ...
}

// Call once per main-loop iteration.
void batteryLoopHousekeeping() {
  // While dialing, keep the MCU in IDLE sleep between the 1 ms timer wakes so the
  // cell sees ~1 mA (not full active current) during the gaps.
  if (dialing) {
    set_sleep_mode(SLEEP_MODE_IDLE);
    sleep_mode();                 // wakes on Timer0 / pin-change
  }

  // Digit/number finished: generate DTMF on LOOP power (loop is closed/steady
  // now, so the ~4 mA tone current does NOT come from the cell), then idle.
  if (dialing && (millis() - lastPulseMs > INTERDIGIT_MS)) {
    dialing = false;
    sendDtmfForNumber();          // existing DDS routine, runs on loop power
    // cell stays armed but sources nothing (D_rev reverse-biased on loop power)
  }
}

// Optional: flag a tired cell. Measure BATT+ under the gap load; replace when
// its open-circuit voltage falls below ~2.9 V (see the simulation).
bool coinCellLow() {
  uint16_t mv = (uint32_t)analogRead(PIN_VBAT_ADC) * VREF_MV * DIV_RATIO / 1023;
  return (mv < 2900);
}

/* Integration:
 *   setup()  -> call batterySetup() after the normal init (crystal, Bounce2, DDS)
 *   loop()   -> call batteryLoopHousekeeping() each iteration
 *   pulse ISR/handler -> call onPulseEdge() on each loop-break edge
 * On-hook the MCU simply loses power; the gate pull-up turns Q_batt off, so no
 * explicit power-down is required (but calling cellRelease() on a detected
 * on-hook is harmless belt-and-suspenders).
 */
