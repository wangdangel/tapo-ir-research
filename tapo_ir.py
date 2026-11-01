#!/usr/bin/env python3
"""Experimental C101 GPIO mapping helper; see PAPER.md before use."""
import argparse
import getpass
import json
import os
from pathlib import Path
import time

from pytapo import Tapo


def pins(camera):
    return camera.executeFunction(
        "getDeviceInfo", {"image_profile": {"name": ["ir_gpio_attr"]}}
    )["image_profile"]["ir_gpio_attr"]


def set_led_pin(camera, value):
    camera.executeFunction(
        "setLedStatus", {"image_profile": {"ir_gpio_attr": {"ir_led_gpio_port": str(value)}}}
    )
    if str(pins(camera)["ir_led_gpio_port"]) != str(value):
        raise RuntimeError("LED pin readback did not match the requested value")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("host", help="Camera local address")
    parser.add_argument("action", choices=("inspect", "apply", "restore"))
    parser.add_argument("--backup", type=Path, help="Private JSON backup path (required for apply/restore)")
    args = parser.parse_args()
    if args.action != "inspect" and not args.backup:
        parser.error("--backup is required for apply and restore")
    backup = None
    if args.action == "restore":
        backup = json.loads(args.backup.read_text())
        if backup.get("host") != args.host or backup.get("version") != 1:
            raise ValueError("Backup host or format does not match")
    user = input("Local camera control username: ")
    password = getpass.getpass("Local camera control password: ")
    camera = Tapo(args.host, user, password)
    current = pins(camera)
    mode = camera.getDayNightMode()
    print("Day/night mode:", mode)
    print("Filter GPIO:", current.get("ir_cut_gpio_port"))
    print("LED GPIO:", current.get("ir_led_gpio_port"))
    if args.action == "inspect":
        return
    if args.action == "apply":
        cut, led = str(current["ir_cut_gpio_port"]), str(current["ir_led_gpio_port"])
        if not cut.isdigit() or not led.isdigit() or cut == led or cut == "999" or led == "999":
            raise ValueError("Pin values are missing, identical or unsupported; no change made")
        if mode not in ("on", "off", "auto"):
            raise ValueError("Unknown day/night mode; no change made")
        backup = {"version": 1, "host": args.host, "ir_led_gpio_port": led, "day_night_mode": mode}
        fd = os.open(args.backup, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "w") as stream:
            json.dump(backup, stream, indent=2)
            stream.write("\n")
        print("Backup saved to", args.backup)
        try:
            camera.setDayNightMode("off")
            time.sleep(3)
            set_led_pin(camera, cut)
            camera.setDayNightMode(mode)
            print("Applied. Verify actual IR LEDs and night image; persistence is unknown.")
        except Exception:
            try:
                set_led_pin(camera, led)
                camera.setDayNightMode(mode)
                print("Original settings restored after failure.")
            except Exception as rollback_error:
                print("Rollback failed; use the backup to restore:", type(rollback_error).__name__)
            raise
    else:
        led = str(backup["ir_led_gpio_port"])
        original_mode = backup["day_night_mode"]
        if not led.isdigit() or led == "999" or original_mode not in ("on", "off", "auto"):
            raise ValueError("Invalid backup values; no change made")
        set_led_pin(camera, led)
        camera.setDayNightMode(original_mode)
        print("Restored saved LED GPIO and day/night mode; verify camera operation.")


if __name__ == "__main__":
    main()
