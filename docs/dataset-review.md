# Data-rights desk research — E1 candidate, not downloaded

**Candidate:** OpenNeuro `ds008496` v1.0.3, “EEG RKI” (DOI: 10.18112/openneuro.ds008496.v1.0.3).
- Source: https://openneuro.org/datasets/ds008496
- Public landing page lists **CC0**, 15 subjects, EEG task variants and events metadata; checked 2026-10-20. Source citation: OpenNeuro dataset DOI above.
- Why candidate: EEG recording and task condition metadata exist; opportunity to inspect event clocks in a future controlled integration fixture.
- **Gaps:** no `*_beh.tsv` or trial-wise participant response verification was established from the overview alone. EEG RKI is **not proven** to satisfy EEG+behavior alignment requirements; confirm actual files and consent/rights before ingest. Not downloaded or used in any test. 1.17 GB source size from listing; bounded limits must be configured for actual EDF.

Policy sources:
- BIDS event onset in seconds relative to first recorded sample: https://github.com/bids-standard/bids-specification/blob/master/src/schema/objects/columns.yaml
- MNE annotation/stim events details: https://mne.tools/stable/generated/mne.io.read_raw_edf.html
- OpenNeuro repository license policies and conditions: https://docs.openneuro.org/faq
- DANDI also allows datasets with approved Creative Commons licenses, but license is per dataset: https://docs.dandiarchive.org/terms-policies/policies/

No human data is bundled and no scientific outcome is asserted.

## Continued candidate review (2026-10-20; public metadata only)

**Potentially suitable, NOT INGESTED:** OpenNeuro [ds003061, v1.1.2](https://openneuro.org/datasets/ds003061/versions/1.1.2), Arnaud Delorme, *EEG data from an auditory oddball task* (2022), DOI `10.18112/openneuro.ds003061.v1.1.2`. Public page reports **CC0**, 13 participants, oddball button responses, and EEG provided in **EEGLAB** format. This is a promising P300 EEG+behavior subject-level benchmark candidate. However, its EEG is in EEGLAB `.set` format, **not supported by the current EDF-only real adapter**, and the public page alone does not validate its event clocks or per-trial response extraction. Files total approximately 2.26 GB; no complete dataset files have been downloaded or processed.

**Potentially suitable after different adapter:** [ds007471, v1.0.0](https://openneuro.org/datasets/ds007471/versions/1.0.0) reports **CC0**, separate behavioral TSV and BrainVision EEG for joint-action hyperscanning. This requires a BrainVision reader, paired-subject group split rather than assuming independent people, and explicit trial mapping; no source bytes inspected.

**Rejected for current E1 allowlist:** [PhysioNet eegmmidb v1.0.0](https://physionet.org/content/eegmmidb/1.0.0/) advertises ODC-By-1.0 rather than CC0 or CC-BY-4.0. License permissions may be broad but the strict configured importer correctly rejects an unreviewed license extension.

**No real-data claim:** A license statement on a dataset landing page does not independently verify rights of every derivative, stimulus or participant-level file; each selected study version and subfile requires source provenance and documented evaluation decisions. The candidate pages are not benchmark data.
