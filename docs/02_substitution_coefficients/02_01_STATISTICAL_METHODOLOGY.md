# STATISTICAL METHODOLOGY - Phase 2

> **Версія:** 2.0 | **Створено:** 01.02.2026 | **Оновлено:** 03.03.2026

---

## 1. ПРИЗНАЧЕННЯ

Цей документ описує статистичні методи для розрахунку загальних коефіцієнтів субститованості across markets.

**Реалізація:** `exec_scripts/02_substitution_coefficients/02_01_statistical_analysis.py`

---

## 2. ПРОБЛЕМА

### Вхідні дані
Для кожного препарату маємо набір значень SHARE_INTERNAL з різних ринків:

```
Препарат X: [0.75, 0.82, 0.68, 0.71, 0.79, 0.65, 0.88, ...]
             ↑ Ринок 1  ↑ Ринок 2  ... (N ринків)
```

### Задача
Визначити **один загальний коефіцієнт** з оцінкою надійності.

---

## 3. ПОПЕРЕДНЯ ОБРОБКА: IQR OUTLIER DETECTION

> *Додано у v2.0*

Перед розрахунком статистик виконується фільтрація аномальних спостережень per DRUGS_ID.

### 3.1. Метод IQR (Interquartile Range)

**Алгоритм:**
```
Для кожного препарату окремо:
1. Q1 = 25-й перцентиль SHARE_INTERNAL
2. Q3 = 75-й перцентиль SHARE_INTERNAL
3. IQR = Q3 - Q1
4. Lower bound = Q1 - 1.5 × IQR
5. Upper bound = Q3 + 1.5 × IQR
6. Outlier = значення за межами [Lower, Upper]
```

**Множник:** `IQR_MULTIPLIER = 1.5` (стандартний, охоплює ~99.3% при нормальному розподілі).

### 3.2. Обробка outliers

- Outliers **не видаляються** з даних — позначаються прапорцем `IS_OUTLIER = True`
- Статистики (MEDIAN, MEAN, STD, VARIATION_COEFFICIENT, CI, WEIGHTED_MEAN) розраховуються **без** outliers
- `flat_bi_export.csv` містить **всі** записи з прапорцем для окремого аналізу

### 3.3. Single observation

Препарати з одним спостереженням (N=1) позначаються `SINGLE_OBSERVATION = True`. IQR для них не визначений.

---

## 4. МЕТОДИ РОЗРАХУНКУ ЦЕНТРАЛЬНОЇ ТЕНДЕНЦІЇ

### 4.1. Медіана (основна метрика)

> *Додано у v2.0*

**Формула:**
```
MEDIAN_SHARE_INTERNAL = медіана значень SHARE_INTERNAL по чистих ринках
```

**Обґрунтування:**
- Стійка до залишкових аномалій (навіть після IQR фільтрації)
- Краще відображає "типову" поведінку при асиметричних розподілах
- Рекомендована для препаратів з LOW та INSUFFICIENT покриттям (секція 6.2)

### 4.2. Зважене середнє

**Формула:**
```
WEIGHTED_MEAN_SHARE = Σ(SHARE_INTERNAL_i × WEIGHT_i) / Σ(WEIGHT_i)

де WEIGHT_i = INTERNAL_LIFT_i (сума LIFT substitutes на ринку i)
```

**Обґрунтування:**
- Ринки з більшим INTERNAL_LIFT мають більше stock-out подій
- Більше подій → надійніша оцінка SHARE_INTERNAL
- Зважене середнє дає більшу вагу надійнішим оцінкам

**Приклад:**
```
Ринок A: SHARE_INTERNAL = 0.80, INTERNAL_LIFT = 500 упак.
Ринок B: SHARE_INTERNAL = 0.40, INTERNAL_LIFT = 20 упак.

Просте середнє:  (0.80 + 0.40) / 2 = 0.60
Зважене середнє: (0.80×500 + 0.40×20) / (500+20) = 0.785

→ Зважене середнє ближче до Ринку A (більша вага)
```

### 4.3. Просте середнє (для порівняння)

**Формула:**
```
SIMPLE_MEAN_SHARE = Σ(SHARE_INTERNAL_i) / N
```

**Використання:** Зберігається для порівняння з медіаною та зваженим середнім.

---

## 5. МЕТРИКИ ВАРІАТИВНОСТІ

### 5.1. Стандартне відхилення (STD)

**Формула:**
```
STD_SHARE = √(Σ(SHARE_i - MEAN)² / (N - 1))
```

**Інтерпретація:** Абсолютна міра розкиду значень по ринках.

### 5.2. Коефіцієнт варіації (VARIATION_COEFFICIENT)

**Формула:**
```
VARIATION_COEFFICIENT = STD_SHARE / MEAN_SHARE
```

**Інтерпретація:** Відносна міра варіативності. Зберігається як ratio (не %).

### 5.3. Класифікація надійності (RELIABILITY)

> *Формалізовано у v2.0*

