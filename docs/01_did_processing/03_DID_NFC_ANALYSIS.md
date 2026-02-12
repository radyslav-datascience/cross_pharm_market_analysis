# Step 3: DiD аналіз + NFC декомпозиція

> **Версія:** 1.0 | **Створено:** 31.01.2026

---

## 1. ПРИЗНАЧЕННЯ

Третій крок реалізує Difference-in-Differences (DiD) аналіз для оцінки ефекту stock-out:

- Визначення POST-періодів для кожної події
- Ідентифікація valid substitutes (NFC filter + Phantom filter)
- Розрахунок LIFT, SHARE_INTERNAL, SHARE_LOST
- NFC декомпозиція (SAME vs DIFF форми)
- Класифікація препаратів

**Головне питання:** Як відсутність препарату впливає на розподіл попиту покупців?

---

## 2. РЕАЛІЗАЦІЯ

### Скрипт

**Розташування:** `exec_scripts/01_did_processing/02_03_did_analysis.py`

**Виконання:**
```bash
# Один ринок:
/opt/miniconda3/envs/proxima/bin/python exec_scripts/01_did_processing/02_03_did_analysis.py --market_id {CLIENT_ID}

# Всі ринки:
/opt/miniconda3/envs/proxima/bin/python exec_scripts/01_did_processing/02_03_did_analysis.py --all
```

### Допоміжні модулі

| Модуль | Використання |
|--------|--------------|
| `project_core/data_config/paths_config.py` | Шляхи до даних, `load_target_pharmacies()` |
| `project_core/did_config/stockout_params.py` | MIN_POST_PERIOD_WEEKS, MAX_POST_GAP_WEEKS |
| `project_core/did_config/classification_thresholds.py` | CRITICAL_THRESHOLD, SUBSTITUTABLE_THRESHOLD, classify_drug |
| `project_core/did_config/nfc_compatibility.py` | is_compatible, get_compatibility_group |
| `project_core/utility_functions/did_utils.py` | DiD функції: define_post_period, calculate_market_growth, calculate_lift, calculate_shares, nfc_decomposition |

### Вхід / Вихід

```
ВХІД:
  data/processed_data/01_per_market/{CLIENT_ID}/01_aggregation_{CLIENT_ID}/
  └── inn_{INN_ID}_{CLIENT_ID}.csv        # Агреговані дані per INN

  data/processed_data/01_per_market/{CLIENT_ID}/02_stockout_{CLIENT_ID}/
  └── stockout_events_{CLIENT_ID}.csv     # Stock-out події

ВИХІД:
  data/processed_data/01_per_market/{CLIENT_ID}/03_did_analysis_{CLIENT_ID}/
  ├── did_results_{CLIENT_ID}.csv           # DiD результати (всі події + NFC decomposition)
  ├── substitute_mapping_{CLIENT_ID}.csv    # Маппінг target -> substitutes
  └── _stats/
      ├── did_summary_{CLIENT_ID}.csv       # Per INN статистика
      ├── drugs_summary_{CLIENT_ID}.csv     # Per DRUGS + класифікація
      └── did_metadata_{CLIENT_ID}.csv      # Параметри та метадані
```

---

## 3. PIPELINE

