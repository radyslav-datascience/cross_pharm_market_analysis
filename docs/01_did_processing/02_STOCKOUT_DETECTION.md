# Step 2: Ідентифікація Stock-out подій

> **Версія:** 1.0 | **Створено:** 31.01.2026

---

## 1. ПРИЗНАЧЕННЯ

Другий крок pipeline відповідає за виявлення та валідацію періодів відсутності препаратів (stock-out):

- Ідентифікація послідовних тижнів з нульовими продажами
- Багаторівнева валідація якості подій
- Визначення PRE-періодів для кожної події
- Розрахунок базових метрик (PRE_AVG_Q)

**Визначення Stock-out:** Період, коли препарат був відсутній у цільовій аптеці (Q=0 протягом ≥ MIN_STOCKOUT_WEEKS тижнів).

---

## 2. РЕАЛІЗАЦІЯ

### Скрипт

**Розташування:** `exec_scripts/01_did_processing/02_02_stockout_detection.py`

**Виконання:**
```bash
# Один ринок:
/opt/miniconda3/envs/proxima/bin/python exec_scripts/01_did_processing/02_02_stockout_detection.py --market_id {CLIENT_ID}

# Всі ринки:
/opt/miniconda3/envs/proxima/bin/python exec_scripts/01_did_processing/02_02_stockout_detection.py --all
```

### Допоміжні модулі

| Модуль | Використання |
|--------|--------------|
| `project_core/data_config/paths_config.py` | Шляхи до даних, `load_target_pharmacies()` |
| `project_core/did_config/stockout_params.py` | MIN_STOCKOUT_WEEKS, MIN_PRE_PERIOD_WEEKS |

### Вхід / Вихід

```
ВХІД:
  data/processed_data/01_per_market/{CLIENT_ID}/01_aggregation_{CLIENT_ID}/
  └── inn_{INN_ID}_{CLIENT_ID}.csv    # Агреговані дані per INN

ВИХІД:
  data/processed_data/01_per_market/{CLIENT_ID}/02_stockout_{CLIENT_ID}/
  ├── stockout_events_{CLIENT_ID}.csv    # Валідовані події (всі INN)
  └── _stats/
      ├── stockout_summary_{CLIENT_ID}.csv   # Загальна статистика
      └── stockout_per_inn_{CLIENT_ID}.csv   # Статистика per INN
```

---

## 3. ВХІДНІ ДАНІ

**Джерело:** Агреговані дані з Step 1

| Колонка | Використання |
|---------|--------------|
| `Date` | Визначення тижнів без продажів |
| `DRUGS_ID` | Групування по препаратах |
| `Q` | Ідентифікація stock-out (Q=0) |
| `MARKET_TOTAL_DRUGS_PACK` | Валідація активності ринку |
| `NFC1_ID`, `NFC_ID` | Класифікація форм випуску |
| `DRUGS_NAME`, `INN_NAME` | Інформація для звітів |

---

## 4. АЛГОРИТМИ

### 4.1 Ідентифікація Stock-out періодів

Stock-out період — це послідовність тижнів з Q=0, яка:
1. Починається після тижня з продажами (Q > 0)
2. Закінчується перед тижнем з продажами АБО в кінці даних
3. Має тривалість ≥ MIN_STOCKOUT_WEEKS

```python
def identify_stockout_periods(df_drug: pd.DataFrame, min_stockout_weeks: int) -> list:
    """
    Ідентифікувати періоди stock-out для одного препарату.

    Parameters:
    -----------
    df_drug : DataFrame
        Дані одного препарату (відсортовані по Date)
    min_stockout_weeks : int
        Мінімальна тривалість stock-out (з did_config)

    Returns:
    --------
    list : Список словників {'start': date, 'end': date, 'weeks': int}
    """
    df_sorted = df_drug.sort_values('Date').copy()
    df_sorted['has_sales'] = df_sorted['Q'] > 0

    stockout_periods = []
    current_start = None
    current_weeks = 0

    for _, row in df_sorted.iterrows():
        if not row['has_sales']:
            # Stock-out тиждень
            if current_start is None:
                current_start = row['Date']
            current_weeks += 1
        else:
            # Продажі — закриваємо поточний stock-out
            if current_start is not None and current_weeks >= min_stockout_weeks:
                stockout_periods.append({
                    'start': current_start,
                    'end': row['Date'] - timedelta(days=7),
                    'weeks': current_weeks
                })
            current_start = None
            current_weeks = 0

    # Останній період (якщо дані закінчуються stock-out)
    if current_start is not None and current_weeks >= min_stockout_weeks:
        stockout_periods.append({
            'start': current_start,
            'end': df_sorted['Date'].max(),
            'weeks': current_weeks
        })

    return stockout_periods
```

