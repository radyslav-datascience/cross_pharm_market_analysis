# PHASE 2: Cross-Market Substitution Coefficients

> **Версія:** 1.0 | **Створено:** 01.02.2026

---

## ПРИЗНАЧЕННЯ

Цей документ надає технічний огляд **Phase 2 (Cross-Market Aggregation)** — визначення загальних коефіцієнтів субститованості препаратів на основі даних з усіх локальних ринків.

**Phase 2 використовує результати Phase 1** (cross_market_{CLIENT_ID}.csv) для крос-ринкової агрегації.

**Результат Phase 2:** Загальні коефіцієнти субститованості з оцінкою надійності для кожного препарату.

---

## ЗАГАЛЬНА КОНЦЕПЦІЯ

Phase 2 відповідає на ключові дослідницькі питання:

```
1. Чи мають препарати загальну тенденцію субститованості across markets?
2. Як розрахувати загальний коефіцієнт субститованості?
3. Яким статистичним вимогам повинен відповідати препарат?
```

**Ключова ідея:** Агрегувати SHARE_INTERNAL з різних ринків для отримання стабільного коефіцієнта з оцінкою надійності (CI, CV).

---

## PIPELINE OVERVIEW

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                          PHASE 2: CROSS-MARKET AGGREGATION                          │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                      │
│  Step 2.1           Step 2.2            Step 2.3           Step 2.4                 │
│  ─────────          ─────────           ─────────          ─────────                │
│  Підготовка    →    Агрегація      →    Кластеризація  →   Вихідні                  │
│  даних              коефіцієнтів        та надійність      файли                    │
│                                                                                      │
│  - Список всіх      - Weighted Mean     - Coverage         - Aggregated CSV         │
│    препаратів       - STD, CV           - Reliability      - Wide-format            │
│  - Coverage         - CI_95             - Clusters         - INSUFFICIENT           │
│    аналіз                                                    окремо                 │
│                                                                                      │
└─────────────────────────────────────────────────────────────────────────────────────┘
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
COVERAGE_PERCENT = N_markets_with_data / TOTAL_markets × 100
Для кожного препарату: в скількох ринках він присутній як досліджуваний
```

### Детальна документація
→ [03_DATA_PREPARATION_AND_OUTPUTS.md](./03_DATA_PREPARATION_AND_OUTPUTS.md)

---

## STEP 2.2: АГРЕГАЦІЯ КОЕФІЦІЄНТІВ

### Мета
Розрахувати загальний коефіцієнт субститованості для кожного препарату.

### Ключові алгоритми

**1. Зважене середнє (основна метрика)**
```
WEIGHTED_MEAN_SHARE = Σ(SHARE_INTERNAL_i × INTERNAL_LIFT_i) / Σ(INTERNAL_LIFT_i)

Логіка: ринки з більшим INTERNAL_LIFT мають більшу вагу
```

**2. Статистичні метрики**
```
STD_SHARE = std(SHARE_INTERNAL across markets)
CV_PERCENT = (STD / MEAN) × 100
CI_95_LOWER = MEAN - 1.96 × (STD / √N)
CI_95_UPPER = MEAN + 1.96 × (STD / √N)
```

### Детальна документація
→ [04_STATISTICAL_METHODOLOGY.md](./04_STATISTICAL_METHODOLOGY.md)

---

## STEP 2.3: КЛАСТЕРИЗАЦІЯ ТА НАДІЙНІСТЬ

### Мета
Оцінити надійність коефіцієнтів та кластеризувати препарати за coverage.

### Ключові алгоритми

**1. Coverage Clusters (гібридний підхід)**
```
Точне значення: COVERAGE_PERCENT (наприклад, 87%)
Категорія: COVERAGE_CLUSTER
  - HIGH:         ≥ 50% (≥ 50 ринків зі 100)
  - MEDIUM:       20-49%
  - LOW:          10-19%
  - INSUFFICIENT: < 10% (окремий датасет)
