#!/usr/bin/env python3
"""PIC18F4550 bootloader uploader.

Target: PIC18F4550, external 20 MHz crystal
UART: 115200 8-N-1 fixed baud
CP2102: TXD -> PIC RC7/RX (pin 26), RXD <- PIC RC6/TX (pin 25)

PIC18F4550 program Flash is erased in 64-byte blocks and programmed in 32-byte blocks.
The application area is 0x1000..0x7FFF. Intel HEX configuration-word
records at 0x300000..0x300007 are ignored.
"""
from __future__ import annotations
import argparse
import time
from pathlib import Path
import serial
from serial.tools import list_ports

BAUD = 115200
SYNC = 0x55
RESP_SYNC = 0xAA
CMD_HELLO = 0x01
CMD_ERASE = 0x02
CMD_WRITE = 0x03
CMD_READ = 0x04
CMD_RUN = 0x05
STATUS_OK = 0x00
APP_BASE = 0x1000
FLASH_END = 0x8000
ROW_SIZE = 64
CONFIG_START = 0x300000
CONFIG_END = 0x300007
CP210X_VID = 0x10C4
CP210X_PIDS = {0xEA60, 0xEA70, 0xEA71, 0xEA7A}

class BootloaderError(RuntimeError):
    pass

def checksum(values: bytes | bytearray) -> int:
    return sum(values) & 0xFF

def read_exact(ser, n: int, deadline: float) -> bytes:
    out = bytearray()
    while len(out) < n and time.monotonic() < deadline:
        b = ser.read(n - len(out))
        if b:
            out.extend(b)
    if len(out) != n:
        raise BootloaderError(f"timeout waiting for {n} response byte(s)")
    return bytes(out)

