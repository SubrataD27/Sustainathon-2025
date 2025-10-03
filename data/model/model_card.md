# Model Card: Drone Threat Classifier

## Overview
Multimodal classifier fusing RF, acoustic, and vision-derived features to label aerial objects and potential hostile emitters.

## Intended Use
- Real-time detection and classification of small UAVs and potential jamming sources in campus perimeter.
- Supports automated decision engine for dispatch.

## Not Intended For
- Military-grade beyond visual line-of-sight targeting.
- Attribution or legal evidence without corroborating sensors.

## Inputs
- RF: 256-length spectral power vector (normalized)
- Acoustic: 128-length mel-spectrogram slice
- Vision: 64-length embedding from lightweight CNN

## Outputs
- threat_class: {consumer_quadcopter, prosumer_quadcopter, bird, jammer_sweep, unknown}
- intent: {benign, suspicious, hostile, unknown}
- confidence: 0.0 - 1.0

## Performance (Placeholder)
| Class | Precision | Recall |
|-------|-----------|--------|
| consumer_quadcopter | TBD | TBD |
| prosumer_quadcopter | TBD | TBD |
| bird | TBD | TBD |
| jammer_sweep | TBD | TBD |

## Ethical / Bias Considerations
- Avoid misclassifying birds as drones (wildlife impact).
- False positives increase resource & energy usage.

## Security Considerations
- Model file signed (Ed25519) before deployment.
- Adversarial perturbation resilience via augmentation.

## Versioning
- SemVer: MAJOR.MINOR.PATCH
- Current: 0.1.0

## Change Log
- 0.1.0: Initial baseline architecture defined.
