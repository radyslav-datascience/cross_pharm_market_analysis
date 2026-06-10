# Step 1: Агрегація та підготовка даних

> **Версія:** 1.0 | **Створено:** 31.01.2026

---

## 1. ПРИЗНАЧЕННЯ

Перший крок pipeline відповідає за підготовку чистих, консистентних даних для DiD-аналізу:

- Завантаження та трансформація сирих даних ринку
- Тижнева агрегація продажів
- **Gap Filling** — заповнення пропущених тижнів нулями (критично!)
- Розрахунок ринкових показників для DiD

**Без коректного виконання цього кроку подальший аналіз неможливий.**

---

## 2. РЕАЛІЗАЦІЯ

### Скрипт

**Розташування:** `exec_scripts/01_did_processing/02_01_data_aggregation.py`

**Виконання:**
```bash
# Один ринок:
/opt/miniconda3/envs/proxima/bin/python exec_scripts/01_did_processing/02_01_data_aggregation.py --market_id {CLIENT_ID}

# Всі ринки:
/opt/miniconda3/envs/proxima/bin/python exec_scripts/01_did_processing/02_01_data_aggregation.py --all
```

### Допоміжні модулі

| Модуль | Використання |
|--------|--------------|
| `project_core/data_config/paths_config.py` | Шляхи до даних |
| `project_core/did_config/classification_thresholds.py` | Пороги NOTSOLD |
| `project_core/utility_functions/etl_utils.py` | ETL функції: парсинг дат, gap filling, агрегація |

### Вхід / Вихід

```
ВХІД:
  data/raw/Rd2_{CLIENT_ID}.csv

ВИХІД:
  data/processed_data/01_per_market/{CLIENT_ID}/01_aggregation_{CLIENT_ID}/
  ├── inn_{INN_ID}_{CLIENT_ID}.csv         # Агреговані дані per INN (тільки TARGET)
  └── stats_inn_{CLIENT_ID}/
      ├── summary_{CLIENT_ID}.csv          # Зведена статистика per DRUGS_ID
      └── inn_summary_{CLIENT_ID}.csv      # Агрегована статистика per INN
```

---

## 3. СТРУКТУРА СИРИХ ДАНИХ

**Джерело:** `data/raw/Rd2_{CLIENT_ID}.csv`

| Колонка | Тип | Опис |
|---------|-----|------|
| `ORG_ID` | int | Ідентифікатор аптеки-продавця |
| `CLIENT_ID` | int | ID цільової аптеки (= з назви файлу) |
| `DRUGS_ID` | int | Унікальний ідентифікатор препарату (Morion ID) |
| `PERIOD_ID` | int | Період у форматі YYYYNNNNN |
| `Q` | str | Кількість (рядок з комою: "12,5") |
| `V` | str | Виручка (рядок з комою: "1234,56") |
| `INN` | str | МНН — Міжнародна непатентована назва |
| `INN_ID` | int | Ідентифікатор МНН |
| `Full medication name` | str | Повна назва препарату |
| `NFC Code (1)` | str | Широка категорія форми випуску (NFC1) |
| `NFC Code (2)` | str | Специфічна форма випуску |

---

## 4. ETL PIPELINE

### Етап 1: Завантаження

```python
# Читання CSV з роздільником ';'
df = pd.read_csv(filepath, sep=';')

# Конвертація Q, V: str → float (заміна ',' на '.')
df['Q'] = df['Q'].str.replace(',', '.').astype(float)
df['V'] = df['V'].str.replace(',', '.').astype(float)
```

### Етап 2: Перейменування колонок

```
INN                  → INN_NAME
Full medication name → DRUGS_NAME
NFC Code (1)         → NFC1_ID
NFC Code (2)         → NFC_ID
```

### Етап 3: Парсинг PERIOD_ID → Date

**Формат PERIOD_ID:** `YYYYNNNNN`
- `YYYY` — рік (4 цифри)
- `NNNNN` — week_day_code (5 цифр)

**Алгоритм:**
```python
def parse_period_id(period_id: int) -> datetime:
    """Конвертує PERIOD_ID у datetime."""
    period_str = str(int(period_id))
    year = int(period_str[:4])
    week_day_code = int(period_str[4:])

    week = week_day_code // 7
    day_of_week = week_day_code % 7

    first_day = datetime(year, 1, 1)
    target_date = first_day + timedelta(weeks=week, days=day_of_week)

    return target_date
```

