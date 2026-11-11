# GCP retirement

Date: 11 November 2026. Status: archive and cloud shutdown verified on 11 November 2026. All eight inventoried GCP projects are shut down and billing links removed; local GCP logins were revoked. Full checksums and receipts are in the private archive.

Former GCP project: `disinformation-demo`. Former Cloud Run services: `nlu-reasoning-orchestrator`.

The owner requested preservation of source, cloud data, configuration, and a complete stop to GCP use. Credential values are excluded; credential names and configuration are retained.

Active deployment entry points were moved into `historical-deployment/` with a `.disabled` extension: `cloudbuild.yaml`, `scripts/deploy_cloud_run.sh`. GitHub deployment workflows were also disabled at the repository level where present.

Historical source and deployment code remain available for study. This retirement does not provide a replacement hosted service. Any future deployment requires a separate decision and fresh credentials.

The private [GCP retirement archive](https://github.com/miharcan/gcp-retirement-archive) contains the cross-project inventory, encrypted release archives, checksums, backup exclusions, and restore instructions. Its encryption key is stored separately on the owner's machine.
