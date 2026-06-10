# Опис значень - Phase 2 Step 2: Statistical Analysis

> **Версія:** 2.0 | **Оновлено:** 03.03.2026

---

## 1. ЗАГАЛЬНА ІНФОРМАЦІЯ

**Вихідна папка:** `results/substitution_research/02_statistics_and_filter/02_01_statistical_analysis/`

**Скрипт-джерело:** `exec_scripts/02_substitution_coefficients/02_01_statistical_analysis.py`

**Конфігурація порогів:**
- `project_core/sub_coef_config/coverage_thresholds.py` (COVERAGE_CLUSTER)
- `project_core/sub_coef_config/reliability_thresholds.py` (RELIABILITY)

**Вхідні дані:**
- `results/cross_market_data/market_substitution_{CLIENT_ID}/sub_coef_{CLIENT_ID}.csv` (97 файлів, concat в long format)
- `results/substitution_research/01_preparation/researched_drugs_list.csv` (coverage кластери)

**IQR параметри:** `IQR_MULTIPLIER = 1.5` (стандартний множник для визначення outliers)

---

## 2. drug_statistics.csv

**Призначення:** Агреговані статистичні метрики SHARE_INTERNAL per DRUGS_ID з усіх локальних ринків. Outliers відфільтровані за IQR методом. Основний файл для бізнес-рішень.

### 2.1. Ідентифікатори препарату

| Технічна назва | Розшифровка | Опис | Джерело |
|----------------|-------------|------|---------|
| `DRUGS_ID` | Drug Identifier | Унікальний числовий ідентифікатор препарату | `sub_coef_*.csv`, колонка `DRUGS_ID` |
| `DRUGS_NAME` | Drug Name | Повна назва препарату (виробник, форма, дозування, фасовка) | `researched_drugs_list.csv` |
| `INN_ID` | INN Identifier | ID групи діючої речовини (МНН) | `researched_drugs_list.csv` |
| `INN_NAME` | INN Name | Назва групи діючої речовини | `researched_drugs_list.csv` |
| `NFC1_ID` | NFC Level 1 | Широка категорія форми випуску | `researched_drugs_list.csv` |

### 2.2. Метрики покриття та якості

| Технічна назва | Розшифровка | Опис | Формула |
|----------------|-------------|------|---------|
| `COVERAGE_CLUSTER` | Coverage Cluster | Кластер покриття (HIGH/MEDIUM/LOW/INSUFFICIENT) | З `researched_drugs_list.csv`, визначається `coverage_thresholds.py` |
| `RELIABILITY` | Reliability | Класифікація надійності коефіцієнта субституції (HIGH/MEDIUM/LOW/SINGLE_MARKET) | На основі `VARIATION_COEFFICIENT` — див. секцію 2.5 |
| `MARKET_COUNT_TOTAL` | Total Market Count | Загальна к-сть ринків з даними для цього препарату (включно з outliers) | `COUNT(DISTINCT CLIENT_ID)` per DRUGS_ID |
| `MARKET_COUNT_CLEAN` | Clean Market Count | К-сть ринків після видалення outliers | `COUNT(DISTINCT CLIENT_ID)` per DRUGS_ID де `IS_OUTLIER = False` |
| `OUTLIERS_COUNT` | Outliers Count | К-сть спостережень, визначених як outliers за IQR | `MARKET_COUNT_TOTAL - MARKET_COUNT_CLEAN` |
| `MARKET_COVERAGE` | Market Coverage | Частка покриття ринків (0.0 - 1.0) | З `researched_drugs_list.csv` |

### 2.3. Статистичні метрики SHARE_INTERNAL

Всі метрики розраховані на **clean** даних (без outliers).

