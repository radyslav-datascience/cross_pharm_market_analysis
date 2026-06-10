# PHASE 2: Cross-Market Substitution Coefficients

> **Версія:** 2.1 | **Створено:** 01.02.2026 | **Оновлено:** 04.03.2026

---

## ПРИЗНАЧЕННЯ

Цей документ надає технічний огляд **Phase 2 (Cross-Market Aggregation)** — визначення загальних коефіцієнтів субститованості препаратів на основі даних з усіх локальних ринків.

**Phase 2 використовує результати Phase 1** (`results/cross_market_data/cross_market_{CLIENT_ID}.csv`) для крос-ринкової агрегації.

**Результат Phase 2:** Загальні коефіцієнти субститованості з оцінкою надійності (CI, VARIATION_COEFFICIENT, RELIABILITY) для кожного препарату.

---

## ЗАГАЛЬНА КОНЦЕПЦІЯ

Phase 2 відповідає на ключові дослідницькі питання:

```
1. Чи мають препарати загальну тенденцію субститованості across markets?
2. Як розрахувати загальний коефіцієнт субститованості?
3. Яким статистичним вимогам повинен відповідати препарат?
```

**Ключова ідея:** Агрегувати SHARE_INTERNAL з різних ринків для отримання стабільного коефіцієнта з оцінкою надійності (CI, VARIATION_COEFFICIENT, RELIABILITY).

---

## PIPELINE OVERVIEW

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    PHASE 2: CROSS-MARKET AGGREGATION                        │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  Step 2.1                Step 2.2 part 1            Step 2.2 part 2         │
│  ─────────               ──────────────             ──────────────          │
│  Підготовка даних   →    Статистичний аналіз   →    Фільтрація              │
│                                                                              │
│  - Генеральна            - IQR outlier detection    - Scenario A (strict)   │
│    сукупність            - Центральна тенденція:      COVERAGE ∈ {H, M}    │
│  - Coverage аналіз         MEDIAN, WEIGHTED_MEAN      AND RELIABILITY ∈    │
│  - Wide-format             SIMPLE_MEAN                {H, M}               │
│    матриця               - Варіативність: STD,      - Cross-table          │
│    коефіцієнтів            VARIATION_COEFFICIENT       COVERAGE × RELIAB.  │
│                          - CI_95, RELIABILITY       - Pipeline funnel      │
│                          - Distribution bins        - Інтерполяція         │
│                          - Flat BI export                                   │
│                                                                              │
│  [01_data_             [02_01_statistical_       [02_02_valid_data_         │
│   preparation.py]       analysis.py]              filter.py]               │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## STEP 2.1: ПІДГОТОВКА ДАНИХ

### Мета
Зібрати та підготувати дані з усіх локальних ринків для агрегації.

### Ключові алгоритми

**1. Список ВСІХ препаратів (генеральна сукупність)**
```
Зібрати унікальні DRUGS_ID з усіх raw файлів (Rd2_{CLIENT_ID}.csv)
→ Це ВСІ препарати, що продавались на ринках
```

**2. Список досліджуваних препаратів**
```
Зібрати унікальні DRUGS_ID з усіх cross_market_{CLIENT_ID}.csv
→ Це препарати, що мають SHARE_INTERNAL (пройшли Phase 1)
```

**3. Coverage аналіз**
```
MARKET_COVERAGE = N_markets_with_data / TOTAL_markets
COVERAGE_CLUSTER — категорія за порогами з project_core/sub_coef_config/
```

**4. Wide-format матриця**
```
Per drug: SHARE_INTERNAL_LOC_{ID}, INTERNAL_LIFT_LOC_{ID}, EVENTS_COUNT_LOC_{ID}
Сортування: ринки за заповненістю (DESC), препарати за coverage (DESC)
→ Трикутна структура
```

### Детальна документація
→ [01_DATA_PREPARATION_AND_OUTPUTS.md](./01_DATA_PREPARATION_AND_OUTPUTS.md)

---

## STEP 2.2: СТАТИСТИЧНИЙ АНАЛІЗ

