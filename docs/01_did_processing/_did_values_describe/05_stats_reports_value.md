# Документація вихідних файлів: 02_05_reports_cross_market.py

> **Версія:** 1.0 | **Дата:** 28.01.2026

---

## Призначення

Скрипт `02_05_reports_cross_market.py` генерує **звіти для кожного ринку** та **CSV-файли для cross-market аналізу**.

**Бізнес-питання:** Які препарати є критичними для утримання в асортименті, а які можна потенційно вивести?

---

## Вхідні дані

```
data/processed_data/01_per_market/{CLIENT_ID}/03_did_analysis_{CLIENT_ID}/
├── did_results_{CLIENT_ID}.csv
└── _stats/drugs_summary_{CLIENT_ID}.csv

data/processed_data/01_per_market/{CLIENT_ID}/04_substitute_shares_{CLIENT_ID}/
└── substitute_shares_{CLIENT_ID}.csv
```

---

## Вихідні файли

```
results/
├── data_reports/
│   └── reports_{CLIENT_ID}/
│       ├── 01_technical_report_{CLIENT_ID}.xlsx   # Повний технічний звіт
│       └── 02_business_report_{CLIENT_ID}.xlsx    # Спрощений бізнес-звіт
│
└── cross_market_data/
    └── cross_market_{CLIENT_ID}.csv               # Flat data для агрегації
```

---

## 1. 01_technical_report_{CLIENT_ID}.xlsx

**Опис:** Повний технічний звіт з усіма колонками та вертикальним списком субститутів.

### Формат

