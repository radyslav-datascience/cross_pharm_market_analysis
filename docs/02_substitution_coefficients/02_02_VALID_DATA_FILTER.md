# VALID DATA FILTER - Phase 2

> **Версія:** 1.0 | **Створено:** 04.03.2026

---

## 1. ПРИЗНАЧЕННЯ

Фільтрація препаратів за критеріями якості даних для відбору тих, що мають достатньо надійні коефіцієнти субституції для бізнес-рішень.

**Реалізація:** `exec_scripts/02_substitution_coefficients/02_02_valid_data_filter.py`

---

## 2. ПРОБЛЕМА

### Вхідні дані
Після статистичного аналізу (Step 2.2 part 1) кожен препарат має:
- `COVERAGE_CLUSTER` — на скількох ринках присутній (HIGH/MEDIUM/LOW/INSUFFICIENT)
- `RELIABILITY` — наскільки стабільний коефіцієнт (HIGH/MEDIUM/LOW/SINGLE_MARKET)

### Задача
Відібрати препарати з **достатнім покриттям** та **надійними коефіцієнтами** для подальшого аналізу.

---

## 3. КРИТЕРІЇ ФІЛЬТРАЦІЇ

### 3.1. Scenario A (strict)

Обраний сценарій фільтрації — AND-логіка двох критеріїв:

```
VALID = COVERAGE_CLUSTER ∈ {HIGH, MEDIUM}
    AND RELIABILITY ∈ {HIGH, MEDIUM}
```

### 3.2. Пороги з конфігурації

| Параметр | Джерело | Опис |
|----------|---------|------|
| COVERAGE_HIGH (≥50%) | `project_core/sub_coef_config/coverage_thresholds.py` | Присутність на ≥50% ринків |
| COVERAGE_MEDIUM (≥20%) | `project_core/sub_coef_config/coverage_thresholds.py` | Присутність на ≥20% ринків |
| RELIABILITY_HIGH (<0.15) | `project_core/sub_coef_config/reliability_thresholds.py` | VARIATION_COEFFICIENT < 0.15 |
| RELIABILITY_MEDIUM (<0.30) | `project_core/sub_coef_config/reliability_thresholds.py` | VARIATION_COEFFICIENT < 0.30 |

### 3.3. Причини відхилення

Кожен відхилений препарат отримує `REJECT_REASON`:

| Категорія | Умова |
|-----------|-------|
| Тільки COVERAGE | COVERAGE ∈ {LOW, INSUFFICIENT}, але RELIABILITY ∈ {HIGH, MEDIUM} |
| Тільки RELIABILITY | COVERAGE ∈ {HIGH, MEDIUM}, але RELIABILITY ∈ {LOW, SINGLE_MARKET} |
| Обидва критерії | COVERAGE ∈ {LOW, INSUFFICIENT} та RELIABILITY ∈ {LOW, SINGLE_MARKET} |

---

## 4. PIPELINE