### Мета
Розрахувати загальний коефіцієнт субститованості для кожного препарату з оцінкою надійності та класифікацією.

### Ключові алгоритми

**1. IQR Outlier Detection (per drug)**
```
Q1, Q3 → IQR = Q3 - Q1
Outliers: SHARE_INTERNAL за межами [Q1 - k×IQR, Q3 + k×IQR]
Множник k визначений в project_core/sub_coef_config/
Outliers позначаються IS_OUTLIER, але не видаляються з даних
```

**2. Центральна тенденція (по чистих ринках, без outliers)**
```
MEDIAN_SHARE_INTERNAL — основна метрика, стійка до залишкових аномалій
WEIGHTED_MEAN_SHARE = Σ(SHARE_i × INTERNAL_LIFT_i) / Σ(INTERNAL_LIFT_i)
MEAN_SHARE_INTERNAL — просте середнє для порівняння
```

**3. Варіативність**
```
STD_SHARE_INTERNAL = std(SHARE_INTERNAL across clean markets)
VARIATION_COEFFICIENT = STD / MEAN  (ratio, не %)
Q1, Q3, IQR — квартильні метрики per drug
```

**4. Довірчий інтервал**
```
CI_95_LOWER = MEAN - 1.96 × (STD / √N), clipped to [0, 1]
CI_95_UPPER = MEAN + 1.96 × (STD / √N), clipped to [0, 1]
Розраховується тільки при N >= 2
```

**5. Класифікація**
```
COVERAGE_CLUSTER — категорія покриття ринків (пороги в sub_coef_config/)
RELIABILITY — категорія надійності на основі VARIATION_COEFFICIENT (пороги в sub_coef_config/)
```

**6. Вихідні файли**
```
drug_statistics.csv      — агреговані метрики per drug (основний файл)
drug_distribution.csv    — гістограма SHARE_INTERNAL з кроком 10%
flat_bi_export.csv       — long-format для BI (DRUGS_ID × CLIENT_ID)
drug_statistics.xlsx     — Excel з кольоровим кодуванням
```

### Детальна документація
→ [02_01_STATISTICAL_METHODOLOGY.md](./02_01_STATISTICAL_METHODOLOGY.md)

---

## STEP 2.2 part 2: VALID DATA FILTER

### Мета
Відібрати препарати з достатнім покриттям та надійними коефіцієнтами.

### Критерії (Scenario A — strict)
```
VALID = COVERAGE_CLUSTER ∈ {HIGH, MEDIUM}
    AND RELIABILITY ∈ {HIGH, MEDIUM}
```

Пороги: `project_core/sub_coef_config/coverage_thresholds.py`, `reliability_thresholds.py`

### Додаткові вихідні файли
```
valid_drugs.csv / .xlsx        — препарати що пройшли фільтр
rejected_drugs.csv / .xlsx     — відхилені з REJECT_REASON
cross_table_distribution.xlsx  — COVERAGE × RELIABILITY (counts + ratios)
pipeline_funnel.xlsx           — воронка raw → researched → filtered + інтерполяція
```

### Детальна документація
→ [02_02_VALID_DATA_FILTER.md](./02_02_VALID_DATA_FILTER.md)

---

## КЛЮЧОВІ ФОРМУЛИ

| Метрика | Формула | Опис |
|---------|---------|------|
| `MEDIAN` | `median(SHARE_i)` | Основна метрика центральної тенденції |
| `WEIGHTED_MEAN` | `Σ(SHARE_i × LIFT_i) / Σ(LIFT_i)` | Зважений коефіцієнт субституції |
| `STD` | `√(Σ(SHARE_i - MEAN)² / (N-1))` | Стандартне відхилення по ринках |
| `VARIATION_COEFFICIENT` | `STD / MEAN` | Коефіцієнт варіації (ratio) |
| `CI_95` | `MEAN ± 1.96 × (STD / √N)` | 95% довірчий інтервал |
| `MARKET_COVERAGE` | `N_markets / TOTAL_markets` | Частка покриття ринків (ratio) |

---

## ІНВАРІАНТИ (ЗАВЖДИ ПЕРЕВІРЯТИ)