```

**2. Reliability Score (на основі CV)**
```
HIGH:   CV < 15%  → Стабільна субституція
MEDIUM: CV 15-30% → Помірна варіативність
LOW:    CV > 30%  → Нестабільна субституція
```

### Поріг INSUFFICIENT
Препарати з coverage < 10% виносяться в окремий датасет — недостатньо даних для статистично значущих висновків.

---

## STEP 2.4: ВИХІДНІ ФАЙЛИ

### Мета
Сформувати фінальні артефакти для бізнес-використання.

### Типи виходів

**1. Aggregated Dataset (основний)**
```
Один рядок = один препарат з агрегованими метриками:
DRUGS_ID, DRUGS_NAME, INN_ID, INN_NAME, NFC1_ID,
WEIGHTED_MEAN_SHARE, STD_SHARE, CV_PERCENT,
CI_95_LOWER, CI_95_UPPER,
N_MARKETS, COVERAGE_PERCENT, COVERAGE_CLUSTER, RELIABILITY
```

**2. Wide-Format (для аналізу)**
```
SHARE_INTERNAL per market у колонках:
DRUGS_ID, ..., SHARE_INTERNAL_LOC_{ID_1}, SHARE_INTERNAL_LOC_{ID_2}, ...
```

**3. INSUFFICIENT Dataset (окремо)**
```
Препарати з coverage < 10% — для подальшого дослідження
```

### Детальна документація
→ [03_DATA_PREPARATION_AND_OUTPUTS.md](./03_DATA_PREPARATION_AND_OUTPUTS.md)

---

## КЛЮЧОВІ ФОРМУЛИ

| Метрика | Формула | Опис |
|---------|---------|------|
| `WEIGHTED_MEAN_SHARE` | `Σ(SHARE_i × LIFT_i) / Σ(LIFT_i)` | Зважений коефіцієнт субституції |
| `STD_SHARE` | `std(SHARE_INTERNAL)` | Стандартне відхилення по ринках |
| `CV_PERCENT` | `(STD / MEAN) × 100` | Коефіцієнт варіації |
| `CI_95` | `MEAN ± 1.96 × (STD / √N)` | 95% довірчий інтервал |
| `COVERAGE_PERCENT` | `N_markets / TOTAL × 100` | % покриття ринків |

---

## ІНВАРІАНТИ (ЗАВЖДИ ПЕРЕВІРЯТИ)

```python
# Coverage в межах [0, 100]
assert 0 <= COVERAGE_PERCENT <= 100

# WEIGHTED_MEAN_SHARE в межах [0, 1]
assert 0 <= WEIGHTED_MEAN_SHARE <= 1

# CI логіка
assert CI_95_LOWER <= WEIGHTED_MEAN_SHARE <= CI_95_UPPER

# CV невід'ємний
assert CV_PERCENT >= 0
```

---

## СТРУКТУРА СКРИПТІВ

| Скрипт | Опис |
|--------|------|
| `exec_scripts/03_01_data_preparation.py` | Step 2.1: Підготовка даних |
| `exec_scripts/03_02_coefficient_aggregation.py` | Step 2.2-2.3: Агрегація та кластеризація |
| `exec_scripts/03_03_output_generation.py` | Step 2.4: Генерація виходів |

**Виконання:**
```bash
# Після завершення Phase 1 для всіх ринків:
python exec_scripts/03_01_data_preparation.py
python exec_scripts/03_02_coefficient_aggregation.py
python exec_scripts/03_03_output_generation.py
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
    │  Агрегація:
    │  - WEIGHTED_MEAN_SHARE
    │  - CI_95, CV
    │  - COVERAGE_CLUSTER
    │  - RELIABILITY
    │
    ▼
FINAL: Загальні коефіцієнти субституції across markets
```

---

## НАВІГАЦІЯ

| Ресурс | Посилання |
|--------|-----------|
| Бізнес-контекст Phase 2 | [02_SUBSTITUTION_BUSINESS_CONTEXT.md](./02_SUBSTITUTION_BUSINESS_CONTEXT.md) |
| Підготовка даних | [03_DATA_PREPARATION_AND_OUTPUTS.md](./03_DATA_PREPARATION_AND_OUTPUTS.md) |
| Статистична методологія | [04_STATISTICAL_METHODOLOGY.md](./04_STATISTICAL_METHODOLOGY.md) |
| Phase 1 документація | [../01_did_processing/00_PIPELINE_PHASE_1.md](../01_did_processing/00_PIPELINE_PHASE_1.md) |
| Загальний бізнес-контекст | [../00_ai_rules/01_BUSINESS_CONTEXT.md](../00_ai_rules/01_BUSINESS_CONTEXT.md) |
