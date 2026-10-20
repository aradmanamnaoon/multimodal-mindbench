# Synthetic benchmark evaluation protocol — P09-E2/E3/E4/E5 local engineering checkpoint

Status: **software-validation demonstration**, not scientific replication, a human population result, a released benchmark, or an independently accepted epic. All output values are synthetic and seed-dependent.

## Estimand and scope

Predict a **programmatically assigned binary class** from two invented EEG-like float features, two invented behavioral float features, or both. These vectors are not recorded EEG, individual reaction times or model-ready task effects, and their relationship to the synthetic class is artificially stipulated. Four methods: EEG-only logistic, behavior-only logistic, early concatenation with logistic, late average of calibrated unimodal probabilities. Missing late-fusion modality uses the remaining unimodal estimator; if both missing, abstain.

## Leakage barriers

- Sample identifier uniqueness is verified.
- Distinct subject groups are partitioned once into train, calibration, and external test; no overlap allowed. Subjects are the split unit, not trials. Seed and subject IDs are serialized.
- StandardScaler and regularized logistic estimators fit on training subjects only, calibrator sigmoid models on separate calibration subjects, metrics on untouched test subjects.
- A fixed 0.5 threshold is declared in advance; no threshold or model selection on the holdout. Candidate metrics share *exactly the same* complete-case test rows. The missing-input fallback is a **separate denominator**; it is not comparable to complete-case scores.
- Simulated subject-specific nuisance is present. Note that random class assignment still occurs in software, not participants.
- Nonclinical only. No psychological trait, disorder, cognition, EEG biomarkers or medical claims.

## Metrics

Accuracy, balanced accuracy, ROC AUC when both classes exist, Brier score, and 10-bin expected calibration error are computed on the test fold. Accuracy 95% intervals use a subject-cluster percentile bootstrap (300 resamples by default); these are descriptive for **one synthetic held-out population and one split**, not inferential uncertainty about humans. Bootstrap does not refit estimators, and test results cannot guide further hyperparameters. The calibration method is Platt-style sigmoid fitted on disjoint calibration subjects; no automatic assertion of good calibration is made. Configuration and code versions should be pinned in production.

## Alignment and EEG extraction

Conservative one-to-one event/response matching never assigns a response to two events and does not reassign a post-next-stimulus response backward. Any unknown behavior clock origin produces **no matches**. EEG artifacts are supplied as explicit intervals and overlapping epochs are flagged. Missing EEG or behavior is an explicit mask. Two EEG time-window mean features are computed by bounded synthetic TSV streaming or optional lazy EDF epochs through MNE. Channel order must be made consistent across all subjects before any empirical benchmark. Missing modalities are not disguised as measured zero values.

## What is still NOT proven

No real EEG+behavior data was ingested into the multimodal benchmark; no clock synchronization experimentally verified, no external replication or peer review, no distribution shift validation across hospitals/sites/people, no tested fairness, no usability study, no hosted CI run or deployment. `rights.json` remains importer-supplied attestation only; independently verified original rights are necessary prior to using data from a public archive.

## Authoritative method/background documents (not citations for performance claims)

- BIDS task events: https://bids-specification.readthedocs.io/en/stable/modality-specific-files/task-events.html
- scikit-learn grouped CV: https://scikit-learn.org/stable/modules/cross_validation.html#cross-validation-iterators-for-grouped-data
- scikit-learn calibration: https://scikit-learn.org/stable/modules/calibration.html
- PhysioNet EEG motor imagery dataset currently advertises ODC-By-1.0; it is **outside our E1 explicit license allowlist**, so do not ingest it without a reviewed policy update: https://physionet.org/content/eegmmidb/1.0.0/
