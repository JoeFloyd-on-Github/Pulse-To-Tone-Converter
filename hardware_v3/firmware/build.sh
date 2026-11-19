#!/bin/sh
# build.sh - build and (optionally) program the rev-V3 firmware with arduino-cli.
#
#   ./build.sh                  compile -> images/pulse-dtmf-converter-v3.hex
#   ./build.sh setup            install ATTinyCore 1.5.2 + Bounce2 (needs internet, once)
#   ./build.sh fuses  /dev/ttyACM0   write fuses through an Arduino-as-ISP (once per chip)
#   ./build.sh flash  /dev/ttyACM0   compile and write the flash through the Arduino-as-ISP
#
# See README.md for the wiring, the fuse values and what each step does.
set -eu
cd "$(dirname "$0")"

URL=http://drazzy.com/package_drazzy.com_index.json
FQBN='ATTinyCore:avr:attinyx5:chip=85,clock=8external,TimerClockSource=default,LTO=enable,millis=enabled,eesave=aenable,bod=2v7'
SKETCH=pulse-dtmf-converter-v3
PROGRAMMER=arduinoasisp

case "${1:-build}" in
setup)
    arduino-cli core update-index --additional-urls "$URL"
    arduino-cli core install ATTinyCore:avr@1.5.2 --additional-urls "$URL"
    arduino-cli lib install Bounce2@2.71.0
    ;;
build)
    arduino-cli compile -b "$FQBN" --warnings all --output-dir build "$SKETCH"
    cp "build/$SKETCH.ino.hex" "images/$SKETCH.hex"
    echo "wrote images/$SKETCH.hex"
    ;;
fuses)
    # "Burn Bootloader": chip erase + lfuse 0xFF, hfuse 0xD5, efuse 0xFF (no bootloader is installed)
    arduino-cli burn-bootloader -b "$FQBN" -p "${2:?serial port of the Arduino-as-ISP}" -P "$PROGRAMMER" --verify
    ;;
flash)
    arduino-cli compile -b "$FQBN" --output-dir build "$SKETCH"
    arduino-cli upload -b "$FQBN" -p "${2:?serial port of the Arduino-as-ISP}" -P "$PROGRAMMER" --input-dir build --verify
    ;;
*)
    echo "usage: $0 [setup|build|fuses PORT|flash PORT]" >&2
    exit 2
    ;;
esac
