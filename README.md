# Tapo C101: infrared night vision through glass

A reverse-engineering case study and experimental local API workaround for a Tapo C101 V5 camera. The goal is to use infrared-sensitive night vision without its built-in IR lamps reflecting off a window.

**Status: experimental, not a proven persistent fix.** One camera accepted the configuration change and its owner observed night mode without IR. Later, the setting reverted to its original value at an unknown time; a second application was accepted, but the automatic day-to-night transition and reboot persistence were not verified. Firmware updates or other models may behave differently. The camera still needs outside light or an external IR illuminator to see in darkness.

Read the [research paper](PAPER.md) before trying the [local helper](tapo_ir.py). This is independent research, not affiliated with TP-Link. No firmware, camera recordings, credentials, or device-specific identifiers are included.

## Quick start

Use Python 3.10+ and install [PyTapo](https://github.com/JurajNyiri/pytapo):

```sh
python -m venv .venv
. .venv/bin/activate
pip install pytapo
python tapo_ir.py CAMERA_IP inspect
```

The helper prompts for the local camera control account and password. It does not save credentials. `inspect` is read-only. To try the workaround, follow the steps in the paper; `apply` changes a device configuration and writes a local backup file. `restore` requires that backup. Use your own camera on a trusted local network.