```
┌─────────────────────────────────────────────────────────────────────┐
│ 03.1: POST-PERIOD DEFINITION                                        │
├─────────────────────────────────────────────────────────────────────┤
│ Для кожної події:                                                   │
│ 1. Знайти перший тиждень з Q>0 після STOCKOUT_END                   │
│ 2. Перевірити gap ≤ MAX_POST_GAP_WEEKS                              │
│ 3. Визначити POST ≥ MIN_POST_PERIOD_WEEKS                           │
│ → OUTPUT: events_with_periods.csv                                   │
└─────────────────────────────────────────────────────────────────────┘
                                ↓
┌─────────────────────────────────────────────────────────────────────┐
│ 03.2: SUBSTITUTE IDENTIFICATION                                     │
├─────────────────────────────────────────────────────────────────────┤
│ Для кожного target:                                                 │
│ 1. Знайти всі препарати того ж INN                                  │
│ 2. Застосувати NFC COMPATIBILITY FILTER                             │
│ 3. ⚠️ Застосувати PHANTOM FILTER (див. 02_KNOWN_ISSUES.md)          │
│ → OUTPUT: substitute_mapping.csv                                    │
└─────────────────────────────────────────────────────────────────────┘
                                ↓
┌─────────────────────────────────────────────────────────────────────┐
│ 03.3: DiD CORE CALCULATIONS                                         │
├─────────────────────────────────────────────────────────────────────┤
│ MARKET_GROWTH = MARKET_DURING / MARKET_PRE                          │
│ EXPECTED = SALES_PRE × MARKET_GROWTH                                │
│ LIFT = max(0, ACTUAL - EXPECTED)                                    │
│ INTERNAL_LIFT = Σ LIFT всіх substitutes                             │
│ SHARE_INTERNAL = INTERNAL_LIFT / TOTAL_EFFECT                       │
│ SHARE_LOST = 1 - SHARE_INTERNAL                                     │
│ → OUTPUT: did_results.csv                                           │
└─────────────────────────────────────────────────────────────────────┘
                                ↓
┌─────────────────────────────────────────────────────────────────────┐
│ 03.4: NFC DECOMPOSITION                                             │
├─────────────────────────────────────────────────────────────────────┤
│ LIFT_SAME_NFC1 = Σ LIFT substitutes тієї ж форми                    │
│ LIFT_DIFF_NFC1 = Σ LIFT substitutes іншої форми                     │
│ SHARE_SAME_NFC1 = LIFT_SAME / INTERNAL_LIFT                         │
│ → OUTPUT: nfc_decomposition.csv                                     │
└─────────────────────────────────────────────────────────────────────┘
                                ↓
┌─────────────────────────────────────────────────────────────────────┐
│ 03.5: VALIDATION & STATISTICS                                       │
├─────────────────────────────────────────────────────────────────────┤
│ 1. Валідація інваріантів                                            │
│ 2. Агрегація по препаратах                                          │
│ 3. Класифікація: CRITICAL / SUBSTITUTABLE / MIXED                   │
│ → OUTPUT: did_statistics.csv                                        │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 4. NFC COMPATIBILITY FILTER

### Логіка

```python
def is_compatible(form_A: str, form_B: str) -> bool:
    """
    ПРАВИЛА:
    0. EXCLUDED форми → False
    1. Exact Match (form_A == form_B) → True
    2. Обидві в ORAL_GROUP → True
    3. Інше → False
    """
```

### Групи сумісності

```
ORAL_GROUP (взаємозамінні):
  • Пероральные твердые обычные
  • Пероральные твердые длительно действующие
  • Пероральные жидкие обычные

