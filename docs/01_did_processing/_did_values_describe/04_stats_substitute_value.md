# Документація вихідних файлів: 02_04_substitute_analysis.py

> **Версія:** 1.0 | **Дата:** 28.01.2026

---

## Призначення

Скрипт `02_04_substitute_analysis.py` аналізує **частку кожного substitute** в загальній внутрішній субституції.

**Бізнес-питання:** Коли препарат X відсутній — який саме substitute забирає найбільше попиту?

---

## Вхідні дані

```
data/processed_data/01_per_market/{CLIENT_ID}/03_did_analysis_{CLIENT_ID}/
├── did_results_{CLIENT_ID}.csv
└── substitute_mapping_{CLIENT_ID}.csv

data/processed_data/01_per_market/{CLIENT_ID}/01_aggregation_{CLIENT_ID}/
└── inn_{INN_ID}_{CLIENT_ID}.csv
```

---

## Вихідні файли

```
data/processed_data/01_per_market/{CLIENT_ID}/04_substitute_shares_{CLIENT_ID}/
├── substitute_shares_{CLIENT_ID}.csv      # LIFT та SHARE per substitute
└── _stats/
    ├── substitute_summary_{CLIENT_ID}.csv # Зведена статистика
    └── substitute_metadata_{CLIENT_ID}.csv # Параметри та метадані
```

---

## 1. substitute_shares_{CLIENT_ID}.csv

**Опис:** Розрахунок SUBSTITUTE_SHARE для кожної пари (stockout_drug, substitute).

### Колонки

| Колонка | Тип | Опис |
|---------|-----|------|
| `CLIENT_ID` | int | ID цільової аптеки (ринку) |
| `STOCKOUT_DRUG_ID` | int | ID препарату, який був відсутній |
| `STOCKOUT_DRUG_NAME` | str | Назва stockout препарату |
| `STOCKOUT_NFC1_ID` | str | Форма випуску stockout препарату |
| `SUBSTITUTE_DRUG_ID` | int | ID препарату-замінника |
| `SUBSTITUTE_DRUG_NAME` | str | Назва substitute препарату |
| `SUBSTITUTE_NFC1_ID` | str | Форма випуску substitute |
| `SAME_NFC1` | bool | True якщо форми випуску однакові |
| `TOTAL_LIFT` | float | Сумарний LIFT від цього substitute (по всіх подіях) |
| `LIFT_SAME_NFC1` | float | LIFT якщо SAME_NFC1=True, інакше 0 |
| `LIFT_DIFF_NFC1` | float | LIFT якщо SAME_NFC1=False, інакше 0 |
| `INTERNAL_LIFT` | float | Сума LIFT всіх substitutes для цього stockout drug |
| `SUBSTITUTE_SHARE` | float | Частка substitute (%) = TOTAL_LIFT / INTERNAL_LIFT × 100 |
| `EVENTS_COUNT` | int | Кількість stock-out подій, де цей substitute мав LIFT > 0 |

### Формули

```
LIFT = max(0, ACTUAL - EXPECTED)
EXPECTED = SALES_PRE × MARKET_GROWTH

TOTAL_LIFT = Σ LIFT (по всіх подіях)
INTERNAL_LIFT = Σ TOTAL_LIFT (для всіх substitutes одного stockout drug)
SUBSTITUTE_SHARE = TOTAL_LIFT / INTERNAL_LIFT × 100%
```

### Важливо

- **Zero-LIFT Filter:** Substitutes з `TOTAL_LIFT = 0` відфільтровуються — вони існували в асортименті, але покупці їх не обирали
- **Валідація:** Сума `SUBSTITUTE_SHARE` для кожного stockout drug = 100%
- Файл сортований по `STOCKOUT_DRUG_ID`, потім по `SUBSTITUTE_SHARE` (desc)

### Приклад

```csv
CLIENT_ID,STOCKOUT_DRUG_ID,...,SUBSTITUTE_SHARE,EVENTS_COUNT
28670,4043,...,33.61,11
28670,4043,...,24.28,11
28670,4043,...,20.57,11
```

---

## 2. substitute_summary_{CLIENT_ID}.csv

**Опис:** Зведена статистика по substitute shares для ринку.

### Колонки

| Колонка | Тип | Опис |
|---------|-----|------|
| `CLIENT_ID` | int | ID цільової аптеки |
| `METRIC` | str | Назва метрики |
| `VALUE` | float | Значення метрики |

### Метрики

