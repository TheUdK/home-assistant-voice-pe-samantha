"""Verify provenance/runtime preservation, inspect generated code, package OTA files."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parent
LOCK = json.loads((ROOT / "samantha-lock.json").read_text())


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def verify():
    # Every upstream runtime file must exactly match the recorded official commit.
    paths = subprocess.check_output(
        ["git", "ls-tree", "-r", "--name-only", LOCK["upstream_commit"]],
        cwd=ROOT, text=True).splitlines()
    for name in paths:
        if name.startswith(".github/"):
            continue  # Distribution automation is fork-specific.
        original = subprocess.check_output(
            ["git", "show", f'{LOCK["upstream_commit"]}:{name}'], cwd=ROOT)
        assert (ROOT / name).read_bytes() == original, f"Upstream file changed: {name}"
    overlay = (ROOT / "samantha.yaml").read_text()
    assert "official: !include home-assistant-voice.factory.yaml" in overlay
    assert "${ota_base}/manifest.json" in overlay
    assert "${ota_base}/manifest-beta.json" in overlay
    for m in LOCK["models"]:
        manifest = ROOT / m["manifest"]
        model = ROOT / m["model"]
        assert sha256(manifest.read_bytes()) == m["manifest_sha256"]
        assert sha256(model.read_bytes()) == m["model_sha256"]
        data = json.loads(manifest.read_text())
        assert data["type"] == "micro" and data["version"] == 2
        assert data["wake_word"].lower() == m["wake_word"]
        assert data["model"] == m["model"]  # Local, never a mutable URL.
        assert model.read_bytes()[4:8] == b"TFL3"
        assert "MIT License" in (ROOT / m["license_file"]).read_text()
        assert f'id: {m["id"]}' in overlay
    print("Verified pinned official runtime, model integrity and local manifests.")


def config():
    # Inspect the actual merged ESPHome configuration, not only source text.
    from esphome.config import read_config
    from esphome.core import CORE
    CORE.config_path = ROOT / "samantha.yaml"
    resolved = read_config({})
    assert resolved is not None, "ESPHome configuration failed"
    models = resolved["micro_wake_word"]["models"]
    ids = {str(m["id"]) for m in models}
    required = {"okay_nabu", "hey_jarvis", "hey_mycroft", "stop"}
    required.update(m["id"] for m in LOCK["models"])
    assert required <= ids, (required, ids)
    assert next(m for m in models if str(m["id"]) == "stop")["internal"]
    sensitivity = next(s for s in resolved["select"] if str(s["id"]) == "wake_word_sensitivity")
    assert list(sensitivity["options"]) == ["Slightly sensitive", "Moderately sensitive", "Very sensitive"]
    assert resolved["esp32"]["variant"] == "ESP32S3"
    assert resolved["esp32"]["flash_size"] == "16MB"
    print("Verified merged configuration: all upstream models, Stop and sensitivity options retained.")


def generated():
    build = ROOT / ".esphome/build/home-assistant-voice"
    source = "\n".join(p.read_text(errors="replace") for p in (build / "src").rglob("*.cpp"))
    for m in LOCK["models"]:
        # Match the complete model bytes in one emitted C++ data array.
        arrays = re.findall(r"\{\s*((?:0x[0-9a-fA-F]{2}\s*,?\s*){100,})\}", source)
        hashes = {sha256(bytes(int(x, 16) for x in re.findall(r"0x([0-9a-fA-F]{2})", a))) for a in arrays}
        assert m["model_sha256"] in hashes, f"Model bytes absent from generated code: {m['id']}"
    main = (build / "src/main.cpp").read_text()
    for identifier in ["okay_nabu", "hey_jarvis", "hey_mycroft", "stop", "samantha"]:
        assert identifier in main
    print("Verified complete custom model bytes in generated build sources.")


def package():
    generated()
    version = LOCK["firmware_version"]
    repo = os.environ.get("GITHUB_REPOSITORY", "TheUdK/home-assistant-voice-pe-samantha")
    build = ROOT / ".esphome/build/home-assistant-voice/.pioenvs/home-assistant-voice"
    out = ROOT / "dist"
    out.mkdir(exist_ok=True)
    for name in ["firmware.ota.bin", "firmware.factory.bin", "firmware.elf"]:
        source = build / name
        assert source.is_file() and source.stat().st_size > 0, source
        shutil.copy2(source, out / name)
    ota = (out / "firmware.ota.bin").read_bytes()
    manifest = {"name": "Home Assistant Voice PE — Samantha", "version": version,
                "builds": [{"chipFamily": "ESP32-S3", "ota": {
                    "path": f"releases/{version}/firmware.ota.bin",
                    "md5": hashlib.md5(ota).hexdigest(),
                    "release_url": f"https://github.com/{repo}/releases/tag/{version}",
                    "summary": "Samantha wake word. Experimental: physical detection and false-positive testing required. Install only with manual approval."
                }}]}
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    (out / "SHA256SUMS").write_text("".join(f"{sha256(p.read_bytes())}  {p.name}\n" for p in sorted(out.glob("firmware.*"))))
    shutil.copy2(ROOT / "samantha-lock.json", out)
    shutil.copy2(ROOT / "SAMANTHA-MODEL-LICENSE", out)
    shutil.copy2(ROOT / "LICENSE", out / "UPSTREAM-LICENSE")
    shutil.copy2(ROOT / "SAMANTHA.md", out)
    site = ROOT / "site"
    release = site / "releases" / version
    release.mkdir(parents=True, exist_ok=True)
    for name in ["firmware.ota.bin", "firmware.factory.bin", "SHA256SUMS"]:
        shutil.copy2(out / name, release)
    for name in ["manifest.json", "manifest-beta.json"]:
        (site / name).write_text(json.dumps(manifest, indent=2) + "\n")
    (site / "index.html").write_text(f'<!doctype html><html lang="en"><meta charset="utf-8"><title>Voice PE Samantha</title><h1>Voice PE Samantha</h1><p>Experimental version {version}. Device installation requires manual approval.</p><p><a href="https://github.com/{repo}/blob/samantha/SAMANTHA.md">Selection, installation and recovery guide</a></p><p><a href="manifest.json">OTA manifest</a></p><p><a href="https://github.com/{repo}/releases/tag/{version}">Versioned release and checksums</a></p></html>')
    print(f"Packaged {version}; OTA size: {len(ota)} bytes")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["verify", "config", "generated", "package"])
    args = parser.parse_args()
    globals()[args.command]()