### 4.2 Визначення PRE-періоду

```
PRE_END = STOCKOUT_START - 7 днів
PRE_START = PRE_END - (MIN_PRE_PERIOD_WEEKS - 1) * 7 днів
```

**Призначення PRE-періоду:**
- Розрахунок PRE_AVG_Q (середні продажі до stock-out)
- Базова лінія для DiD-аналізу
- Валідація: чи були продажі до stock-out?

### 4.3 Pipeline валідації

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         БАГАТОРІВНЕВА ВАЛІДАЦІЯ                          │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │ РІВЕНЬ 1: MARKET ACTIVITY                                       │    │
│  │ Питання: Чи був ринок INN групи активний під час stock-out?     │    │
│  │                                                                  │    │
│  │ Перевірка: MARKET_TOTAL_DRUGS_PACK > 0 під час stock-out        │    │
│  │ Якщо НІ → ВІДХИЛЕНО (no_market_activity)                        │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                              ↓ ТАК                                      │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │ РІВЕНЬ 2: PRE-PERIOD SALES                                      │    │
│  │ Питання: Чи були продажі препарату до stock-out?                │    │
│  │                                                                  │    │
│  │ Перевірка: Q > 0 хоча б в один тиждень PRE-періоду              │    │
│  │ Якщо НІ → ВІДХИЛЕНО (no_pre_sales)                              │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                              ↓ ТАК                                      │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │ РІВЕНЬ 3: COMPETITORS AVAILABILITY                              │    │
│  │ Питання: Чи продавали конкуренти цей препарат?                  │    │
│  │                                                                  │    │
│  │ Перевірка: MARKET_TOTAL_DRUGS_PACK > 0 для цього DRUGS_ID       │    │
│  │ Якщо НІ → ВІДХИЛЕНО (no_competitors)                            │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                              ↓ ТАК                                      │
│                                                                         │
│  ПОДІЯ ВАЛІДНА → Розрахунок PRE_AVG_Q, збереження                      │
└─────────────────────────────────────────────────────────────────────────┘
```

### 4.4 Рівні валідації: деталі

Три рівні валідації працюють на **різних рівнях агрегації** — це свідоме архітектурне рішення для забезпечення консистентності з DiD аналізом та якості даних.

#### Рівень 1: Market Activity (INN group level)

**Питання:** Чи був ринок INN групи взагалі активний під час stock-out?

**Рівень перевірки:** Вся INN група (всі препарати в межах МНН)

**Формула:**
```python
df_inn_during = df_inn[(df_inn['Date'] >= stockout_start) & (df_inn['Date'] <= stockout_end)]
market_during_inn = df_inn_during['MARKET_TOTAL_DRUGS_PACK'].sum()
```

**Чому INN group level:**
- Якщо вся INN група неактивна — це не stock-out конкретного препарату, а відсутність попиту на категорію
- Консистентність з MARKET_GROWTH в Step 3, який також розраховується на рівні INN групи
- Якби перевіряли тільки конкретний препарат — могли б відхиляти валідні події (препарат міг зникнути з ринку, але INN ще активний)

#### Рівень 2: PRE-period Sales (drug level)

**Питання:** Чи були продажі саме цього препарату до stock-out?

**Рівень перевірки:** Конкретний препарат (DRUGS_ID)

**Формула:**
```python
df_pre = df_drug[(df_drug['Date'] >= pre_start) & (df_drug['Date'] <= pre_end)]
pre_sales = df_pre['Q'].sum()
```

**Чому drug level:**
- Суворіша перевірка для якості даних
- Якщо препарат ніколи не продавався — неможливо оцінити вплив його відсутності
- Фільтрує "фантомні" препарати без історії продажів

#### Рівень 3: Competitors Availability (drug level)

**Питання:** Чи продавали конкуренти саме цей препарат під час stock-out?

**Рівень перевірки:** Конкретний препарат (DRUGS_ID)

**Формула:**
```python
df_drug_during = df_drug[(df_drug['Date'] >= stockout_start) & (df_drug['Date'] <= stockout_end)]
competitors_sales = df_drug_during['MARKET_TOTAL_DRUGS_PACK'].sum()
```

**Чому drug level:**
- Перевіряємо наявність альтернативи для СПОЖИВАЧА саме цього ліку
- Якщо конкуренти теж не продають цей препарат — споживач не мав вибору
- Забезпечує релевантність substitution аналізу

### 4.5 Функція валідації

```python
def validate_stockout_event(
    df_drug: pd.DataFrame,
    df_inn: pd.DataFrame,
    stockout_start: pd.Timestamp,
    stockout_end: pd.Timestamp,
    pre_start: pd.Timestamp,
    pre_end: pd.Timestamp
) -> tuple:
    """
    Багаторівнева валідація stock-out події.

    Parameters:
    -----------
    df_drug : DataFrame
        Дані конкретного препарату (для Level 2, 3)
    df_inn : DataFrame
        Дані всієї INN групи (для Level 1)

    Returns:
    --------
    tuple: (is_valid: bool, reason: str, details: dict)

    Можливі причини відхилення:
    - 'no_market_activity': ринок INN групи не був активний
    - 'no_pre_sales': немає продажів препарату до stock-out
    - 'no_competitors': конкуренти не продавали препарат
    """