```
┌─────────────────────────────────────────────────────────────────────────────┐
│              PHASE 2 STEP 2.2 part 2: VALID DATA FILTER                    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  4.1 ЗАВАНТАЖЕННЯ                                                          │
│      drug_statistics.csv (Step 2.2 part 1)                                 │
│      all_drugs_list.csv (Step 2.1)                                         │
│      data/raw/Rd2_*.csv → підрахунок унікальних DRUGS_ID                   │
│      ↓                                                                      │
│  4.2 ФІЛЬТРАЦІЯ (Scenario A — strict)                                      │
│      COVERAGE ∈ {HIGH, MEDIUM} AND RELIABILITY ∈ {HIGH, MEDIUM}            │
│      ↓                                                                      │
│      → valid_drugs (FILTER_STATUS = VALID)                                 │
│      → rejected_drugs (FILTER_STATUS = REJECTED + REJECT_REASON)           │
│      ↓                                                                      │
│  4.3 CROSS-TABLE                                                           │
│      COVERAGE_CLUSTER × RELIABILITY → counts, ratios, combined            │
│      ↓                                                                      │
│  4.4 PIPELINE FUNNEL                                                       │
│      Raw drugs → Researched → Filter passed                                │
│      + Інтерполяція (логарифмічна модель)                                  │
│      ↓                                                                      │
│  4.5 ВАЛІДАЦІЯ (14 checks)                                                 │
│      ↓                                                                      │
│  4.6 ЕКСПОРТ (CSV + XLSX)                                                  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 5. ВХІДНІ ДАНІ

| Джерело | Шлях | Призначення |
|---------|------|-------------|
| Drug statistics | `.../02_01_statistical_analysis/drug_statistics.csv` | Статистики per drug (507 рядків) |
| All drugs list | `.../01_preparation/all_drugs_list.csv` | Генеральна сукупність (652 рядки) |
| Raw data | `data/raw/Rd2_*.csv` | Підрахунок унікальних DRUGS_ID для воронки |

---

## 6. ВИХІДНІ ДАНІ

### 6.1. CSV файли

Шлях: `results/substitution_research/02_statistics_and_filter/02_02_valid_data_filter/`

| Файл | Опис |
|------|------|
| `valid_drugs.csv` | Препарати що пройшли фільтр |
| `rejected_drugs.csv` | Відхилені препарати з причинами |
| `filter_summary.csv` | Агреговані метрики фільтрації |
| `validation_report.txt` | Результати 14 валідаційних перевірок |

### 6.2. XLSX бізнес-звіти

Шлях: `.../02_02_valid_data_filter/filter_business_reports/`

| Файл | Sheets | Опис |
|------|--------|------|
| `valid_drugs.xlsx` | Valid Drugs | З кольоровим маркуванням COVERAGE/RELIABILITY |
| `rejected_drugs.xlsx` | Rejected Drugs | З причинами відхилення |
| `cross_table_distribution.xlsx` | Counts, Ratios, Combined | Крос-таблиця COVERAGE × RELIABILITY |
| `pipeline_funnel.xlsx` | Pipeline Funnel, Interpolation | Воронка + інтерполяція |

### 6.3. Порядок колонок (valid_drugs, rejected_drugs)

Колонки згруповані логічними блоками:

| Блок | Колонки |
|------|---------|
| ID | FILTER_STATUS, DRUGS_ID, DRUGS_NAME, INN_ID, INN_NAME, NFC1_ID |
| Coverage | COVERAGE_CLUSTER, MARKET_COVERAGE, MARKET_COUNT_TOTAL, MARKET_COUNT_CLEAN, OUTLIERS_COUNT |
| Reliability | RELIABILITY, VARIATION_COEFFICIENT, STD_SHARE_INTERNAL |
| Центральні метрики | MEDIAN_SHARE_INTERNAL, MEAN_SHARE_INTERNAL, WEIGHTED_MEAN_SHARE |
| CI & розподіл | CI_95_LOWER, CI_95_UPPER, MIN/Q1/Q3/MAX/IQR_SHARE_INTERNAL |
| Обсяг | TOTAL_EVENTS, TOTAL_INTERNAL_LIFT |
| (rejected only) | REJECT_REASON |

---

## 7. CROSS-TABLE (COVERAGE × RELIABILITY)

Крос-таблиця показує розподіл препаратів по двох вимірах якості:

```
              COVERAGE ↓ \ RELIABILITY →
              ┌────────┬────────┬────────┬──────────────┬────────┐
              │  HIGH  │ MEDIUM │  LOW   │ SINGLE_MARKET│ TOTAL  │
├─────────────┼────────┼────────┼────────┼──────────────┼────────┤
│ HIGH        │  ✓✓    │  ✓✓    │   ✗    │     ✗        │        │
│ MEDIUM      │  ✓✓    │  ✓✓    │   ✗    │     ✗        │        │
│ LOW         │   ✗    │   ✗    │   ✗    │     ✗        │        │
│ INSUFFICIENT│   ✗    │   ✗    │   ✗    │     ✗        │        │
├─────────────┼────────┼────────┼────────┼──────────────┼────────┤
│ TOTAL       │        │        │        │              │        │
└─────────────┴────────┴────────┴────────┴──────────────┴────────┘

✓✓ = проходить фільтр (Scenario A)
✗  = відхилено
```

**Вихідні формати (3 sheets):**
- **Counts** — абсолютна кількість препаратів
- **Ratios** — частки від загальної кількості досліджених
- **Combined** — "count (ratio%)"

---

## 8. PIPELINE FUNNEL

Воронка показує шлях від повної популяції до відфільтрованих препаратів:

```
Raw drugs (data/raw/) ─── 100% (генеральна сукупність)
    ↓
