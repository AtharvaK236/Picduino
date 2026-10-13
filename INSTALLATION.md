# Installation and setup

These instructions describe the current experimental Arduino IDE 2.x platform files. The exact package layout and build environment may need adjustment as PICduino develops.

## Requirements

- Arduino IDE 2.x (the supplied `platform.txt` says Arduino IDE 2.3.x).
- Microchip XC8 compiler compatible with PIC18F4550.
- A PIC18F4550 device-family pack (DFP) containing the device headers and linker support.
- Python 3.
- Python package `pyserial`.
- PIC18F4550 hardware with a compatible bootloader already programmed, unless you have a separate ICSP programming setup.
- USB-to-UART adapter and reset wiring compatible with the uploader.

## 1. Install Python dependency

Open a terminal and run:

```sh
python -m pip install -r "path/to/Board Files/picduino/PICduino/tools/requirements.txt"
```

The current requirements file specifies `pyserial>=3.5`.

## 2. Place the platform files

The supplied `Board Files/Readme.txt` says to place the board files under:

```text
%LOCALAPPDATA%\Arduino15\packages\
```

and says the final folder should look like:

```text
%LOCALAPPDATA%\Arduino15\packages\picduino\PICduino
```

That is the path documented in the included text file. Arduino IDE platform discovery can be sensitive to directory layout; if the board does not appear, check the current Arduino IDE 2.x platform installation requirements and make sure the `boards.txt`, `platform.txt`, `cores`, `variants`, `libraries`, and `tools` folders are under the directory Arduino actually discovers as a platform.

Restart Arduino IDE after installing or changing platform files.

## 3. Install/configure XC8 and the device pack

The build scripts call XC8 and try to locate a PIC18 device pack. If automatic detection fails, use the options supported by `picduino_compiler.py` to provide the compiler or DFP location. See the examples and help output:

```sh
python "path/to/picduino_compiler.py" --help
```

The exact compiler and DFP command-line options can vary by script version; use the tool's own `--help` output as the source of truth.

## 4. Select the board

In Arduino IDE, look for **PICduino 18F4550**. Select the serial port associated with your USB-to-UART adapter.

Before building, resolve the clock mismatch noted in `ALPHA_STATUS.md`: the current board definition says 48 MHz, while the core default and supplied bootloader documentation target 20 MHz.

## 5. Build an example

Open one of these sketches from the installed platform's examples:

- `PICduinoExamples/Blink/Blink.ino`
- `PICduinoExamples/UART_LED_Reply/UART_LED_Reply.ino`

Build first, without uploading. Save the complete compiler output if it fails.

## 6. Upload

The current platform's upload recipe invokes `pic18f4550_uploader.py` and passes the selected serial port plus the generated HEX file. The uploader expects a compatible PIC18F4550 serial bootloader and the matching UART/reset behavior.

Read `BOOTLOADER.md` before uploading. Do not use a random HEX file or assume every PIC18F4550 bootloader uses the same protocol.

## Troubleshooting

- **Board not listed:** check platform folder layout, restart IDE, and verify `boards.txt` is present.
- **Compiler not found:** install XC8 and ensure `xc8-cc` is on PATH, or use the script's supported explicit compiler option.
- **Device pack not found:** install the PIC18F4550 DFP or pass the correct pack path using the compiler wrapper's supported option.
- **`pyserial` import error:** run `python -m pip install pyserial`.
- **Uploader timeout:** verify COM port, TX/RX cross-connect, shared ground, baud compatibility, reset wiring, and that a compatible bootloader is already programmed.
- **Application does not start:** verify that the HEX is built for the `0x1000` application offset and does not overwrite the bootloader region.
