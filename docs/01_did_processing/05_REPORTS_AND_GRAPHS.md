# Step 5: Звіти та Cross-Market CSV

> **Версія:** 1.0 | **Створено:** 31.01.2026

---

## 1. ПРИЗНАЧЕННЯ

П'ятий крок генерує **вихідні артефакти** на основі результатів DiD-аналізу:

- **Excel звіти** — технічний та бізнес-звіти для per-market аналізу
- **Cross-Market CSV** — flat data для агрегації в Phase 2

**Step 5 НЕ модифікує дані — лише читає результати попередніх кроків та генерує нові файли.**

---

## 2. РЕАЛІЗАЦІЯ

### Скрипт

**Розташування:** `exec_scripts/01_did_processing/02_05_reports_cross_market.py`

**Виконання:**
```bash
# Один ринок:
/opt/miniconda3/envs/proxima/bin/python exec_scripts/01_did_processing/02_05_reports_cross_market.py --market_id {CLIENT_ID}

# Всі ринки:
/opt/miniconda3/envs/proxima/bin/python exec_scripts/01_did_processing/02_05_reports_cross_market.py --all
```

### Вхід / Вихід

```
ВХІД (READ-ONLY):
  data/processed_data/01_per_market/{CLIENT_ID}/03_did_analysis_{CLIENT_ID}/
    └── _stats/drugs_summary_{CLIENT_ID}.csv    # Статистика DiD
  data/processed_data/01_per_market/{CLIENT_ID}/04_substitute_shares_{CLIENT_ID}/
    └── substitute_shares_{CLIENT_ID}.csv       # SUBSTITUTE_SHARE per substitute

ВИХІД:
  results/data_reports/reports_{CLIENT_ID}/
    ├── 01_technical_report_{CLIENT_ID}.xlsx   # Повний технічний звіт
    └── 02_business_report_{CLIENT_ID}.xlsx    # Спрощений бізнес-звіт

  results/cross_market_data/
    └── cross_market_{CLIENT_ID}.csv           # Flat data для Phase 2
```

---

## 3. ТИПИ ВИХОДІВ

### 3.1 Технічний звіт (Excel)

**Файл:** `01_technical_report_{CLIENT_ID}.xlsx`

**Призначення:** Детальна інформація для аналітиків

**Формат:**
- Два рядки заголовків (технічний + людський)
- Кожен substitute = окремий рядок
- Сортування: CRITICAL → SUBSTITUTABLE, потім по SUBSTITUTE_SHARE

**Ключові колонки (27):**

| Група | Колонки |
|-------|---------|
| Ідентифікація | CLIENT_ID, DRUGS_ID, DRUGS_NAME, INN_ID, INN_NAME, NFC1_ID |
| DiD метрики | EVENTS_COUNT, TOTAL_EFFECT, INTERNAL_LIFT, LOST_SALES |
| Основні SHARE | SHARE_INTERNAL, SHARE_LOST |
| NFC декомпозиція | LIFT_SAME_NFC1, LIFT_DIFF_NFC1, SHARE_SAME_NFC1, SHARE_DIFF_NFC1 |
| Substitute info | SUBSTITUTE_DRUG_ID, SUBSTITUTE_DRUG_NAME, SUBSTITUTE_NFC1_ID |
| Substitute SHARE | SUBSTITUTE_SHARE, SAME_NFC1, SUBSTITUTE_EVENTS_COUNT |
| Класифікація | CLASSIFICATION, RECOMMENDATION |

### 3.2 Бізнес-звіт (Excel)

**Файл:** `02_business_report_{CLIENT_ID}.xlsx`

**Призначення:** Спрощений звіт для керівництва

**Формат:**
- 18 колонок (замість 27 в технічному)
- Групування substitutes по NFC1 (SAME/DIFF)
- Кольорове маркування категорій

**Колонки (18):**

| Група | Колонка | Опис |
|-------|---------|------|
| Препарат | DRUGS_ID | ID препарату |
| | DRUGS_NAME | Назва препарату |
| | INN_ID | ID МНН групи |
| | INN_NAME | Назва МНН групи |
| | NFC1_ID | Категорія форми (NFC1) |
| Показники | SHARE_INTERNAL | % внутрішньої субституції |
| | SHARE_LOST | % втрат до конкурентів |
| | AGG_SHARE_SAME_NFC1 | % тієї ж категорії |
| | AGG_SHARE_DIFF_NFC1 | % іншої категорії |
| Субст. (та ж) | SAME_NFC1_DRUG_NAME | Препарати-субститути |
| | SAME_NFC1_DRUG_ID | ID субститутів |
| | SAME_NFC1_SUBSTITUTE_SHARE | % заміщення |
| Субст. (інша) | DIFF_NFC1_DRUG_NAME | Препарати-субститути |
| | DIFF_NFC1_DRUG_ID | ID субститутів |
| | DIFF_NFC1_SUBSTITUTE_SHARE | % заміщення |
| | DIFF_NFC1_ID | ID інших категорій |
| Класифікація | CLASSIFICATION | Категорія |
| | RECOMMENDATION | Рекомендація |

