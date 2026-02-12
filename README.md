<p align="center">
  <h1 align="center">💊 Cross-Pharma Market Analysis</h1>
  <p align="center">
    <strong>Multi-Market Pharmaceutical Substitution Research Pipeline</strong>
  </p>
  <p align="center">
    <em>Difference-in-Differences approach to drug substitutability estimation across local pharmacy markets</em>
  </p>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/python-3.11-blue?logo=python&logoColor=white" alt="Python 3.11">
  <img src="https://img.shields.io/badge/pandas-2.3-green?logo=pandas&logoColor=white" alt="pandas">
  <img src="https://img.shields.io/badge/scipy-1.16-orange" alt="scipy">
  <img src="https://img.shields.io/badge/license-All%20Rights%20Reserved-red" alt="License">
  <img src="https://img.shields.io/badge/status-In%20Development-yellow" alt="Status">
</p>

---

## 📋 Table of Contents

- [Project Goal](#-project-goal)
- [Business Context](#-business-context)
- [Pipeline Architecture](#-pipeline-architecture)
- [Technical Stack](#-technical-stack)
- [Project Structure](#-project-structure)
- [Key Metrics](#-key-metrics)
- [Data Privacy](#-data-privacy)
- [License](#-license)
- [Author](#-author)

---

## 🎯 Project Goal

This project implements a **multi-phase research pipeline** for pharmaceutical market analysis. The core objective is to determine **drug substitution coefficients** — quantitative measures of how likely customers are to switch to an alternative drug when their preferred product is out of stock at a pharmacy.

### Research Questions

1. **Do drugs exhibit a general substitution tendency** not just on one local market, but across ALL studied local markets?
2. **Can we determine a reliable substitution coefficient** for each drug based on cross-market data?
3. **What is the correct methodology** for calculating such coefficients?
4. **What statistical requirements** must a drug meet for its coefficient to be considered reliable?

### Expected Outcome

For each drug present across multiple markets, produce:
- A **substitution coefficient** (weighted mean of SHARE_INTERNAL across markets)
- **Confidence intervals** (95% CI)
- **Reliability classification** (CRITICAL / SUBSTITUTABLE / MODERATE)
- **Coverage analysis** (on how many markets the drug was observed)

---

## 💼 Business Context

### The Problem

When a pharmacy runs out of a specific drug (a **stock-out event**), customers face a choice:

```
Customer arrives for Drug X (out of stock):
├── Buys a substitute (Drug Y) at the SAME pharmacy    → INTERNAL demand
└── Leaves to buy Drug X at a DIFFERENT pharmacy        → LOST demand
```

Understanding this behavior is critical for:

| Stakeholder | Value |
|:---|:---|
| **Pharmacy chains** | Optimize SKU portfolio — which drugs are safe to delist? |
| **Distributors** | Predict demand shifts during supply disruptions |
| **Manufacturers** | Understand competitive vulnerability of their products |

### Methodology: Difference-in-Differences (DiD)

The pipeline applies the **DiD** econometric approach:

- **Treatment group:** Target pharmacy experiencing stock-out
- **Control group:** Competitor pharmacies (no stock-out)
- **Treatment period:** Weeks when the drug is absent
- **Measured effect:** Change in substitute drug sales (LIFT) beyond normal market growth

This isolates the **pure substitution effect** from seasonal trends, promotions, and general demand shifts.

---

## 🔧 Pipeline Architecture

The pipeline consists of two major phases:

### Phase 1: Per-Market DiD Processing

Executed **independently for each local market** (pharmacy + its competitors):

| Step | Script | Description |
|:---:|:---|:---|
| 0 | `01_preproc.py` | Preprocessing — build reference lists (INN, NFC, drugs) |
| 1 | `02_01_data_aggregation.py` | Weekly aggregation, gap filling, market indicators |
| 2 | `02_02_stockout_detection.py` | Identify stock-out events per drug per pharmacy |
| 3 | `02_03_did_analysis.py` | DiD calculation — baseline, expected, actual, LIFT |
| 4 | `02_04_substitute_analysis.py` | Substitute share analysis — INTERNAL vs LOST |
| 5 | `02_05_reports_cross_market.py` | Excel reports + cross-market CSV export |

> Steps 1–5 are independent per market and designed for **parallel execution** via `ProcessPoolExecutor`.

### Phase 2: Cross-Market Aggregation

Aggregates results from all local markets:

| Step | Script | Description |
|:---:|:---|:---|
| 1 | `01_data_preparation.py` | Coverage analysis, data assembly |
| 2 | `02_coefficient_aggregation.py` | Weighted mean, CI, CV, classification *(planned)* |
| 3 | `03_output_generation.py` | Final reports and output files *(planned)* |

### Pipeline Diagram

```
Raw Data (Rd2_*.csv)
        │
        ▼
  ┌─────────────┐
  │  Phase 0    │  Preprocessing (once for all markets)
  │  01_preproc │
  └──────┬──────┘
         │
         ▼
  ┌─────────────────────────────────────────────────────┐
  │              Phase 1 (per market, parallel)          │
  │                                                      │
  │  Aggregation → Stockout → DiD → Substitutes → Reports│
  │                                                      │
  │  Market A ═══════════════════════════════════════►   │
  │  Market B ═══════════════════════════════════════►   │
  │  Market C ═══════════════════════════════════════►   │
  │  ...                                                 │
  └──────────────────────┬──────────────────────────────┘
                         │
                         ▼
  ┌─────────────────────────────────┐
  │        Phase 2                   │
  │  Cross-Market Aggregation        │
  │  Coefficients + Classification   │
  └─────────────────────────────────┘
```

---

## 🛠 Technical Stack

| Component | Technology | Version |
|:---|:---|:---|
| Language | Python | 3.11 |
| Data Processing | pandas | 2.3.3 |
| Numerical Computing | NumPy | 2.3.1 |
| Statistical Analysis | SciPy | 1.16.3 |
| Visualization | Matplotlib + Seaborn | 3.10.7 / 0.13.2 |
| Excel Reports | openpyxl + XlsxWriter | 3.1.5 / 3.2.3 |
| Parallelization | concurrent.futures (ProcessPoolExecutor) | stdlib |
| Environment | Conda (proxima) | — |

### Key Technical Decisions

- **Per-market file isolation** — each market writes to its own directory, enabling safe parallel processing
- **Intermediate file persistence** — all intermediate results are saved as CSV for debugging and auditability
- **Configuration-driven thresholds** — all classification thresholds, NFC compatibility rules, and stockout parameters are defined in `project_core/` config modules
- **Modular utility functions** — shared ETL and DiD logic in `project_core/utility_functions/`

---

## 📁 Project Structure

```
cross_pharm_market_analysis/
│
├── project_core/                          # Configuration & utilities
│   ├── data_config/                       # Paths, column mapping
│   ├── did_config/                        # DiD thresholds, NFC rules, stockout params
│   ├── sub_coef_config/                   # Phase 2 coverage thresholds
│   ├── calculation_parameters_config/     # Machine & parallelization params
│   └── utility_functions/                 # Shared ETL & DiD functions
│
├── exec_scripts/                          # Executable pipeline scripts
│   ├── 01_did_processing/                 # Phase 1: per-market scripts
│   ├── 02_substitution_coefficients/      # Phase 2: cross-market scripts
│   └── run_full_pipeline.py               # Pipeline orchestrator
│
├── data/
│   ├── raw/                               # Input data (Rd2_*.csv) — NOT in repo
│   └── processed_data/                    # Intermediate results — NOT in repo
│       ├── 00_preproc_results/            # Reference lists
│       └── 01_per_market/{CLIENT_ID}/     # Per-market processing outputs
│
├── results/                               # Final outputs — NOT in repo
│   ├── cross_market_data/                 # Cross-market CSV files
│   ├── data_reports/                      # Excel reports per market
│   └── substitution_research/             # Phase 2 outputs
│
└── docs/                                  # Project documentation
    ├── 00_ai_rules/                       # AI assistant context & rules
    ├── 01_did_processing/                 # Phase 1 methodology docs
    ├── 02_substitution_coefficients/      # Phase 2 methodology docs
    └── _project_tech_parameters/          # Machine & computing docs
```

---

## 📊 Key Metrics

### Per-Market Metrics (Phase 1)

| Metric | Formula | Interpretation |
|:---|:---|:---|
| `SHARE_INTERNAL` | INTERNAL_LIFT / TOTAL_EFFECT | Share of demand retained by the pharmacy |
| `SHARE_LOST` | LOST_SALES / TOTAL_EFFECT | Share of demand lost to competitors |
| `SHARE_SAME_NFC1` | LIFT_SAME_NFC1 / INTERNAL_LIFT | Share that chose the same dosage form |

### Cross-Market Metrics (Phase 2)

| Metric | Formula | Interpretation |
|:---|:---|:---|
| `MARKET_COVERAGE` | N_markets / N_total | % of markets where the drug is present |
| `WEIGHTED_MEAN_SHARE` | Σ(SHARE × WEIGHT) / Σ(WEIGHT) | Weighted substitution coefficient |
| `CI_95` | mean ± 1.96 × (std / √N) | 95% confidence interval |
| `CV_PERCENT` | (STD / MEAN) × 100 | Coefficient of variation |

### Drug Classification

| Category | Condition | Business Decision |
|:---|:---|:---|
| **CRITICAL** | CI upper bound < low threshold | Must keep in stock |
| **SUBSTITUTABLE** | CI lower bound > high threshold | Safe to optimize SKU |
| **MODERATE** | Otherwise | Analyze individually |

---

## 🔒 Data Privacy

- All **sensitive and proprietary data** has been removed from this repository
- The `data/raw/`, `data/processed_data/`, and `results/` directories are **excluded via `.gitignore`**
- Any data samples referenced in documentation are **anonymized** and use **synthetic identifiers**
- No personally identifiable information (PII) is present in the codebase
- See [SECURITY.md](SECURITY.md) for the full data privacy statement

---

## 📄 License

**© 2026 Radyslav Lomanov. All Rights Reserved.**

This project is proprietary. No part of this codebase, documentation, or methodology may be reproduced, distributed, or used in any form without the **explicit written consent** of the author.

See [LICENSE](LICENSE) for full terms.

---

## 👤 Author

**Radyslav Lomanov**

Data Scientist & Pharmaceutical Market Analyst

| Contact | Link |
|:---|:---|
| 📧 Email | [lomanov.mail@gmail.com](mailto:lomanov.mail@gmail.com) |
| 💬 Telegram | [@radyslav_datascience](https://t.me/radyslav_datascience) |

---

<p align="center">
  <sub>Built with 🐍 Python • 📊 pandas • 📈 scipy</sub>
</p>
