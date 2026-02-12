# DATA PREPARATION AND OUTPUTS - Phase 2 Step 1

> **Версія:** 2.0 | **Оновлено:** 04.02.2026

---

## 1. ПРИЗНАЧЕННЯ

Етап підготовки даних для Phase 2 Cross-Market Aggregation:
- Збір генеральної сукупності препаратів з raw даних
- Ідентифікація препаратів з результатами Phase 1 (DiD аналізу)
- Аналіз покриття ринків для кожного препарату
- Формування широкоформатного датасету коефіцієнтів субституції

---

## 2. РЕАЛІЗАЦІЯ

### 2.1. Скрипти

| Скрипт | Опис |
|--------|------|
| `exec_scripts/02_substitution_coefficients/01_data_preparation.py` | Основний скрипт підготовки даних |

### 2.2. Конфігурація

| Модуль | Параметри |
|--------|-----------|
| `project_core/sub_coef_config/coverage_thresholds.py` | Пороги кластерів покриття |

---

## 3. ВХІДНІ ДАНІ

| Джерело | Шлях | Призначення |
|---------|------|-------------|
| Raw дані | `data/raw/Rd2_{CLIENT_ID}.csv` | Генеральна сукупність препаратів |
| Phase 1 результати | `results/cross_market_data/cross_market_{CLIENT_ID}.csv` | SHARE_INTERNAL, INTERNAL_LIFT per drug per market |
| Preprocessing | `data/processed_data/00_preproc_results/target_pharmacies_list.csv` | Список ринків |

---