### Етап 4: Тижнева агрегація

```python
# Групування
groupby_cols = ['Date', 'ORG_ID', 'DRUGS_ID', 'NFC1_ID']

# Агрегація
agg_rules = {
    'Q': 'sum',      # Кількість за тиждень
    'V': 'sum',      # Виручка за тиждень
}

# Результат: один рядок = один препарат в одній аптеці за один тиждень
```

### Етап 5: GAP FILLING (КРИТИЧНО!)

```
┌─────────────────────────────────────────────────────────────────────────┐
│  ПРОБЛЕМА: Сирі дані містять ТІЛЬКИ тижні з продажами.                  │
│  Тижні без продажів (stock-out) ВІДСУТНІ в даних!                       │
│                                                                         │
│  РІШЕННЯ: Створити повну сітку дат і заповнити пропуски нулями.         │
│                                                                         │
│  ЧОМУ ЦЕ КРИТИЧНО:                                                      │
│  - Без GAP FILLING ми НЕ бачимо періоди stock-out                       │
│  - DiD-аналіз базується на виявленні переходу від продажів до нуля      │
│  - Пропущені нулі = пропущені stock-out events                          │
└─────────────────────────────────────────────────────────────────────────┘
```

**Приклад:**
```
До GAP FILLING:           Після GAP FILLING:
Week 1: Q=10              Week 1: Q=10
Week 3: Q=15              Week 2: Q=0  ← STOCK-OUT!
Week 5: Q=8               Week 3: Q=15
                          Week 4: Q=0  ← STOCK-OUT!
                          Week 5: Q=8
```

**Алгоритм:**
```python
def fill_gaps_for_pharmacy_drug(df: pd.DataFrame) -> pd.DataFrame:
    """Заповнює пропущені тижні нулями для пари (ORG_ID, DRUGS_ID)."""
    result_frames = []

    for (org_id, drug_id), group in df.groupby(['ORG_ID', 'DRUGS_ID']):
        # Діапазон дат
        min_date = group['Date'].min()
        max_date = group['Date'].max()

        # Повний тижневий range (понеділки)
        full_date_range = pd.date_range(start=min_date, end=max_date, freq='W-MON')

        # Reindex на повний range
        group_indexed = group.set_index('Date')
        group_reindexed = group_indexed.reindex(full_date_range)

        # Заповнення NaN → 0 для Q та V
        group_reindexed['Q'] = group_reindexed['Q'].fillna(0)
        group_reindexed['V'] = group_reindexed['V'].fillna(0)

        # Forward fill для категоріальних колонок
        categorical_cols = ['DRUGS_NAME', 'INN_NAME', 'NFC1_ID', 'NFC_ID']
        group_reindexed[categorical_cols] = group_reindexed[categorical_cols].ffill().bfill()

        result_frames.append(group_reindexed.reset_index())

    return pd.concat(result_frames, ignore_index=True)
```

### Етап 6: Target vs Competitors Split

```python
# Target = цільова аптека (CLIENT_ID з назви файлу)
df_target = df[df['ORG_ID'] == CLIENT_ID]
df_competitors = df[df['ORG_ID'] != CLIENT_ID]
```

**Призначення:**
- **Target:** виявлення stock-out events
- **Competitors:** розрахунок MARKET_TOTAL (reference для DiD)

### Етап 7: NOTSOLD аналіз

```python
# Для кожного препарату в Target аптеці
NOTSOLD_PERCENT = (тижні з Q=0) / (всього тижнів)

# Фільтрація визначена в project_core/did_config/
```

**Логіка фільтру:**
- `< MIN`: препарат завжди в наявності → немає stock-out events
- `> MAX`: препарат майже не продається → недостатньо даних
- Між порогами: оптимальний діапазон для DiD-аналізу

### Етап 8: MARKET TOTALS

```python
# Агрегація по конкурентах
market_totals = df_competitors.groupby(['Date', 'DRUGS_ID']).agg({
    'Q': 'sum',  # → MARKET_TOTAL_DRUGS_PACK
    'V': 'sum',  # → MARKET_TOTAL_DRUGS_REVENUE
})
```

**Призначення для DiD:**
- Якщо ринок стабільний, а Target падає → stock-out effect
- Якщо ринок і Target падають разом → сезонність/тренд