```

---

## 5. СТРУКТУРА ВИХІДНИХ ДАНИХ

### Валідовані події

**Файл:** `stockout_events_{CLIENT_ID}.csv`

| Колонка | Тип | Опис |
|---------|-----|------|
| `EVENT_ID` | str | Унікальний ID: `{CLIENT_ID}_{INN_ID}_{0001}` |
| `CLIENT_ID` | int | ID цільової аптеки |
| `INN_ID` | int | ID МНН |
| `INN_NAME` | str | Назва МНН |
| `DRUGS_ID` | int | ID препарату |
| `DRUGS_NAME` | str | Назва препарату |
| `NFC1_ID` | str | Широка категорія форми |
| `NFC_ID` | str | Специфічна форма |
| `STOCKOUT_START` | date | Початок stock-out (понеділок) |
| `STOCKOUT_END` | date | Кінець stock-out (понеділок) |
| `STOCKOUT_WEEKS` | int | Тривалість (тижнів) |
| `PRE_START` | date | Початок PRE-періоду |
| `PRE_END` | date | Кінець PRE-періоду |
| `PRE_WEEKS` | int | Фактична кількість тижнів в PRE-періоді |
| `PRE_AVG_Q` | float | Середні продажі в PRE |
| `MARKET_DURING_Q` | float | Продажі конкурентів під час stock-out |

---

## 6. КОНФІГУРАЦІЯ

Параметри визначені в `project_core/did_config/stockout_params.py`:

| Параметр | Значення | Опис |
|----------|----------|------|
| `MIN_STOCKOUT_WEEKS` | 1 | Мінімальна тривалість stock-out для реєстрації |
| `MIN_PRE_PERIOD_WEEKS` | 4 | Мінімальна кількість тижнів PRE-періоду |

**Для зміни параметрів:** редагувати `project_core/did_config/stockout_params.py`, перезапустити Steps 2-5.

---

## 7. ВАЛІДАЦІЯ

### Автоматичні перевірки

```python
def validate_stockout_dataset(df: pd.DataFrame) -> dict:
    """Валідація датасету stock-out подій."""
    checks = {
        'unique_event_ids': df['EVENT_ID'].is_unique,
        'chronology_valid': (df['STOCKOUT_START'] <= df['STOCKOUT_END']).all(),
        'pre_before_stockout': (df['PRE_END'] < df['STOCKOUT_START']).all(),
        'positive_weeks': (df['STOCKOUT_WEEKS'] >= 1).all(),
        'non_negative_pre_q': (df['PRE_AVG_Q'] >= 0).all(),
        'validation_passed': df['VALIDATION_PASSED'].all()
    }
    return checks
