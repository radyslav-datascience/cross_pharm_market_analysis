# Step 4: Аналіз розподілу substitutes (SUBSTITUTE_SHARE)

> **Версія:** 1.0 | **Створено:** 31.01.2026

---

## 1. ПРИЗНАЧЕННЯ

Четвертий крок розраховує **частку кожного substitute** в загальній внутрішній субституції:

- Розрахунок індивідуального LIFT для кожного substitute
- Агрегація по парах (stockout_drug, substitute)
- Розрахунок SUBSTITUTE_SHARE (% від INTERNAL_LIFT)
- Валідація консистентності з результатами Step 3

**Бізнес-питання:** Коли препарат X відсутній — який саме substitute забирає найбільше попиту?

---

## 2. РЕАЛІЗАЦІЯ

### Скрипт

**Розташування:** `exec_scripts/01_did_processing/02_04_substitute_analysis.py`

**Виконання:**
```bash
# Один ринок:
/opt/miniconda3/envs/proxima/bin/python exec_scripts/01_did_processing/02_04_substitute_analysis.py --market_id {CLIENT_ID}

# Всі ринки:
/opt/miniconda3/envs/proxima/bin/python exec_scripts/01_did_processing/02_04_substitute_analysis.py --all
```

### Допоміжні модулі

| Модуль | Використання |
|--------|--------------|
| `project_core/data_config/paths_config.py` | Шляхи до даних |
| `project_core/utility_functions/did_utils.py` | `calculate_substitute_lift()` |

### Вхід / Вихід

```
ВХІД (READ-ONLY):
  data/processed_data/01_per_market/{CLIENT_ID}/01_aggregation_{CLIENT_ID}/
    └── inn_{INN_ID}_{CLIENT_ID}.csv              # Тижневі продажі
  data/processed_data/01_per_market/{CLIENT_ID}/03_did_analysis_{CLIENT_ID}/
    ├── did_results_{CLIENT_ID}.csv              # POST періоди, MARKET_GROWTH
    ├── substitute_mapping_{CLIENT_ID}.csv       # Список substitutes
    └── _stats/drugs_summary_{CLIENT_ID}.csv    # Для валідації INTERNAL_LIFT

ВИХІД:
  data/processed_data/01_per_market/{CLIENT_ID}/04_substitute_shares_{CLIENT_ID}/
  ├── substitute_shares_{CLIENT_ID}.csv   # LIFT та SHARE per substitute
  └── _stats/                            # Статистика
```

---

## 3. PIPELINE

