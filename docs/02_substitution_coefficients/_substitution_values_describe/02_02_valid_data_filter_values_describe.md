# Опис значень - Phase 2 Step 2.2 part 2: Valid Data Filter

> **Версія:** 1.0 | **Оновлено:** 04.03.2026

---

## 1. ЗАГАЛЬНА ІНФОРМАЦІЯ

**Вихідна папка:** `results/substitution_research/02_statistics_and_filter/02_02_valid_data_filter/`

**Скрипт-джерело:** `exec_scripts/02_substitution_coefficients/02_02_valid_data_filter.py`

**Конфігурація порогів:**
- `project_core/sub_coef_config/coverage_thresholds.py` (COVERAGE_CLUSTER)
- `project_core/sub_coef_config/reliability_thresholds.py` (RELIABILITY)

**Вхідні дані:**
- `results/substitution_research/02_statistics_and_filter/02_01_statistical_analysis/drug_statistics.csv` (507 рядків)
- `results/substitution_research/01_preparation/all_drugs_list.csv` (генеральна сукупність)
- `data/raw/Rd2_*.csv` (підрахунок унікальних DRUGS_ID для воронки)

**Фільтр:** Scenario A (strict) — AND-логіка двох критеріїв:
```
VALID = COVERAGE_CLUSTER ∈ {HIGH, MEDIUM}
    AND RELIABILITY ∈ {HIGH, MEDIUM}
```

---

## 2. valid_drugs.csv

**Призначення:** Препарати, що пройшли фільтр якості даних. Мають достатнє покриття ринків та надійні (стабільні) коефіцієнти субституції для бізнес-рішень.

### 2.1. Ідентифікатори та статус

| Технічна назва | Розшифровка | Опис | Джерело |
|----------------|-------------|------|---------|
| `FILTER_STATUS` | Filter Status | Завжди `VALID` для цього файлу | Результат фільтрації |
| `DRUGS_ID` | Drug Identifier | Унікальний числовий ідентифікатор препарату | `drug_statistics.csv` |
| `DRUGS_NAME` | Drug Name | Повна назва препарату (виробник, форма, дозування, фасовка) | `drug_statistics.csv` |
| `INN_ID` | INN Identifier | ID групи діючої речовини (МНН) | `drug_statistics.csv` |
| `INN_NAME` | INN Name | Назва групи діючої речовини | `drug_statistics.csv` |
| `NFC1_ID` | NFC Level 1 | Широка категорія форми випуску | `drug_statistics.csv` |

### 2.2. Блок покриття (Coverage)

| Технічна назва | Розшифровка | Опис | Допустимі значення |
|----------------|-------------|------|-------------------|
| `COVERAGE_CLUSTER` | Coverage Cluster | Кластер покриття ринків | Тільки `HIGH` або `MEDIUM` (умова фільтру) |
| `MARKET_COVERAGE` | Market Coverage | Числове значення покриття (0.0 - 1.0) | >= 0.20 (мінімум для MEDIUM) |
| `MARKET_COUNT_TOTAL` | Total Market Count | Загальна к-сть ринків з даними для препарату (включно з outliers) | >= 1 |
| `MARKET_COUNT_CLEAN` | Clean Market Count | К-сть ринків після видалення outliers | >= 1 |
| `OUTLIERS_COUNT` | Outliers Count | К-сть спостережень, визначених як outliers за IQR | >= 0 |

### 2.3. Блок надійності (Reliability)

| Технічна назва | Розшифровка | Опис | Допустимі значення |
|----------------|-------------|------|-------------------|
| `RELIABILITY` | Reliability | Класифікація надійності коефіцієнта | Тільки `HIGH` або `MEDIUM` (умова фільтру) |
| `VARIATION_COEFFICIENT` | Coefficient of Variation | Коефіцієнт варіації — міра однорідності | < 0.30 (мінімум для MEDIUM) |
| `STD_SHARE_INTERNAL` | Standard Deviation | Стандартне відхилення коефіцієнта по ринках | >= 0 |

### 2.4. Центральні метрики SHARE_INTERNAL

| Технічна назва | Розшифровка | Опис | Формула | Діапазон |
|----------------|-------------|------|---------|----------|
| `MEDIAN_SHARE_INTERNAL` | Median Share Internal | Медіанний коефіцієнт субституції | `MEDIAN(SHARE_INTERNAL)` per DRUGS_ID | 0.0 - 1.0 |
| `MEAN_SHARE_INTERNAL` | Mean Share Internal | Середнє арифметичне коефіцієнта | `MEAN(SHARE_INTERNAL)` per DRUGS_ID | 0.0 - 1.0 |
| `WEIGHTED_MEAN_SHARE` | Weighted Mean Share | Зважене середнє (вага = INTERNAL_LIFT) | `Σ(SHARE_i × LIFT_i) / Σ(LIFT_i)` | 0.0 - 1.0 |

