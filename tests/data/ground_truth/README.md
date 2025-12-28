# Ground Truth Test Datasets

This directory contains synthetic datasets with known device groups/clusters to validate categorization engine accuracy.

## Purpose

These datasets serve as **ground truth** for testing clustering accuracy. Each dataset represents a different company type with:
- **Known device groups** (what devices should cluster together)
- **Labeled endpoints** (expected cluster assignments)
- **Traffic patterns** that distinguish device types
- **Identity data** (AD groups, ISE profiles) where applicable

**Important:** These datasets do NOT include SGT assignments initially. The goal is to test raw clustering accuracy based on:
- Traffic patterns (communication behavior)
- Identity data (AD groups, user assignments)
- Device characteristics (MAC addresses, hostnames)

## Dataset Structure

Each company type has its own subdirectory:

```
tests/data/ground_truth/
├── enterprise/          # Enterprise Corporation
├── healthcare/          # Healthcare Organization
├── manufacturing/       # Manufacturing Company
├── education/           # Education Institution
└── retail/              # Retail Chain
```

Each dataset contains:
- `flows.csv` - Network flow data
- `endpoints.csv` - Endpoint metadata with ground truth cluster labels
- `ad_users.csv` - Active Directory users and groups
- `ise_sessions.csv` - ISE authentication sessions (if applicable)
- `ground_truth.json` - Metadata about expected clusters

## Ground Truth Format

Each dataset includes a `ground_truth.json` file that defines:
- Expected cluster IDs
- Expected cluster labels (e.g., "Corporate Laptops", "IP Phones", "Servers")
- Endpoint → expected cluster mapping
- Device type distinctions (e.g., IP Phone vs Mobile Phone)

### Key Distinctions

**IP Phone vs Mobile Phone:**
- **IP Phone:** Only talks to voice servers, never to Internet
- **Mobile Phone:** Talks to central servers, may have voice app (different pattern)

**Other distinctions:**
- Servers vs Clients (inbound vs outbound traffic patterns)
- IoT devices (low peer diversity, specific ports)
- Printers (few destinations, specific ports)
- Guest devices (no AD identity, limited destinations)

## Validation

See `src/clarion/clustering/validator.py` for validation framework that:
- Compares actual clusters to expected clusters
- Calculates precision, recall, F1-score
- Reports misclassified endpoints
- Validates device type distinctions