| Технічна назва | Розшифровка | Опис | Формула | Діапазон |
|----------------|-------------|------|---------|----------|
| `MEDIAN_SHARE_INTERNAL` | Median Share Internal | Медіанний коефіцієнт субституції по ринках | `MEDIAN(SHARE_INTERNAL)` per DRUGS_ID | 0.0 - 1.0 |
| `MEAN_SHARE_INTERNAL` | Mean Share Internal | Середнє арифметичне коефіцієнта субституції | `MEAN(SHARE_INTERNAL)` per DRUGS_ID | 0.0 - 1.0 |
| `WEIGHTED_MEAN_SHARE` | Weighted Mean Share | Зважене середнє, де вага = INTERNAL_LIFT ринку | `Σ(SHARE_i × LIFT_i) / Σ(LIFT_i)` (fallback: MEAN якщо Σ(LIFT)=0) | 0.0 - 1.0 |
| `STD_SHARE_INTERNAL` | Standard Deviation | Стандартне відхилення коефіцієнта | `STD(SHARE_INTERNAL)` per DRUGS_ID | >= 0 |
| `VARIATION_COEFFICIENT` | Coefficient of Variation | Коефіцієнт варіації — міра однорідності | `STD / MEAN` (NaN якщо MEAN = 0) | >= 0 |
| `CI_95_LOWER` | 95% CI Lower Bound | Нижня межа 95% довірчого інтервалу | `MEAN - 1.96 × (STD / √N)`, clip [0, 1]; NaN якщо N < 2 | 0.0 - 1.0 |
| `CI_95_UPPER` | 95% CI Upper Bound | Верхня межа 95% довірчого інтервалу | `MEAN + 1.96 × (STD / √N)`, clip [0, 1]; NaN якщо N < 2 | 0.0 - 1.0 |
| `MIN_SHARE_INTERNAL` | Minimum Share | Мінімальне значення коефіцієнта | `MIN(SHARE_INTERNAL)` per DRUGS_ID | 0.0 - 1.0 |
| `Q1_SHARE_INTERNAL` | First Quartile | 25-й перцентиль | `QUANTILE(0.25)` per DRUGS_ID | 0.0 - 1.0 |
| `Q3_SHARE_INTERNAL` | Third Quartile | 75-й перцентиль | `QUANTILE(0.75)` per DRUGS_ID | 0.0 - 1.0 |
| `MAX_SHARE_INTERNAL` | Maximum Share | Максимальне значення коефіцієнта | `MAX(SHARE_INTERNAL)` per DRUGS_ID | 0.0 - 1.0 |
| `IQR_SHARE_INTERNAL` | Interquartile Range | Міжквартильний розмах | `Q3 - Q1` | >= 0 |

### 2.4. Додаткові агреговані метрики

| Технічна назва | Розшифровка | Опис | Формула |
|----------------|-------------|------|---------|
| `TOTAL_EVENTS` | Total Events | Загальна к-сть stock-out подій по всіх ринках (clean) | `SUM(EVENTS_COUNT)` per DRUGS_ID |
| `TOTAL_INTERNAL_LIFT` | Total Internal Lift | Сумарний LIFT по всіх ринках (clean), в упаковках | `SUM(INTERNAL_LIFT)` per DRUGS_ID |

### 2.5. Інтерпретація ключових метрик

| Значення VARIATION_COEFFICIENT | Інтерпретація |
|--------------------------------|---------------|
| `< 0.15` | Високо однорідні дані — коефіцієнт стабільний між ринками |
| `0.15 <= VC < 0.30` | Помірна варіативність — прийнятно для бізнес-рішень |
| `>= 0.30` | Висока варіативність — потрібен аналіз причин розбіжності |

| Значення MEDIAN | Інтерпретація |
|-----------------|---------------|
| `MEDIAN >= 0.70` | Висока субституція — покупці активно обирають аналоги |
| `0.30 <= MEDIAN < 0.70` | Помірна субституція — частина покупців йде до конкурентів |
| `MEDIAN < 0.30` | Низька субституція — більшість покупців втрачається |