```python
# Всі центральні метрики в межах [0, 1]
assert 0 <= MEDIAN_SHARE_INTERNAL <= 1
assert 0 <= WEIGHTED_MEAN_SHARE <= 1
assert 0 <= MEAN_SHARE_INTERNAL <= 1

# CI логіка
assert CI_95_LOWER <= MEAN_SHARE_INTERNAL <= CI_95_UPPER

# CI в межах [0, 1]
assert 0 <= CI_95_LOWER and CI_95_UPPER <= 1

# VARIATION_COEFFICIENT невід'ємний
assert VARIATION_COEFFICIENT >= 0

# MIN <= MEAN <= MAX
assert MIN_SHARE <= MEAN_SHARE_INTERNAL <= MAX_SHARE

# Distribution bins sum = MARKET_COUNT_CLEAN per drug
assert sum(BIN_0_10 ... BIN_90_100) == MARKET_COUNT_CLEAN
```

---

## КОНФІГУРАЦІЯ

| Модуль | Параметри |
|--------|-----------|
| `project_core/sub_coef_config/coverage_thresholds.py` | Пороги COVERAGE_CLUSTER |
| `project_core/sub_coef_config/reliability_thresholds.py` | Пороги RELIABILITY (на основі VARIATION_COEFFICIENT) |
| `project_core/data_config/` | Шляхи до даних, завантаження |

---

## СТРУКТУРА СКРИПТІВ

| Скрипт | Опис |
|--------|------|
| `exec_scripts/02_substitution_coefficients/01_data_preparation.py` | Step 2.1: Підготовка даних |
| `exec_scripts/02_substitution_coefficients/02_01_statistical_analysis.py` | Step 2.2 part 1: Статистичний аналіз |
| `exec_scripts/02_substitution_coefficients/02_02_valid_data_filter.py` | Step 2.2 part 2: Фільтрація валідних даних |

**Виконання:**
```bash
# Після завершення Phase 1 для всіх ринків:
python exec_scripts/02_substitution_coefficients/01_data_preparation.py
python exec_scripts/02_substitution_coefficients/02_01_statistical_analysis.py
python exec_scripts/02_substitution_coefficients/02_02_valid_data_filter.py
```

---

## ЗВ'ЯЗОК З PHASE 1

```
PHASE 1 (Per-Market)
    │
    │  Вихід: results/cross_market_data/cross_market_{CLIENT_ID}.csv
    │         (SHARE_INTERNAL per drug per market)
    │
    ▼
PHASE 2 (Cross-Market Aggregation)
    │
    │  Step 2.1: Підготовка (coverage, wide-format)
    │  Step 2.2 part 1: Агрегація (MEDIAN, WEIGHTED_MEAN, CI, VARIATION_COEFFICIENT, RELIABILITY)
    │  Step 2.2 part 2: Фільтрація (Scenario A → valid / rejected drugs)
    │
    ▼
FINAL: Загальні коефіцієнти субституції across markets
```

---

## НАВІГАЦІЯ

| Ресурс | Посилання |
|--------|-----------|
| Бізнес-контекст Phase 2 | [_SUBSTITUTION_BUSINESS_CONTEXT.md](./_SUBSTITUTION_BUSINESS_CONTEXT.md) |
| Підготовка даних | [01_DATA_PREPARATION_AND_OUTPUTS.md](./01_DATA_PREPARATION_AND_OUTPUTS.md) |
| Статистична методологія | [02_01_STATISTICAL_METHODOLOGY.md](./02_01_STATISTICAL_METHODOLOGY.md) |
| Фільтрація валідних даних | [02_02_VALID_DATA_FILTER.md](./02_02_VALID_DATA_FILTER.md) |
| Phase 1 документація | [../01_did_processing/00_PIPELINE_PHASE_1.md](../01_did_processing/00_PIPELINE_PHASE_1.md) |
| Загальний бізнес-контекст | [../00_ai_rules/01_BUSINESS_CONTEXT.md](../00_ai_rules/01_BUSINESS_CONTEXT.md) |
