# KNOWLEDGE BASE - cross_pharm_market_analysis

> **Версія:** 1.0 | **Створено:** 31.01.2026
> **Призначення:** Комплексний документ для NotebookLM — опис проекту, методології, алгоритмів та правил розрахунків

---

# ЧАСТИНА 1: ОГЛЯД ПРОЕКТУ

## 1.1 Про проект

**cross_pharm_market_analysis** — мульти-ринковий шаблон для дослідження субституції препаратів у фармацевтичній мережі.

Проект реалізує **Difference-in-Differences (DiD) аналіз** для оцінки поведінки покупців при stock-out (відсутності препарату в аптеці) з подальшою агрегацією результатів по 50+ локальних ринках.

## 1.2 Ключове бізнес-питання

### Рівень 1: Per-Market Analysis
**Що відбувається з попитом, коли препарат відсутній в аптеці?**

```
Покупець приходить за НУРОФЕН таблетками, а їх немає:
├─ Купує ІБУПРОФЕН таблетки в цій же аптеці? (INTERNAL)
├─ Купує НУРОФЕН в іншій аптеці? (LOST)
└─ Якщо купує substitute — чи важлива форма випуску?
```

### Рівень 2: Cross-Market Analysis
**Чи є субституційна поведінка стабільною across markets?**

```
Препарат X на 50+ ринках:
├─ SHARE_INTERNAL стабільно високий → SUBSTITUTABLE
├─ SHARE_INTERNAL стабільно низький → CRITICAL
└─ SHARE_INTERNAL нестабільний → MODERATE
```

## 1.3 Цільові метрики

### Per-Market метрики

| Метрика | Формула | Інтерпретація |
|---------|---------|---------------|
| **SHARE_INTERNAL** | INTERNAL_LIFT / TOTAL_EFFECT | Частка попиту, що залишилась в аптеці |
| **SHARE_LOST** | LOST_SALES / TOTAL_EFFECT | Частка попиту, що пішла до конкурентів |
| **SHARE_SAME_NFC1** | LIFT_SAME_NFC1 / INTERNAL_LIFT | Частка, що обрала ту ж форму випуску |
| **SUBSTITUTE_SHARE** | LIFT_substitute / INTERNAL_LIFT | Частка конкретного substitute |

### Cross-Market метрики

| Метрика | Формула | Інтерпретація |
|---------|---------|---------------|
| **MARKET_COVERAGE** | N_markets_with_drug / N_total | % ринків з препаратом |
| **MEAN_SHARE_INTERNAL** | mean(SHARE_INTERNAL) | Середня субституція |
| **CI_95** | mean ± 1.96 * (std / sqrt(N)) | 95% довірчий інтервал |

## 1.4 Як читати результати

```
SHARE_INTERNAL = 75% означає:
  → 75% покупців купили substitute в нашій аптеці
  → 25% пішли до конкурентів

MARKET_COVERAGE = 90% означає:
  → Препарат присутній на 90% з 50+ ринків

CI_95 = [65%, 85%] означає:
  → З 95% впевненістю реальний SHARE_INTERNAL між 65% і 85%
```

---

# ЧАСТИНА 2: МЕТОДОЛОГІЯ DiD

## 2.1 Чому Difference-in-Differences

### Проблема каузальності

Просте порівняння продажів "до" і "після" stock-out не працює, бо:
- Ринок має власні тренди (сезонність, епідемії)
- Конкуренти змінюють ціни та асортимент
- Неможливо відокремити ефект stock-out від фонових змін

### Альтернативні підходи та їх недоліки

| Підхід | Чому не підходить |
|--------|-------------------|
| **A/B тест** | Неможливо контролювати stock-out — це природне явище |
| **Before-After** | Не враховує фонові тренди ринку |
| **Cross-sectional** | Не враховує індивідуальні особливості препаратів |
| **Регресія** | Потребує багато контрольних змінних, складно інтерпретувати |

### Чому DiD підходить

**Difference-in-Differences** вирішує проблему каузальності через:

1. **Контрольна група** — конкуренти (той самий препарат, але без stock-out)
2. **Подвійна різниця** — віднімаємо зміну в контрольній групі від зміни в treatment

```
DiD Effect = (Treatment_After - Treatment_Before) - (Control_After - Control_Before)
```