```

### Критерії успішності

| Перевірка | Очікуване |
|-----------|-----------|
| Унікальність EVENT_ID | Кожна подія має унікальний ID |
| Хронологія | STOCKOUT_START ≤ STOCKOUT_END |
| PRE перед stock-out | PRE_END < STOCKOUT_START |
| Позитивна тривалість | STOCKOUT_WEEKS ≥ 1 |
| Невід'ємні продажі | PRE_AVG_Q ≥ 0 |

---

## 8. ЗВ'ЯЗОК З ІНШИМИ КРОКАМИ

```
STEP 1: АГРЕГАЦІЯ
    │  Документація: 01_DATA_AGREGATION.md
    │  Вихід: inn_{INN_ID}_{CLIENT_ID}.csv (per INN)
    │
    ▼
STEP 2: ДЕТЕКЦІЯ STOCK-OUT (цей документ)
    │  Вхід: inn_{INN_ID}_{CLIENT_ID}.csv
    │  Вихід: stockout_events_{CLIENT_ID}.csv
    │
    │  Що передається далі:
    │  - EVENT_ID (унікальний ідентифікатор події)
    │  - STOCKOUT_START, STOCKOUT_END (межі stock-out)
    │  - PRE_START, PRE_END (межі PRE-періоду)
    │  - PRE_AVG_Q (baseline для DiD)
    │  - MARKET_DURING_Q (ринкова активність)
    │
    ▼
STEP 3: DiD АНАЛІЗ
    │  Документація: 03_DID_NFC_ANALYSIS.md
    │  Використовує: stockout events + aggregated data
    │
    ▼
STEP 4: АНАЛІЗ SUBSTITUTES
    │  Документація: 04_SUBSTITUTE_SHARE_ANALYSIS.md
    │
    ▼
STEP 5: ЗВІТИ ТА CSV
       Документація: 05_REPORTS_AND_GRAPHS.md
```

### POST-період

**ВАЖЛИВО:** POST-період НЕ визначається на цьому етапі!

POST-період визначається динамічно на Step 3 (DiD аналіз) з урахуванням:
- Відновлення продажів після stock-out
- Наявності достатньої кількості даних
- Параметрів з `project_core/did_config/`

---

## 9. ТИПОВІ ПОМИЛКИ

| Помилка | Симптом | Рішення |
|---------|---------|---------|
| Немає stock-out подій | Пустий вихідний файл | Перевірити Gap Filling на Step 1 |
| Всі події відхилені | 0 валідних подій | Перевірити пороги в `did_config/` |
| no_market_activity | Багато відхилень | Перевірити дані конкурентів |
| no_competitors | Багато відхилень | Препарат унікальний для аптеки |
| Невірні дати | Помилки хронології | Перевірити парсинг дат на Step 1 |

**Детальніше про помилки:** [02_KNOWN_ISSUES.md](../00_ai_rules/02_KNOWN_ISSUES.md)

---

## 10. ПРИКЛАД

### Вхідні дані препарату

```
┌────────────┬────────┬─────────────────┐
│ Date       │ Q      │ Статус          │
├────────────┼────────┼─────────────────┤
│ 2024-01-01 │ 5.0    │ Продажі         │
│ 2024-01-08 │ 3.0    │ Продажі         │
│ 2024-01-15 │ 0.0    │ ← STOCKOUT_START│
│ 2024-01-22 │ 0.0    │ stock-out       │
│ 2024-01-29 │ 0.0    │ ← STOCKOUT_END  │
│ 2024-02-05 │ 7.0    │ Продажі         │
└────────────┴────────┴─────────────────┘
```

### Результат

```
EVENT_ID: {CLIENT_ID}_12345_0001
STOCKOUT_START: 2024-01-15
STOCKOUT_END: 2024-01-29
STOCKOUT_WEEKS: 3

PRE-період (MIN_PRE_PERIOD_WEEKS = 4):
PRE_START: 2023-12-18
PRE_END: 2024-01-08
PRE_AVG_Q: 4.0 (= (5+3)/2 тижні з продажами)
```
