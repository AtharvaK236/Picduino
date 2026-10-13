#!/usr/bin/env python3
"""
PICduino XC8 compiler wrapper for PIC18F4550.

Examples:

    python picduino_compiler.py -c ".\\led_blinking.c" -codeoffset 0x1000

    python picduino_compiler.py -c ".\\led_blinking.c" -codeoffset 0x1000 -romrange 1000-7FFF

Optional explicit DFP:

    python picduino_compiler.py -c ".\\led_blinking.c" -codeoffset 0x1000 ^
        -mdfp "C:\\Program Files\\Microchip\\MPLABX\\v6.35\\packs\\Microchip\\PIC18Fxxxx_DFP\\1.7.171"

The -mdfp argument may be either:
    ...\\PIC18Fxxxx_DFP\\1.7.171
or:
    ...\\PIC18Fxxxx_DFP\\1.7.171\\xc8

The script automatically converts the first form to the second form.
"""

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path


DEFAULT_DEVICE = "18F4550"
DFP_NAME = "PIC18Fxxxx_DFP"


def parse_hex(value):
    value = value.strip().lower()

    if value.startswith("0x"):
        value = value[2:]
    elif value.endswith("h"):
        value = value[:-1]

    if not value:
        raise argparse.ArgumentTypeError("empty hexadecimal value")

    try:
        return int(value, 16)
    except ValueError:
        raise argparse.ArgumentTypeError(
            "invalid hexadecimal value: " + value
        )


def parse_romrange(value):
    if "-" not in value:
        raise argparse.ArgumentTypeError(
            "ROM range must be START-END, for example 1000-7FFF"
        )

    start_text, end_text = value.split("-", 1)

    start = parse_hex(start_text)
    end = parse_hex(end_text)

    if end < start:
        raise argparse.ArgumentTypeError(
            "ROM range END must be greater than or equal to START"
        )

    return start, end


def find_xc8():
    """Find xc8-cc.exe from PATH or normal Microchip installation paths."""

    found = shutil.which("xc8-cc")
    if found:
        return Path(found).resolve()

    roots = []

    for variable in ("ProgramFiles", "ProgramFiles(x86)"):
        value = os.environ.get(variable)
        if value:
            roots.append(Path(value) / "Microchip")

    candidates = []

    for root in roots:
        if not root.exists():
            continue

        try:
            candidates.extend(
                root.glob("xc8/v*/bin/xc8-cc.exe")
            )
        except OSError:
            pass

    if not candidates:
        return None

    candidates.sort(
        key=lambda p: str(p).lower(),
        reverse=True
    )

    return candidates[0].resolve()


def find_dfp_roots():
    """
    Search for PIC18Fxxxx_DFP installations.

    MPLAB X can install packs under:
      %USERPROFILE%\\.mchp_packs\\Microchip
      %ProgramFiles%\\Microchip\\MPLABX\\<version>\\packs\\Microchip
    """

    candidates = []

    # User pack location.
    user_root = (
        Path.home()
        / ".mchp_packs"
        / "Microchip"
        / DFP_NAME
    )

    if user_root.exists():
        try:
            for version in user_root.iterdir():
                if version.is_dir():
                    candidates.append(version)
        except OSError:
            pass

    # MPLAB X system pack locations.
    for variable in ("ProgramFiles", "ProgramFiles(x86)"):
        value = os.environ.get(variable)

        if not value:
            continue

        mplab_root = Path(value) / "Microchip" / "MPLABX"

        if not mplab_root.exists():
            continue

        try:
            for ide_version in mplab_root.glob("v*"):
                pack_root = (
                    ide_version
                    / "packs"
                    / "Microchip"
                    / DFP_NAME
                )

                if pack_root.exists():
                    for version in pack_root.iterdir():
                        if version.is_dir():
                            candidates.append(version)
        except OSError:
            pass

    # Remove duplicates.
    unique = []
    seen = set()

    for path in candidates:
        try:
            resolved = path.resolve()
        except OSError:
            resolved = path

        key = str(resolved).lower()

        if key not in seen:
            seen.add(key)
            unique.append(resolved)

    # Prefer the highest-looking version.
    unique.sort(
        key=lambda p: str(p).lower(),
        reverse=True
    )

    return unique


