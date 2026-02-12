# Опис значень - Phase 2 Step 1: Data Preparation

> **Версія:** 1.0 | **Оновлено:** 04.02.2026

---

## 1. ЗАГАЛЬНА ІНФОРМАЦІЯ

**Вихідна папка:** `results/substitution_research/01_preparation/`

**Скрипт-джерело:** `exec_scripts/02_substitution_coefficients/01_data_preparation.py`

**Конфігурація порогів:** `project_core/sub_coef_config/coverage_thresholds.py`

---

## 2. all_drugs_list.csv

**Призначення:** Генеральна сукупність — всі унікальні препарати, що зустрічались у raw даних будь-якого локального ринку.

| Технічна назва | Розшифровка | Опис | Джерело |
|----------------|-------------|------|---------|
| `DRUGS_ID` | Drug Identifier | Унікальний числовий ідентифікатор препарату в системі Morion | `data/raw/Rd2_*.csv`, колонка `DRUGS_ID` |
| `DRUGS_NAME` | Drug Name | Повна назва препарату включаючи виробника, форму, дозування та фасовку | `data/raw/Rd2_*.csv`, колонка `Full medication name` → перейменовано |
| `INN_ID` | International Nonproprietary Name ID | Числовий ідентифікатор групи діючої речовини (МНН) | `data/raw/Rd2_*.csv`, колонка `INN_ID` |
| `INN_NAME` | INN Name | Назва групи діючої речовини (МНН) | `data/raw/Rd2_*.csv`, колонка `INN` → перейменовано |

**Кількість рядків:** Дорівнює кількості унікальних `DRUGS_ID` по всіх raw файлах.

---

## 3. researched_drugs_list.csv

**Призначення:** Препарати, для яких є результати DiD аналізу з Phase 1 (потрапили в cross_market файли).

### 3.1. Базові ідентифікатори

| Технічна назва | Розшифровка | Опис | Джерело |
|----------------|-------------|------|---------|
| `DRUGS_ID` | Drug Identifier | Унікальний ID препарату | `results/cross_market_data/cross_market_*.csv` |
| `DRUGS_NAME` | Drug Name | Повна назва препарату | `results/cross_market_data/cross_market_*.csv` |
| `INN_ID` | INN Identifier | ID групи діючої речовини | `results/cross_market_data/cross_market_*.csv` |
| `INN_NAME` | INN Name | Назва групи діючої речовини | `results/cross_market_data/cross_market_*.csv` |
| `NFC1_ID` | NFC Level 1 | Широка категорія форми випуску (напр. "Пероральні тверді звичайні") | `results/cross_market_data/cross_market_*.csv` |

### 3.2. Метрики покриття

| Технічна назва | Розшифровка | Опис | Формула розрахунку |
|----------------|-------------|------|-------------------|
| `MARKET_COUNT` | Market Count | Кількість локальних ринків, де цей препарат має дані Phase 1 | `COUNT(DISTINCT CLIENT_ID)` де `DRUGS_ID = X` |
| `TOTAL_MARKETS` | Total Markets | Загальна кількість досліджуваних локальних ринків | Кількість унікальних `cross_market_*.csv` файлів |
| `MARKET_COVERAGE` | Market Coverage | Відсоток покриття ринків (від 0.0 до 1.0) | `MARKET_COUNT / TOTAL_MARKETS` |
| `COVERAGE_CLUSTER` | Coverage Cluster | Кластер покриття для класифікації надійності | Визначається за порогами з `coverage_thresholds.py` |

### 3.3. Coverage Cluster значення

| Значення | Розшифровка | Критерій | Бізнес-значення |
|----------|-------------|----------|-----------------|
| `HIGH` | High Coverage | `MARKET_COVERAGE >= 0.50` (50%+) | Найнадійніші крос-ринкові висновки |
| `MEDIUM` | Medium Coverage | `0.20 <= MARKET_COVERAGE < 0.50` (20-49%) | Достатньо для базового аналізу |
| `LOW` | Low Coverage | `0.10 <= MARKET_COVERAGE < 0.20` (10-19%) | Обмежені дані, широкі довірчі інтервали |
| `INSUFFICIENT` | Insufficient Coverage | `MARKET_COVERAGE < 0.10` (<10%) | Недостатньо для надійних висновків |

---

## 4. researched_drugs_coefficients.csv

**Призначення:** Широкоформатна матриця коефіцієнтів субституції та супутніх даних для кожного препарату по кожному локальному ринку.

### 4.1. Базові колонки

| Технічна назва | Розшифровка | Опис |
|----------------|-------------|------|
| `DRUGS_ID` | Drug Identifier | ID препарату |
| `DRUGS_NAME` | Drug Name | Назва препарату |
| `INN_ID` | INN Identifier | ID групи діючої речовини |
| `INN_NAME` | INN Name | Назва діючої речовини |
| `NFC1_ID` | NFC Level 1 | Категорія форми випуску |
| `MARKET_COUNT` | Market Count | К-сть ринків з даними |

### 4.2. Колонки по ринках

Для кожного локального ринку `{CLIENT_ID}` створюються три колонки:

| Шаблон назви | Розшифровка | Опис | Діапазон значень |
|--------------|-------------|------|------------------|
| `SHARE_INTERNAL_LOC_{CLIENT_ID}` | Share Internal for Location | Коефіцієнт внутрішньої субституції на ринку CLIENT_ID | 0.0 - 1.0 або NaN |
| `INTERNAL_LIFT_LOC_{CLIENT_ID}` | Internal Lift for Location | Сума LIFT всіх substitutes на ринку CLIENT_ID (в упаковках) | ≥0 або NaN |
| `EVENTS_COUNT_LOC_{CLIENT_ID}` | Events Count for Location | Кількість stock-out подій на ринку CLIENT_ID | ≥1 або NaN |