### 2.5. Довірчий інтервал та розподіл

| Технічна назва | Розшифровка | Опис | Формула | Діапазон |
|----------------|-------------|------|---------|----------|
| `CI_95_LOWER` | 95% CI Lower Bound | Нижня межа 95% довірчого інтервалу | `MEAN - 1.96 × (STD / √N)`, clip [0, 1] | 0.0 - 1.0 |
| `CI_95_UPPER` | 95% CI Upper Bound | Верхня межа 95% довірчого інтервалу | `MEAN + 1.96 × (STD / √N)`, clip [0, 1] | 0.0 - 1.0 |
| `MIN_SHARE_INTERNAL` | Minimum Share | Мінімальне значення коефіцієнта | `MIN(SHARE_INTERNAL)` | 0.0 - 1.0 |
| `Q1_SHARE_INTERNAL` | First Quartile | 25-й перцентиль | `QUANTILE(0.25)` | 0.0 - 1.0 |
| `Q3_SHARE_INTERNAL` | Third Quartile | 75-й перцентиль | `QUANTILE(0.75)` | 0.0 - 1.0 |
| `MAX_SHARE_INTERNAL` | Maximum Share | Максимальне значення коефіцієнта | `MAX(SHARE_INTERNAL)` | 0.0 - 1.0 |
| `IQR_SHARE_INTERNAL` | Interquartile Range | Міжквартильний розмах | `Q3 - Q1` | >= 0 |

### 2.6. Обсяг даних

| Технічна назва | Розшифровка | Опис | Формула |
|----------------|-------------|------|---------|
| `TOTAL_EVENTS` | Total Events | Загальна к-сть stock-out подій по всіх ринках (clean) | `SUM(EVENTS_COUNT)` per DRUGS_ID |
| `TOTAL_INTERNAL_LIFT` | Total Internal Lift | Сумарний LIFT по всіх ринках (clean), в упаковках | `SUM(INTERNAL_LIFT)` per DRUGS_ID |

**Порядок рядків:** за `MEDIAN_SHARE_INTERNAL` (DESC) — найбільш "субститутовані" препарати зверху.

---

## 3. rejected_drugs.csv

**Призначення:** Препарати, що не пройшли фільтр якості. Мають недостатнє покриття та/або нестабільні коефіцієнти.

### 3.1. Колонки

Структура ідентична `valid_drugs.csv` (секції 2.1-2.6) з двома відмінностями:

| Відмінність | Опис |
|-------------|------|
| `FILTER_STATUS` | Завжди `REJECTED` |
| `REJECT_REASON` | Додаткова колонка — причина відхилення |

### 3.2. REJECT_REASON

| Технічна назва | Розшифровка | Опис |
|----------------|-------------|------|
| `REJECT_REASON` | Rejection Reason | Текстова причина відхилення у форматі `COVERAGE={cluster}; RELIABILITY={class}` |

**Можливі категорії причин:**

| Категорія | Умова | Приклад значення |
|-----------|-------|------------------|
| Тільки COVERAGE | COVERAGE ∈ {LOW, INSUFFICIENT}, RELIABILITY ∈ {HIGH, MEDIUM} | `COVERAGE=LOW` |
| Тільки RELIABILITY | COVERAGE ∈ {HIGH, MEDIUM}, RELIABILITY ∈ {LOW, SINGLE_MARKET} | `RELIABILITY=LOW` |
| Обидва критерії | COVERAGE ∈ {LOW, INSUFFICIENT} та RELIABILITY ∈ {LOW, SINGLE_MARKET} | `COVERAGE=INSUFFICIENT; RELIABILITY=SINGLE_MARKET` |

### 3.3. Допустимі значення для відхилених

На відміну від `valid_drugs.csv`, тут:

| Поле | Допустимі значення |
|------|--------------------|
| `COVERAGE_CLUSTER` | `HIGH`, `MEDIUM`, `LOW`, `INSUFFICIENT` |
| `RELIABILITY` | `HIGH`, `MEDIUM`, `LOW`, `SINGLE_MARKET` |
| `VARIATION_COEFFICIENT` | Будь-яке >= 0 або NaN (для SINGLE_MARKET) |
| `STD_SHARE_INTERNAL` | Будь-яке >= 0 або NaN (для SINGLE_MARKET) |
| `CI_95_LOWER`, `CI_95_UPPER` | 0.0-1.0 або NaN (для SINGLE_MARKET) |

**Порядок рядків:** за `MEDIAN_SHARE_INTERNAL` (DESC).