Researched drugs ──────── ≤100% (мали stock-out events)
    ↓
Filter passed ─────────── ≤100% (COVERAGE & RELIABILITY ok)
```

Кожен рівень має:
- `RATIO_VS_RAW` — частка від генеральної сукупності
- `RATIO_VS_RESEARCHED` — частка від досліджених

---

## 9. ІНТЕРПОЛЯЦІЯ

### 9.1. Модель

Логарифмічна апроксимація (закон зменшення віддачі):

```
rate(N) = rate_current × ln(N) / ln(N_current)
N_target = N_current ^ (1 / rate_current)
```

### 9.2. Дві оцінки

| Оцінка | Rate | Питання | Оцінка реалістичності |
|--------|------|---------|----------------------|
| **Research coverage** | researched / raw | Скільки ринків щоб усі потрапили в дослідження | Реалістична |
| **Filter pass rate** | valid / raw | Скільки ринків щоб усі пройшли фільтр | Нереалістична |

### 9.3. Обмеження

**Research coverage** — реалістична оцінка: більше ринків → більше stock-out events → більше препаратів досліджено.

**Filter pass rate** — нереалістична: RELIABILITY залежить від природної варіативності субституції препарату, а не лише від кількості ринків. Препарати з нестабільною субституцією не пройдуть фільтр незалежно від кількості даних.

---

## 10. ВАЛІДАЦІЯ

### 14 перевірок

| # | Перевірка | Що перевіряє |
|---|-----------|-------------|
| 1 | COMPLETENESS | valid + rejected = total |
| 2 | VALID_NO_DUPLICATES | Унікальність DRUGS_ID у valid |
| 3 | REJECTED_NO_DUPLICATES | Унікальність DRUGS_ID у rejected |
| 4 | NO_OVERLAP | Жодного DRUGS_ID одночасно в обох |
| 5 | VALID_COVERAGE_CRITERIA | Всі valid мають COVERAGE ∈ {HIGH, MEDIUM} |
| 6 | VALID_RELIABILITY_CRITERIA | Всі valid мають RELIABILITY ∈ {HIGH, MEDIUM} |
| 7 | REJECTED_HAVE_REASON | Кожен rejected не відповідає хоча б одному критерію |
| 8 | CROSS_TABLE_TOTAL | Сума cross-table = total |
| 9-12 | CROSS_TABLE_ROW_* | Суми рядків cross-table збігаються з маргіналами |
| 13 | VALID_FILTER_STATUS | Всі valid мають FILTER_STATUS = 'VALID' |
| 14 | REJECTED_FILTER_STATUS | Всі rejected мають FILTER_STATUS = 'REJECTED' |

---

## 11. EDGE CASES

| Ситуація | Поведінка |
|----------|-----------|
| Всі препарати valid | rejected_drugs буде порожній, REJECT_REASON не генерується |
| Всі препарати rejected | valid_drugs буде порожній |
| N=1 для препарату | RELIABILITY = SINGLE_MARKET → автоматично rejected |
| VARIATION_COEFFICIENT = NaN | RELIABILITY = SINGLE_MARKET → rejected |

---

## 12. НАВІГАЦІЯ

| Ресурс | Посилання |
|--------|-----------|
| Pipeline Phase 2 | [00_PIPELINE_PHASE_2.md](./00_PIPELINE_PHASE_2.md) |
| Бізнес-контекст | [_SUBSTITUTION_BUSINESS_CONTEXT.md](./_SUBSTITUTION_BUSINESS_CONTEXT.md) |
| Підготовка даних (Step 2.1) | [01_DATA_PREPARATION_AND_OUTPUTS.md](./01_DATA_PREPARATION_AND_OUTPUTS.md) |
| Статистичний аналіз (Step 2.2 part 1) | [02_01_STATISTICAL_METHODOLOGY.md](./02_01_STATISTICAL_METHODOLOGY.md) |
| Coverage пороги | `project_core/sub_coef_config/coverage_thresholds.py` |
| Reliability пороги | `project_core/sub_coef_config/reliability_thresholds.py` |