- **Рядок 1:** Технічні назви колонок (DRUGS_ID, DRUGS_NAME, ...)
- **Рядок 2:** Людські назви колонок українською
- **Рядок 3+:** Дані
- **Заморожені панелі:** Перші 2 рядки
- **Кольорове маркування:**
  - CRITICAL — червоний (#FFCCCC)
  - SUBSTITUTABLE — зелений (#CCFFCC)

### Колонки (27 колонок)

#### Інформація про препарат (18 колонок)
| Колонка | Тип | Опис |
|---------|-----|------|
| `DRUGS_ID` | int | ID препарату |
| `DRUGS_NAME` | str | Назва препарату |
| `INN_ID` | int | ID МНН групи |
| `INN_NAME` | str | Назва МНН групи |
| `NFC1_ID` | str | Широка категорія форми (NFC1) |
| `EVENTS_COUNT` | int | Кількість stock-out подій |
| `TOTAL_STOCKOUT_WEEKS` | int | Загальна тривалість stock-out (тижні) |
| `FIRST_STOCKOUT_DATE` | date | Дата першого stock-out |
| `LAST_STOCKOUT_DATE` | date | Дата останнього stock-out |
| `INTERNAL_LIFT` | float | Загальний внутрішній ліфт (упак.) |
| `LOST_SALES` | float | Загальні втрачені продажі (упак.) |
| `TOTAL_EFFECT` | float | Загально перерозподілено (упак.) |
| `TOTAL_LIFT_SAME_NFC1` | float | Ліфт від substitutes тієї ж форми |
| `TOTAL_LIFT_DIFF_NFC1` | float | Ліфт від substitutes іншої форми |
| `SHARE_INTERNAL` | float | Частка внутрішньої субституції (%) |
| `SHARE_LOST` | float | Частка втрат до конкурентів (%) |
| `SHARE_SAME_NFC1` | float | Частка тієї ж категорії (%) |
| `SHARE_DIFF_NFC1` | float | Частка іншої категорії (%) |

#### Субститути тієї ж категорії (3 колонки)
| Колонка | Тип | Опис |
|---------|-----|------|
| `SAME_NFC1_DRUG_NAME` | str | Назва substitute (та ж форма) |
| `SAME_NFC1_DRUG_ID` | int | ID substitute (та ж форма) |
| `SAME_NFC1_SUBSTITUTE_SHARE` | float | Відсоток заміщення (%) |

#### Субститути іншої категорії (4 колонки)
| Колонка | Тип | Опис |
|---------|-----|------|
| `DIFF_NFC1_DRUG_NAME` | str | Назва substitute (інша форма) |
| `DIFF_NFC1_DRUG_ID` | int | ID substitute (інша форма) |
| `DIFF_NFC1_SUBSTITUTE_SHARE` | float | Відсоток заміщення (%) |
| `DIFF_NFC1_ID` | str | Форма випуску substitute |

#### Класифікація (2 колонки)
| Колонка | Тип | Опис |
|---------|-----|------|
| `CLASSIFICATION` | str | Категорія: CRITICAL / SUBSTITUTABLE |
| `RECOMMENDATION` | str | Рекомендація для керівництва |

### Особливості формату

- **Вертикальний список субститутів:** Кожен substitute = окремий рядок
- **Дані препарату тільки в першому рядку:** Наступні рядки для субститутів порожні в колонках препарату
- **Сортування:** CRITICAL спочатку, потім по SHARE_LOST спадаючи

---

## 2. 02_business_report_{CLIENT_ID}.xlsx

**Опис:** Спрощений звіт для керівництва з ключовими метриками.

### Колонки (18 колонок)

| Група | Колонки |
|-------|---------|
| Інформація про препарат | DRUGS_ID, DRUGS_NAME, INN_ID, INN_NAME, NFC1_ID |
| Ключові метрики | SHARE_INTERNAL, SHARE_LOST, SHARE_SAME_NFC1, SHARE_DIFF_NFC1 |
| Substitutes (та ж форма) | SAME_NFC1_DRUG_NAME, SAME_NFC1_DRUG_ID, SAME_NFC1_SUBSTITUTE_SHARE |
| Substitutes (інша форма) | DIFF_NFC1_DRUG_NAME, DIFF_NFC1_DRUG_ID, DIFF_NFC1_SUBSTITUTE_SHARE, DIFF_NFC1_ID |
| Класифікація | CLASSIFICATION, RECOMMENDATION |

### Відмінності від технічного звіту

- Немає колонок EVENTS_COUNT, TOTAL_STOCKOUT_WEEKS, дат
- Немає INTERNAL_LIFT, LOST_SALES, TOTAL_EFFECT
- Немає TOTAL_LIFT_SAME_NFC1, TOTAL_LIFT_DIFF_NFC1

---

## 3. cross_market_{CLIENT_ID}.csv

**Опис:** Flat data для cross-market аналізу (один рядок = один препарат).

### Колонки (21 колонка)

| Колонка | Тип | Опис |
|---------|-----|------|
| `CLIENT_ID` | int | ID ринку (цільової аптеки) |
| `DRUGS_ID` | int | ID препарату |
| `DRUGS_NAME` | str | Назва препарату |
| `INN_ID` | int | ID МНН групи |
| `INN_NAME` | str | Назва МНН групи |
| `NFC1_ID` | str | Широка категорія форми |
| `EVENTS_COUNT` | int | Кількість stock-out подій |
| `TOTAL_STOCKOUT_WEEKS` | int | Загальна тривалість stock-out |
| `FIRST_STOCKOUT_DATE` | date | Дата першого stock-out |
| `LAST_STOCKOUT_DATE` | date | Дата останнього stock-out |
| `INTERNAL_LIFT` | float | Внутрішній ліфт |
| `LOST_SALES` | float | Втрачені продажі |
| `TOTAL_EFFECT` | float | Загальний ефект |
| `TOTAL_LIFT_SAME_NFC1` | float | Ліфт тієї ж форми |
| `TOTAL_LIFT_DIFF_NFC1` | float | Ліфт іншої форми |
| `SHARE_INTERNAL` | float | Частка внутрішньої субституції |
| `SHARE_LOST` | float | Частка втрат |
| `SHARE_SAME_NFC1` | float | Частка тієї ж форми |
| `SHARE_DIFF_NFC1` | float | Частка іншої форми |
| `CLASSIFICATION` | str | Категорія |
| `RECOMMENDATION` | str | Рекомендація |

### Призначення

CSV-файли призначені для:
1. Cross-market агрегації (Phase 2)
2. Статистичного аналізу по всіх ринках
3. Розрахунку MARKET_COVERAGE
4. Confidence Interval розрахунків

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
    │  Вихід: did_results, drugs_summary
    │
    ▼
ЕТАП 4: SUBSTITUTE ANALYSIS (02_04_substitute_analysis.py)
    │  Вихід: substitute_shares
    │
    ▼
ЕТАП 5: REPORTS (02_05_reports_cross_market.py) ← цей документ
    │  Вхід: drugs_summary + did_results + substitute_shares
    │  Вихід: Excel reports + cross_market CSV
    │
    ▼
PHASE 2: CROSS-MARKET AGGREGATION (планується)
```

---

## Типові значення

На основі тестових даних (5 ринків):

| Метрика | Значення |
|---------|----------|
| Всього препаратів | 775 |
| Всього CRITICAL | 427 (55%) |
| Всього SUBSTITUTABLE | 348 (45%) |
| Рядків в Excel (всього) | ~7,186 |
| Середній час обробки ринку | ~2.5 сек |

---

## Рекомендації

| CLASSIFICATION | Значення | Рекомендація |
|----------------|----------|--------------|
| CRITICAL | SHARE_LOST > 50% | KEEP - High loss to competitors |
| SUBSTITUTABLE | SHARE_INTERNAL > 50% | CONSIDER_REMOVAL - Good internal substitution |

---

## Команди виконання

```bash
# Один ринок:
/opt/miniconda3/envs/proxima/bin/python exec_scripts/01_did_processing/02_05_reports_cross_market.py --market_id 28670

# Всі ринки:
/opt/miniconda3/envs/proxima/bin/python exec_scripts/01_did_processing/02_05_reports_cross_market.py --all
```
