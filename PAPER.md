# Separating infrared illumination from night vision on a Tapo C101

**Research note, 2026-11-01.** One Tapo C101 V5, firmware 1.5.7 Build 260709 Rel.28020n, was examined over its authenticated local API. Related C100 V5 firmware was analyzed offline. Results for the C100 must not be assumed to describe the C101's installed binary.

## Abstract

An indoor camera aimed through a window reflects its infrared (IR) illuminators into its lens. Day mode extinguishes those lamps but also changes the IR-cut filter, making it unsuitable for a dark scene. A C101 reported separate GPIO assignments for the filter and illuminator and accepted a configuration change making the two assignments equal. On a related C100 firmware image, decompilation showed a code path that skips a separate LED GPIO write when the configured GPIOs match. Following the change, the C101 owner reported night mode without apparent IR illumination. This is a promising observation, not a controlled optical verification: the exact installed C101 firmware was not analyzed, the setting later reverted for an unknown reason, and persistence and automatic transitions remain unverified.

## Background and scope

TP-Link says its normal night mode does not offer independent IR LED shutdown and recommends day mode to disable the LEDs ([Tapo FAQ](https://www.tapo.com/us/faq/754/)). That does not meet the requirement where infrared illumination is needed outside the glass. Night vision without onboard IR still requires suitable ambient light or an external IR source. Glass transmission varies.

The study used authenticated local access to a camera owned by the operator. It did not flash firmware, enable factory mode, or modify the camera's executable. The result is a configuration-level workaround, not a firmware patch.

## Observed C101 configuration

The local API advertised `infrared_lamp` and `inf_night_vision`, but reported `inf_lamp_type_support`, `intensity_support`, and `smart_inf_lamp_support` as `0`. A read of `image_profile.ir_gpio_attr` reported `ir_cut_gpio_port` as `57` and `ir_led_gpio_port` as `49`. Those values are specific to the examined unit; do not assume them for another hardware revision.

PyTapo wraps individual methods inside `multipleRequest`. In this firmware, a request named `getDeviceInfo` accepted a different configuration subtree:

```json
{"method":"getDeviceInfo","params":{"image_profile":{"name":["ir_gpio_attr"]}}}
```

A request called `setLedStatus`, ordinarily associated with the status indicator, also accepted an `image_profile` payload. For example, the test unit accepted:

```json
{"method":"setLedStatus","params":{"image_profile":{"ir_gpio_attr":{"ir_led_gpio_port":"57"}}}}
```

These examples are the inner requests passed to PyTapo's `executeFunction`. A successful response or configuration readback **does not prove that a setting affected hardware**. The camera accepted 49→57, then 57→49, with readback confirming each value. The operator subsequently switched to day, wrote 57, and selected night. The owner reported night mode with no apparent IR; no calibrated LED or image measurement was performed.

After the owner later selected Auto, a read returned the original LED pin, 49. The time and cause of the reversion are unknown. The workaround was reapplied in Auto, with 57 read back; whether automatic transitions or reboot retain it has not been demonstrated. Check the configuration and actual image after dark and after restart. Do not assume this is reliable security monitoring.

## Offline firmware analysis and mechanism

TP-Link publishes a [C100/C101/TC60 V5 GPL source package](https://static.tp-link.com/upload/gpl-code/2025/202503/20250303/C100_C101__TC60_V5_GPL.tar.bz2). Its generic `product_config/ALL/buildroot.config` listed separate filter and LED pins. This was a lead, not proof of the running C101 configuration, which was read independently as described above.

An older related **C100 V5 1.4.4 Build 260413** firmware image was obtained from [TP-Link's download server](https://download.tplinkcloud.com/firmware/assigned/Tapo_C100v5_en_1.4.4_Build_260413_Rel.27634n_up_boot-signed_1776824401820.bin). SHA-256: `2ab4bb2ff69aa5f05d7e25248432ba72a318a1e40fa54b3939757fc7833c8a5c`. It is **not the C101 firmware** and must not be flashed to the C101.

The image's header matched a documented encrypted TP-Link camera format. [tpbreak-cli](https://github.com/haxorthematrix/tpbreak-cli) reported a successful signature verification and produced a decrypted image. [REA](https://github.com/morluto/rea) firmware inspection identified MIPS uImages and a SquashFS filesystem; extraction was partial, but recovered `bin/main`, SHA-256 `c20d87545f17590c0624f15be8f8e80fcbb560904a56a54041a61189cf36643f`. REA uses Binwalk and Unblob for these stages and Ghidra for the MIPS code. An equivalent offline workflow is:

```sh
# Download the exact related image using the link above, then:
tpbreak decrypt Tapo_C100v5_en_1.4.4_Build_260413_Rel.27634n_up_boot-signed_1776824401820.bin
# Inspect and extract the resulting .dec image using REA's
# inspect_firmware_regions and extract_firmware tools.
# Open the recovered SquashFS bin/main in REA with Ghidra.
```

Search for `irled_lock_handle`, `camera_image_ir_on`, and `camera_image_ir_off`. In this C100 binary, the handler identified by the first string accepts `enabled` values `on` and `off`, checks factory mode, and sends an internal message. The corresponding callback stores a lock flag. The IR-on path operates the filter and, when the configured filter and LED pins differ, conditionally operates the LED pin; the equal-pin branch returns before the separate LED write. The related IR-off path has a similar equal-pin branch. This supports the **hypothesis** behind the C101 configuration change. It does not establish the exact behavior of the installed C101 firmware, the electrical state of any pin, or persistence.

The C100's `etc/dsd_convert.json` maps `irLedLock` to a `do` operation. An intentionally invalid `irLedLock` request on the C101 returned method-not-found (`-40105`). The factory-mode guard was not bypassed and factory mode was not enabled. A generic source-package configuration or unrecognized API method is not proof that a function is available on the C101.

## Reproducing and restoring the configuration experiment

The helper uses PyTapo's local control login. Use a current backup and note that this is an undocumented hardware configuration: wrong values can disrupt camera operation, and updates may alter behavior. Do not apply on a model whose reported pins are missing, invalid, or already equal. The script stores the actual original values in a file chosen by the operator; the backup may contain a camera address, so treat it as private.

```sh
# Read and record the device's settings first:
python tapo_ir.py CAMERA_IP inspect
# Test: switch to day, save original GPIO and mode, set LED pin to filter pin,
# then return to the original mode:
python tapo_ir.py CAMERA_IP apply --backup ./camera-backup.json
# Restore the original GPIO and mode using the saved backup:
python tapo_ir.py CAMERA_IP restore --backup ./camera-backup.json
```

Check that day mode really extinguishes the lamps before the change, and verify night vision and the lamps physically afterward. On the test device, setting the pin while Auto was already active was accepted, but whether that alone switches off an already-lit LED is unknown. Avoid changing the mode in an active monitoring interval. The helper restores the saved configuration if its apply sequence reports an error, but cannot guarantee rollback after a power loss, network failure, or reboot.

## Other settings and image-quality tests

The examined camera reported a 1920×1080 H.264 main stream, bitrate `1280`, and advertised `2048` among its bitrate options, as well as H.265. It also reported a 720p substream, motion and person detection, recording schedules, audio controls, and image controls including contrast and wide dynamic range. Some generic capability flags conflicted with the physical camera, so reported capability is not conclusive proof of support. Higher bitrate can reduce compression artifacts but cannot add sensor detail; codec compatibility needs testing.

The camera accepted a temporary main bitrate change from 1280 to 2048 and back. Full-resolution RTSP setup failed in this test environment, so no meaningful bitrate comparison was possible. For two 640×360 snapshot comparisons in overcast daylight, temporarily enabling `wide_dynamic` and raising contrast from 50 to 60 showed no obvious improvement. Both values were restored. Readback does not establish that the live image pipeline applied those values, and these comparisons do not determine performance in other lighting.

The related C100 image contained a driver for the SmartSens SC2336P; that is not proof the C101 uses it. SmartSens lists the [SC2336P](https://smartsens.oss-cn-beijing.aliyuncs.com/web/img/1676880676453184940.pdf) as a 2 MP sensor with 1080p video at up to 30 fps. The C101 advertised a maximum 1080p stream; no hidden higher-resolution mode was established.

## Limitations and open work

- Obtain and analyze the matching C101 firmware image, including GPIO handling and any reload behavior.
- Verify LEDs and captured image during automatic day/night transitions, repeated reboots, and power cycles.
- Determine whether and when a mode switch, configuration reload, or firmware update restores the original GPIO mapping.
- Test whether a more direct, documented and persistent local control exists.
- Compare actual full-resolution footage with controlled lighting and stable scenes before recommending image-quality changes.

The investigation used [PyTapo](https://github.com/JurajNyiri/pytapo), [REA](https://github.com/morluto/rea), [tpbreak-cli](https://github.com/haxorthematrix/tpbreak-cli), and published vendor source and specifications. Those projects and vendor firmware retain their own licenses; no third-party firmware or code is redistributed here.
