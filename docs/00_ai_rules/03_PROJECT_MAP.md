# PROJECT MAP - cross_pharm_market_analysis

> **Версія:** 2.1 | **Оновлено:** 10.02.2026

---

## 1. ОГЛЯД PIPELINE

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        MULTI-MARKET RESEARCH PIPELINE                        │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  Phase 0           Phase 1              Phase 2           Phase 3           │
│  ─────────         ─────────            ─────────         ─────────         │
│  Preproc      →    Per-Market      →    Cross-Market  →   Final            │
│  (lists,stats)     Processing           Aggregation       Reports           │
│                                                                              │
│  [01_preproc.py]   [For each market]    [CI, Coverage]   [Excel, CSV]      │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. ДЕТАЛЬНИЙ PIPELINE

### Phase 0: Preprocessing (`exec_scripts/01_did_processing/01_preproc.py`) ✅

| Скрипт | Опис | Вхід | Вихід |
|--------|------|------|-------|
| `01_preproc.py` | Збір списків та статистики | `data/raw/Rd2_*.csv` | `data/processed_data/00_preproc_results/` |

**Вихідні файли:**
- `target_pharmacies_list.csv` — список CLIENT_ID
- `inn_list.csv` — INN_ID + INN_NAME
- `nfc1_list.csv`, `nfc2_list.csv` — форми випуску
- `drugs_list.csv` — DRUGS_ID + DRUGS_NAME
- `markets_statistics.csv` — статистика по ринках

---

### Phase 1: Per-Market Processing (`exec_scripts/01_did_processing/`)

Виконується для кожного файлу `Rd2_{CLIENT_ID}.csv`:

| Скрипт | Опис | Статус |
|--------|------|--------|
| `02_01_data_aggregation.py` | Агрегація, gap filling | ✅ |
| `02_02_stockout_detection.py` | Детекція stock-out | ✅ |
| `02_03_did_analysis.py` | DiD розрахунки | ✅ |
| `02_04_substitute_analysis.py` | SUBSTITUTE_SHARE | ✅ |
| `02_05_reports_cross_market.py` | Excel звіти + CSV для cross-market | ✅ |

**Вхід/Вихід:**
```
raw/Rd2_{CLIENT_ID}.csv → 01_per_market/{CLIENT_ID}/01_aggregation_{CLIENT_ID}/
                        → 01_per_market/{CLIENT_ID}/02_stockout_{CLIENT_ID}/
                        → 01_per_market/{CLIENT_ID}/03_did_analysis_{CLIENT_ID}/
                        → 01_per_market/{CLIENT_ID}/04_substitute_shares_{CLIENT_ID}/
                        → results/data_reports/reports_{CLIENT_ID}/
                        → results/cross_market_data/
```

**Залежності:** `02_01 → 02_02 → 02_03 → 02_04 → 02_05` (послідовно для кожного ринку)

---

### Phase 2: Cross-Market Aggregation (в розробці)

| Скрипт | Опис |
|--------|------|
| `01_data_preparation.py` | Підготовка даних, coverage аналіз ✅ |
| `02_coefficient_aggregation.py` | Агрегація коефіцієнтів, CI, класифікація (планується) |
| `03_output_generation.py` | Генерація вихідних файлів (планується) |

---

### Phase 3: Final Reports (планується)

| Скрипт | Опис |
|--------|------|
| `10_cross_market_report.py` | Крос-ринковий звіт |
| `11_summary.py` | Текстовий summary |

---

## 3. СТРУКТУРА ПРОЕКТУ

```
cross_pharm_market_analysis/
│
├── project_core/                        # Конфігурація та утиліти
│   ├── data_config/                     # Шляхи, ID аптек, INN групи ✅
│   ├── did_config/                      # Phase 1: Пороги, NFC сумісність ✅
│   ├── sub_coef_config/                 # Phase 2: Параметри агрегації
│   └── utility_functions/               # ETL, DiD функції ✅
│
├── data/
│   ├── raw/                             # Вхідні дані (READ-ONLY)
│   │   └── Rd2_{CLIENT_ID}.csv          # 5 тестових ринків
│   │
│   └── processed_data/
│       ├── 00_preproc_results/          # ✅ Preprocessing
│       │
│       ├── 01_per_market/               # ✅ Per-market processing
│       │   └── {CLIENT_ID}/
│       │       ├── 01_aggregation_{CLIENT_ID}/   # ✅ Step 1
│       │       │   ├── inn_{INN_ID}_{CLIENT_ID}.csv
│       │       │   └── _stats/
│       │       │       ├── stats_inn_{INN_ID}.csv
│       │       │       ├── _summary.csv
│       │       │       └── _inn_summary.csv
│       │       │
│       │       ├── 02_stockout_{CLIENT_ID}/      # ✅ Step 2
│       │       ├── 03_did_analysis_{CLIENT_ID}/  # ✅ Step 3
│       │       └── 04_substitute_shares_{CLIENT_ID}/ # ✅ Step 4
│       │
│       └── 02_cross_market/             # планується
│
├── exec_scripts/
│   ├── 01_did_processing/               # ✅ Phase 1 скрипти
│   │   ├── 01_preproc.py
│   │   ├── 02_01_data_aggregation.py
│   │   ├── 02_02_stockout_detection.py
│   │   ├── 02_03_did_analysis.py
│   │   ├── 02_04_substitute_analysis.py
│   │   └── 02_05_reports_cross_market.py
│   └── 02_substitution_coefficients/    # Phase 2 скрипти
│
├── results/                             # ✅ Звіти та CSV
│   ├── data_reports/
│   │   └── reports_{CLIENT_ID}/
│   │       ├── 01_technical_report_{CLIENT_ID}.xlsx
│   │       └── 02_business_report_{CLIENT_ID}.xlsx
│   └── cross_market_data/
│       └── cross_market_{CLIENT_ID}.csv
│
└── docs/
    ├── 00_ai_rules/
    ├── 01_did_processing/
    ├── 02_substitution_coefficients/
    └── _project_history/
```