---

## 5. СТРУКТУРА ВИХІДНИХ ДАНИХ

**Файл:** `inn_{INN_ID}_{CLIENT_ID}.csv` (один файл per INN, містить тільки TARGET pharmacy)

| Колонка | Тип | Опис |
|---------|-----|------|
| `Date` | datetime | Дата (понеділок тижня) |
| `PHARM_ID` | int | ID аптеки (= CLIENT_ID, тільки TARGET) |
| `DRUGS_ID` | int | ID препарату |
| `DRUGS_NAME` | str | Назва препарату |
| `INN_ID` | int | ID МНН |
| `INN_NAME` | str | Назва МНН |
| `NFC1_ID` | str | Широка категорія форми |
| `NFC_ID` | str | Специфічна форма |
| `Q` | float | Кількість за тиждень |
| `V` | float | Виручка за тиждень |
| `MARKET_TOTAL_DRUGS_PACK` | float | Ринкова кількість |
| `MARKET_TOTAL_DRUGS_REVENUE` | float | Ринкова виручка |
| `NOTSOLD_PERCENT` | float | % тижнів без продажів |

---

## 6. КОНФІГУРАЦІЯ

Параметри визначені в `project_core/`:

| Параметр | Розташування |
|----------|--------------|
| Шляхи до даних | `project_core/data_config/paths_config.py` |
| Пороги NOTSOLD | `project_core/did_config/classification_thresholds.py` |

**Для зміни параметрів:** редагувати відповідні файли в `project_core/`, перезапустити Step 1.

---

## 7. ВАЛІДАЦІЯ

### Перевірки після ETL

```python
def validate_aggregated_data(df: pd.DataFrame) -> dict:
    """Валідація підготовленого датасету."""
    checks = {
        'has_zeros': (df['Q'] == 0).any(),
        'date_is_datetime': pd.api.types.is_datetime64_any_dtype(df['Date']),
        'q_is_numeric': pd.api.types.is_numeric_dtype(df['Q']),
        'unique_combinations': df.groupby(['Date', 'ORG_ID', 'DRUGS_ID']).size().max() == 1,
        'no_nulls_in_key_cols': df[['Date', 'ORG_ID', 'DRUGS_ID']].notna().all().all()
    }
    return checks
```

### Критерії успішності

| Перевірка | Очікуване |
|-----------|-----------|
| Наявність нулів (Q=0) | True — stock-out тижні присутні |
| Тип Date | datetime64 |
| Тип Q, V | float64 |
| Унікальність ключів | Кожна комбінація (Date, ORG_ID, DRUGS_ID) унікальна |
| Відсутність NULL | Ключові колонки не містять NULL |

---

## 8. ЗВ'ЯЗОК З ІНШИМИ КРОКАМИ

```
STEP 1: АГРЕГАЦІЯ (цей документ)
    │
    │  Вихід: inn_{INN_ID}_{CLIENT_ID}.csv (per INN)
    │
    ▼
STEP 2: ДЕТЕКЦІЯ STOCK-OUT
    │  Вхід: inn_{INN_ID}_{CLIENT_ID}.csv
    │  Документація: 02_STOCKOUT_DETECTION.md
    │
    ▼
STEP 3: DiD АНАЛІЗ
    │  Документація: 03_DID_NFC_ANALYSIS.md
    │
    ▼
STEP 4: АНАЛІЗ SUBSTITUTES
    │  Документація: 04_SUBSTITUTE_SHARE_ANALYSIS.md
    │
    ▼
STEP 5: ЗВІТИ ТА CSV
       Документація: 05_REPORTS_AND_GRAPHS.md
```

---

## 9. ТИПОВІ ПОМИЛКИ

| Помилка | Симптом | Рішення |
|---------|---------|---------|
| Пропущено Gap Filling | Немає stock-out events | Перезапустити агрегацію |
| Невірний роздільник CSV | Помилка парсингу | Використовувати `sep=';'` |
| Невірний формат Q/V | NaN значення | Замінити ',' на '.' перед конвертацією |
| Невірний PERIOD_ID | Неправильні дати | Перевірити алгоритм парсингу |

**Детальніше про помилки:** [02_KNOWN_ISSUES.md](../00_ai_rules/02_KNOWN_ISSUES.md)
