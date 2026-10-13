# PICduino — Arduino-style development for PIC18F4550 (Alpha)

PICduino is an experimental project that aims to make it easier to write small programs for the **Microchip PIC18F4550** using an Arduino-style sketch workflow.

This repository currently contains:
- An early Arduino IDE platform definition.
- A small PICduino core with basic GPIO, delay, and UART functions.
- Two example sketches: `Blink` and `UART_LED_Reply`.
- Python build/upload tools.
- A PIC18F4550 bootloader HEX file.

> **Status: Alpha / early development.** This project is incomplete and may change. It is not yet a drop-in replacement for the Arduino platform, and it does not support the full Arduino language, core, or library ecosystem. Some features are placeholders. Use it for experimentation, not safety-critical or production projects.

## Important: Bootloader uses pin 33 of pic18f4550 so either dont connect anything on it or connect an LED with an resistor.

## Current features (Alpha)

The following features are present in the supplied files; some are experimental and have not been independently verified across all hardware setups.

- **Arduino-style sketches:** includes `setup()` / `loop()` examples and a small translator for a limited subset of sketch syntax.
- **Basic GPIO API:** `pinMode()`, `digitalWrite()`, and `digitalRead()` are provided by the minimal core.
- **Delay helper:** `delay()` is available for simple timing. Timing depends on the configured clock.
- **Basic UART / Serial API:** a limited `Serial` interface supports common operations used by the examples, including `begin`, `print`, `println`, `available`, and `read`.
- **Blink example:** a first test for GPIO and timing.
- **UART LED Reply example:** listens for `hi`, replies with `hello host`, and changes the LED state.
- **Python build helper:** translates the supported sketch subset and invokes the XC8 toolchain.
- **Serial bootloader uploader:** uploads an application HEX over UART, using the bootloader protocol, with erase/write/read-back verification.
- **Automatic reset attempt during upload:** the supplied uploader toggles DTR/RTS lines before waiting for the bootloader banner. This is **reset-circuit dependent**; it only works automatically if the adapter and board reset wiring/polarity match the uploader's assumptions.
- **Bootloader timeout and run command:** the supplied bootloader behavior is documented to enter application mode after its boot window, or when the uploader sends the run command. Check the exact bootloader version installed on your board.
- **Application memory offset:** the uploader expects applications to start at `0x1000`; the application HEX must match this memory layout.

### Features not complete or not guaranteed

- Full Arduino language and library compatibility.
- A working `millis()` timebase; in this Alpha core it is currently a placeholder.
- Universal automatic reset across arbitrary USB-to-UART adapters.
- Automatic detection/correction of the board clock.
- A general-purpose C++ compiler; the sketch translator supports only a subset.
- External programmer integration through the `programmers.txt` placeholder.
- Compatibility with arbitrary PIC18F4550 bootloaders.

## Repository layout

```text
Picduino/
├── README.md
├── ALPHA_STATUS.md
├── INSTALLATION.md
├── EXAMPLES.md
├── BOOTLOADER.md
├── Board Files/
│   ├── Readme.txt
│   └── picduino/PICduino/
│       ├── boards.txt
│       ├── platform.txt
│       ├── programmers.txt
│       ├── cores/picduino/
│       ├── variants/pic18f4550/
│       ├── libraries/PICduinoExamples/
│       └── tools/
├── Bootloader/
│   └── PIC18F4550_Bootloader.hex
└── circuit_image.png
```

## Hardware currently targeted

- **MCU:** PIC18F4550
- **Clock used by the supplied bootloader and core:** external 20 MHz crystal
- **UART:** hardware UART1 on RC6/TX and RC7/RX
- **USB-to-UART adapter:** a CP2102-style adapter is described by the uploader
- **Bootloader application start:** `0x1000`

The current board definition in `boards.txt` says `48 MHz`, while the supplied core defaults to `20 MHz` and the supplied bootloader is documented for a 20 MHz crystal. **This mismatch must be resolved before relying on timing-sensitive sketches.** Do not assume the 48 MHz setting is correct.

## Quick start

1. Read [Alpha status and limitations](ALPHA_STATUS.md).
2. Read [Installation and setup](INSTALLATION.md).
3. Check the board's clock setting and wiring before building or uploading.
4. Try the `Blink` example first.
5. Try `UART_LED_Reply` after serial wiring and baud-rate behavior are confirmed.
6. Read [Bootloader notes](BOOTLOADER.md) before using the bootloader HEX or uploader.

The build scripts invoke Microchip XC8. Install a compatible XC8 compiler and the PIC18F4550 device-family pack (DFP), and install the Python dependency listed in `Board Files/picduino/PICduino/tools/requirements.txt`.

## Important limitations

- The sketch translator supports a **small, documented subset** of Arduino-style sketches, not arbitrary C++.
- `millis()` is currently a placeholder and does not advance.
- The logical pin map D0–D7 to RB0–RB7 is marked as provisional in the source and should be checked against the actual board schematic.
- The normal upload path uses the serial bootloader. `programmers.txt` explicitly does not provide an external-programmer integration.
- The supplied bootloader HEX is a prebuilt file; its source is not included in this repository archive.
- Build and upload success can depend on the exact compiler, device pack, board clock, reset circuit, serial adapter, and firmware version.

## Contributing / bug reports

Please include:
- PIC18F4550 board and clock details.
- Arduino IDE version and operating system.
- XC8 version and installed device-family pack.
- The exact sketch being built.
- Full build or upload log.
- Whether the bootloader was already installed and how the reset circuit is wired.

Small, focused contributions are welcome. Please label untested features as untested and avoid describing this Alpha as fully Arduino-compatible.

## License

No license file was present in the supplied archive. Until a license is added, do not assume this repository is open source for unrestricted reuse. Add a license that reflects the author's intent before publishing it publicly.
