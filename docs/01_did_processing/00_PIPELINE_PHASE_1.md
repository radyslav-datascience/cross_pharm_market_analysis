# PHASE 1: Per-Market DiD Processing

> **Версія:** 1.1 | **Оновлено:** 03.02.2026

---

## ПРИЗНАЧЕННЯ

Цей документ надає технічний огляд **Phase 1 (Per-Market Processing)** — DiD-аналізу на рівні окремого локального ринку.

**Phase 1 виконується для кожного ринку (CLIENT_ID) паралельно.**

**Результати Phase 1 використовуються в Phase 2** для крос-ринкового аналізу коефіцієнтів субституції.

---

## ЗАГАЛЬНА КОНЦЕПЦІЯ

Pipeline реалізує **Difference-in-Differences (DiD)** аналіз для оцінки поведінки покупців при відсутності препарату (stock-out):

```
Питання: Що відбувається з попитом, коли препарату немає?
         ├─ Покупець обирає substitute в цій аптеці? (INTERNAL)
         └─ Покупець йде до конкурентів? (LOST)
```

**Ключова ідея DiD:** Порівняти фактичні продажі substitutes під час stock-out з очікуваними (baseline × market growth), щоб виділити чистий ефект відсутності препарату.

---

## PIPELINE OVERVIEW

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                          PHASE 1: PER-MARKET PROCESSING                              │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                      │
│  Step 0          Step 1          Step 2           Step 3        Step 4      Step 5  │
│  ────────        ────────        ────────         ────────      ────────    ─────── │
│  Preproc   →     Агрегація  →    Детекція    →    DiD      →   Substitute → Звіти   │
│  (1 раз)         даних           stock-out        аналіз       аналіз       + CSV   │
│                                                                                      │
│  [01_preproc]    [02_01_*.py]    [02_02_*.py]    [02_03_*.py] [02_04_*.py] [02_05]  │
│                                                                                      │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

---

## STEP 0: PREPROCESSING

### Мета
Зібрати метадані по всіх ринках та створити список цільових аптек для наступних кроків.

### Ключові алгоритми

**1. Сканування Raw файлів**
```
Знаходить всі Rd2_{CLIENT_ID}.csv у data/raw/
Витягує CLIENT_ID з назв файлів
```

**2. Збір унікальних значень**
```
- INN_ID + INN_NAME (групи діючих речовин)
- NFC1_ID, NFC2_ID (форми випуску)
- DRUGS_ID + DRUGS_NAME (препарати)
```

**3. Генерація статистики**
```
Per-market: competitors_count, weeks_range, drugs_count
```

### Критичний вихід
`target_pharmacies_list.csv` — використовується функцією `load_target_pharmacies()` у всіх наступних скриптах.

### Детальна документація
→ [01_0_PREPROCESSING.md](./01_0_PREPROCESSING.md)

---

## STEP 1: АГРЕГАЦІЯ ДАНИХ

### Мета
Підготувати чисті, консистентні дані для аналізу: тижнева агрегація, заповнення пропусків, розрахунок ринкових показників.

### Ключові алгоритми

**1. Gap Filling (критично)**
```
Проблема: Відсутні рядки ≠ нульові продажі
Рішення: Для кожного препарату створити повний ряд тижнів,
         заповнити пропуски Q=0
```

**2. Week Alignment**
```
Всі дати вирівнюються по понеділках для консистентності
```

**3. Market Totals**
```
Для кожного тижня розраховується сума продажів конкурентів
→ MARKET_TOTAL використовується для розрахунку MARKET_GROWTH
```

### Детальна документація
→ [01_DATA_AGREGATION.md](./01_DATA_AGREGATION.md)

---

## STEP 2: ДЕТЕКЦІЯ STOCK-OUT

### Мета
Ідентифікувати періоди відсутності препарату з валідацією якості подій.

### Ключові алгоритми

**1. Stock-out Detection**
```
Stock-out = послідовні тижні з Q=0
Мінімальна тривалість: визначається в project_core/did_config/
```

