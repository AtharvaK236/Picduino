# Alpha status and known limitations

PICduino is an **early experimental build**. The goal is to explore an Arduino-style workflow for PIC18F4550, not to claim full Arduino compatibility.

## What is included

- Board definition for PIC18F4550.
- A minimal core with `pinMode`, `digitalWrite`, `digitalRead`, `delay`, `millis`, and a small serial API.
- `Blink` and `UART_LED_Reply` example sketches.
- A Python sketch-build wrapper and a Python serial bootloader uploader.
- A prebuilt bootloader HEX file.

## Known gaps and cautions

1. **Clock setting mismatch:** `boards.txt` declares `picduino18f4550.build.f_cpu=48000000L`, while the core defaults to `F_CPU=20000000UL`; the supplied bootloader notes also target an external 20 MHz crystal. Confirm the real hardware and make these settings consistent before using timing-sensitive functions.
2. **`millis()` is not implemented yet:** the core returns a counter that is never incremented. Do not rely on it for timing.
3. **Limited sketch translation:** `picduino_build.py` explicitly rejects several C++ constructs and only translates a small set of `Serial` methods. This is not a general C++ compiler or a full Arduino library build system.
4. **Pin map is provisional:** D0–D7 map to RB0–RB7 in the current variant header. The source asks users to verify this against the actual board schematic.
5. **Bootloader source not included:** this archive includes only `Bootloader/PIC18F4550_Bootloader.hex`. Keep the matching source and its known working uploader together when distributing a tested firmware release.
6. **External programmer integration is not supplied:** `programmers.txt` says the entry is a placeholder; the standard Upload action uses the serial bootloader.
7. **Hardware validation is setup-dependent:** reset circuitry, UART adapter polarity, crystal frequency, fuse/configuration words, and the bootloader version all matter.

## Suggested Alpha test checklist

- [ ] Confirm the board's actual oscillator frequency.
- [ ] Make `build.f_cpu`, core `F_CPU`, bootloader baud settings, and hardware agree.
- [ ] Confirm D0–D7 mapping with the board schematic.
- [ ] Build `Blink` and check LED pin/polarity.
- [ ] Test serial receive/transmit with `UART_LED_Reply`.
- [ ] Test a full upload, read-back verification, and application start.
- [ ] Power-cycle and reset the board, then repeat upload.
- [ ] Document the exact compiler and device-pack versions used.

Features should be marked stable only after repeatable tests on the intended hardware.