**Інтуїція:** Якщо ринок зріс на 10%, а substitute продажі зросли на 25% — реальний ефект stock-out = 15%.

## 2.2 Концепція розподілу попиту

```
                     STOCK-OUT ПОДІЯ
                (Препарат X відсутній в нашій аптеці)
                              │
                              ▼
              ┌───────────────────────────────────┐
              │   ПОПИТ НА ПРЕПАРАТ X (100%)      │
              │   (Покупець прийшов за ним)       │
              └───────────────────────────────────┘
                        │             │
                        ▼             ▼
         ┌──────────────────┐  ┌──────────────────┐
         │  SHARE_INTERNAL  │  │   SHARE_LOST     │
         │  (Залишився)     │  │   (Втрачено)     │
         │                  │  │                  │
         │  Купив substitute│  │  Пішов в ІНШУ   │
         │  в НАШІЙ аптеці  │  │  аптеку за X    │
         └──────────────────┘  └──────────────────┘
                  │                     │
                  ▼                     │
         ┌──────────────────┐          │
         │  NFC ДЕКОМПОЗИЦІЯ│          │
         ├──────────────────┤          │
         │ SHARE_SAME_NFC1  │          │
         │ (та сама форма)  │          │
         ├──────────────────┤          ▼
         │ SHARE_DIFF_NFC1  │   ВТРАЧЕНИЙ ДОХІД
         │ (інша форма)     │   (конкуренти заробили)
         └──────────────────┘
```

## 2.3 Ключові формули

### Базові розрахунки

| Формула | Опис | Призначення |
|---------|------|-------------|
| `MARKET_GROWTH = MARKET_DURING / MARKET_PRE` | Тренд ринку | Контроль фонових змін |
| `EXPECTED = PRE_AVG_Q × MARKET_GROWTH` | Очікувані продажі | Counterfactual |
| `LIFT = max(0, ACTUAL - EXPECTED)` | Додаткові продажі | Ефект stock-out |

### SHARE метрики

| Метрика | Формула | Інтерпретація |
|---------|---------|---------------|
| `INTERNAL_LIFT` | `SUM(LIFT)` всіх substitutes | Скільки попиту перейшло на substitutes |
| `LOST_SALES` | `SUM(COMP_LIFT)` конкурентів | Скільки пішло до конкурентів |
| `TOTAL_EFFECT` | `INTERNAL_LIFT + LOST_SALES` | Загальний перерозподіл |
| `SHARE_INTERNAL` | `INTERNAL_LIFT / TOTAL_EFFECT` | % що залишився у нас |
| `SHARE_LOST` | `LOST_SALES / TOTAL_EFFECT` | % що пішов до конкурентів |

### NFC декомпозиція

| Метрика | Формула | Інтерпретація |
|---------|---------|---------------|
| `LIFT_SAME_NFC1` | `SUM(LIFT)` тієї ж форми | Субституція в межах форми |
| `LIFT_DIFF_NFC1` | `SUM(LIFT)` іншої форми | Субституція між формами |
| `SHARE_SAME_NFC1` | `LIFT_SAME / INTERNAL_LIFT` | Важливість форми випуску |

### Інваріанти (для валідації)

```
SHARE_INTERNAL + SHARE_LOST = 1.0
SHARE_SAME_NFC1 + SHARE_DIFF_NFC1 = 1.0
LIFT_SAME + LIFT_DIFF = INTERNAL_LIFT
SUM(SUBSTITUTE_SHARE) = 100% (для кожного stockout drug)
```

---

# ЧАСТИНА 3: NFC COMPATIBILITY FILTER

## 3.1 Проблема

Без фільтру методологія вважала б, що крем може замінити таблетку — це клінічно неможливо та хибно завищує SHARE_INTERNAL.

## 3.2 Клінічне обґрунтування

Форми випуску мають різні:
- **Шляхи введення** (перорально, парентерально, місцево)
- **Біодоступність** (швидкість та повнота всмоктування)
- **Показання** (системна дія vs локальна)

Покупець, який прийшов за таблетками, НЕ купить крем як заміну.

## 3.3 NFC1 категорії

```
ORAL_GROUP (взаємозамінні):
├─ Пероральные твердые обычные (таблетки, капсули)
├─ Пероральные жидкие обычные (сиропи)
└─ Пероральные твердые длительно действующие

EXACT_MATCH (тільки на себе):
├─ Парентеральные обычные (ін'єкції)
├─ Местно действующие (мазі, гелі)
├─ Ректальные системные (свічки)
└─ Інші форми

EXCLUDED:
└─ Не предназначенные для использования у человека
```