def get_xc8_dfp_path(path):
    """
    Convert a DFP root into the exact path required by XC8.

    IMPORTANT:
    XC8 documentation specifies the 'xc8' directory INSIDE the DFP
    for -mdfp.
    """

    path = Path(path).expanduser().resolve()

    if not path.exists():
        return None

    # User supplied ...\\PIC18Fxxxx_DFP\\1.7.171\\xc8
    if path.name.lower() == "xc8":
        xc8_dir = path
    else:
        # User supplied ...\\PIC18Fxxxx_DFP\\1.7.171
        xc8_dir = path / "xc8"

    if not xc8_dir.is_dir():
        return None

    return xc8_dir


def find_dfp():
    """Return the XC8 directory inside the best detected DFP."""

    for root in find_dfp_roots():
        xc8_dir = get_xc8_dfp_path(root)

        if xc8_dir is not None:
            return xc8_dir

    return None


def format_command(command):
    """Display a Windows-friendly version of the command."""

    result = []

    for item in command:
        item = str(item)

        if any(c in item for c in (" ", "\t")):
            result.append('"' + item + '"')
        else:
            result.append(item)

    return " ".join(result)


def find_hex(directory, stem):
    """Return only the HEX expected from this build; never reuse a stale HEX."""
    expected = directory / (stem + ".hex")
    return expected if expected.is_file() else None


