# Step 0: Preprocessing — Підготовка метаданих

> **Версія:** 1.0 | **Створено:** 31.01.2026

---

## 1. ПРИЗНАЧЕННЯ

Preprocessing — нульовий крок pipeline, який виконується **один раз** перед обробкою всіх ринків:

- Сканування raw файлів `Rd2_{CLIENT_ID}.csv`
- Збір списків унікальних значень (INN, NFC, препарати)
- Генерація статистики по кожному ринку
- Створення файлу `target_pharmacies_list.csv` — використовується наступними скриптами

**Важливо:** Всі наступні скрипти залежать від результатів preprocessing через функцію `load_target_pharmacies()`.

---

## 2. РЕАЛІЗАЦІЯ

### Скрипт

**Розташування:** `exec_scripts/01_did_processing/01_preproc.py`

**Виконання:**
```bash
python exec_scripts/01_did_processing/01_preproc.py
```

### Допоміжні модулі

| Модуль | Використання |
|--------|--------------|
| `project_core/data_config/paths_config.py` | Шляхи: `RAW_DATA_PATH`, `PREPROC_RESULTS_PATH`, `CSV_SEPARATOR` |
| `project_core/utility_functions/etl_utils.py` | Функція `parse_period_id()` для парсингу дат |

### Вхід / Вихід

```
ВХІД:
  data/raw/Rd2_*.csv              # Raw файли ринків

ВИХІД:
  data/processed_data/00_preproc_results/
  ├── target_pharmacies_list.csv  # Список CLIENT_ID (критично!)
  ├── inn_list.csv                # Унікальні INN_ID + INN_NAME
  ├── nfc1_list.csv               # Унікальні NFC1_ID
  ├── nfc2_list.csv               # Унікальні NFC2_ID
  ├── drugs_list.csv              # Унікальні DRUGS_ID + DRUGS_NAME
  └── markets_statistics.csv      # Статистика per market
```

---

## 3. СТРУКТУРА ВИХІДНИХ ФАЙЛІВ

### 3.1. target_pharmacies_list.csv

**Найважливіший файл** — визначає список ринків для обробки.

| Колонка | Тип | Опис |
|---------|-----|------|
| `CLIENT_ID` | int | ID цільової аптеки (з назви файлу Rd2_{ID}.csv) |

**Використання в коді:**
```python
from project_core.data_config.paths_config import load_target_pharmacies

pharmacies = load_target_pharmacies()  # [28670, 28753, 79021, ...]
```

### 3.2. markets_statistics.csv

Статистика по кожному локальному ринку.

| Колонка | Тип | Опис |
|---------|-----|------|
| `CLIENT_ID` | int | ID цільової аптеки |
| `FILE_NAME` | str | Назва raw файлу |
| `COMPETITORS_COUNT` | int | Кількість конкурентів (ORG_ID != CLIENT_ID) |
| `DATA_START` | str | Дата початку даних (DD.MM.YYYY) |
| `DATA_END` | str | Дата кінця даних (DD.MM.YYYY) |
| `DAYS_RANGE` | int | Діапазон даних в днях |
| `WEEKS_RANGE` | int | Діапазон даних в тижнях |
| `DRUGS_COUNT` | int | Кількість унікальних препаратів |
| `INN_COUNT` | int | Кількість INN груп |
| `RECORDS_COUNT` | int | Загальна кількість записів |

### 3.3. inn_list.csv

| Колонка | Тип | Опис |
|---------|-----|------|
| `INN_ID` | int | ID групи діючої речовини |
| `INN_NAME` | str | Міжнародна непатентована назва |

### 3.4. drugs_list.csv

| Колонка | Тип | Опис |
|---------|-----|------|
| `DRUGS_ID` | int | Morion ID препарату |
| `DRUGS_NAME` | str | Повна назва препарату |

### 3.5. nfc1_list.csv / nfc2_list.csv

| Колонка | Тип | Опис |
|---------|-----|------|
| `NFC1_ID` / `NFC2_ID` | str | Код форми випуску |

---

## 4. ПЕРІОД ДАНИХ

На основі поточних даних (станом на 31.01.2026):

| Параметр | Значення |
|----------|----------|
| Початок даних | 02.01.2023 |
| Кінець даних | 01.01.2026 |
| Тривалість | 156 тижнів (3 роки) |
| Кількість ринків | 5 |

---

## 5. ПРИКЛАД РЕЗУЛЬТАТІВ

### markets_statistics.csv

| CLIENT_ID | COMPETITORS_COUNT | WEEKS_RANGE | DRUGS_COUNT | RECORDS_COUNT |
|-----------|-------------------|-------------|-------------|---------------|
| 28670 | 7 | 156 | 508 | 110,485 |
| 28753 | 5 | 156 | 454 | 51,913 |
| 79021 | 12 | 156 | 558 | 161,768 |
| 98911 | 7 | 156 | 514 | 96,784 |
| 99617 | 24 | 156 | 581 | 309,364 |

---

## 6. ЗАЛЕЖНОСТІ

```
┌─────────────────┐
│  01_preproc.py  │
└────────┬────────┘
         │ створює
         ▼
┌────────────────────────────┐
│ target_pharmacies_list.csv │
└────────────┬───────────────┘
             │ читає load_target_pharmacies()
             ▼
┌────────────────────────────────────────────┐
│ 02_01_data_aggregation.py                  │
│ 02_02_stockout_detection.py                │
│ 02_03_did_analysis.py                      │
│ 02_04_substitute_analysis.py               │
│ 02_05_reports_cross_market.py              │
└────────────────────────────────────────────┘
```

---

## 7. TROUBLESHOOTING

### Помилка: "Файл target_pharmacies_list.csv не знайдено"

```
FileNotFoundError: Файл .../target_pharmacies_list.csv не знайдено.
Спочатку виконайте preprocessing: python exec_scripts/01_did_processing/01_preproc.py
```

**Рішення:** Запустіть preprocessing скрипт.

### Помилка: "Файли Rd2_*.csv не знайдено"

**Причина:** Папка `data/raw/` порожня або файли мають неправильні назви.

**Рішення:** Перевірте що raw файли мають формат `Rd2_{CLIENT_ID}.csv`.

---

## 8. ЗМІНИ ВЕРСІЙ

| Версія | Дата | Зміни |
|--------|------|-------|
| 1.0 | 31.01.2026 | Початкова версія. Рефакторинг для використання project_core модулів |
