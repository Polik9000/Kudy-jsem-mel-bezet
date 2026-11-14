"""Build an unsigned x64 MSIX from the existing PyInstaller onedir output.

The default publisher is deliberately a test identity. Set MSIX_PUBLISHER to the
exact Publisher value shown in Partner Center before creating a Store submission.
"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
TEMPLATE = Path(__file__).with_name("Package.appxmanifest.in")
TEST_PUBLISHER = "CN=KudyJsemMelBezet.TestOnly"
TEST_IDENTITY_NAME = "KudyJsemMelBezet.TestOnly"


def find_makeappx() -> Path:
    found = shutil.which("makeappx.exe") or shutil.which("makeappx")
    if found:
        return Path(found)
    kits = Path(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")) / "Windows Kits" / "10" / "bin"
    candidates = sorted(kits.glob("*/x64/MakeAppx.exe"), reverse=True)
    if candidates:
        return candidates[0]
    raise SystemExit("MakeAppx.exe nebyl nalezen. Nainstaluj Windows 10/11 SDK.")


def main() -> int:
    # GitHub-hosted Windows runners may default to cp1252; CI logs and Czech paths are UTF-8.
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, OSError):
            pass

    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True, help="PyInstaller onedir folder")
    parser.add_argument("--output", type=Path, required=True, help="Output .msix path")
    parser.add_argument("--version", required=True, help="Three-part app version, e.g. 0.1.0")
    parser.add_argument("--publisher", default=os.environ.get("MSIX_PUBLISHER") or TEST_PUBLISHER)
    parser.add_argument("--identity-name", default=os.environ.get("MSIX_IDENTITY_NAME") or TEST_IDENTITY_NAME)
    args = parser.parse_args()

    source = args.source.resolve()
    output = args.output.resolve()
    executable = source / "KudyJsemMelBezet.exe"
    if not executable.is_file():
        raise SystemExit(f"Chybí PyInstaller executable: {executable}")
    env_publisher = os.environ.get("MSIX_PUBLISHER", "").strip()
    env_identity_name = os.environ.get("MSIX_IDENTITY_NAME", "").strip()
    if bool(env_publisher) != bool(env_identity_name):
        raise SystemExit("Nastav buď obě hodnoty MSIX_PUBLISHER a MSIX_IDENTITY_NAME, nebo ani jednu.")
    if not args.publisher.strip() or "__" in args.publisher:
        raise SystemExit("MSIX Publisher musí být neprázdný a musí odpovídat Partner Center.")
    if not args.identity_name.strip() or "__" in args.identity_name:
        raise SystemExit("MSIX Identity Name musí být neprázdný a musí odpovídat Partner Center.")

    parts = args.version.split(".")
    if len(parts) == 3:
        parts.append("0")
    if len(parts) != 4 or any(not p.isdigit() or int(p) > 65535 for p in parts):
        raise SystemExit(f"Neplatná MSIX verze: {args.version}")
    version = ".".join(str(int(p)) for p in parts)

    with tempfile.TemporaryDirectory(prefix="kudy-msix-") as temp:
        staging = Path(temp) / "package"
        app_dir = staging / "app"
        assets_dir = staging / "Assets"
        shutil.copytree(source, app_dir)
        assets_dir.mkdir(parents=True)

        icon = ROOT / "build" / "icons" / "app.png"
        if not icon.is_file():
            raise SystemExit("Chybí build/icons/app.png; nejdřív spusť desktop/icons.py.")
        with Image.open(icon) as original:
            original = original.convert("RGBA")
            for name, size in (
                ("StoreLogo.png", (50, 50)),
                ("Square150x150Logo.png", (150, 150)),
                ("Square44x44Logo.png", (44, 44)),
                ("Wide310x150Logo.png", (310, 150)),
            ):
                original.resize(size, Image.Resampling.LANCZOS).save(assets_dir / name)

        manifest = TEMPLATE.read_text(encoding="utf-8")
        manifest = manifest.replace("__MSIX_PUBLISHER__", args.publisher.strip())
        manifest = manifest.replace("__MSIX_IDENTITY_NAME__", args.identity_name.strip())
        manifest = manifest.replace("__APP_VERSION__", version)
        manifest_path = staging / "AppxManifest.xml"
        manifest_path.write_text(manifest, encoding="utf-8")
        ET.parse(manifest_path)  # fail early on malformed XML

        output.parent.mkdir(parents=True, exist_ok=True)
        makeappx = find_makeappx()
        subprocess.run(
            [str(makeappx), "pack", "/d", str(staging), "/p", str(output), "/o"],
            check=True,
        )
        # MakeAppx has no "validate" subcommand. Unpack the result to verify
        # that the package is readable and contains a valid manifest.
        verification = Path(temp) / "verification"
        subprocess.run(
            [str(makeappx), "unpack", "/p", str(output), "/d", str(verification)],
            check=True,
        )
        extracted_manifest = verification / "AppxManifest.xml"
        if not extracted_manifest.is_file():
            raise SystemExit("The generated MSIX is missing AppxManifest.xml.")
        ET.parse(extracted_manifest)
    print(f"MSIX vytvořen: {output}")
    if args.publisher == TEST_PUBLISHER or args.identity_name == TEST_IDENTITY_NAME:
        print("POZOR: balíček používá TESTOVACÍ Publisher identity a není určený k odeslání do Store.")
    else:
        print("Publisher je převzatý z konfigurace; před odesláním ověř identitu a verzi v Partner Center.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