| Значення RELIABILITY | VARIATION_COEFFICIENT порогове | Інтерпретація |
|----------------------|-------------------------------|---------------|
| `HIGH` | < 0.15 | Стабільна субституція — коефіцієнт надійний для бізнес-рішень |
| `MEDIUM` | 0.15 <= VC < 0.30 | Помірна варіативність — коефіцієнт як орієнтир |
| `LOW` | >= 0.30 | Нестабільна — потрібен додатковий аналіз причин |
| `SINGLE_MARKET` | N/A (N=1) | Один ринок — статистика варіативності відсутня |

| CI_95 діапазон | Інтерпретація |
|----------------|---------------|
| Вузький (< 0.05) | Висока точність оцінки; великий N та низька варіативність |
| Помірний (0.05 - 0.15) | Прийнятна точність для бізнес-рішень |
| Широкий (> 0.15) | Низька точність; потрібно більше даних або висока варіативність |

**Порядок рядків:** за `MEDIAN_SHARE_INTERNAL` (DESC) — найбільш "субститутовані" препарати зверху.

---

## 3. drug_distribution.csv

**Призначення:** Розподіл значень SHARE_INTERNAL по діапазонах з кроком 10% для кожного препарату. Показує в скільки аптек потрапляє кожний діапазон субституції. Дані без outliers.

### 3.1. Ідентифікатори

| Технічна назва | Розшифровка | Опис |
|----------------|-------------|------|
| `DRUGS_ID` | Drug Identifier | ID препарату |
| `DRUGS_NAME` | Drug Name | Назва препарату |
| `INN_ID` | INN Identifier | ID діючої речовини |
| `INN_NAME` | INN Name | Назва діючої речовини |

### 3.2. Колонки діапазонів (bins)

Кожна колонка містить **кількість аптек (ринків)**, де SHARE_INTERNAL потрапляє у відповідний діапазон.

| Технічна назва | Розшифровка | Діапазон SHARE_INTERNAL |
|----------------|-------------|-------------------------|
| `BIN_0_10` | Bin 0-10% | [0.00, 0.10] |
| `BIN_10_20` | Bin 10-20% | (0.10, 0.20] |
| `BIN_20_30` | Bin 20-30% | (0.20, 0.30] |
| `BIN_30_40` | Bin 30-40% | (0.30, 0.40] |
| `BIN_40_50` | Bin 40-50% | (0.40, 0.50] |
| `BIN_50_60` | Bin 50-60% | (0.50, 0.60] |
| `BIN_60_70` | Bin 60-70% | (0.60, 0.70] |
| `BIN_70_80` | Bin 70-80% | (0.70, 0.80] |
| `BIN_80_90` | Bin 80-90% | (0.80, 0.90] |
| `BIN_90_100` | Bin 90-100% | (0.90, 1.00] |

### 3.3. Підсумок

| Технічна назва | Розшифровка | Опис | Формула |
|----------------|-------------|------|---------|
| `TOTAL` | Total Observations | Загальна к-сть спостережень (clean) для цього препарату | `SUM(BIN_0_10 ... BIN_90_100)` |

### 3.4. Інтерпретація

| Патерн розподілу | Інтерпретація |
|------------------|---------------|
| Концентрація в 1-2 сусідніх bins | Стабільний коефіцієнт, однорідна поведінка між ринками |
| Рівномірний розподіл по bins | Високо варіативний коефіцієнт, різна поведінка на різних ринках |
| Бімодальний (два піки) | Можлива кластеризація ринків за якоюсь характеристикою |

**Порядок рядків:** за `TOTAL` (DESC) — препарати з найбільшою кількістю спостережень зверху.

---

## 4. flat_bi_export.csv

**Призначення:** Long format файл для імпорту в Power BI або інші BI-інструменти. Суворо структурований — без пустих полів, без wide format. Кожен рядок = один препарат на одному ринку.

### 4.1. Ідентифікатори