## 3.4 Правила сумісності

| Група | Форми | Правило |
|-------|-------|---------|
| **ORAL_GROUP** | Пероральні тверді, рідкі, пролонговані | Взаємозамінні |
| **EXACT_MATCH** | Парентеральні, місцеві, ректальні, офтальмологічні | Тільки на себе |
| **EXCLUDED** | Не для людини | Виключаються |

## 3.5 Логіка фільтру

```python
def is_compatible(form_A, form_B):
    if form_A in EXCLUDED or form_B in EXCLUDED:
        return False
    if form_A == form_B:
        return True
    if form_A in ORAL_GROUP and form_B in ORAL_GROUP:
        return True
    return False
```

## 3.6 Вплив на результати

| Аспект | Без фільтру | З фільтром |
|--------|-------------|------------|
| SHARE_INTERNAL | Завищений | Реалістичний |
| CRITICAL препаратів | Менше | Більше |
| Бізнес-рекомендації | Хибні | Коректні |

---

# ЧАСТИНА 4: КЛАСИФІКАЦІЯ ПРЕПАРАТІВ

## 4.1 Per-Market класифікація

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

## 4.2 Cross-Market класифікація

```
IF CI_95_UPPER < low_threshold:
    → CRITICAL (стабільно погана субституція)

ELIF CI_95_LOWER > high_threshold:
    → SUBSTITUTABLE (стабільно хороша субституція)

ELSE:
    → MODERATE (невизначеність)
```

## 4.3 Категорії та бізнес-значення

| Категорія | Критерій | Бізнес-значення |
|-----------|----------|-----------------|
| **CRITICAL** | Високий SHARE_LOST across markets | Обов'язково тримати в наявності |
| **SUBSTITUTABLE** | Високий SHARE_INTERNAL across markets | Можна оптимізувати SKU |
| **MODERATE** | Нестабільний результат | Аналізувати індивідуально |

## 4.4 Бізнес-рекомендації

### CRITICAL препарати — не допускати stock-out:
- Встановити safety stock
- Налаштувати автозамовлення
- Моніторити залишки
- Диверсифікувати постачальників

### SUBSTITUTABLE препарати — можна оптимізувати SKU:
- Зменшити кількість позицій в групі
- Тримати 2-3 найпопулярніші варіанти
- Покупці переключаться на substitute
- Фокус на маржинальність

### MODERATE препарати — індивідуальний аналіз:
- Аналіз по регіонах
- Аналіз маржинальності
- Врахування локальних факторів

---

# ЧАСТИНА 5: PIPELINE (2 ФАЗИ)

## 5.1 Загальна схема

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    PHASE 1: PER-MARKET PROCESSING                           │
│                    (для кожного з 50+ ринків)                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  Step 1          Step 2           Step 3          Step 4        Step 5      │
│  ────────        ────────         ────────        ────────      ────────    │
│  Агрегація  →    Детекція    →    DiD        →   Substitute →  Звіти       │
│  даних           stock-out        аналіз         аналіз        + CSV        │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
                                        │
                                        ▼
                              Cross-Market CSV
                                        │
                                        ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                    PHASE 2: CROSS-MARKET AGGREGATION                        │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  Агрегація по всіх ринках → CI_95 → Cross-Market Classification             │
│                                                                              │
│  ВИХІД: Стабільні коефіцієнти субституції                                   │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

## 5.2 PHASE 1: Step 1 — Агрегація даних

### Призначення
Підготувати чисті, консистентні дані для аналізу: тижнева агрегація, заповнення пропусків, розрахунок ринкових показників.

### Ключовий алгоритм: Gap Filling (КРИТИЧНО!)

```
Проблема: Сирі дані містять ТІЛЬКИ тижні з продажами.
          Тижні без продажів (stock-out) ВІДСУТНІ в даних!

Рішення: Для кожного препарату створити повний ряд тижнів,
         заповнити пропуски Q=0

ЧОМУ ЦЕ КРИТИЧНО:
- Без GAP FILLING ми НЕ бачимо періоди stock-out
- DiD-аналіз базується на виявленні переходу від продажів до нуля
- Пропущені нулі = пропущені stock-out events
```

