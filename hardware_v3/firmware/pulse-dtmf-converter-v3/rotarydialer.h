#ifndef ROTARYDIALER_H
#define ROTARYDIALER_H

#include "Arduino.h"
#include "Bounce2.h"
#include "singletimer.h"

class RotaryDialer
{
public:
    RotaryDialer(byte pulsePin);
    void init();
    void update();
    bool available();
    byte readPulses();
    // rev-V3 addition: current debounced loop state, reused for on-hook detect.
    // Loop OPEN (break / on-hook) reads LOW; loop CLOSED (off-hook) reads HIGH.
    bool lineIsOpen() { return _debouncer.read() == LOW; }
private:
    byte _pulsePin;
    Bounce _debouncer;
    SingleTimer _pulseTimeout;
    byte _pulseCounter;
    bool _dataReady;
};

#endif // ROTARYDIALER_H