EXACT_MATCH (тільки на себе):
  • Парентеральные обычные (ін'єкції)
  • Местно действующие (креми, мазі)
  • Ректальные системные (свічки)
  • Офтальмологические, Прочие системные

EXCLUDED:
  • Не предназначенные для использования у человека
```

**Реалізація:** `project_core/did_config/nfc_compatibility.py`

---

## 5. PHANTOM SUBSTITUTES FILTER

**⚠️ КРИТИЧНО:** Без цього фільтру результати будуть некоректними!

**Проблема:** NFC filter знаходить substitutes, які теоретично сумісні, але фактично не продавались в аптеці під час stockout.

**Рішення:**
```python
# Перевірити чи substitute має дані під час stockout періодів
valid_substitutes = valid_substitutes[
    valid_substitutes['DRUGS_ID'].apply(
        lambda drug_id: has_data_during_periods(df_agg, drug_id, stockout_periods)
    )
]
```

**Детальніше:** [02_KNOWN_ISSUES.md](../00_ai_rules/02_KNOWN_ISSUES.md) — секція 5

---

## 6. КЛЮЧОВІ ФОРМУЛИ

| Формула | Опис |
|---------|------|
| `MARKET_GROWTH = MARKET_DURING / MARKET_PRE` | Коригує на тренд ринку |
| `EXPECTED = SALES_PRE × MARKET_GROWTH` | Очікувані продажі без stock-out |
| `LIFT = max(0, ACTUAL - EXPECTED)` | Додаткові продажі через stock-out |
| `INTERNAL_LIFT = Σ LIFT` | Сума LIFT всіх substitutes |
| `SHARE_INTERNAL = INTERNAL_LIFT / TOTAL_EFFECT` | Частка що залишилась |
| `SHARE_LOST = 1 - SHARE_INTERNAL` | Частка втрачена |
| `SHARE_SAME_NFC1 = LIFT_SAME / INTERNAL_LIFT` | Частка тієї ж форми |

### 6.1 MARKET_GROWTH: деталі розрахунку

**КРИТИЧНО:** MARKET_GROWTH розраховується на рівні **INN групи** з використанням **ринкових даних** (конкурентів), а не продажів цільової аптеки.

**Формула:**
```python
# PRE-період: ринкові продажі всієї INN групи
df_market_pre = df_inn[(df_inn['Date'] >= pre_start) & (df_inn['Date'] <= pre_end)]
market_pre = df_market_pre['MARKET_TOTAL_DRUGS_PACK'].sum()

# DURING-період: ринкові продажі всієї INN групи
df_market_during = df_inn[(df_inn['Date'] >= stockout_start) & (df_inn['Date'] <= stockout_end)]
market_during = df_market_during['MARKET_TOTAL_DRUGS_PACK'].sum()

# Тренд ринку
market_growth = market_during / market_pre  # якщо market_pre >= MIN_MARKET_PRE
```

**Чому використовуємо MARKET_TOTAL_DRUGS_PACK (а не Q):**

| Показник | Що містить | Чому НЕ підходить для MARKET_GROWTH |
|----------|------------|-------------------------------------|
| `Q` | Продажі цільової аптеки | Спотворено stock-out (Q=0 під час відсутності) |
| `MARKET_TOTAL_DRUGS_PACK` | Продажі конкурентів | Відображає реальний тренд попиту на ринку |

**Логіка:**
- MARKET_GROWTH коригує на загальний тренд ринку (сезонність, зростання/падіння попиту)
- Якщо використовувати `Q` цільової аптеки — під час stock-out `Q=0`, що спотворить тренд
- `MARKET_TOTAL_DRUGS_PACK` агрегує продажі конкурентів і показує **об'єктивний** тренд ринку

**Консистентність з Step 2:**
Level 1 валідація stock-out подій також перевіряє активність на рівні INN групи через `MARKET_TOTAL_DRUGS_PACK` — це забезпечує методологічну консистентність.

---

## 7. КЛАСИФІКАЦІЯ ПРЕПАРАТІВ

```
SHARE_LOST > CRITICAL_THRESHOLD?
      │
  ┌───┴───┐
  ТАК     НІ
  ↓       ↓
CRITICAL  SHARE_INTERNAL > SUBSTITUTABLE_THRESHOLD?
              │
          ┌───┴───┐
          ТАК     НІ
          ↓       ↓
    SUBSTITUTABLE  MIXED
```

| Категорія | Критерій | Рекомендація |
|-----------|----------|--------------|
| **CRITICAL** | SHARE_LOST > threshold | Не допускати stock-out |
| **SUBSTITUTABLE** | SHARE_INTERNAL > threshold | Можна оптимізувати SKU |
| **MIXED** | Інші | Індивідуальний аналіз |

**Пороги:** `project_core/did_config/classification_thresholds.py`

---

## 8. СТРУКТУРА ВИХІДНИХ ДАНИХ

### substitute_mapping.csv

| Колонка | Опис |
|---------|------|
| `INN_ID`, `INN_NAME` | МНН група |
| `TARGET_DRUGS_ID`, `TARGET_DRUGS_NAME` | Target препарат |
| `TARGET_NFC1_ID` | Форма target |
| `SUBSTITUTE_DRUGS_ID`, `SUBSTITUTE_DRUGS_NAME` | Substitute |
| `SUBSTITUTE_NFC1_ID` | Форма substitute |
| `SAME_NFC1` | bool: та сама форма? |
| `NFC_GROUP` | ORAL / EXACT_MATCH |

### did_results_{CLIENT_ID}.csv (фінальний)

| Колонка | Опис |
|---------|------|
| `EVENT_ID`, `CLIENT_ID` | Ідентифікатори |
| `INN_ID`, `INN_NAME` | МНН група |
| `DRUGS_ID`, `DRUGS_NAME` | Препарат |
| `NFC1_ID`, `NFC_ID` | Форма випуску |
| `STOCKOUT_START`, `STOCKOUT_END`, `STOCKOUT_WEEKS` | Stock-out період |
| `PRE_START`, `PRE_END`, `PRE_WEEKS`, `PRE_AVG_Q` | PRE-період |
| `POST_START`, `POST_END`, `POST_WEEKS`, `POST_STATUS` | POST-період |
| `MARKET_PRE`, `MARKET_DURING`, `MARKET_GROWTH` | Ринкові показники |
| `INTERNAL_LIFT`, `LOST_SALES`, `TOTAL_EFFECT` | DiD результати |
| `SHARE_INTERNAL`, `SHARE_LOST` | Основні метрики |
| `SUBSTITUTES_COUNT`, `SUBSTITUTES_WITH_LIFT` | Статистика substitutes |
| `LIFT_SAME_NFC1`, `LIFT_DIFF_NFC1` | NFC декомпозиція |
| `SHARE_SAME_NFC1`, `SHARE_DIFF_NFC1` | NFC частки |

---

## 9. КОНФІГУРАЦІЯ

Параметри визначені в `project_core/did_config/`:

**stockout_params.py:**
| Параметр | Значення | Опис |
|----------|----------|------|
| `MIN_POST_PERIOD_WEEKS` | 4 | Мінімум тижнів POST-періоду |
| `MAX_POST_GAP_WEEKS` | 2 | Максимальний gap до відновлення |
| `MIN_MARKET_PRE` | 1.0 | Мін. продажі PRE для MARKET_GROWTH |
| `MIN_TOTAL_FOR_SHARE` | 0.001 | Мін. TOTAL_EFFECT для SHARE розрахунку |

**classification_thresholds.py:**
| Параметр | Значення | Опис |
|----------|----------|------|
| `CRITICAL_THRESHOLD` | 0.40 | Поріг SHARE_LOST для CRITICAL |
| `SUBSTITUTABLE_THRESHOLD` | 0.60 | Поріг SHARE_INTERNAL для SUBSTITUTABLE |

---

## 10. ВАЛІДАЦІЯ

### Інваріанти (завжди перевіряти)

```python
# 1. Сума SHARE = 1.0
assert abs(SHARE_INTERNAL + SHARE_LOST - 1.0) < 0.001

# 2. NFC сума = 1.0
assert abs(SHARE_SAME_NFC1 + SHARE_DIFF_NFC1 - 1.0) < 0.001

# 3. LIFT декомпозиція
assert abs(LIFT_SAME_NFC1 + LIFT_DIFF_NFC1 - INTERNAL_LIFT) < 0.01
```

### Edge Cases

| Ситуація | Обробка |
|----------|---------|
| Немає valid substitutes | SHARE_INTERNAL = 0, SHARE_LOST = 1 |
| TOTAL_EFFECT = 0 | SHARE метрики = NaN |
| INTERNAL_LIFT = 0 | SHARE_SAME/DIFF_NFC1 = NaN |
| POST не визначено | Подія відхиляється |

---

## 11. ЗВ'ЯЗОК З ІНШИМИ КРОКАМИ

```
STEP 1: АГРЕГАЦІЯ
    │  Документація: 01_DATA_AGREGATION.md
    │  Вихід: inn_{INN_ID}_{CLIENT_ID}.csv
    │
    ▼
STEP 2: ДЕТЕКЦІЯ STOCK-OUT
    │  Документація: 02_STOCKOUT_DETECTION.md
    │  Вихід: stockout_events_{CLIENT_ID}.csv
    │
    ▼
STEP 3: DiD АНАЛІЗ (цей документ)
    │  Вхід: stockout_events_{CLIENT_ID}.csv + inn_{INN_ID}_{CLIENT_ID}.csv
    │  Вихід: did_results_{CLIENT_ID}.csv, substitute_mapping_{CLIENT_ID}.csv
    │
    │  Що передається далі:
    │  - SHARE_INTERNAL, SHARE_LOST (основні метрики)
    │  - SHARE_SAME_NFC1, SHARE_DIFF_NFC1 (NFC декомпозиція)
    │  - CLASSIFICATION (per drug)
    │
    ▼
STEP 4: АНАЛІЗ SUBSTITUTES
    │  Документація: 04_SUBSTITUTE_SHARE_ANALYSIS.md
    │  Розраховує: SUBSTITUTE_SHARE
    │
    ▼
STEP 5: ЗВІТИ ТА CSV
       Документація: 05_REPORTS_AND_GRAPHS.md
```

---

## 12. ТИПОВІ ПОМИЛКИ

| Помилка | Симптом | Рішення |
|---------|---------|---------|
| Phantom substitutes | 0% SHARE в звіті | Перевірити Phantom Filter |
| Невірні SHARE суми | ≠ 100% | Перевірити інваріанти |
| Багато NaN | Відсутні дані | Перевірити POST validation |
| Всі CRITICAL | SHARE_LOST завищений | Перевірити NFC filter |

**Детальніше:** [02_KNOWN_ISSUES.md](../00_ai_rules/02_KNOWN_ISSUES.md)