**Приклад Gap Filling:**
```
До GAP FILLING:           Після GAP FILLING:
Week 1: Q=10              Week 1: Q=10
Week 3: Q=15              Week 2: Q=0  ← STOCK-OUT!
Week 5: Q=8               Week 3: Q=15
                          Week 4: Q=0  ← STOCK-OUT!
                          Week 5: Q=8
```

## 5.3 PHASE 1: Step 2 — Детекція Stock-out

### Визначення Stock-out
Період, коли препарат був відсутній у цільовій аптеці (Q=0 протягом ≥ MIN_STOCKOUT_WEEKS тижнів).

### Багаторівнева валідація

```
РІВЕНЬ 1: MARKET ACTIVITY
  Чи був ринок INN групи активний під час stock-out?
  Якщо НІ → ВІДХИЛЕНО

РІВЕНЬ 2: PRE-PERIOD SALES
  Чи були продажі препарату до stock-out?
  Якщо НІ → ВІДХИЛЕНО

РІВЕНЬ 3: COMPETITORS AVAILABILITY
  Чи продавали конкуренти цей препарат?
  Якщо НІ → ВІДХИЛЕНО

ПОДІЯ ВАЛІДНА → Розрахунок PRE_AVG_Q, збереження
```

## 5.4 PHASE 1: Step 3 — DiD Аналіз

### Pipeline

```
1. POST-PERIOD DEFINITION
   → Знайти перший тиждень з Q>0 після STOCKOUT_END
   → Перевірити gap ≤ MAX_POST_GAP_WEEKS

2. SUBSTITUTE IDENTIFICATION
   → Знайти всі препарати того ж INN
   → Застосувати NFC COMPATIBILITY FILTER
   → ⚠️ Застосувати PHANTOM FILTER

3. DiD CORE CALCULATIONS
   → MARKET_GROWTH, EXPECTED, LIFT
   → SHARE_INTERNAL, SHARE_LOST

4. NFC DECOMPOSITION
   → LIFT_SAME_NFC1, LIFT_DIFF_NFC1
   → SHARE_SAME_NFC1, SHARE_DIFF_NFC1
```

### Критичний фільтр: Phantom Substitutes

**Проблема:** NFC filter знаходить substitutes, які теоретично сумісні, але фактично не продавались в аптеці під час stockout.

**Рішення:** Перевірити чи substitute має дані хоча б в одному stockout періоді.

## 5.5 PHASE 1: Step 4 — Аналіз Substitutes

### Бізнес-питання
Коли препарат X відсутній — який саме substitute забирає найбільше попиту?

### Критичний фільтр: Zero-LIFT

**Проблема:** Деякі substitutes мають TOTAL_LIFT = 0 — вони існували в асортименті, але покупці їх НЕ обирали як заміну.

**Рішення:** Фільтрувати substitutes з TOTAL_LIFT = 0.

## 5.6 PHASE 1: Step 5 — Звіти та CSV

### Типи виходів

| Тип | Формат | Призначення |
|-----|--------|-------------|
| Технічний звіт | Excel | Повні дані для аналітиків |
| Бізнес-звіт | Excel | Ключові метрики для керівництва |
| Cross-Market CSV | CSV | Flat data для Phase 2 |

## 5.7 PHASE 2: Cross-Market Aggregation

### Призначення
Агрегація результатів по всіх ринках для отримання стабільних коефіцієнтів.

### Метрики

| Метрика | Формула |
|---------|---------|
| MARKET_COVERAGE | N_markets_with_drug / N_total |
| MEAN_SHARE_INTERNAL | mean(SHARE_INTERNAL across markets) |
| STD_SHARE_INTERNAL | std(SHARE_INTERNAL across markets) |
| CI_95 | mean ± 1.96 * (std / sqrt(N)) |

### Класифікація

```
IF CI_95_UPPER < 0.40:  → CRITICAL
ELIF CI_95_LOWER > 0.60: → SUBSTITUTABLE
ELSE:                    → MODERATE
```

---

# ЧАСТИНА 6: СТРУКТУРА ПРОЕКТУ

## 6.1 Файлова структура