---

## 4. filter_summary.csv

**Призначення:** Агреговані метрики фільтрації — загальна статистика результатів у форматі key-value.

| Технічна назва (METRIC) | Тип VALUE | Опис |
|-------------------------|-----------|------|
| `TOTAL_DRUGS` | int | Всього препаратів на вході (з drug_statistics.csv) |
| `VALID_DRUGS` | int | К-сть препаратів, що пройшли фільтр |
| `REJECTED_DRUGS` | int | К-сть відхилених препаратів |
| `VALID_RATIO` | float | Частка валідних (VALID_DRUGS / TOTAL_DRUGS) |
| `FILTER_TYPE` | str | Тип застосованого фільтру (`SCENARIO_A_STRICT`) |
| `COVERAGE_CRITERIA` | str | Допустимі COVERAGE_CLUSTER (`HIGH, MEDIUM`) |
| `RELIABILITY_CRITERIA` | str | Допустимі RELIABILITY (`HIGH, MEDIUM`) |
| `COVERAGE_HIGH_THRESHOLD` | float | Поріг HIGH з конфігурації (>=50%) |
| `COVERAGE_MEDIUM_THRESHOLD` | float | Поріг MEDIUM з конфігурації (>=20%) |
| `RELIABILITY_HIGH_THRESHOLD` | float | Поріг HIGH (VARIATION_COEFFICIENT < 0.15) |
| `RELIABILITY_MEDIUM_THRESHOLD` | float | Поріг MEDIUM (VARIATION_COEFFICIENT < 0.30) |
| `REJECTED_COVERAGE_ONLY` | int | Відхилені лише через COVERAGE (RELIABILITY ok) |
| `REJECTED_RELIABILITY_ONLY` | int | Відхилені лише через RELIABILITY (COVERAGE ok) |
| `REJECTED_BOTH` | int | Відхилені через обидва критерії |

**Інваріанти:**
- `VALID_DRUGS + REJECTED_DRUGS = TOTAL_DRUGS`
- `REJECTED_COVERAGE_ONLY + REJECTED_RELIABILITY_ONLY + REJECTED_BOTH = REJECTED_DRUGS`

**Структура файлу:** 3 колонки — `METRIC`, `VALUE`, `DESCRIPTION`.

---

## 5. validation_report.txt

**Призначення:** Текстовий звіт з результатами 14 автоматичних валідаційних перевірок.

### 5.1. Перевірки

| # | Код | Що перевіряє | Очікуваний результат |
|---|-----|-------------|----------------------|
| 1 | `COMPLETENESS` | valid + rejected = total | Рівність |
| 2 | `VALID_NO_DUPLICATES` | Унікальність DRUGS_ID у valid | unique = total |
| 3 | `REJECTED_NO_DUPLICATES` | Унікальність DRUGS_ID у rejected | unique = total |
| 4 | `NO_OVERLAP` | Жодного DRUGS_ID одночасно в обох файлах | overlap = 0 |
| 5 | `VALID_COVERAGE_CRITERIA` | Всі valid мають COVERAGE ∈ {HIGH, MEDIUM} | 100% відповідність |
| 6 | `VALID_RELIABILITY_CRITERIA` | Всі valid мають RELIABILITY ∈ {HIGH, MEDIUM} | 100% відповідність |
| 7 | `REJECTED_HAVE_REASON` | Кожен rejected не відповідає хоча б одному критерію | 100% |
| 8 | `CROSS_TABLE_TOTAL` | Сума cross-table = total | Рівність |
| 9-12 | `CROSS_TABLE_ROW_*` | Суми рядків cross-table збігаються з маргіналами | Рівність per row |
| 13 | `VALID_FILTER_STATUS` | Всі valid мають FILTER_STATUS = 'VALID' | 100% |
| 14 | `REJECTED_FILTER_STATUS` | Всі rejected мають FILTER_STATUS = 'REJECTED' | 100% |

### 5.2. Статуси

| Статус | Значення |
|--------|----------|
| `PASSED` | Перевірка пройшла успішно |
| `FAILED` | Перевірка не пройшла — потребує уваги |

---

## 6. filter_business_reports/*.xlsx

**Призначення:** Excel-файли з візуальним форматуванням для бізнес-презентацій.

### 6.1. valid_drugs.xlsx / rejected_drugs.xlsx

| Файл | Відповідає CSV | Sheet Name | Форматування |
|------|----------------|------------|--------------|
| `valid_drugs.xlsx` | `valid_drugs.csv` | "Valid Drugs" | SHARE/CI колонки як %, кольорове маркування COVERAGE та RELIABILITY |
| `rejected_drugs.xlsx` | `rejected_drugs.csv` | "Rejected Drugs" | Аналогічне + кольорове маркування REJECT_REASON |