На основі VARIATION_COEFFICIENT кожному препарату присвоюється категорія RELIABILITY.

**Пороги:** `project_core/sub_coef_config/reliability_thresholds.py`

| VARIATION_COEFFICIENT | RELIABILITY | Інтерпретація |
|-----------------------|-------------|---------------|
| < 0.15 | **HIGH** | Стабільна субституція across markets |
| 0.15–0.30 | **MEDIUM** | Помірна варіативність |
| >= 0.30 | **LOW** | Нестабільна — коефіцієнт ненадійний |
| N/A (N=1) | **SINGLE_MARKET** | Один ринок — статистика відсутня |

**Приклад:**
```
Препарат X: MEAN = 0.72, STD = 0.08 → VARIATION_COEFFICIENT = 0.11 → HIGH reliability
Препарат Y: MEAN = 0.55, STD = 0.25 → VARIATION_COEFFICIENT = 0.45 → LOW reliability
```

### 5.4. Квартилі та IQR per drug

> *Додано у v2.0*

| Метрика | Формула | Значення |
|---------|---------|----------|
| `Q1_SHARE_INTERNAL` | 25-й перцентиль | 25% ринків мають значення нижче |
| `Q3_SHARE_INTERNAL` | 75-й перцентиль | 75% ринків мають значення нижче |
| `IQR_SHARE_INTERNAL` | Q3 - Q1 | Ширина "типового коридору" (50% ринків) |

---

## 6. ДОВІРЧИЙ ІНТЕРВАЛ (CI)

### 6.1. Формула 95% CI

```
CI_95_LOWER = MEAN - 1.96 × (STD / √N)
CI_95_UPPER = MEAN + 1.96 × (STD / √N)
```

**Де:**
- `MEAN` — просте середнє (MEAN_SHARE_INTERNAL)
- `STD` — стандартне відхилення
- `N` — кількість чистих ринків (MARKET_COUNT_CLEAN)
- `1.96` — z-score для 95% рівня довіри

**Обрізка:** CI clipped до [0, 1]:
```
CI_95_LOWER = max(0, CI_95_LOWER)
CI_95_UPPER = min(1, CI_95_UPPER)
```

**Умова:** CI розраховується тільки при N >= 2.

### 6.2. Інтерпретація

```
CI_95 = [0.68, 0.76] означає:
→ З 95% впевненістю "справжній" коефіцієнт субституції
  знаходиться в діапазоні від 68% до 76%
```

### 6.3. Вплив N на ширину CI

```
Формула: CI_width = 2 × 1.96 × (STD / √N)

При STD = 0.10:
- N = 10  → CI_width = 0.124 (±6.2%)
- N = 25  → CI_width = 0.078 (±3.9%)
- N = 50  → CI_width = 0.055 (±2.8%)
- N = 100 → CI_width = 0.039 (±2.0%)

→ Більше ринків = вужчий CI = точніша оцінка
```

---

## 7. КЛАСТЕРИЗАЦІЯ ЗА COVERAGE

### 7.1. Гібридний підхід

**Точне значення:** `MARKET_COVERAGE` зберігається для детального аналізу.

**Категорія:** `COVERAGE_CLUSTER` для групування.

| Кластер | Coverage | Мін. ринків (при 97) | Статистичне обґрунтування |
|---------|----------|---------------------|---------------------------|
| **HIGH** | >= 50% | >= 49 | Достатньо для надійних статистичних тестів |
| **MEDIUM** | 20-49% | 20-48 | Мінімум для CLT (Central Limit Theorem) |
| **LOW** | 10-19% | 10-19 | Базова статистика можлива, обмежена надійність |
| **INSUFFICIENT** | < 10% | < 10 | Окремий датасет — недостатньо для висновків |

**Реалізація:** `project_core/sub_coef_config/coverage_thresholds.py`

### 7.2. Обґрунтування порогів

**>= 50% (HIGH):**
- CLT працює надійно
- Можливі параметричні тести
- Вузькі CI

**20-49% (MEDIUM):**
- CLT наближення прийнятне при N >= 20
- Базові висновки можливі
- Помірні CI

**10-19% (LOW):**
- Мінімум для розрахунку STD та CI
- Широкі CI — обережність у висновках
- Краще використовувати медіану замість середнього

**<10% (INSUFFICIENT):**
- Недостатньо точок для надійної статистики
- Виносяться в окремий датасет

---

## 8. РОЗПОДІЛ ПО ДІАПАЗОНАХ (DISTRIBUTION)

> *Додано у v2.0*

### 8.1. Гістограма з кроком 10%

Для кожного препарату розраховується кількість чистих ринків (без outliers), де SHARE_INTERNAL потрапляє в кожен з 10 діапазонів:

```
BIN_0_10:   [0.0, 0.1]
BIN_10_20:  (0.1, 0.2]
BIN_20_30:  (0.2, 0.3]
...
BIN_90_100: (0.9, 1.0]
```

