# Samantha firmware for Home Assistant Voice Preview Edition

This public fork tracks official stable firmware. `samantha.yaml` is the additive build entrypoint; the official runtime and factory YAML remain byte-for-byte intact. The baseline, ESPHome version and model checksums are recorded in `samantha-lock.json`.

## Plan and status

1. Vendor and verify the existing English **samantha** microWakeWord model.
2. Build the additive overlay with ESPHome 2026.10.1 for official 16 MB ESP32-S3 Voice PE hardware; retain Okay Nabu, Hey Jarvis, Hey Mycroft, Stop, VAD, microphone settings, factory provisioning, timers, mute controls and upstream sensitivity behavior.
3. Validate merged configuration, compare official runtime files against the baseline commit, and verify custom TFLite bytes in generated sources and the compiled OTA binary before packaging.
4. Publish versioned experimental firmware only after successful GitHub Actions compilation. Serve OTA binaries and manifests from GitHub Pages. Updates require manual approval in Home Assistant; no automatic device installation, HACS or Wyoming server.
5. Keep checking [Hey Samantha request #314](https://github.com/TaterTotterson/Tater-Wake-Words/issues/314). Add it alongside Samantha after verifying its artifacts and license. Do not replace Samantha or any official model.
6. Test real detection and false positives on the physical device before treating the release as production ready.

## Model provenance and license

The manifest and TFLite model are from `TaterTotterson/Tater-Wake-Words`, commit `a901f6236a5489e54883b5b5f2335c0c0f2e3c24`, paths `microWakeWordsV3/samantha.json` and `microWakeWordsV3/samantha.tflite`. The manifest was renamed `samantha.esphome.json`; its contents and relative model path are unchanged. Author: Tater Totterson. Both files are vendored, not downloaded during builds.

The original Samantha metadata identifies the author's microWakeWord trainer. The project publishes its original artifacts under MIT; the maintainer confirmed the model license in [issue #293](https://github.com/TaterTotterson/Tater-Wake-Words/issues/293). The verbatim MIT notice is retained as `SAMANTHA-MODEL-LICENSE`. The project excludes third-party historical assets from relicensing; no independent third-party origin was identified for this author-attributed Samantha model. These are upstream license statements, not an independent audit of training-data rights. Official firmware retains its original `LICENSE`.

## Build and release

Use Python 3.12 and install the exact ESPHome version in the lock file. Run:

```sh
python samantha_tools.py verify
esphome config samantha.yaml
python samantha_tools.py config
esphome compile samantha.yaml
python samantha_tools.py package
```

The **Samantha firmware** GitHub Actions workflow builds on pushes and pull requests. Its manual **Publish validated firmware** option creates a versioned prerelease and deploys the Pages site only after all checks and compilation pass. It never contacts or installs on a device. Bump `firmware_version` in both the lock and substitution before a new release; release tags must remain immutable. The daily upstream job pushes a new stable baseline to an update branch and proposes a pull request when repository policy permits it, without auto-merging or installing it. If automated PR creation is disabled, the workflow summary/log identifies the branch for a manual PR. Review and build that PR before merging; then dispatch a validated release.

Pages publishes `manifest.json` and `manifest-beta.json` and versioned OTA binaries. The existing Beta firmware switch remains available, with both channels directed to this fork. Until separate beta promotion is needed, both manifests describe the same validated experimental release. The HTTP update entity checks every six hours and only installs on explicit request.

## First installation — requires manual approval

The official firmware initially points to the official update source, so it cannot discover this fork automatically. After reviewing the release and backing up any local ESPHome configuration, explicitly approve the first custom installation. Use the factory image with ESPHome Web over USB, or use a supported ESPHome manual OTA upload of the **OTA** image if the device's existing credentials and access permit it. Never upload the factory image as an OTA image. No Wi-Fi credentials or API keys are stored in this public repository. Provision using the official Improv flow when needed, then connect the device to the Home Assistant ESPHome integration.

Once this custom firmware is installed, its native firmware update entity uses this fork's Pages manifest. Do not enable a Home Assistant automation that installs these updates without approval.

## Select Samantha in Home Assistant

Open **Settings → Devices & services → ESPHome → your Voice PE device**. Open the voice assistant's configuration (or **Settings → Voice assistants**, select the device) and choose **samantha** from the available on-device wake words. Home Assistant's labels can vary by version. The model's manifest label is lowercase `samantha`; no separate wake-word select entity is added. Existing wake words remain available.

The official **Wake word sensitivity** select keeps its original three options and thresholds for the official models. It does not tune custom models. Samantha keeps the published cutoff `0.47`, sliding window `3`, feature step `10 ms`, and tensor arena `30000` bytes. Do not assume that the official sensitivity labels imply validated Samantha false-positive rates.

When the new model arrives, retain both `samantha` and `hey samantha` as distinct entries. Home Assistant may limit how many wake words can be active at once; select the desired one rather than enabling every model during initial hardware testing.

## Add Hey Samantha later

Obtain the matching `.esphome.json` and `.tflite` from issue #314. Verify the phrase and microWakeWord schema, source commit, license, and checksums. Vendor them locally; rewrite only an upstream model URL to its local relative filename when necessary, recording that transformation and both source and vendored hashes. Add a second entry to `samantha-lock.json` under `models` and a second `micro_wake_word.models` entry with `id: hey_samantha` in `samantha.yaml`. Keep Samantha and all official entries. Re-run all checks, compile in Actions, bump the firmware version, publish a new release, then select the desired phrase in Home Assistant. No placeholder model is compiled now.

## Physical validation

Before production use, test normal voice, distance and direction, background conversations, television/music, different speakers, silence and overnight false positives. Compare recognition and false accepts with official wake words. Verify mute switch, wake sound, LEDs, timers/Stop, button controls, media playback, Home Assistant reconnect, reboot, saved model selection and OTA recovery. Record measured results; compilation cannot establish acoustic accuracy or real-time performance with both custom models enabled.

## Recover official firmware

Connect Voice PE by a data-capable USB cable and use the [official Voice PE installer](https://esphome.github.io/home-assistant-voice-pe/). Select the official Home Assistant Voice Preview Edition firmware and follow the installer. USB recovery remains the fallback if OTA fails. If the device does not enter flashing mode automatically, follow the official installer/hardware bootloader instructions. A factory erase may require Wi-Fi provisioning and Home Assistant re-pairing. Restoring official firmware also restores the official OTA source and removes custom wake words. The hardware mute switch and factory reset do not themselves restore official firmware.
