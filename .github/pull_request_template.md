<!-- 
  REMINDER: Use a Conventional Commit / Semantic PR title so release.yml auto-generates clean changelogs!
  Examples:
    feat(firmware): move window energy and threshold logic to src.ino
    feat(dsp): implement 2nd-order 12Hz Butterworth low-pass filter
    fix(analysis): prevent plot_before.png from being overwritten
    docs(readme): add Windows setup and COM port instructions
-->

## Summary
<!-- Briefly describe what this PR does and why these changes are needed. -->

- **Related Issue:** Closes #
- **Target Milestone:** <!-- e.g., Signal Processing Pipeline / Hip Data Validation / Dashboard & ML / Final Testing -->

---

## Type of Change
- [ ] `feat`: New feature (firmware, DSP, ML model, or dashboard)
- [ ] `fix`: Bug fix
- [ ] `refactor`: Code restructuring without changing external behavior
- [ ] `perf`: Latency, sampling rate, or memory optimization
- [ ] `ci`: GitHub Actions workflow updates
- [ ] `docs`: Documentation updates (`README.md`, reports, comments)
- [ ] `chore`: Calibration, dataset updates, or maintenance

## Component(s) Affected
- [ ] **Firmware (`src/src.ino`)** - Seeed Studio XIAO MG24 Sense / LSM6DS3
- [ ] **Analysis & DSP (`src/analysis.py`)** - Serial parsing, plotting, FFT/STFT, metric extraction
- [ ] **Machine Learning / Dashboard** - Form classifier or real-time athlete UI
- [ ] **Hardware / Mounting** - Hip attachment or enclosure adjustments
- [ ] **CI/CD & Configs** - `.github/workflows/` or `requirements.txt`

---

## EmbedQB Hardware & DSP Checklist
<!-- Check all items that apply to this PR, or mark N/A if purely documentation/CI. -->
- [ ] **Sampling & Baud Rate:** Serial baud rate matches across `src.ino` and `analysis.py`, and loop timing maintains the target **416 Hz** ($2404\ \mu\text{s}$) rate.
- [ ] **Filter & Window Parameters:** Any changes to the **12 Hz 2nd-order Butterworth LPF**, `WINDOW_SIZE` ($20$), or `THRESHOLD_VAL` ($25.0$) are documented and verified.
- [ ] **Serial Packet Format:** CSV packet field order and count match between `src.ino` output and `analysis.py` parsing.
- [ ] **Sensor Placement Context:** Specified whether testing was performed on the **wrist** (bench/preliminary) or **hip-mounted** (target throwing motion).

---

## Testing & CI Verification
- [ ] **Firmware CI (`firmware-ci.yml`):** Compiles cleanly for `SiliconLabs:silabs:xiao_mg24` with zero new warnings.
- [ ] **Python CI (`python-ci.yml`):** Passes `flake8` lint checks and headless CSV/figure generation tests.
- [ ] **Security Audit (`secrets.yml`):** No hardcoded API keys, credentials, or tracked `.env` files.
- [ ] **Hardware Bench Test:** Verified on physical XIAO MG24 Sense hardware (if firmware/serial logic was modified).

---

## Evidence / Figures / Output
<!-- Attach relevant screenshots, generated figures (e.g., plot_after.png, energy.png, FFT/STFT), or sample Serial CSV output below. -->