```
cross_pharm_market_analysis/
├── data/
│   ├── raw/                           # Вхідні дані
│   │   ├── Rd2_125467.csv
│   │   ├── Rd2_125468.csv
│   │   └── ... (50+ файлів)
│   └── processed_data/
│       ├── 01_data_aggregation/market_{ID}/
│       ├── 02_stockout_detection/market_{ID}/
│       ├── 03_did_analysis/market_{ID}/
│       └── 04_substitute_analysis/market_{ID}/
│
├── exec_scripts/
│   ├── 01_did_processing/
│   │   ├── 01_preproc.py                  # Phase 0
│   │   ├── 02_01_data_aggregation.py      # Phase 1, Step 1
│   │   ├── 02_02_stockout_detection.py    # Phase 1, Step 2
│   │   ├── 02_03_did_analysis.py          # Phase 1, Step 3
│   │   ├── 02_04_substitute_analysis.py   # Phase 1, Step 4
│   │   └── 02_05_reports_cross_market.py  # Phase 1, Step 5
│   └── 02_substitution_coefficients/
│       └── 01_data_preparation.py         # Phase 2, Step 1
│
├── project_core/
│   ├── data_config/
│   │   └── paths_config.py            # Шляхи до даних
│   ├── did_config/
│   │   ├── classification_thresholds.py # Пороги
│   │   └── nfc_compatibility.py       # NFC фільтр
│   └── utility_functions/
│       ├── etl_utils.py               # ETL функції
│       └── did_utils.py               # DiD функції
│
├── results/
│   ├── data_reports/reports_{ID}/     # Excel звіти per market
│   └── cross_market_data/             # CSV для Phase 2
│
└── docs/
    ├── 00_ai_rules/                   # Правила для AI
    ├── 01_did_processing/             # Phase 1 документація
    ├── 02_substitution_coefficients/  # Phase 2 документація
    └── 03_project_instructions/       # Методологія, історія
```

## 6.2 Виконання скриптів

```bash
# Conda environment
/opt/miniconda3/envs/proxima/bin/python

# Один ринок
/opt/miniconda3/envs/proxima/bin/python exec_scripts/01_did_processing/02_01_data_aggregation.py --market_id 125467

# Всі ринки
/opt/miniconda3/envs/proxima/bin/python exec_scripts/01_did_processing/02_01_data_aggregation.py --all
```

---

# ЧАСТИНА 7: ВІДОМІ ПРОБЛЕМИ ТА EDGE CASES

## 7.1 Критичні помилки (уникати!)

### 1. Gap Filling — ОБОВ'ЯЗКОВИЙ

**Проблема:** Без gap filling stock-out детекція працює некоректно.

**Симптом:** Категорія "UNKNOWN", рекомендація "Insufficient data".

**Перевірка:** Після gap filling кожен препарат має безперервний часовий ряд.

### 2. Stock-out = рядки з Q=0, НЕ відсутні рядки

**Проблема:** Після gap filling всі рядки є (з Q=0), тому шукати "відсутні рядки" — неправильно.

```python
# НЕПРАВИЛЬНО:
if week not in weeks_with_sales:

# ПРАВИЛЬНО:
df_drug['has_sales'] = df_drug['Q'] > 0
stockout_weeks = df_drug[~df_drug['has_sales']]
```

### 3. Target Pharmacy — фільтрувати по ORG_ID == CLIENT_ID

**Проблема:** В даних є продажі як цільової аптеки, так і конкурентів.

```python
# ПРАВИЛЬНО:
df_target = df[df['ORG_ID'] == df['CLIENT_ID']]
df_competitors = df[df['ORG_ID'] != df['CLIENT_ID']]
```

### 4. Phantom Substitutes — фільтрувати на Step 3

**Симптом:** Substitutes з 0% SUBSTITUTE_SHARE у звіті.

**Рішення:** Перевіряти наявність даних substitute під час stockout.

### 5. Zero-LIFT Substitutes — фільтрувати на Step 4

**Проблема:** Substitutes з TOTAL_LIFT = 0 не мають цінності для аналізу.

**Рішення:** `df_agg = df_agg[df_agg['TOTAL_LIFT'] > 0].copy()`

### 6. Каскадний вплив змін

**Правило:** При зміні Step N — перезапустити всі Step > N.

## 7.2 Мульти-ринкові проблеми

### 7. INN групи можуть відрізнятись між ринками

**Рішення:** Динамічна валідація INN при обробці кожного ринку.

### 8. Мала кількість ринків для статистики

**Проблема:** При coverage < 50% довірчі інтервали занадто широкі.

