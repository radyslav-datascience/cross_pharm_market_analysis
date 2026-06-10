# DRUG COEFFICIENTS - Phase 3 Step 1

> **Версія:** 1.0 | **Створено:** 27.04.2026

---

## 1. ПРИЗНАЧЕННЯ

Формування таблиці коефіцієнтів субституції препаратів для Power BI:
- Відбір препаратів з достатньою кількістю ринків (`MARKET_COUNT >= 20`)
- Завантаження медіани з Phase 2 (після IQR-фільтрації)
- CSV + XLSX з кольоровим кодуванням рівнів коефіцієнта

**Реалізація:** `exec_scripts/03_final_output/01_drug_coefficients.py`

---

## 2. РЕАЛІЗАЦІЯ

### 2.1. Скрипти

| Скрипт | Опис |
|--------|------|
| `exec_scripts/03_final_output/01_drug_coefficients.py` | Основний скрипт Step 3.1 |

### 2.2. Конфігурація

Параметри фільтрації та кольорового кодування задаються безпосередньо в скрипті
(константи `MIN_MARKET_COUNT`, `COEF_HIGH_THRESHOLD`, `COEF_MEDIUM_THRESHOLD`).

---

## 3. ВХІДНІ ДАНІ

| Джерело | Шлях | Призначення |
|---------|------|-------------|
| Phase 2 статистики | `results/substitution_research/02_statistics_and_filter/02_01_statistical_analysis/drug_statistics.csv` | `MEDIAN_SHARE_INTERNAL` (після IQR), `MARKET_COUNT_TOTAL` |

---

## 4. PIPELINE

```
┌─────────────────────────────────────────────────────────────────────────────┐
│               PHASE 3 STEP 1: DRUG COEFFICIENTS                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  4.1 ЗАВАНТАЖЕННЯ                                                           │
│      drug_statistics.csv (Phase 2)                                          │
│      Перейменування:                                                         │
│        MARKET_COUNT_TOTAL    → MARKET_COUNT                                 │
│        MEDIAN_SHARE_INTERNAL → MEDIAN_SUBSTITUTION_COEF                     │
│      ↓                                                                       │
│  4.2 ФІЛЬТРАЦІЯ                                                             │
│      MARKET_COUNT >= MIN_MARKET_COUNT (20)                                  │
│      ↓                                                                       │
│      → accepted (drug_coefficients.csv)                                     │
│      → rejected (rejected_drugs.csv + REJECT_REASON)                        │
│      ↓                                                                       │
│  4.3 FILTER SUMMARY                                                         │
│      → filter_summary.csv (12 метрик)                                       │
│      ↓                                                                       │
│  4.4 ВАЛІДАЦІЯ (7 checks)                                                   │
│      → validation_report.txt                                                │
│      ↓                                                                       │
│  4.5 XLSX БІЗНЕС-ЗВІТИ                                                      │
│      MEDIAN_SUBSTITUTION_COEF форматується як %                              │
│      Кольорове кодування: HIGH (зелений) / MEDIUM (жовтий) / LOW (червоний) │
│      → coef_business_reports/drug_coefficients.xlsx                         │
│      → coef_business_reports/rejected_drugs.xlsx                            │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 5. ВИХІДНІ ФАЙЛИ

### 5.1. Структура виходів

```
results/substitution_research/03_final_output/03_01_drug_coefficients/
├── drug_coefficients.csv        # Прийняті препарати (Power BI)
├── rejected_drugs.csv           # Відхилені препарати
├── filter_summary.csv           # Summary метрики
├── validation_report.txt        # Результати 7 валідаційних перевірок
│
└── coef_business_reports/       # XLSX для бізнесу
    ├── drug_coefficients.xlsx   # Кольорове кодування по рівнях
    └── rejected_drugs.xlsx