**2. PRE/POST Period Definition**
```
PRE:  N тижнів ДО stock-out (baseline для порівняння)
POST: N тижнів ПІСЛЯ відновлення продажів
```

**3. Validation Criteria**
```
Валідна подія повинна мати:
├─ Достатній PRE-період (мін. N тижнів з продажами)
├─ Достатній POST-період (мін. N тижнів з продажами)
└─ Gap між stock-out та POST ≤ M тижнів
```

### Детальна документація
→ [02_STOCKOUT_DETECTION.md](./02_STOCKOUT_DETECTION.md)

---

## STEP 3: DiD АНАЛІЗ

### Мета
Розрахувати ефект stock-out: скільки попиту перейшло на substitutes (INTERNAL) vs втрачено до конкурентів (LOST).

### Ключові алгоритми

**1. Substitute Identification**
```
Substitute = препарат тієї ж INN групи з сумісною формою випуску
Фільтр: NFC1 Compatibility Matrix (ORAL_GROUP взаємозамінні)
```

**2. LIFT Calculation (DiD core)**
```
EXPECTED = PRE_AVG × MARKET_GROWTH
ACTUAL   = фактичні продажі substitute під час stock-out
LIFT     = max(0, ACTUAL - EXPECTED)
```

**3. Share Decomposition**
```
INTERNAL_LIFT = Σ LIFT всіх substitutes
LOST_SALES    = Попит, що пішов до конкурентів (розрахунок в did_utils.py)
TOTAL_EFFECT  = INTERNAL_LIFT + LOST_SALES
SHARE_INTERNAL = INTERNAL_LIFT / TOTAL_EFFECT
SHARE_LOST     = LOST_SALES / TOTAL_EFFECT
```

**4. NFC1 Decomposition**
```
LIFT_SAME_NFC1 = LIFT substitutes тієї ж форми
LIFT_DIFF_NFC1 = LIFT substitutes іншої форми
SHARE_SAME_NFC1 = LIFT_SAME_NFC1 / INTERNAL_LIFT
```

### Критичні фільтри
- **Phantom Substitutes Filter** — виключає substitutes без даних під час stock-out
- Детальніше: [02_KNOWN_ISSUES.md](../00_ai_rules/02_KNOWN_ISSUES.md) (секція 5)

### Детальна документація
→ [03_DID_NFC_ANALYSIS.md](./03_DID_NFC_ANALYSIS.md)

---

## STEP 4: АНАЛІЗ SUBSTITUTES

### Мета
Розрахувати частку кожного substitute в загальній внутрішній субституції (SUBSTITUTE_SHARE).

### Ключові алгоритми

**1. Aggregate LIFT per Substitute**
```
Для кожного substitute агрегувати LIFT по всіх stock-out подіях,
де він виступав замінником
```

**2. SUBSTITUTE_SHARE Calculation**
```
SUBSTITUTE_SHARE = LIFT_substitute / INTERNAL_LIFT × 100%
Сума SHARE для всіх substitutes одного препарату = 100%
```

**3. Drug Classification**
```
CRITICAL:      SHARE_LOST > threshold (багато втрат)
SUBSTITUTABLE: SHARE_INTERNAL > threshold (хороша субституція)
```

### Критичні фільтри
- **Zero-LIFT Filter** — виключає substitutes з LIFT=0 (не обирались покупцями)
- Детальніше: [02_KNOWN_ISSUES.md](../00_ai_rules/02_KNOWN_ISSUES.md) (секція 6)

### Детальна документація
→ [04_SUBSTITUTE_SHARE_ANALYSIS.md](./04_SUBSTITUTE_SHARE_ANALYSIS.md)

---

## STEP 5: ЗВІТИ ТА CSV

### Мета
Сформувати вихідні артефакти: Excel звіти для per-market аналізу, CSV для Phase 2.

### Типи виходів

**1. Technical Report (Excel)**
```
Повний звіт з усіма 27 колонками для технічного аналізу
```

**2. Business Report (Excel)**
```
Спрощений звіт з 18 ключовими метриками для керівництва
```