| Технічна назва | Розшифровка | Опис |
|----------------|-------------|------|
| `CLIENT_ID` | Client/Market Identifier | ID цільової аптеки (локальний ринок) |
| `DRUGS_ID` | Drug Identifier | ID препарату |
| `DRUGS_NAME` | Drug Name | Назва препарату |
| `INN_ID` | INN Identifier | ID діючої речовини |
| `INN_NAME` | INN Name | Назва діючої речовини |
| `NFC1_ID` | NFC Level 1 | Категорія форми випуску |

### 4.2. Метрики stock-out

| Технічна назва | Розшифровка | Опис | Діапазон |
|----------------|-------------|------|----------|
| `EVENTS_COUNT` | Events Count | К-сть stock-out подій на цьому ринку | >= 1 |
| `TOTAL_STOCKOUT_WEEKS` | Total Stockout Weeks | Загальна тривалість stock-out у тижнях | >= 1 |

### 4.3. DiD метрики

| Технічна назва | Розшифровка | Опис | Діапазон |
|----------------|-------------|------|----------|
| `INTERNAL_LIFT` | Internal Lift | Сума LIFT від substitutes в аптеці (упаковки) | >= 0 |
| `LOST_SALES` | Lost Sales | Продажі, втрачені конкурентам (упаковки) | >= 0 |
| `TOTAL_EFFECT` | Total Effect | Загальний ефект stock-out (INTERNAL_LIFT + LOST_SALES) | >= 0 |

### 4.4. Коефіцієнти субституції

| Технічна назва | Розшифровка | Опис | Діапазон |
|----------------|-------------|------|----------|
| `SHARE_INTERNAL` | Share Internal | Частка ефекту, що залишилась в аптеці | 0.0 - 1.0 |
| `SHARE_LOST` | Share Lost | Частка ефекту, втрачена конкурентам | 0.0 - 1.0 |
| `SHARE_SAME_NFC1` | Share Same NFC1 | Частка LIFT від substitutes тієї ж форми випуску | 0.0 - 1.0 |
| `SHARE_DIFF_NFC1` | Share Different NFC1 | Частка LIFT від substitutes іншої форми випуску | 0.0 - 1.0 |

**Інваріанти:**
- `SHARE_INTERNAL + SHARE_LOST = 1.0`
- `SHARE_SAME_NFC1 + SHARE_DIFF_NFC1 = 1.0`

### 4.5. Класифікація

| Технічна назва | Розшифровка | Можливі значення |
|----------------|-------------|------------------|
| `CLASSIFICATION` | Drug Classification | `CRITICAL` — високий ризик втрати, `WARNING` — помірний ризик, `SUBSTITUTABLE` — є альтернативи |

### 4.6. Прапорці якості даних

| Технічна назва | Розшифровка | Опис | Тип |
|----------------|-------------|------|-----|
| `IS_OUTLIER` | Is Outlier | Чи є це спостереження статистичним викидом за IQR методом | Boolean (True/False) |
| `SINGLE_OBSERVATION` | Single Observation | Чи є це єдине спостереження для цього препарату (MARKET_COUNT = 1) | Boolean (True/False) |

### 4.7. IQR метод визначення outliers

Для кожного `DRUGS_ID` окремо:
1. Розраховується `Q1 = QUANTILE(SHARE_INTERNAL, 0.25)`
2. Розраховується `Q3 = QUANTILE(SHARE_INTERNAL, 0.75)`
3. `IQR = Q3 - Q1`
4. `lower_bound = Q1 - 1.5 * IQR`
5. `upper_bound = Q3 + 1.5 * IQR`
6. `IS_OUTLIER = True` якщо `SHARE_INTERNAL < lower_bound` або `SHARE_INTERNAL > upper_bound`

**Порядок рядків:** за `DRUGS_ID` (ASC), потім `CLIENT_ID` (ASC).

---

## 5. validation_report.txt

**Призначення:** Текстовий звіт з результатами автоматичної валідації.

### 5.1. Перевірки

