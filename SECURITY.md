# Security & Data Privacy Policy

## Data Handling Statement

This repository is part of a pharmaceutical market research project that processes
pharmacy sales data. The following measures have been taken to protect sensitive
information:

### 1. Data Removal

All raw and processed data files have been **excluded from this repository**:

| Directory | Content | Status |
|:---|:---|:---|
| `data/raw/` | Raw pharmacy sales data | ❌ **Excluded** (via `.gitignore`) |
| `data/processed_data/` | Intermediate processing results | ❌ **Excluded** (via `.gitignore`) |
| `results/` | Final analysis outputs & reports | ❌ **Excluded** (via `.gitignore`) |

### 2. Anonymization

- All pharmacy identifiers (`CLIENT_ID`) are **synthetic numeric codes** with no mapping to real pharmacy names or locations
- All drug identifiers (`DRUGS_ID`, `INN_ID`) are **internal system codes** that cannot be traced to commercial databases without the original data source
- No patient, customer, or employee data was ever part of this dataset
- Geographic information has been fully removed

### 3. What IS Included in This Repository

Only the following are present in the repository:

- ✅ **Source code** — Python scripts for data processing pipeline
- ✅ **Configuration files** — thresholds, parameters, column mappings
- ✅ **Documentation** — methodology, business context, technical guides
- ✅ **Utility functions** — shared ETL and statistical calculation modules

### 4. What is NOT Included

- ❌ Raw sales data (CSV files with transaction records)
- ❌ Processed intermediate files (aggregated data, stockout events)
- ❌ Analysis results (substitution coefficients, reports)
- ❌ Excel reports with market-specific findings
- ❌ Any data that could identify specific pharmacies, drugs, or markets

## Reporting Security Concerns

If you believe you have found sensitive data that was accidentally committed, please
contact the author immediately:

- **Email:** [lomanov.mail@gmail.com](mailto:lomanov.mail@gmail.com)
- **Telegram:** [@radyslav_datascience](https://t.me/radyslav_datascience)

## Intellectual Property

All code, methodology, and documentation in this repository are proprietary.
See [LICENSE](LICENSE) for full terms.

---

**© 2026 Radyslav Lomanov. All Rights Reserved.**