### 3.3 Cross-Market CSV

**Файл:** `cross_market_{CLIENT_ID}.csv`

**Призначення:** Flat data (1 рядок = 1 препарат) для агрегації в Phase 2

**Колонки (21):**

| Колонка | Тип | Опис |
|---------|-----|------|
| `CLIENT_ID` | int | ID цільової аптеки (ринку) |
| `DRUGS_ID` | int | ID препарату |
| `DRUGS_NAME` | str | Назва препарату |
| `INN_ID` | int | ID МНН |
| `INN_NAME` | str | Назва МНН |
| `NFC1_ID` | str | Категорія форми |
| `EVENTS_COUNT` | int | Кількість stock-out подій |
| `TOTAL_EFFECT` | float | Загальний ефект |
| `INTERNAL_LIFT` | float | Внутрішній LIFT |
| `LOST_SALES` | float | Втрачені продажі |
| `SHARE_INTERNAL` | float | % внутрішньої субституції |
| `SHARE_LOST` | float | % втрат |
| `LIFT_SAME_NFC1` | float | LIFT тієї ж форми |
| `LIFT_DIFF_NFC1` | float | LIFT іншої форми |
| `SHARE_SAME_NFC1` | float | % тієї ж форми |
| `SHARE_DIFF_NFC1` | float | % іншої форми |
| `SUBSTITUTES_COUNT` | int | Кількість substitutes |
| `SUBSTITUTES_WITH_LIFT` | int | Кількість з LIFT > 0 |
| `PER_MARKET_CLASSIFICATION` | str | CRITICAL/SUBSTITUTABLE/MIXED |
| `PRE_AVG_Q_TOTAL` | float | Сума PRE_AVG_Q по всіх подіях |
| `STOCKOUT_WEEKS_TOTAL` | int | Сума тижнів stock-out |

---

## 4. ВАЛІДАЦІЯ ВИХОДІВ

### Інваріанти

```python
# 1. Сума SHARE = 100% для кожного препарату
assert abs(SHARE_INTERNAL + SHARE_LOST - 1.0) < 0.001

# 2. NFC декомпозиція = 100%
assert abs(SHARE_SAME_NFC1 + SHARE_DIFF_NFC1 - 1.0) < 0.001

# 3. SUBSTITUTE_SHARE сума = 100% для кожного stockout drug
assert df.groupby('STOCKOUT_DRUG_ID')['SUBSTITUTE_SHARE'].sum() ≈ 100%
```

---

## 5. ЗВ'ЯЗОК З PHASE 2

```
PHASE 1 (Per-Market) - Step 5
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

## 6. ЗВ'ЯЗОК З ІНШИМИ КРОКАМИ

```
STEP 1: АГРЕГАЦІЯ
    │  Документація: 01_DATA_AGREGATION.md
    │
    ▼
STEP 2: ДЕТЕКЦІЯ STOCK-OUT
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
STEP 5: ЗВІТИ ТА CSV (цей документ)
       Вхід: did_statistics + substitute_shares
       Вихід: Excel звіти + Cross-Market CSV
```

**Критичні фільтри з попередніх кроків:**
- Step 3: Phantom substitutes filter
- Step 4: Zero-LIFT filter

---

## 7. ТИПОВІ ПОМИЛКИ

| Помилка | Симптом | Рішення |
|---------|---------|---------|
| Немає даних | Порожні звіти | Перевірити виконання Steps 3-4 |
| Проблеми з кирилицею | Квадратики | Встановити шрифт DejaVu Sans |
| Старі дані | Невідповідність | Перезапустити Steps 3-4-5 |
| SHARE ≠ 100% | Помилка валідації | Перевірити фільтри в Steps 3-4 |

**Детальніше:** [02_KNOWN_ISSUES.md](../00_ai_rules/02_KNOWN_ISSUES.md)

---

## 8. ВІЗУАЛІЗАЦІЇ (ОПЦІОНАЛЬНО)

При необхідності можна додати генерацію графіків:

### Параметри візуалізації

```python
# Розмір та якість
DPI = 150
FIGSIZE = (14, 8)  # дюймів
FONT_FAMILY = 'DejaVu Sans'  # підтримка кирилиці

# Кольорова палітра
COLORS = {
    'critical': '#E74C3C',      # Червоний
    'substitutable': '#27AE60', # Зелений
    'mixed': '#F39C12',         # Жовтий
    'same_nfc': '#3498DB',      # Синій
    'diff_nfc': '#E67E22',      # Помаранчевий
}
```

### Типи графіків

| Тип | Опис |
|-----|------|
| Top-N CRITICAL | Bar chart препаратів з найвищим SHARE_LOST |
| Top-N SUBSTITUTABLE | Bar chart препаратів з найвищим SHARE_INTERNAL |
| Top-N substitutes SAME_NFC1 | Bubble chart найактивніших substitutes тієї ж форми |
| Top-N substitutes DIFF_NFC1 | Bubble chart найактивніших substitutes іншої форми |