def main():
    parser = argparse.ArgumentParser(
        description="PICduino PIC18F4550 XC8 compiler wrapper"
    )

    parser.add_argument(
        "-c",
        "--source",
        required=True,
        help="C source file"
    )

    parser.add_argument(
        "-codeoffset",
        type=parse_hex,
        default=0,
        help="Application code offset, e.g. 0x1000"
    )

    parser.add_argument(
        "-romrange",
        type=parse_romrange,
        default=None,
        help="Application ROM range, e.g. 1000-7FFF"
    )

    parser.add_argument(
        "-mdfp",
        "--mdfp",
        default=None,
        help="DFP root or DFP xc8 directory"
    )

    parser.add_argument(
        "--output-dir",
        default=None,
        help="Directory for ELF/HEX/MAP outputs (default: directory containing this script)"
    )

    parser.add_argument(
        "--xc8",
        default=None,
        help="Full path to xc8-cc.exe"
    )

    parser.add_argument(
        "--chip",
        default=DEFAULT_DEVICE,
        help="PIC device, default is 18F4550"
    )

    parser.add_argument(
        "-O",
        "--optimization",
        default=None,
        help="Optimization level, e.g. 1, 2 or 3"
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show command without compiling"
    )

    args = parser.parse_args()

    # ---------------------------------------------------------------
    # Source
    # ---------------------------------------------------------------

    source = Path(args.source).expanduser().resolve()

    if not source.exists():
        print("ERROR: source file does not exist:")
        print("  " + str(source))
        return 2

    # ---------------------------------------------------------------
    # Output paths
    # ---------------------------------------------------------------

    script_dir = Path(__file__).resolve().parent
    output_dir = Path(args.output_dir).expanduser().resolve() if args.output_dir else script_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    stem = source.stem

    elf_file = output_dir / (stem + ".elf")
    hex_file = output_dir / (stem + ".hex")
    map_file = output_dir / (stem + ".map")

    # ---------------------------------------------------------------
    # XC8
    # ---------------------------------------------------------------

    if args.xc8:
        xc8 = Path(args.xc8).expanduser().resolve()

        if not xc8.exists():
            print("ERROR: XC8 executable not found:")
            print("  " + str(xc8))
            return 3
    else:
        xc8 = find_xc8()

        if xc8 is None:
            print("ERROR: xc8-cc.exe was not found.")
            print()
            print("Use --xc8 to specify its full path.")
            return 3

    # ---------------------------------------------------------------
    # DFP
    # ---------------------------------------------------------------

    if args.mdfp:
        dfp = get_xc8_dfp_path(args.mdfp)

        if dfp is None:
            print("ERROR: invalid DFP path:")
            print("  " + str(Path(args.mdfp).expanduser().resolve()))
            print()
            print("The DFP must contain an 'xc8' directory.")
            return 4
    else:
        dfp = find_dfp()

        if dfp is None:
            print("ERROR: PIC18Fxxxx_DFP was not found.")
            print()
            print("Your XC8 version requires a DFP.")
            print()
            print("You can locate it with:")
            print(
                'Get-ChildItem "C:\\Program Files\\Microchip\\MPLABX" '
                '-Recurse -Directory -Filter "PIC18Fxxxx_DFP" '
                '-ErrorAction SilentlyContinue'
            )
            print()
            print("Then use:")
            print(
                '  -mdfp "C:\\...\\PIC18Fxxxx_DFP\\VERSION\\xc8"'
            )
            return 5

    # ---------------------------------------------------------------
    # Build XC8 command
    # ---------------------------------------------------------------

    command = [
        str(xc8),
        "-mcpu=" + args.chip,
        "-mdfp=" + str(dfp),
        "-mcodeoffset=0x" + format(args.codeoffset, "X"),
        "-Wl,-Map=" + str(map_file),
        "-o",
        str(elf_file),
    ]

    if args.romrange is not None:
        start, end = args.romrange

        command.append(
            "-mrom=0x" +
            format(start, "X") +
            "-0x" +
            format(end, "X")
        )

    if args.optimization:
        optimization = args.optimization

        if not optimization.startswith("-O"):
            optimization = "-O" + optimization

        command.append(optimization)

    command.append(str(source))

    # ---------------------------------------------------------------
    # Display
    # ---------------------------------------------------------------

    print("=" * 72)
    print("PICduino XC8 Compiler")
    print("=" * 72)
    print("Source      : " + str(source))
    print("CPU         : PIC" + args.chip)
    print("XC8         : " + str(xc8))
    print("DFP         : " + str(dfp))
    print(
        "Code offset : 0x" +
        format(args.codeoffset, "X")
    )

    if args.romrange is None:
        print("ROM range   : XC8 device default")
    else:
        start, end = args.romrange
        print(
            "ROM range   : 0x" +
            format(start, "X") +
            "-0x" +
            format(end, "X")
        )

    print("HEX output  : " + str(hex_file))
    print("MAP output  : " + str(map_file))
    print()
    print("XC8 command:")
    print(format_command(command))
    print()

    if args.dry_run:
        print("DRY RUN: XC8 was not executed.")
        return 0

    # ---------------------------------------------------------------
    # Compile
    # ---------------------------------------------------------------

    print("Compiling...")
    print("-" * 72)

    try:
        result = subprocess.run(
            command,
            cwd=str(output_dir),
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
    except OSError as error:
        print("ERROR: could not start XC8:")
        print(error)
        return 6

    print(result.stdout)

    if result.returncode != 0:
        print("-" * 72)
        print(
            "COMPILATION FAILED (exit code " +
            str(result.returncode) +
            ")"
        )
        return result.returncode

    # ---------------------------------------------------------------
    # HEX
    # ---------------------------------------------------------------

    generated_hex = find_hex(output_dir, stem)

    if generated_hex is None:
        print("-" * 72)
        print("XC8 finished but no HEX file was found.")
        return 7

    if generated_hex.resolve() != hex_file.resolve():
        try:
            if hex_file.exists():
                hex_file.unlink()

            generated_hex.replace(hex_file)
        except OSError:
            hex_file = generated_hex

    print("-" * 72)
    print("COMPILATION SUCCESSFUL")
    print()
    print("HEX : " + str(hex_file))
    print("MAP : " + str(map_file))
    print("ELF : " + str(elf_file))
    print("=" * 72)

    return 0


if __name__ == "__main__":
    sys.exit(main())