| METRIC | Опис |
|--------|------|
| `UNIQUE_STOCKOUT_DRUGS` | Кількість унікальних stockout препаратів |
| `UNIQUE_SUBSTITUTES` | Кількість унікальних substitutes |
| `TOTAL_PAIRS` | Кількість пар (stockout, substitute) |
| `TOTAL_LIFT` | Сумарний LIFT по всіх парах |
| `AVG_SUBSTITUTE_SHARE` | Середній SUBSTITUTE_SHARE (%) |
| `MEDIAN_SUBSTITUTE_SHARE` | Медіана SUBSTITUTE_SHARE (%) |
| `LIFT_SAME_NFC1` | Сума LIFT для substitutes тієї ж форми |
| `LIFT_DIFF_NFC1` | Сума LIFT для substitutes іншої форми |
| `SHARE_SAME_NFC1_PERCENT` | % LIFT від тієї ж форми випуску |
| `COUNT_SHARE_100` | Кількість пар з SHARE = 100% (єдиний substitute) |
| `COUNT_SHARE_50_99` | Кількість пар з SHARE 50-99% |
| `COUNT_SHARE_25_49` | Кількість пар з SHARE 25-49% |
| `COUNT_SHARE_10_24` | Кількість пар з SHARE 10-24% |
| `COUNT_SHARE_BELOW_10` | Кількість пар з SHARE < 10% |

### Інтерпретація SHARE_SAME_NFC1_PERCENT

- **> 80%:** Форма випуску ДУЖЕ ВАЖЛИВА для покупців
- **50-80%:** Форма випуску ПОМІРНО ВАЖЛИВА
- **< 50%:** Покупці ГНУЧКІ до форми випуску

---

## 3. substitute_metadata_{CLIENT_ID}.csv

**Опис:** Метадані обробки (параметри, час, статистика).

### Колонки

| Колонка | Тип | Опис |
|---------|-----|------|
| `CLIENT_ID` | int | ID цільової аптеки |
| `PROCESSING_DATE` | str | Дата та час обробки |
| `EVENTS_PROCESSED` | int | Кількість оброблених stock-out подій |
| `EVENTS_WITH_LIFT` | int | Кількість stockout препаратів з LIFT > 0 |
| `PAIRS_TOTAL` | int | Загальна кількість пар до фільтрації |
| `PAIRS_AFTER_FILTER` | int | Кількість пар після Zero-LIFT Filter |
| `PAIRS_FILTERED_ZERO_LIFT` | int | Кількість відфільтрованих пар (LIFT=0) |
| `PROCESSING_TIME_SEC` | float | Час обробки в секундах |
| `MIN_TOTAL_LIFT_THRESHOLD` | float | Поріг фільтрації (завжди 0) |

---

## Зв'язок з іншими етапами

```
ЕТАП 1: АГРЕГАЦІЯ (02_01_data_aggregation.py)
    │
    ▼
ЕТАП 2: ДЕТЕКЦІЯ STOCK-OUT (02_02_stockout_detection.py)
    │
    ▼
ЕТАП 3: DiD АНАЛІЗ (02_03_did_analysis.py)
    │  Вихід: did_results, substitute_mapping
    │
    ▼
ЕТАП 4: SUBSTITUTE ANALYSIS (02_04_substitute_analysis.py) ← цей документ
    │  Вхід: did_results + substitute_mapping + aggregation
    │  Вихід: substitute_shares, substitute_summary
    │
    ▼
PHASE 2: CROSS-MARKET AGGREGATION (планується)
```

---

## Типові значення

На основі тестових даних (5 ринків):

| Метрика | Значення |
|---------|----------|
| Пар (stockout, substitute) | 8,341 |
| Загальний LIFT | 61,158.34 |
| Середній % SAME_NFC1 | 78.3% |
| Відфільтровано (LIFT=0) | ~10-12% |
| Суми SHARE | Завжди 100% |

---

## Валідація

### Інваріанти

1. Для кожного `STOCKOUT_DRUG_ID`: `Σ SUBSTITUTE_SHARE = 100%`
2. `LIFT_SAME_NFC1 + LIFT_DIFF_NFC1 = TOTAL_LIFT`
3. `PAIRS_AFTER_FILTER + PAIRS_FILTERED_ZERO_LIFT = PAIRS_TOTAL`

### Edge Cases

| Ситуація | Обробка |
|----------|---------|
| Один substitute | SUBSTITUTE_SHARE = 100% |
| Всі substitutes з LIFT=0 | Stockout drug не має записів |
| INTERNAL_LIFT = 0 | Не потрапляє в результат |

---

## Команди виконання

```bash
# Один ринок:
/opt/miniconda3/envs/proxima/bin/python exec_scripts/01_did_processing/02_04_substitute_analysis.py --market_id 28670

# Всі ринки:
/opt/miniconda3/envs/proxima/bin/python exec_scripts/01_did_processing/02_04_substitute_analysis.py --all
```