---

## 4. ГРАФ ЗАЛЕЖНОСТЕЙ

```
                         ┌─────────────────┐
                         │  raw/Rd2_*.csv  │
                         │   (5+ files)    │
                         └────────┬────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────┐
│ PHASE 0: Preprocessing (01_preproc.py) ✅                       │
│ → data/processed_data/00_preproc_results/                       │
└─────────────────────────────────────────────────────────────────┘
                                  │
            ┌─────────────────────┼─────────────────────┐
            │                     │                     │
            ▼                     ▼                     ▼
     ┌──────────┐          ┌──────────┐          ┌──────────┐
     │ Market 1 │          │ Market 2 │   ...    │ Market N │
     └────┬─────┘          └────┬─────┘          └────┬─────┘
          │                     │                     │
          ▼                     ▼                     ▼
┌─────────────────────────────────────────────────────────────────┐
│ PHASE 1: Per-Market Processing (parallel)                       │
│ aggregation → stockout → did → substitute → report              │
└─────────────────────────────────────────────────────────────────┘
          │                     │                     │
          └─────────────────────┼─────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│ PHASE 2: Cross-Market Aggregation                               │
│ collect → coverage → statistical analysis                       │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│ PHASE 3: Final Reports                                          │
│ cross_market_report → summary                                   │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
                    ┌─────────────────────────┐
                    │        results/         │
                    └─────────────────────────┘
```

---

## 5. КОМАНДИ ВИКОНАННЯ

### Phase 0: Preprocessing
```bash
cd /Users/radyslav/data_analysis/proxima/cross_pharm_market_analysis
/opt/miniconda3/envs/proxima/bin/python exec_scripts/01_did_processing/01_preproc.py
```

### Phase 1, Step 1: Data Aggregation
```bash
# Один ринок:
/opt/miniconda3/envs/proxima/bin/python exec_scripts/01_did_processing/02_01_data_aggregation.py --market_id 28670

# Всі ринки:
/opt/miniconda3/envs/proxima/bin/python exec_scripts/01_did_processing/02_01_data_aggregation.py --all
```

### Phase 1, Step 2: Stockout Detection
```bash
# Один ринок:
/opt/miniconda3/envs/proxima/bin/python exec_scripts/01_did_processing/02_02_stockout_detection.py --market_id 28670

# Всі ринки:
/opt/miniconda3/envs/proxima/bin/python exec_scripts/01_did_processing/02_02_stockout_detection.py --all
```

### Phase 1, Step 3: DiD Analysis
```bash
# Один ринок:
/opt/miniconda3/envs/proxima/bin/python exec_scripts/01_did_processing/02_03_did_analysis.py --market_id 28670

# Всі ринки:
/opt/miniconda3/envs/proxima/bin/python exec_scripts/01_did_processing/02_03_did_analysis.py --all
```

### Phase 1, Step 4: Substitute Analysis
```bash
# Один ринок:
/opt/miniconda3/envs/proxima/bin/python exec_scripts/01_did_processing/02_04_substitute_analysis.py --market_id 28670

# Всі ринки:
/opt/miniconda3/envs/proxima/bin/python exec_scripts/01_did_processing/02_04_substitute_analysis.py --all
```

### Phase 1, Step 5: Reports Generation
```bash
# Один ринок:
/opt/miniconda3/envs/proxima/bin/python exec_scripts/01_did_processing/02_05_reports_cross_market.py --market_id 28670

# Всі ринки:
/opt/miniconda3/envs/proxima/bin/python exec_scripts/01_did_processing/02_05_reports_cross_market.py --all
```

---

## 6. КЛЮЧОВІ ДОКУМЕНТИ

| Документ | Призначення |
|----------|-------------|
| `docs/00_ai_rules/00_CLAUDE_RULES.md` | Правила роботи з проектом |
| `docs/00_ai_rules/01_BUSINESS_CONTEXT.md` | Бізнес-контекст та метрики |
| `docs/00_ai_rules/02_KNOWN_ISSUES.md` | Відомі проблеми та рішення |
| `docs/_project_history/00_WORK_HISTORY.md` | Історія змін |
| `project_core/data_config/` | Конфігурація даних |
| `project_core/did_config/` | Конфігурація дослідження |
| `project_core/utility_functions/` | Функції-утиліти |

---

## 7. ОНОВЛЕННЯ ЦЬОГО ДОКУМЕНТА

**При зміні структури проекту оновити:**
1. Секцію "ДЕТАЛЬНИЙ PIPELINE" — якщо додано/видалено скрипти
2. Секцію "СТРУКТУРА ПРОЕКТУ" — якщо змінились папки
3. Секцію "ГРАФ ЗАЛЕЖНОСТЕЙ" — якщо змінились зв'язки
4. Версію документа та дату