### 8.2. Використання

- Візуалізація форми розподілу per drug
- Виявлення бімодальних або скошених розподілів
- Підготовка даних для BI-інструментів (Power BI)

**Вихідний файл:** `drug_distribution.csv`

---

## 9. FLAT BI EXPORT

> *Додано у v2.0*

Long-format таблиця (DRUGS_ID x CLIENT_ID) з усіма вхідними даними та прапорцями IS_OUTLIER / SINGLE_OBSERVATION. Призначена для імпорту в Power BI та інші BI-інструменти.

**Вихідний файл:** `flat_bi_export.csv`

---

## 10. EDGE CASES

### 10.1. N = 1 (один ринок)

```
STD = undefined (ділення на 0)
CI = undefined
VARIATION_COEFFICIENT = undefined

Рішення:
- WEIGHTED_MEAN = SHARE_INTERNAL цього ринку
- MEDIAN = SHARE_INTERNAL цього ринку
- STD, VARIATION_COEFFICIENT, CI = NULL
- RELIABILITY = "SINGLE_MARKET"
- Включити в INSUFFICIENT dataset
```

### 10.2. Всі SHARE_INTERNAL однакові

```
STD = 0
VARIATION_COEFFICIENT = 0
CI = [MEAN, MEAN]

Це нормальний випадок — ідеальна консистентність.
RELIABILITY = HIGH
```

### 10.3. INTERNAL_LIFT = 0 для всіх ринків

```
WEIGHTED_MEAN = undefined (ділення на 0)

Рішення: Використовувати SIMPLE_MEAN як fallback
```

---

## 11. ФОРМУЛИ SUMMARY

| Метрика | Формула | Примітка |
|---------|---------|----------|
| `MEDIAN` | `median(SHARE_i)` | Основна метрика |
| `WEIGHTED_MEAN` | `Σ(SHARE_i × LIFT_i) / Σ(LIFT_i)` | Зважена метрика |
| `SIMPLE_MEAN` | `Σ(SHARE_i) / N` | Для порівняння |
| `STD` | `√(Σ(SHARE_i - MEAN)² / (N-1))` | N >= 2 |
| `VARIATION_COEFFICIENT` | `STD / MEAN` | ratio |
| `RELIABILITY` | `based on VARIATION_COEFFICIENT thresholds` | HIGH/MEDIUM/LOW/SINGLE_MARKET |
| `CI_95_LOWER` | `MEAN - 1.96 × (STD / √N)` | clipped to [0, 1] |
| `CI_95_UPPER` | `MEAN + 1.96 × (STD / √N)` | clipped to [0, 1] |
| `Q1` | `quantile(SHARE_i, 0.25)` | |
| `Q3` | `quantile(SHARE_i, 0.75)` | |
| `IQR` | `Q3 - Q1` | |
| `MIN` | `min(SHARE_i)` | |
| `MAX` | `max(SHARE_i)` | |

---

## 12. ВАЛІДАЦІЯ

### Інваріанти

```python
# Всі центральні метрики в межах [0, 1]
assert 0 <= MEDIAN_SHARE_INTERNAL <= 1
assert 0 <= WEIGHTED_MEAN_SHARE <= 1
assert 0 <= MEAN_SHARE_INTERNAL <= 1

# CI логіка
assert CI_95_LOWER <= MEAN_SHARE_INTERNAL <= CI_95_UPPER

# CI в межах [0, 1] (обрізати якщо виходить)
CI_95_LOWER = max(0, CI_95_LOWER)
CI_95_UPPER = min(1, CI_95_UPPER)

# VARIATION_COEFFICIENT невід'ємний
assert VARIATION_COEFFICIENT >= 0

# MIN <= MEAN <= MAX
assert MIN_SHARE <= MEAN_SHARE_INTERNAL <= MAX_SHARE

# Distribution bins sum
assert sum(BIN_0_10 ... BIN_90_100) == TOTAL per drug

# Flat export completeness
assert len(flat_bi_export) == len(raw_data)
```

---

## 13. НАВІГАЦІЯ

| Ресурс | Посилання |
|--------|-----------|
| Pipeline Phase 2 | [00_PIPELINE_PHASE_2.md](./00_PIPELINE_PHASE_2.md) |
| Бізнес-контекст | [_SUBSTITUTION_BUSINESS_CONTEXT.md](./_SUBSTITUTION_BUSINESS_CONTEXT.md) |
| Підготовка даних | [01_DATA_PREPARATION_AND_OUTPUTS.md](./01_DATA_PREPARATION_AND_OUTPUTS.md) |
| Опис змінних | [_substitution_values_describe/02_statistical_analysis_values_describe.md](./_substitution_values_describe/02_statistical_analysis_values_describe.md) |
| Бізнес-пояснення | [_substitution_values_describe/02_statistical_analysis_business_explanation.txt](./_substitution_values_describe/02_statistical_analysis_business_explanation.txt) |