## 4. PIPELINE

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    PHASE 2 STEP 1: DATA PREPARATION                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  4.1 ЗАВАНТАЖЕННЯ RAW                                                       │
│      Rd2_*.csv → унікальні (DRUGS_ID, DRUGS_NAME, INN_ID, INN_NAME)         │
│      ↓                                                                       │
│      → all_drugs_list.csv                                                   │
│                                                                              │
│  4.2 ЗАВАНТАЖЕННЯ PHASE 1                                                   │
│      cross_market_*.csv → (DRUGS_ID, SHARE_INTERNAL, INTERNAL_LIFT)         │
│      ↓                                                                       │
│      Підрахунок MARKET_COUNT per drug                                       │
│      ↓                                                                       │
│      MARKET_COVERAGE = MARKET_COUNT / TOTAL_MARKETS                         │
│      ↓                                                                       │
│      COVERAGE_CLUSTER assignment (HIGH/MEDIUM/LOW/INSUFFICIENT)             │
│      ↓                                                                       │
│      → researched_drugs_list.csv                                            │
│                                                                              │
│  4.3 WIDE-FORMAT MATRIX                                                     │
│      Per drug: SHARE_INTERNAL_LOC_{ID}, INTERNAL_LIFT_LOC_{ID},             │
│                EVENTS_COUNT_LOC_{ID} для кожного ринку                      │
│      ↓                                                                       │
│      Сортування: ринки по заповненості (DESC), препарати по coverage (DESC) │
│      ↓                                                                       │
│      → researched_drugs_coefficients.csv (трикутна структура)               │
│                                                                              │
│  4.4 SUMMARY STATISTICS                                                     │
│      → coverage_analysis.csv                                                │
│                                                                              │
│  4.5 VALIDATION                                                             │
│      → validation_report.txt                                                │
│                                                                              │
│  4.6 BUSINESS REPORTS (XLSX)                                                │
│      → prep_business_reports/*.xlsx                                         │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 5. ВИХІДНІ ФАЙЛИ

### 5.1. Структура виходів

```
results/substitution_research/01_preparation/
├── all_drugs_list.csv              # Генеральна сукупність
├── researched_drugs_list.csv       # Препарати з Phase 1 + coverage
├── researched_drugs_coefficients.csv # Wide-format (трикутник)
├── coverage_analysis.csv           # Summary статистика
├── validation_report.txt           # Результати валідації
│
└── prep_business_reports/          # XLSX для бізнесу
    ├── researched_drugs_list.xlsx
    ├── researched_drugs_coefficients.xlsx
    └── coverage_analysis.xlsx
```

### 5.2. all_drugs_list.csv

**Призначення:** Всі унікальні препарати з raw даних (генеральна сукупність).

| Колонка | Тип | Опис |
|---------|-----|------|
| `DRUGS_ID` | int | Унікальний ID препарату (Morion) |
| `DRUGS_NAME` | str | Повна назва препарату |
| `INN_ID` | int | ID групи діючої речовини |
| `INN_NAME` | str | Назва діючої речовини |

### 5.3. researched_drugs_list.csv

**Призначення:** Препарати з результатами Phase 1 DiD аналізу + метрики покриття.

| Колонка | Тип | Опис |
|---------|-----|------|
| `DRUGS_ID` | int | Унікальний ID препарату |
| `DRUGS_NAME` | str | Повна назва препарату |
| `INN_ID` | int | ID групи діючої речовини |
| `INN_NAME` | str | Назва діючої речовини |
| `NFC1_ID` | str | Широка категорія форми випуску |
| `MARKET_COUNT` | int | К-сть ринків з даними по цьому препарату |
| `TOTAL_MARKETS` | int | Загальна к-сть досліджуваних ринків |
| `MARKET_COVERAGE` | float | `MARKET_COUNT / TOTAL_MARKETS` (0.0-1.0) |
| `COVERAGE_CLUSTER` | str | Кластер покриття (пороги в `sub_coef_config/`) |

### 5.4. researched_drugs_coefficients.csv

**Призначення:** Широкоформатна матриця коефіцієнтів субституції з "трикутною" структурою.

**Базові колонки:**

| Колонка | Тип | Опис |
|---------|-----|------|
| `DRUGS_ID` | int | ID препарату |
| `DRUGS_NAME` | str | Назва препарату |
| `INN_ID` | int | ID групи діючої речовини |
| `INN_NAME` | str | Назва діючої речовини |
| `NFC1_ID` | str | Категорія форми випуску |
| `MARKET_COUNT` | int | К-сть ринків з даними |

**Колонки по ринках (для кожного CLIENT_ID):**

| Колонка | Тип | Опис |
|---------|-----|------|
| `SHARE_INTERNAL_LOC_{ID}` | float | Коефіцієнт внутрішньої субституції на ринку ID |
| `INTERNAL_LIFT_LOC_{ID}` | float | Сума LIFT substitutes (для зваженого середнього) |
| `EVENTS_COUNT_LOC_{ID}` | int | К-сть stock-out подій на ринку |

**Примітки:**
- Порядок ринків: за кількістю препаратів (DESC) — для кращого "трикутника"
- Порядок препаратів: за MARKET_COUNT (DESC)
- NaN для ринків, де препарат не досліджувався

### 5.5. coverage_analysis.csv

**Призначення:** Summary статистика по покриттю.

| Метрика | Опис |
|---------|------|
| `TOTAL_MARKETS` | К-сть досліджуваних ринків |
| `TOTAL_DRUGS_RAW` | Всього унікальних препаратів в raw |
| `TOTAL_DRUGS_RESEARCHED` | Препаратів з даними Phase 1 |
| `RAW_COVERAGE_RATE` | `RESEARCHED / RAW` |
| `DRUGS_HIGH_COVERAGE` | К-сть препаратів у кластері HIGH |
| `DRUGS_MEDIUM_COVERAGE` | К-сть препаратів у кластері MEDIUM |
| `DRUGS_LOW_COVERAGE` | К-сть препаратів у кластері LOW |
| `DRUGS_INSUFFICIENT_COVERAGE` | К-сть препаратів у кластері INSUFFICIENT |
| `AVG_MARKETS_PER_DRUG` | Середня к-сть ринків на препарат |
| `AVG_MARKET_COVERAGE` | Середній % покриття |

---

## 6. COVERAGE CLUSTERS

Пороги визначені в `project_core/sub_coef_config/coverage_thresholds.py`:

| Кластер | Критерій | Бізнес-значення |
|---------|----------|-----------------|
| **HIGH** | ≥50% ринків | Найнадійніші дані для висновків |
| **MEDIUM** | 20-49% ринків | Достатньо даних для аналізу |
| **LOW** | 10-19% ринків | Обмежені дані, широкі CI |
| **INSUFFICIENT** | <10% ринків | Недостатньо для надійних висновків |

---

## 7. ВАЛІДАЦІЯ

Скрипт виконує автоматичні перевірки:

| Перевірка | Опис |
|-----------|------|
| `TOTAL_MARKETS` | К-сть ринків = к-сть cross_market файлів |
| `COVERAGE_CLUSTERS` | Σ препаратів по кластерах = TOTAL_RESEARCHED |
| `SHARE_INTERNAL` range | Всі значення в діапазоні [0, 1] |
| `TRIANGLE_STRUCTURE` | Перший препарат має максимальне заповнення |
| `MARKET_MATCH` | Ринки в coefficients = ринки в Phase 1 |
| `MARKET_COUNT` integrity | Фактична к-сть значень = MARKET_COUNT |

Результати записуються в `validation_report.txt`.

---

## 8. БІЗНЕС-ІНТЕРПРЕТАЦІЯ

### INTERNAL_LIFT = 0

Коли `INTERNAL_LIFT = 0` для препарату на ринку:
- Під час stock-out жоден substitute не був обраний покупцями
- Або substitute не існує (єдиний препарат в INN+NFC1)
- Або покупці принципово йдуть до конкурентів
- Результат: `SHARE_INTERNAL = 0%`, `SHARE_LOST = 100%`
- Класифікація: **CRITICAL** — обов'язково тримати в асортименті

---

## 9. НАВІГАЦІЯ

| Ресурс | Посилання |
|--------|-----------|
| Pipeline Phase 2 | [01_PIPELINE_PHASE_2.md](./01_PIPELINE_PHASE_2.md) |
| Бізнес-контекст | [02_SUBSTITUTION_BUSINESS_CONTEXT.md](./02_SUBSTITUTION_BUSINESS_CONTEXT.md) |
| Статистична методологія | [04_STATISTICAL_METHODOLOGY.md](./04_STATISTICAL_METHODOLOGY.md) |
| Coverage thresholds config | `project_core/sub_coef_config/coverage_thresholds.py` |
| Values describe | [01_preparation_values_describe.md](./_substitution_values_describe/01_preparation_values_describe.md) |