def read_response(ser, timeout=2.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        b = ser.read(1)
        if b and b[0] == RESP_SYNC:
            break
    else:
        raise BootloaderError("timeout waiting for response sync 0xAA")
    status, cmd, length = read_exact(ser, 3, deadline)
    payload = read_exact(ser, length, deadline)
    rxsum = read_exact(ser, 1, deadline)[0]
    calc = checksum(bytes([status, cmd, length]) + payload)
    if rxsum != calc:
        raise BootloaderError(f"response checksum mismatch: got {rxsum:02X}, expected {calc:02X}")
    if status != STATUS_OK:
        raise BootloaderError(f"bootloader rejected command 0x{cmd:02X} (status {status:02X})")
    return cmd, payload

def send_frame(ser, cmd: int, payload=b"", timeout=2.0, expect_response=True):
    payload = bytes(payload)
    if len(payload) > 255:
        raise BootloaderError("payload too large")
    header = bytes([SYNC, cmd, len(payload)])
    frame = header + payload + bytes([checksum(header[1:] + payload)])
    ser.write(frame)
    ser.flush()

    # CMD_RUN transfers execution to the application immediately.
    # The bootloader may therefore disappear before it can send a reply.
    if not expect_response:
        return None

    return read_response(ser, timeout)

def pulse_auto_reset(ser):
    """Reset PIC using the DTR-HIGH + RTS-LOW detector circuit.

    With the CP2102/pyserial polarity used by the test circuit:
      dtr=False -> physical DTR HIGH
      rts=False -> physical RTS HIGH
      rts=True  -> physical RTS LOW

    The reset circuit uses DTR HIGH + RTS LOW to turn Q1 on and pull
    MCLR low. The 2 x 1 uF base/emitter capacitors make this relatively
    slow, so RTS LOW is held for 400 ms for a reliable reset.
    """
    try:
        # Safe idle state: physical DTR HIGH, physical RTS HIGH.
        ser.dtr = False
        ser.rts = False
        time.sleep(0.10)

        # Trigger state: physical DTR HIGH + physical RTS LOW.
        ser.rts = True
        time.sleep(0.40)

        # Release reset. Q1 turns off and R4 pulls MCLR HIGH.
        ser.rts = False
        time.sleep(0.30)

        # Keep both control lines in their normal idle state.
    except serial.SerialException as e:
        raise BootloaderError(f"could not control CP2102 DTR/RTS: {e}")

def wait_for_text(ser, text: bytes, timeout=6.0):
    deadline = time.monotonic() + timeout
    buf = bytearray()
    while time.monotonic() < deadline:
        b = ser.read(1)
        if b:
            buf.extend(b)
            if text in buf:
                return True
    return False

def parse_hex(path: Path) -> dict[int, int]:
    memory: dict[int, int] = {}
    upper = 0
    segment = 0
    eof = False
    ignored_config = 0
    for line_no, raw in enumerate(path.read_text(encoding="ascii").splitlines(), 1):
        line = raw.strip()
        if not line:
            continue
        if not line.startswith(":"):
            raise BootloaderError(f"line {line_no}: missing ':'")
        try:
            rec = bytes.fromhex(line[1:])
        except ValueError:
            raise BootloaderError(f"line {line_no}: invalid Intel HEX")
        if len(rec) < 5 or len(rec) != rec[0] + 5 or (sum(rec) & 0xFF):
            raise BootloaderError(f"line {line_no}: invalid/checksum Intel HEX record")
        count, ah, al, typ = rec[:4]
        data = rec[4:4 + count]
        addr = (ah << 8) | al
        if typ == 0x00:
            base = upper + segment
            for i, b in enumerate(data):
                a = base + addr + i
                if CONFIG_START <= a <= CONFIG_END:
                    ignored_config += 1
                    continue
                if a < APP_BASE or a >= FLASH_END:
                    raise BootloaderError(
                        f"HEX contains data outside application area: 0x{a:06X}; "
                        f"allowed program memory is 0x{APP_BASE:04X}..0x{FLASH_END - 1:04X}"
                    )
                old = memory.get(a)
                if old is not None and old != b:
                    raise BootloaderError(f"overlapping HEX data at 0x{a:04X}")
                memory[a] = b
        elif typ == 0x01:
            eof = True
            break
        elif typ == 0x02:
            if count != 2:
                raise BootloaderError(f"line {line_no}: bad type-02 record")
            segment = int.from_bytes(data, "big") << 4
            upper = 0
        elif typ == 0x04:
            if count != 2:
                raise BootloaderError(f"line {line_no}: bad type-04 record")
            upper = int.from_bytes(data, "big") << 16
            segment = 0
        elif typ in (0x03, 0x05):
            pass
        else:
            raise BootloaderError(f"line {line_no}: unsupported Intel HEX record type 0x{typ:02X}")
    if not eof:
        raise BootloaderError("HEX has no EOF record")
    if not memory:
        raise BootloaderError("HEX contains no application program bytes")
    return memory, ignored_config

def make_rows(memory: dict[int, int]) -> dict[int, bytes]:
    rows: dict[int, bytearray] = {}
    for address, value in memory.items():
        start = address & ~(ROW_SIZE - 1)
        rows.setdefault(start, bytearray([0xFF] * ROW_SIZE))[address - start] = value
    return {a: bytes(v) for a, v in rows.items()}

def validate_rows(rows: dict[int, bytes]):
    for address in rows:
        if address < APP_BASE or address + ROW_SIZE > FLASH_END:
            raise BootloaderError(f"internal row outside application area: 0x{address:04X}")
        if address & (ROW_SIZE - 1):
            raise BootloaderError(f"internal row is not 64-byte aligned: 0x{address:04X}")

def main():
    ap = argparse.ArgumentParser(description="PIC18F4550 bootloader uploader: 64-byte erase / 32-byte program")
    ap.add_argument("hexfile", nargs="?")
    ap.add_argument("--port", help="COM port, e.g. COM6")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--no-reset", action="store_true", help="do not perform CP2102 DTR/RTS auto-reset")
    ap.add_argument("--dummy-test", action="store_true", help="send ASCII hi and expect hello host")
    args = ap.parse_args()

    if args.list:
        for p in list_ports.comports():
            print(f"{p.device}: {p.description} VID={p.vid!s} PID={p.pid!s}")
        return 0
    if not args.hexfile and not args.dummy_test:
        ap.error("hexfile is required unless --dummy-test is used")

    port = args.port
    if not port:
        ports = [p.device for p in list_ports.comports() if p.vid == CP210X_VID and p.pid in CP210X_PIDS]
        if len(ports) == 1:
            port = ports[0]
        elif not ports:
            raise SystemExit("ERROR: no CP2102 serial port found; use --port COMx")
        else:
            raise SystemExit(f"ERROR: multiple CP2102 ports found: {', '.join(ports)}; use --port")

    try:
        ser_cm = serial.Serial(port, BAUD, timeout=0.05, write_timeout=2, dsrdtr=False, rtscts=False)
    except serial.SerialException as e:
        if 'Access is denied' in str(e) or 'PermissionError' in str(e):
            raise SystemExit(f"ERROR: {port} is busy. Close MPLAB/Serial Monitor and try again.")
        raise SystemExit(f"ERROR: cannot open {port}: {e}")

    with ser_cm as ser:
        ser.reset_input_buffer()
        print(f"Baud:             {BAUD} 8-N-1")
        print(f"Serial port:      {port}")
        if args.no_reset:
            print("Reset:            not requested")
        else:
            print("Auto-reset:       DTR HIGH + RTS LOW")
            pulse_auto_reset(ser)

        print("Waiting for 'ENTER BOOT MODE'...")
        print("If auto-reset did not work, press the PIC RESET button now.")
        if not wait_for_text(ser, b"ENTER BOOT MODE", timeout=15.0):
            raise SystemExit("ERROR: did not receive ENTER BOOT MODE. Auto-reset failed or bootloader is not running.")
        print("Bootloader banner: OK")

        if args.dummy_test:
            ser.write(b"hi")
            ser.flush()
            if wait_for_text(ser, b"hello host", timeout=1.0):
                print("Dummy UART test: OK (hi -> hello host)")
                return 0
            raise SystemExit("ERROR: bootloader banner worked but dummy hi -> hello host failed")

        path = Path(args.hexfile)
        if not path.exists():
            raise SystemExit(f"ERROR: file not found: {path}")
        memory, ignored = parse_hex(path)
        rows = make_rows(memory)
        validate_rows(rows)
        addresses = sorted(rows)
        print(f"HEX bytes:        {len(memory)}")
        print(f"Ignored config:   {ignored} byte(s) at 0x300000..0x300007")
        print(f"Erase rows:       {len(rows)} x 64 bytes")
        print(f"Application data: 0x{min(memory):04X}..0x{max(memory):04X}")

        # HELLO is deliberately retried during the 1-second boot window.
        last = None
        for _ in range(12):
            try:
                cmd, payload = send_frame(ser, CMD_HELLO, b"", timeout=0.8)
                if cmd == CMD_HELLO:
                    print("Bootloader handshake: OK")
                    break
            except Exception as e:
                last = e
            time.sleep(0.10)
        else:
            raise SystemExit(f"ERROR: bootloader handshake failed: {last}")

        print("Erasing application...")
        erased = set()
        for a in addresses:
            erase = a & ~(ROW_SIZE - 1)
            if erase in erased:
                continue
            send_frame(ser, CMD_ERASE, bytes([erase & 0xFF, (erase >> 8) & 0xFF]), timeout=2.0)
            erased.add(erase)
        print(f"Erase complete:   {len(erased)} row(s)")

        print("Writing application (32-byte PIC18F4550 programming blocks)...")
        total_writes = len(addresses) * 2
        write_no = 0
        for a in addresses:
            data = rows[a]
            for half in (0, 32):
                write_addr = a + half
                chunk = data[half:half + 32]
                payload = bytes([write_addr & 0xFF, (write_addr >> 8) & 0xFF]) + chunk
                send_frame(ser, CMD_WRITE, payload, timeout=2.0)
                time.sleep(0.002)
                write_no += 1
                print(f"  {write_no:3d}/{total_writes}  0x{write_addr:04X} (32 bytes)")

        print("Verifying application...")
        for i, a in enumerate(addresses, 1):
            _, got = send_frame(ser, CMD_READ, bytes([a & 0xFF, (a >> 8) & 0xFF]), timeout=2.0)
            expected = rows[a]
            if got != expected:
                for j, (x, y) in enumerate(zip(got, expected)):
                    if x != y:
                        raise SystemExit(f"ERROR: verify failed at 0x{a+j:04X}: PIC={x:02X}, HEX={y:02X}")
                raise SystemExit(f"ERROR: verify length mismatch at 0x{a:04X}")
        print("Verification:     OK")

        print("Starting application at 0x1000...")
        # Do not wait for a response: CMD_RUN immediately leaves the
        # bootloader and transfers execution to the application.
        send_frame(ser, CMD_RUN, b"", timeout=1.0, expect_response=False)
        time.sleep(0.10)
        print("Upload successful.")
    return 0

if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except BootloaderError as e:
        raise SystemExit(f"ERROR: {e}")