```

### 5.2. drug_coefficients.csv

**Призначення:** Фінальна таблиця коефіцієнтів — основний файл для Power BI.

| Колонка | Тип | Опис |
|---------|-----|------|
| `DRUGS_ID` | int | ID препарату (Morion) |
| `DRUGS_NAME` | str | Повна назва препарату |
| `INN_ID` | int | ID групи діючої речовини |
| `INN_NAME` | str | Назва діючої речовини |
| `NFC1_ID` | str | Широка фармацевтична форма |
| `MARKET_COUNT` | int | Кількість ринків (>= 20) |
| `MEDIAN_SUBSTITUTION_COEF` | float | Коефіцієнт субституції (0–1) |

Сортування: `MEDIAN_SUBSTITUTION_COEF` DESC.

### 5.3. rejected_drugs.csv

Ті ж колонки що й `drug_coefficients.csv` + `REJECT_REASON` = `"MARKET_COUNT < 20"`.
Сортування: `MARKET_COUNT` DESC.

### 5.4. filter_summary.csv

| Метрика | Опис |
|---------|------|
| `TOTAL_RESEARCHED` | Всього досліджених препаратів (Phase 2) |
| `ACCEPTED` | Пройшли фільтр |
| `REJECTED` | Відхилені |
| `ACCEPTANCE_RATIO` | Частка прийнятих |
| `MIN_MARKET_COUNT` | Поріг фільтрації |
| `MAX_MARKET_COUNT_ALL` | Максимум ринків серед усіх |
| `MAX_MARKET_COUNT_REJECTED` | Максимум ринків серед відхилених |
| `MEDIAN_COEF_ACCEPTED` | Медіана коефіцієнту (прийняті) |
| `MEAN_COEF_ACCEPTED` | Середнє коефіцієнту (прийняті) |
| `COEF_HIGH_COUNT` | К-сть препаратів HIGH (>= 70%) |
| `COEF_MEDIUM_COUNT` | К-сть препаратів MEDIUM (40–70%) |
| `COEF_LOW_COUNT` | К-сть препаратів LOW (< 40%) |

---

## 6. ФІЛЬТРАЦІЯ

### 6.1. Критерій

```
ACCEPTED:  MARKET_COUNT >= MIN_MARKET_COUNT (= 20)
REJECTED:  MARKET_COUNT < MIN_MARKET_COUNT
```

Поріг `MIN_MARKET_COUNT = 20` — мінімальна кількість спостережень для стабільного
визначення типу розподілу (Sequential Analyzer, Study 02).

### 6.2. Важлива різниця з Phase 2

Phase 3 застосовує **власний фільтр** (MARKET_COUNT >= 20), незалежний від Phase 2
Scenario A (COVERAGE + RELIABILITY). Препарат може пройти один фільтр і не пройти інший.

---

## 7. КОЛЬОРОВЕ КОДУВАННЯ (XLSX)

| Рівень | Умова | Колір |
|--------|-------|-------|
| **HIGH** | MEDIAN_SUBSTITUTION_COEF >= 0.70 | Зелений |
| **MEDIUM** | 0.40 <= MEDIAN_SUBSTITUTION_COEF < 0.70 | Жовтий |
| **LOW** | MEDIAN_SUBSTITUTION_COEF < 0.40 | Червоний |

---

## 8. ВАЛІДАЦІЯ

| # | Перевірка | Опис |
|---|-----------|------|
| 1 | `COMPLETENESS` | accepted + rejected = total |
| 2 | `COEF_RANGE_ACCEPTED` | Всі коефіцієнти в [0, 1] |
| 3 | `NO_NAN_ACCEPTED` | Немає NaN у `MEDIAN_SUBSTITUTION_COEF` |
| 4 | `MIN_MARKET_COUNT_ACCEPTED` | Всі accepted мають `MARKET_COUNT >= 20` |
| 5 | `MARKET_COUNT_REJECTED` | Жоден rejected не має `MARKET_COUNT >= 20` |
| 6 | `NO_DUPLICATES_ACCEPTED` | Унікальність `DRUGS_ID` у accepted |
| 7 | `NO_OVERLAP` | Жоден `DRUGS_ID` не в обох групах одночасно |

---

## 9. EDGE CASES

| Ситуація | Поведінка |
|----------|-----------|
| Жоден препарат не проходить фільтр | `drug_coefficients.csv` буде порожній |
| Препарат має `MARKET_COUNT = NaN` | Не проходить фільтр (відхиляється) |
| `drug_statistics.csv` не існує | `FileNotFoundError` з підказкою запустити Phase 2 |

---

## 10. НАВІГАЦІЯ

| Ресурс | Посилання |
|--------|-----------|
| Pipeline Phase 3 | [00_PIPELINE_PHASE_3.md](./00_PIPELINE_PHASE_3.md) |
| Substitute Shares (Step 3.2) | [02_SUBSTITUTE_SHARES.md](./02_SUBSTITUTE_SHARES.md) |
| Статистичний аналіз Phase 2 | [../02_substitution_coefficients/02_01_STATISTICAL_METHODOLOGY.md](../02_substitution_coefficients/02_01_STATISTICAL_METHODOLOGY.md) |
