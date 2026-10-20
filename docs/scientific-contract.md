# Scientific contract / evidence boundaries

Version: 1.0.0; Epic: P09-E1.

## Units and clock semantics

EEG synthetic voltage values are in volts; optional MNE EDF signal data are in MNE's native SI units (typically EEG volts). `SamplingFrequency` is in Hz and must be finite and positive. Task event onsets/durations are acquisition-relative seconds, following BIDS EEG convention. Negative onsets are permitted for a pre-acquisition event, reported in audit.

Behavior `*_beh.tsv` is a **MindBench extension**, not a standardized BIDS behavior modality. Behavioral onset is an asserted acquisition-relative time when `clock.json.behavior_origin = acquisition_start`; otherwise synchronization is explicitly unverified. No calibration pulse, timestamp-correlation, drift estimate, or independent trigger verification occurs in E1. E2 will need a shared hardware or reliable logged reference; declaring `hardware_synced` is **not** objective evidence.

Stored recording interval for N samples is [0,N/sfreq); events whose end exceeds it are flagged, not automatically paired with responses. Rounding onset to the nearest sample is only for audit of quantization, NOT a physical time alignment or sample-based EEG epoch. No event matching, trial labels or subject split is produced in E1.

## Input rights

Licenses must be evidenced at the originating data repository and bound to a pinned dataset version. `rights.json` is an **attestation**, not a trusted automatic verification. Actual licensed datasets are not fetched or bundled in E1. CC BY requires attribution and may include additional dataset-specific obligations. No individual participant data or clinical labels are included in this source tree.

## No scientific evaluation claim

Counts, ranges and SHA digests are engineering invariants, not classification metrics. No sensitivity, specificity, AUC, reliability, prediction, user adoption or medical performance exists at E1. E3 must define subject/group split, holdout, chance baseline, confidence intervals and leakage audits *before* reporting results.

## Known risks

- EDF numerical min/max scanning is lazy, but MNE's EDF reader may load file metadata and transient sample blocks; memory upper bound depends on MNE and channel count.
- EDF requires an optional MNE dependency and was not exercised by synthetic-only CI until a licensed small EDF fixture is explicitly run.
- `rights.json` can falsely claim a source license; maintain an explicit, separately reviewed verification record before making real-dataset claims.
- BIDS EEG recordings may be BrainVision, EEGLAB or other supported formats; current real adapter is EDF only.
- No anonymization or re-identification proof is provided. Keep potentially identifying metadata outside exported reports.