**3. Cross-Market CSV**
```
Flat data (1 рядок = 1 препарат) для агрегації в Phase 2
21 колонка з ключовими метриками
```

### Детальна документація
→ [05_REPORTS_AND_GRAPHS.md](./05_REPORTS_AND_GRAPHS.md)

---

## КЛЮЧОВІ ФОРМУЛИ

| Метрика | Формула | Опис |
|---------|---------|------|
| `MARKET_GROWTH` | `MARKET_DURING / MARKET_PRE` | Коефіцієнт росту ринку |
| `EXPECTED` | `PRE_AVG × MARKET_GROWTH` | Очікувані продажі без stock-out |
| `LIFT` | `max(0, ACTUAL - EXPECTED)` | Додаткові продажі через stock-out |
| `SHARE_INTERNAL` | `INTERNAL_LIFT / TOTAL_EFFECT` | Частка, що залишилась в аптеці |
| `SHARE_LOST` | `1 - SHARE_INTERNAL` | Частка, що пішла до конкурентів |
| `SUBSTITUTE_SHARE` | `LIFT_sub / INTERNAL_LIFT × 100` | Частка конкретного substitute |

---

## ІНВАРІАНТИ (ЗАВЖДИ ПЕРЕВІРЯТИ)

```python
# Сума часток = 100%
assert abs(SHARE_INTERNAL + SHARE_LOST - 1.0) < 0.001

# NFC декомпозиція
assert abs(SHARE_SAME_NFC1 + SHARE_DIFF_NFC1 - 1.0) < 0.001

# SUBSTITUTE_SHARE сума = 100% для кожного препарату
assert df.groupby('STOCKOUT_DRUG_ID')['SUBSTITUTE_SHARE'].sum() ≈ 100%
```

---

## СТРУКТУРА СКРИПТІВ

| Скрипт | Опис |
|--------|------|
| `exec_scripts/01_did_processing/01_preproc.py` | Step 0: Preprocessing (1 раз) |
| `exec_scripts/01_did_processing/02_01_data_aggregation.py` | Step 1: Агрегація |
| `exec_scripts/01_did_processing/02_02_stockout_detection.py` | Step 2: Stock-out |
| `exec_scripts/01_did_processing/02_03_did_analysis.py` | Step 3: DiD |
| `exec_scripts/01_did_processing/02_04_substitute_analysis.py` | Step 4: Substitutes |
| `exec_scripts/01_did_processing/02_05_reports_cross_market.py` | Step 5: Reports |

**Виконання:**
```bash
# Step 0 (один раз):
python exec_scripts/01_did_processing/01_preproc.py

# Steps 1-5 (один ринок):
python exec_scripts/01_did_processing/02_01_data_aggregation.py --market_id {CLIENT_ID}

# Steps 1-5 (всі ринки):
python exec_scripts/01_did_processing/02_01_data_aggregation.py --all
```

---

## ЗВ'ЯЗОК З PHASE 2

```
PHASE 1 (Per-Market)
    │
    │  Вихід: results/cross_market_data/cross_market_{CLIENT_ID}.csv
    │
    ▼
PHASE 2 (Cross-Market Aggregation)
    │  Документація: ../02_substitution_coefficients/
    │
    │  Агрегація по всіх ринках:
    │  - MARKET_COVERAGE
    │  - WEIGHTED_AVG_SHARE_INTERNAL
    │  - CI_95
    │  - CROSS_MARKET_CLASSIFICATION
    │
    ▼
FINAL: Коефіцієнти субституції across markets
```

---

## НАВІГАЦІЯ

| Ресурс | Посилання |
|--------|-----------|
| Бізнес-контекст | [01_BUSINESS_CONTEXT.md](../00_ai_rules/01_BUSINESS_CONTEXT.md) |
| Відомі проблеми | [02_KNOWN_ISSUES.md](../00_ai_rules/02_KNOWN_ISSUES.md) |
| Структура проекту | [03_PROJECT_MAP.md](../00_ai_rules/03_PROJECT_MAP.md) |
| Конфігурація | `project_core/did_config/` |