**Кольорове маркування COVERAGE_CLUSTER:**

| Кластер | Колір |
|---------|-------|
| `HIGH` | Зелений (#C6EFCE) |
| `MEDIUM` | Жовтий (#FFEB9C) |
| `LOW` | Червоний (#FFC7CE) |
| `INSUFFICIENT` | Сірий (#D9D9D9) |

**Кольорове маркування RELIABILITY:**

| Категорія | Колір |
|-----------|-------|
| `HIGH` | Зелений (#C6EFCE) |
| `MEDIUM` | Жовтий (#FFEB9C) |
| `LOW` | Червоний (#FFC7CE) |
| `SINGLE_MARKET` | Сірий (#D9D9D9) |

### 6.2. cross_table_distribution.xlsx

**Призначення:** Крос-таблиця розподілу препаратів по двох вимірах якості: COVERAGE_CLUSTER (рядки) × RELIABILITY (колонки).

| Sheet | Опис | Тип значень |
|-------|------|-------------|
| "Counts" | Абсолютна кількість препаратів у кожній комірці | int |
| "Ratios" | Частка від загальної к-сті досліджених препаратів | float (0.0-1.0) |
| "Combined" | Комбіноване відображення | "count (ratio%)" |

**Структура таблиці:**
- Рядки: `HIGH`, `MEDIUM`, `LOW`, `INSUFFICIENT`, `TOTAL`
- Колонки: `HIGH`, `MEDIUM`, `LOW`, `SINGLE_MARKET`, `TOTAL`
- Лівий верхній кут (index name): `COVERAGE ↓ \ RELIABILITY →`

**Примітки під таблицею:** кожен sheet містить пояснювальну примітку щодо того, що представлено у таблиці та відносно чого розраховані частки.

### 6.3. pipeline_funnel.xlsx

**Призначення:** Воронка від генеральної сукупності до відфільтрованих препаратів + інтерполяція.

**Sheet "Pipeline Funnel":**

| Технічна назва (STAGE) | Опис |
|------------------------|------|
| `RAW_DRUGS` | К-сть унікальних DRUGS_ID в raw даних (генеральна сукупність) |
| `RESEARCHED_DRUGS` | К-сть досліджених препаратів (мали stock-out events) |
| `FILTER_PASSED` | К-сть препаратів, що пройшли фільтр |

Додаткові колонки:

| Колонка | Опис |
|---------|------|
| `COUNT` | Абсолютна к-сть препаратів на цьому рівні |
| `RATIO_VS_RAW` | Частка від RAW_DRUGS |
| `RATIO_VS_RESEARCHED` | Частка від RESEARCHED_DRUGS (NaN для RAW_DRUGS) |

**Sheet "Interpolation":**

Логарифмічна апроксимація — модель: `rate(N) = rate_current × ln(N) / ln(N_current)`

| Параметр | Опис |
|----------|------|
| `TOTAL_MARKETS` | Поточна кількість досліджених ринків |
| `RESEARCH_RATE` | Частка досліджених від сирих (RESEARCHED / RAW) |
| `FILTER_RATE` | Частка валідних від сирих (VALID / RAW) |
| `N_RESEARCH_100PCT` | Оцінка к-сті ринків для 100% research coverage |
| `N_FILTER_100PCT` | Оцінка к-сті ринків для 100% filter pass |
| `RESEARCH_ESTIMATE_REALISTIC` | Прапорець реалістичності оцінки research (`Реалістична`) |
| `FILTER_ESTIMATE_REALISTIC` | Прапорець реалістичності оцінки filter (`Нереалістична`) |

Додатково — пояснювальні рядки `LIMITATION_*` з описом обмежень кожної оцінки.

---

## 7. НАВІГАЦІЯ

| Ресурс | Посилання |
|--------|-----------|
| Скрипт | `exec_scripts/02_substitution_coefficients/02_02_valid_data_filter.py` |
| Технічна документація | `docs/02_substitution_coefficients/02_02_VALID_DATA_FILTER.md` |
| Coverage thresholds | `project_core/sub_coef_config/coverage_thresholds.py` |
| Reliability thresholds | `project_core/sub_coef_config/reliability_thresholds.py` |
| Попередній крок (Step 2.2 part 1) | `docs/02_substitution_coefficients/_substitution_values_describe/02_01_statistical_analysis_values_describe.md` |
| Вхідні дані | `results/substitution_research/02_statistics_and_filter/02_01_statistical_analysis/drug_statistics.csv` |
| Вихідні дані | `results/substitution_research/02_statistics_and_filter/02_02_valid_data_filter/` |