**Примітки:**
- `NaN` означає, що препарат не потрапив в аналіз Phase 1 на цьому ринку
- Порядок колонок ринків: за кількістю препаратів (DESC) — формує "трикутну" візуалізацію
- Порядок рядків препаратів: за `MARKET_COUNT` (DESC)

### 4.3. Інтерпретація значень

| Комбінація значень | Інтерпретація |
|--------------------|---------------|
| `SHARE_INTERNAL = 0.0`, `INTERNAL_LIFT = 0.0` | Нульова субституція: покупці йдуть до конкурентів (100% LOST) |
| `SHARE_INTERNAL = 1.0`, `INTERNAL_LIFT > 0` | Повна субституція: всі покупці обирають substitutes в цій аптеці |
| `SHARE_INTERNAL = 0.5`, `INTERNAL_LIFT > 0` | Часткова: 50% залишається, 50% йде до конкурентів |
| `INTERNAL_LIFT = 0.0` з будь-яким SHARE | Немає substitutes або жоден не обирався |

---

## 5. coverage_analysis.csv

**Призначення:** Summary статистика по покриттю препаратів ринками.

| Технічна назва метрики | Розшифровка | Опис | Формула |
|------------------------|-------------|------|---------|
| `TOTAL_MARKETS` | Total Markets | Загальна кількість досліджуваних ринків | `COUNT(cross_market_*.csv)` |
| `TOTAL_DRUGS_RAW` | Total Drugs Raw | Всього унікальних препаратів в raw даних | `COUNT(DISTINCT DRUGS_ID)` з raw |
| `TOTAL_DRUGS_RESEARCHED` | Total Drugs Researched | Препаратів з даними Phase 1 | `COUNT(DISTINCT DRUGS_ID)` з cross_market |
| `RAW_COVERAGE_RATE` | Raw Coverage Rate | Частка препаратів, що потрапили в дослідження | `TOTAL_DRUGS_RESEARCHED / TOTAL_DRUGS_RAW` |
| `DRUGS_HIGH_COVERAGE` | Drugs High Coverage | К-сть препаратів у кластері HIGH | `COUNT WHERE COVERAGE_CLUSTER = 'HIGH'` |
| `DRUGS_MEDIUM_COVERAGE` | Drugs Medium Coverage | К-сть препаратів у кластері MEDIUM | `COUNT WHERE COVERAGE_CLUSTER = 'MEDIUM'` |
| `DRUGS_LOW_COVERAGE` | Drugs Low Coverage | К-сть препаратів у кластері LOW | `COUNT WHERE COVERAGE_CLUSTER = 'LOW'` |
| `DRUGS_INSUFFICIENT_COVERAGE` | Drugs Insufficient Coverage | К-сть препаратів у кластері INSUFFICIENT | `COUNT WHERE COVERAGE_CLUSTER = 'INSUFFICIENT'` |
| `AVG_MARKETS_PER_DRUG` | Average Markets per Drug | Середня к-сть ринків на препарат | `MEAN(MARKET_COUNT)` |
| `AVG_MARKET_COVERAGE` | Average Market Coverage | Середній % покриття препаратів | `MEAN(MARKET_COVERAGE)` |

---

## 6. validation_report.txt

**Призначення:** Текстовий звіт з результатами автоматичної валідації даних.

### 6.1. Перевірки

| Код перевірки | Що перевіряється | Очікуваний результат |
|---------------|------------------|----------------------|
| `TOTAL_MARKETS` | К-сть ринків в coverage_analysis = к-сть cross_market файлів | Рівність |
| `COVERAGE_CLUSTERS` | Сума препаратів по кластерах = TOTAL_RESEARCHED | Рівність |
| `SHARE_INTERNAL range` | Всі значення SHARE_INTERNAL в [0, 1] | Жодного виходу за межі |
| `TRIANGLE_STRUCTURE` | Перший препарат має максимальне заповнення | Істина |
| `MARKET_MATCH` | Ринки в coefficients = ринки в cross_market | Повний збіг |
| `MARKET_COUNT integrity` | Фактична к-сть non-NaN = MARKET_COUNT | Рівність для кожного препарату |

### 6.2. Статуси

| Статус | Значення |
|--------|----------|
| `[OK]` | Перевірка пройшла успішно |
| `[FAIL]` | Перевірка не пройшла — потребує уваги |
| `[WARN]` | Попередження — не критично, але варто перевірити |

---

## 7. prep_business_reports/*.xlsx

**Призначення:** Excel-файли для представлення бізнес-замовникам.

| Файл | Відповідає CSV | Sheet Name |
|------|----------------|------------|
| `researched_drugs_list.xlsx` | `researched_drugs_list.csv` | "Researched Drugs" |
| `researched_drugs_coefficients.xlsx` | `researched_drugs_coefficients.csv` | "Coefficients" |
| `coverage_analysis.xlsx` | `coverage_analysis.csv` | "Coverage Analysis" |

**Формат:** Стандартний Excel без додаткового форматування.

---

## 8. НАВІГАЦІЯ

| Ресурс | Посилання |
|--------|-----------|
| Технічна документація | `docs/02_substitution_coefficients/03_DATA_PREPARATION_AND_OUTPUTS.md` |
| Скрипт | `exec_scripts/02_substitution_coefficients/01_data_preparation.py` |
| Coverage thresholds | `project_core/sub_coef_config/coverage_thresholds.py` |
| Phase 1 cross_market | `results/cross_market_data/` |
