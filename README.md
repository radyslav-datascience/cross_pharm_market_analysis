<p align="center">
  <h1 align="center">💊 Cross-Pharma Market Analysis</h1>
  <p align="center">
    <strong>Multi-Market Pharmaceutical Substitution Research Pipeline with Parallel Computing</strong>
  </p>
  <p align="center">
    <em>Difference-in-Differences approach to drug substitutability estimation across local pharmacy markets</em>
  </p>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/python-3.13-blue?logo=python&logoColor=white" alt="Python 3.13">
  <img src="https://img.shields.io/badge/pandas-2.3-green?logo=pandas&logoColor=white" alt="pandas">
  <img src="https://img.shields.io/badge/scipy-1.16-orange" alt="scipy">
  <img src="https://img.shields.io/badge/parallel-ProcessPool%20%2B%20ThreadPool-blueviolet" alt="Parallel Computing">
  <img src="https://img.shields.io/badge/license-All%20Rights%20Reserved-red" alt="License">
  <img src="https://img.shields.io/badge/status-Completed-brightgreen" alt="Status">
</p>

---

## 📋 Table of Contents

- [Project Goal](#-project-goal)
- [Research Results](#-research-results)
- [Business Context](#-business-context)
- [Pipeline Architecture](#-pipeline-architecture)
- [Parallel Computing](#-parallel-computing)
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

## � Research Results

> **Project Status: COMPLETED** — All phases executed, data validated, results exported.

### Dataset Summary

| Parameter | Value |
|:---|:---|
| Local pharmacy markets analyzed | **10** |
| Unique drugs in raw data | **611** |
| Drugs with completed DiD research | **353** (57.8% coverage) |
| Total stock-out drug records across all markets | **1 675** |
| Total substitute drug pairs identified | **23 222** |
| Average markets per drug | **4.75** |

### Key Findings

| Finding | Detail |
|:---|:---|
| **Drugs with good internal substitution** | **904** records (54%) — pharmacy retains demand |
| **Drugs critical for stock (high competitor loss)** | **771** records (46%) — demand lost to competitors |
| **High cross-market coverage drugs** (≥7 markets) | **170** drugs — most reliable coefficients |
| **Medium coverage** (4–6 markets) | **111** drugs |
| **Low coverage** (1–3 markets) | **72** drugs |
| **Insufficient coverage** | **0** drugs — all researched drugs have usable data |

### Output Files

The pipeline produces three categories of outputs per market:

| Output | Path | Description |
|:---|:---|:---|
| **Substitution coefficients** | `results/cross_market_data/market_substitution_{ID}/sub_coef_{ID}.csv` | Per-drug SHARE_INTERNAL, classification, recommendation |
| **Substitute drug pairs** | `results/cross_market_data/market_substitution_{ID}/sub_drugs_{ID}.csv` | Flat table: which specific drugs substitute each stock-out drug |
| **Business reports** | `results/data_reports/reports_{ID}/` | Technical + business Excel reports per market |
| **Cross-market aggregation** | `results/substitution_research/01_preparation/` | All-drugs list, researched drugs, coverage analysis |

### Conclusions

1. **The DiD methodology successfully isolates substitution effects** — across all 10 markets, the pipeline consistently identifies statistically meaningful demand shifts during stock-out periods.
2. **More than half of studied drugs (54%) show good internal substitution** — when these drugs go out of stock, pharmacies retain the majority of demand through substitute products.
3. **46% of drugs are critical for maintaining stock** — their absence leads to significant demand loss to competitor pharmacies.
4. **Cross-market coverage is excellent** — all 353 researched drugs have data from at least one market, with the average drug appearing in 4.75 markets, providing robust statistical basis for coefficient estimation.
5. **The sub_drugs data reveals specific substitution patterns** — for each stock-out drug, the ranked list of actual substitutes (with share percentages) provides actionable intelligence for SKU optimization.

---

## �💼 Business Context

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

> Steps 1–5 are independent per market and execute in **parallel** via `ProcessPoolExecutor` (5 workers) with nested `ThreadPoolExecutor` (2 threads per worker) for INN-level parallelism within each market. See [Parallel Computing](#-parallel-computing) for details.

### Phase 2: Cross-Market Aggregation

Aggregates results from all local markets:

| Step | Script | Description | Status |
|:---:|:---|:---|:---:|
| 1 | `01_data_preparation.py` | Coverage analysis, data assembly, triangular coefficient matrix | ✅ |
| 2 | `02_coefficient_aggregation.py` | Weighted mean, CI, CV, classification | 📋 Planned |
| 3 | `03_output_generation.py` | Final reports and output files | 📋 Planned |

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
  ┌──────────────────────────────────────────────────────────────┐
  │         Phase 1 (per market, parallel execution)             │
  │         ProcessPoolExecutor × 5 workers                      │
  │                                                              │
  │  Aggregation → Stockout → DiD → Substitutes → Reports       │
  │                           ↕              ↕                   │
  │                    ThreadPool ×2    ThreadPool ×2             │
  │                    (INN-parallel)   (INN-parallel)            │
  │                                                              │
  │  Market A ═══════════════════════════════════════►           │
  │  Market B ═══════════════════════════════════════►           │
  │  Market C ═══════════════════════════════════════►           │
  │  ... (10 markets total)                                      │
  └──────────────────────────┬───────────────────────────────────┘
                             │
                             ▼
  ┌─────────────────────────────────┐
  │        Phase 2                   │
  │  Cross-Market Aggregation        │
  │  Coefficients + Classification   │
  └─────────────────────────────────┘
```

---

## ⚡ Parallel Computing

The pipeline implements a **3-level parallelization architecture** for maximum throughput:

### Architecture

| Level | Mechanism | Scope | Configuration |
|:---:|:---|:---|:---|
| **L1** | `ProcessPoolExecutor` | Markets processed in parallel | 5 workers (of 6 CPU cores) |
| **L2** | Sequential steps | 5 pipeline steps per market | Ordered dependency |
| **L3** | `ThreadPoolExecutor` | INN groups within DiD & Substitute steps | 2 threads per worker |

### Performance

| Metric | Value |
|:---|:---|
| Sequential execution (baseline) | ~23 min |
| Parallel execution (10 markets) | **7 min 05 sec** |
| **Speedup** | **3.3×** |
| Bottleneck | Iterative DiD calculations (~80% of time) |

### Design Decisions

- **5 of 6 cores allocated** — one core reserved for OS and monitoring to prevent system freezing
- **Thread-level INN parallelism** — DiD and substitute analysis steps process independent INN groups concurrently within each market worker
- **Configurable via `machine_parameters.py`** — all parallelization parameters adapt to the host machine's hardware
- **Progress monitoring** — `tqdm` progress bars for real-time per-INN tracking within each worker

---

## 🛠 Technical Stack

| Component | Technology | Version |
|:---|:---|:---|
| Language | Python | 3.13 |
| Data Processing | pandas | 2.3.3 |
| Numerical Computing | NumPy | 2.3.1 |
| Statistical Analysis | SciPy | 1.16.3 |
| Visualization | Matplotlib + Seaborn | 3.10.7 / 0.13.2 |
| Excel Reports | openpyxl + XlsxWriter | 3.1.5 / 3.2.3 |
| Process Parallelism | concurrent.futures (ProcessPoolExecutor) | stdlib |
| Thread Parallelism | concurrent.futures (ThreadPoolExecutor) | stdlib |
| Progress Tracking | tqdm | 4.67 |
| Environment | Conda (base) | — |

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
│   ├── raw/                               # Input data (10 × Rd2_*.csv)
│   └── processed_data/                    # Intermediate results
│       ├── 00_preproc_results/            # Reference lists (INN, NFC, drugs)
│       └── 01_per_market/{CLIENT_ID}/     # Per-market processing outputs
│
├── results/                               # Final outputs
│   ├── cross_market_data/                 # market_substitution_{ID}/ (sub_coef + sub_drugs)
│   ├── data_reports/                      # Excel reports per market (technical + business)
│   └── substitution_research/             # Phase 2 outputs (coverage, coefficients)
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

- This repository contains the **complete project** including all data and results for archival purposes
- All pharmacy and market identifiers use **internal numeric IDs** — no real business names are exposed
- No personally identifiable information (PII) is present in any file
- Drug names are public pharmaceutical product names from official registries
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