```
┌─────────────────────────────────────────────────────────────────────┐
│ 04.1: SUBSTITUTE SHARE CALCULATION                                  │
├─────────────────────────────────────────────────────────────────────┤
│ Для кожної події (EVENT_ID):                                        │
│ 1. Отримати POST-період та MARKET_GROWTH з did_results              │
│ 2. Отримати список substitutes з substitute_mapping                 │
│ 3. Для кожного substitute: розрахувати LIFT                         │
│                                                                     │
│ Агрегація по (STOCKOUT_DRUG_ID, SUBSTITUTE_DRUG_ID):                │
│ 4. TOTAL_LIFT = sum(LIFT) по всіх подіях                            │
│ 5. ⚠️ ZERO-LIFT FILTER: відкинути substitutes з TOTAL_LIFT = 0      │
│ 6. SUBSTITUTE_SHARE = TOTAL_LIFT / INTERNAL_LIFT × 100%             │
│ → OUTPUT: substitute_shares.csv                                     │
└─────────────────────────────────────────────────────────────────────┘
                                ↓
┌─────────────────────────────────────────────────────────────────────┐
│ 04.2: VALIDATION & STATISTICS                                       │
├─────────────────────────────────────────────────────────────────────┤
│ 1. Валідація: сума SHARE = 100% для кожного stockout drug           │
│ 2. Валідація: sum(TOTAL_LIFT) = INTERNAL_LIFT (з did_statistics)    │
│ 3. Статистика по NFC1 (SAME vs DIFF)                                │
│ 4. Збереження substitute_statistics.csv                             │
│ → OUTPUT: substitute_statistics.csv                                 │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 4. ZERO-LIFT FILTER (КРИТИЧНО)

**Проблема:** Деякі substitutes мають TOTAL_LIFT = 0 — вони існували в асортименті, але покупці їх НЕ обирали як заміну.

**Бізнес-логіка:** Substitutes з LIFT=0 не мають цінності для аналізу — показувати їх власнику аптеки не допомагає приймати рішення.

**Рішення:**
```python
df_agg = df_agg[df_agg['TOTAL_LIFT'] > 0].copy()
```

**Детальніше:** [02_KNOWN_ISSUES.md](../00_ai_rules/02_KNOWN_ISSUES.md) — секція 6

---

## 5. КЛЮЧОВІ ФОРМУЛИ

| Формула | Опис |
|---------|------|
| `LIFT = max(0, ACTUAL - EXPECTED)` | LIFT per substitute per event |
| `TOTAL_LIFT = sum(LIFT)` | Агрегований LIFT по всіх подіях |
| `INTERNAL_LIFT = sum(TOTAL_LIFT)` | Сума LIFT всіх substitutes для одного stockout drug |
| `SUBSTITUTE_SHARE = TOTAL_LIFT / INTERNAL_LIFT × 100` | Частка substitute в загальній субституції |

---

## 6. СТРУКТУРА ВИХІДНИХ ДАНИХ

### substitute_shares.csv

| Колонка | Опис |
|---------|------|
| `CLIENT_ID` | ID цільової аптеки |
| `INN_ID`, `INN_NAME` | МНН група |
| `STOCKOUT_DRUG_ID`, `STOCKOUT_DRUG_NAME` | Препарат, який був відсутній |
| `STOCKOUT_NFC1_ID` | Форма stockout препарату |
| `SUBSTITUTE_DRUG_ID`, `SUBSTITUTE_DRUG_NAME` | Препарат-замінник |
| `SUBSTITUTE_NFC1_ID` | Форма substitute |
| `SAME_NFC1` | bool: та сама форма? |
| `TOTAL_LIFT` | Сумарний LIFT від цього substitute |
| `LIFT_SAME_NFC1` | LIFT якщо SAME_NFC1=True, інакше 0 |
| `LIFT_DIFF_NFC1` | LIFT якщо SAME_NFC1=False, інакше 0 |
| `INTERNAL_LIFT` | Сума LIFT всіх substitutes (для SHARE) |
| `SUBSTITUTE_SHARE` | % від загального INTERNAL_LIFT |
| `EVENTS_COUNT` | Кількість подій, де substitute мав LIFT > 0 |

---

## 7. ВАЛІДАЦІЯ

### Інваріанти

```python
# 1. Сума SHARE = 100% для кожного stockout drug
for drug_id in df['STOCKOUT_DRUG_ID'].unique():
    total_share = df[df.STOCKOUT_DRUG_ID == drug_id]['SUBSTITUTE_SHARE'].sum()
    assert abs(total_share - 100.0) < 0.1

# 2. Сума LIFT = INTERNAL_LIFT (з did_statistics)
calculated = df.groupby('STOCKOUT_DRUG_ID')['TOTAL_LIFT'].sum()
expected = did_statistics['INTERNAL_LIFT']
assert (calculated - expected).abs().max() < 0.01
```

### Edge Cases

| Ситуація | Обробка |
|----------|---------|
| Всі substitutes з LIFT=0 | Stockout drug не має записів в результаті |
| Один substitute | SUBSTITUTE_SHARE = 100% |
| INTERNAL_LIFT = 0 | SUBSTITUTE_SHARE = 0% |

---

## 8. ЗВ'ЯЗОК З ІНШИМИ КРОКАМИ

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
STEP 4: АНАЛІЗ SUBSTITUTES (цей документ)
    │  Вхід: aggregated_data + did_results + substitute_mapping
    │  Вихід: substitute_shares, substitute_statistics
    │
    ▼
STEP 5: ЗВІТИ ТА CSV
       Документація: 05_REPORTS_AND_GRAPHS.md
```

**Step 4 НЕ модифікує outputs попередніх кроків — лише читає дані.**

---

## 9. ТИПОВІ ПОМИЛКИ

| Помилка | Симптом | Рішення |
|---------|---------|---------|
| Zero-LIFT substitutes | 0% SHARE в звіті | Zero-LIFT Filter відфільтровує |
| Сума SHARE ≠ 100% | Помилка валідації | Перевірити розрахунок INTERNAL_LIFT |
| Не збігається INTERNAL_LIFT | Помилка валідації | Перевірити фільтри |
| Багато записів з малим SHARE | Нормально | Більшість substitutes мають <10% |

**Детальніше:** [02_KNOWN_ISSUES.md](../00_ai_rules/02_KNOWN_ISSUES.md)
