# PIC18F4550 bootloader and uploader notes

This repository contains a prebuilt file at `Bootloader/PIC18F4550_Bootloader.hex`. The bootloader source is not included in this archive, so this document records only the intended setup and uploader behavior visible in the supplied tools.

## Target assumptions

The uploader source documents:
- PIC18F4550 with an external 20 MHz crystal.
- UART on RC7/RX (physical pin 26) and RC6/TX (physical pin 25).
- Nominal serial setting 115200 baud, 8 data bits, no parity, 1 stop bit.
- Application flash region `0x1000` through `0x7FFF`.
- 64-byte erase rows and 32-byte programming blocks.
- CP2102-style USB-to-UART adapter reset control using DTR/RTS.

The exact reset wiring and polarity matter. Follow the circuit used with the tested bootloader; do not assume arbitrary USB-to-UART adapters have the same control-line behavior.

## Upload flow

The Python uploader:
1. Opens the selected serial port.
2. Pulses DTR/RTS to reset the PIC using the documented reset circuit.
3. Waits for the `ENTER BOOT MODE` text.
4. Sends a binary HELLO command.
5. Erases 64-byte rows, writes 32-byte blocks, and reads back 64-byte blocks for verification.
6. Sends RUN so the PIC transfers execution to the application.

The binary protocol used by the supplied uploader has command IDs:
- `0x01` HELLO
- `0x02` ERASE
- `0x03` WRITE
- `0x04` READ
- `0x05` RUN

Host frames start with `0x55`; responses start with `0xAA`. Checksums are 8-bit sums. The uploader ignores Intel HEX configuration-word records at `0x300000..0x300007`.

## Safety notes

- Back up a known-working bootloader HEX and its matching source/uploader.
- Build applications with the bootloader's application offset (`0x1000`).
- Never flash a HEX built for a different memory layout without inspecting it first.
- Do not treat the bootloader HEX as interchangeable with every PIC18F4550 bootloader.
- If uploads fail, verify clock, serial wiring, reset circuit, COM port, bootloader compatibility, and HEX address range.


## Automatic reset behavior

The uploader attempts to reset the PIC automatically by toggling the serial adapter's DTR/RTS control lines before it waits for `ENTER BOOT MODE`. This is not a universal feature that works with every adapter or circuit: the board must have reset wiring compatible with the expected signal polarity and timing. If the bootloader banner never appears, check the reset circuit and adapter control lines, or reset the board manually into its bootloader window.

## Verification wording

The included uploader performs read-back verification by requesting flash data and comparing it with the firmware image. Whether automatic reset and the complete upload sequence work on a particular board depends on its installed bootloader, clock, wiring, adapter, and HEX memory layout.