| Код перевірки | Що перевіряється | Очікуваний результат |
|---------------|------------------|----------------------|
| `DRUGS_COUNT` | К-сть препаратів в statistics = researched_drugs_list | Рівність (507) |
| `MEDIAN_RANGE` | Всі MEDIAN в [0, 1] | Жодного виходу за межі |
| `MARKET_COUNT` | MARKET_COUNT_TOTAL <= загальна к-сть файлів | Для кожного препарату |
| `DISTRIBUTION_SUM` | Сума bins = TOTAL для кожного препарату | Рівність |
| `FLAT_EXPORT` | К-сть записів flat export = вхідні дані | Рівність |
| `CROSS_CHECK` | MARKET_COUNT_TOTAL = MARKET_COUNT з researched_drugs_list | Рівність (top-5 drugs) |
| `VARIATION_COEFFICIENT_RANGE` | Всі VARIATION_COEFFICIENT >= 0 | Жодного від'ємного значення |
| `WEIGHTED_MEAN_RANGE` | Всі WEIGHTED_MEAN_SHARE в [0, 1] | Жодного виходу за межі |
| `CI_LOGIC` | CI_95_LOWER <= MEAN <= CI_95_UPPER (де N >= 2) | Для всіх препаратів з CI |
| `MIN_MEAN_MAX` | MIN <= MEAN <= MAX для кожного препарату | Логічна послідовність |

### 5.2. Статуси

| Статус | Значення |
|--------|----------|
| `[OK]` | Перевірка пройшла успішно |
| `[FAIL]` | Перевірка не пройшла — потребує уваги |
| `[WARN]` | Попередження — не критично, але варто перевірити |

---

## 6. stat_business_reports/*.xlsx

**Призначення:** Excel-файли з візуальним форматуванням для бізнес-презентацій.

| Файл | Відповідає CSV | Sheet Name | Форматування |
|------|----------------|------------|--------------|
| `drug_statistics.xlsx` | `drug_statistics.csv` | "Drug Statistics" | SHARE/WEIGHTED_MEAN/CI_95 колонки як %, кольорове маркування COVERAGE_CLUSTER та RELIABILITY |
| `drug_distribution.xlsx` | `drug_distribution.csv` | "Distribution" | Heatmap на bin колонках (інтенсивність кольору пропорційна кількості) |

### 6.1. Кольорове маркування COVERAGE_CLUSTER

| Кластер | Колір |
|---------|-------|
| `HIGH` | Зелений (#C6EFCE) |
| `MEDIUM` | Жовтий (#FFEB9C) |
| `LOW` | Червоний (#FFC7CE) |
| `INSUFFICIENT` | Сірий (#D9D9D9) |

### 6.1.1. Кольорове маркування RELIABILITY

| Категорія | Колір |
|-----------|-------|
| `HIGH` | Зелений (#C6EFCE) |
| `MEDIUM` | Жовтий (#FFEB9C) |
| `LOW` | Червоний (#FFC7CE) |
| `SINGLE_MARKET` | Сірий (#D9D9D9) |

### 6.2. Heatmap distribution

Bin колонки мають градієнтне кольорове заповнення: від білого (0 спостережень) до зеленого (максимальна к-сть). Інтенсивність кольору пропорційна значенню відносно максимуму по всіх bins.

---

## 7. НАВІГАЦІЯ

| Ресурс | Посилання |
|--------|-----------|
| Скрипт | `exec_scripts/02_substitution_coefficients/02_01_statistical_analysis.py` |
| Coverage thresholds | `project_core/sub_coef_config/coverage_thresholds.py` |
| Вхідні дані Phase 1 | `results/cross_market_data/market_substitution_*/sub_coef_*.csv` |
| Попередній крок (Step 1) | `docs/02_substitution_coefficients/_substitution_values_describe/01_preparation_values_describe.md` |
| Вихідні дані | `results/substitution_research/02_statistics_and_filter/02_01_statistical_analysis/` |