**Рішення:** Класифікувати як "INSUFFICIENT_DATA".

## 7.3 Валідація інваріантів

```python
# SHARE сума = 1.0
assert abs(SHARE_INTERNAL + SHARE_LOST - 1.0) < 0.001

# NFC сума = 1.0 (якщо є INTERNAL_LIFT)
if INTERNAL_LIFT > 0:
    assert abs(SHARE_SAME_NFC1 + SHARE_DIFF_NFC1 - 1.0) < 0.001

# SUBSTITUTE_SHARE сума = 100%
share_sums = df.groupby('STOCKOUT_DRUG_ID')['SUBSTITUTE_SHARE'].sum()
assert (abs(share_sums - 100.0) < 0.1).all()

# Cross-market
assert 0 <= MARKET_COVERAGE <= 1
assert CI_LOWER <= MEAN_SHARE <= CI_UPPER
```

---

# ЧАСТИНА 8: ГЛОСАРІЙ

## 8.1 Терміни аналізу

| Термін | Визначення |
|--------|------------|
| **DiD** | Difference-in-Differences — метод оцінки ефекту |
| **Stock-out** | Період відсутності препарату (Q=0 ≥ 1 тиждень) |
| **PRE-період** | Тижні до stock-out (baseline) |
| **LIFT** | Додаткові продажі: max(0, ACTUAL - EXPECTED) |
| **MARKET_GROWTH** | Коефіцієнт росту ринку |
| **Substitute** | Препарат тієї ж INN групи, що може замінити відсутній |
| **Phantom Substitute** | Substitute без реальних даних під час stockout |
| **Zero-LIFT Substitute** | Substitute, який ніхто не обирав (LIFT=0) |

## 8.2 Терміни даних

| Термін | Визначення |
|--------|------------|
| **CLIENT_ID** | ID цільової аптеки (з назви файлу Rd2_{ID}.csv) |
| **ORG_ID** | ID аптеки, що здійснила продаж |
| **INN** | Міжнародна непатентована назва (діюча речовина) |
| **NFC1** | Широка категорія форми випуску |
| **DRUGS_ID** | Morion ID препарату |
| **Gap Filling** | Заповнення пропущених тижнів нулями |
| **Local Market** | Географічна зона навколо цільової аптеки |

## 8.3 Метрики

| Метрика | Визначення |
|---------|------------|
| **SHARE_INTERNAL** | Частка попиту що залишилась у нас |
| **SHARE_LOST** | Частка попиту що пішла до конкурентів |
| **SHARE_SAME_NFC1** | Частка substitutes тієї ж форми |
| **SUBSTITUTE_SHARE** | Частка конкретного substitute |
| **MARKET_COVERAGE** | % ринків, де препарат присутній |
| **CI_95** | 95% довірчий інтервал |
| **CLASSIFICATION** | Категорія препарату |

---

# ШВИДКА ДОВІДКА

## Основні метрики

| Метрика | Що показує |
|---------|-----------|
| SHARE_INTERNAL | % попиту що залишився у нас |
| SHARE_LOST | % попиту що пішов до конкурентів |
| MARKET_COVERAGE | % ринків з препаратом |
| CI_95 | Невизначеність оцінки |

## Класифікація

| Категорія | Рекомендація |
|-----------|--------------|
| CRITICAL | KEEP — не допускати stock-out |
| SUBSTITUTABLE | CONSIDER_REMOVAL — можна оптимізувати |
| MODERATE | REVIEW — потрібен аналіз |

## NFC фільтр

| Група | Правило |
|-------|---------|
| ORAL_GROUP | Взаємозамінні |
| EXACT_MATCH | Тільки на себе |
| EXCLUDED | Виключаються |

## Pipeline

```
Phase 1: Per-Market (для кожного ринку)
  Step 1 → Step 2 → Step 3 → Step 4 → Step 5 → CSV

Phase 2: Cross-Market
  Агрегація CSV → CI_95 → Classification
```

## Інваріанти

```
SHARE_INTERNAL + SHARE_LOST = 1.0
SHARE_SAME_NFC1 + SHARE_DIFF_NFC1 = 1.0
SUM(SUBSTITUTE_SHARE) = 100%
0 <= MARKET_COVERAGE <= 1
```

---

*Документ створено для завантаження в NotebookLM. Версія 1.0, 31.01.2026*
