# SUBSTITUTE SHARES - Phase 3 Step 2

> **Версія:** 1.0 | **Створено:** 27.04.2026

---

## 1. ПРИЗНАЧЕННЯ

Крос-ринкова агрегація часток субститутів для формування ready-to-import таблиці для Power BI:
- Зібрати дані по субститутах з усіх ринків
- Агрегувати LIFT-зваженим методом
- Сформувати таблиці `substitute_shares` та `substitute_summary`

**Реалізація:** `exec_scripts/03_final_output/02_substitute_shares.py`

**Залежність:** потребує `drug_coefficients.csv` від Step 3.1 — список прийнятих препаратів.

---

## 2. РЕАЛІЗАЦІЯ

| Скрипт | Опис |
|--------|------|
| `exec_scripts/03_final_output/02_substitute_shares.py` | Основний скрипт Step 3.2 |

---

## 3. ВХІДНІ ДАНІ

| Джерело | Шлях | Призначення |
|---------|------|-------------|
| Step 3.1 output | `.../03_01_drug_coefficients/drug_coefficients.csv` | Список прийнятих `DRUGS_ID` |
| Per-market субститути | `results/cross_market_data/market_substitution_{ID}/sub_drugs_{ID}.csv` | Частки субститутів per ринок |
| Per-market коефіцієнти | `results/cross_market_data/market_substitution_{ID}/sub_coef_{ID}.csv` | `INTERNAL_LIFT` per ринок |

---

## 4. PIPELINE

```
┌─────────────────────────────────────────────────────────────────────────────┐
│              PHASE 3 STEP 2: SUBSTITUTE SHARES                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  4.1 ЗАВАНТАЖЕННЯ                                                           │
│      drug_coefficients.csv → valid_drug_ids (accepted у Step 3.1)          │
│      ↓                                                                       │
│  4.2 ОБРОБКА PER РИНОК                                                      │
│      Для кожного market_substitution_{ID}/:                                  │
│        sub_drugs_{ID}.csv + sub_coef_{ID}.csv                               │
│        → фільтр по valid_drug_ids                                           │
│        → merge: sub_drugs JOIN sub_coef ON STOCKOUT_DRUG_ID                 │
│        → TOTAL_LIFT = SUBSTITUTE_SHARE (decimal) × INTERNAL_LIFT            │
│      ↓                                                                       │
│  4.3 КРОС-РИНКОВА АГРЕГАЦІЯ                                                │
│      SUM(TOTAL_LIFT) per (stockout, substitute) pair                        │
│      SUM(INTERNAL_LIFT) per drug з дедублікацією по (CLIENT_ID, DRUGS_ID)  │
│      AGG_SUBSTITUTE_SHARE = SUM(TOTAL_LIFT) / SUM(INTERNAL_LIFT)           │
│      SUBSTITUTE_RANK = порядковий номер (1 = найбільша частка)              │
│      ↓                                                                       │
│  4.4 SUBSTITUTE SUMMARY                                                     │
│      Per drug: N_SUBSTITUTES, TOP_SUBSTITUTE, TOTAL_MARKETS_COVERED         │
│      ↓                                                                       │
│  4.5 ВАЛІДАЦІЯ (7 checks)                                                   │
│      Ключовий: SHARE_SUM_INVARIANT — SUM per drug = 1.0 (±0.01)            │
│      → validation_report.txt                                                │
│      ↓                                                                       │
│  4.6 XLSX БІЗНЕС-ЗВІТИ                                                      │
│      AGG_SUBSTITUTE_SHARE форматується як %                                  │
│      Рядки rank-1 підсвічені зеленим                                        │
│      → subst_business_reports/substitute_shares.xlsx                        │
│      → subst_business_reports/substitute_summary.xlsx                       │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 5. МЕТОД АГРЕГАЦІЇ

### 5.1. LIFT-зважена агрегація

```
Для кожного ринку i, кожної пари (stockout s, substitute t):
  TOTAL_LIFT(s, t, i) = SUBSTITUTE_SHARE(s, t, i) × INTERNAL_LIFT(s, i)

Cross-market:
  AGG_SUBSTITUTE_SHARE(s, t) = Σ_i TOTAL_LIFT(s, t, i) / Σ_i INTERNAL_LIFT(s, i)
```

**Аналогія з Phase 2:** Метод ідентичний `WEIGHTED_MEAN_SHARE` (Phase 2), де вага = INTERNAL_LIFT.
Ринки з більшим INTERNAL_LIFT мали більше stock-out подій → їх оцінки вагоміші.

### 5.2. Дедублікація INTERNAL_LIFT

INTERNAL_LIFT — drug-level метрика: одне значення на `(CLIENT_ID, STOCKOUT_DRUG_ID)`,
однакове для всіх субститутів одного препарату на одному ринку.

```
НЕПРАВИЛЬНО (без дедублікації):
  SUM(INTERNAL_LIFT) рахується K разів (K = кількість субститутів) → завищений знаменник

ПРАВИЛЬНО:
  drop_duplicates(["CLIENT_ID", "STOCKOUT_DRUG_ID"])
  → SUM(INTERNAL_LIFT) per drug (один раз per ринок)
```

### 5.3. Формат SUBSTITUTE_SHARE у вхідних даних

`SUBSTITUTE_SHARE` у `sub_drugs_{ID}.csv` зберігається як **decimal (0–1)**, не відсоток.
Phase 1 Step 5 вже виконав `/100` при збереженні файлів.

---

## 6. ВИХІДНІ ФАЙЛИ

### 6.1. Структура виходів

```
results/substitution_research/03_final_output/03_02_substitute_shares/
├── substitute_shares.csv        # Всі пари (stockout → substitute) — Power BI
├── substitute_summary.csv       # Підсумок per препарат — Power BI
├── validation_report.txt        # Результати 7 перевірок
│
└── subst_business_reports/      # XLSX для бізнесу
    ├── substitute_shares.xlsx   # Rank-1 зелений, % формат
    └── substitute_summary.xlsx
```

### 6.2. substitute_shares.csv

| Колонка | Тип | Опис |
|---------|-----|------|
| `STOCKOUT_DRUG_ID` | int | ID відсутнього препарату |
| `STOCKOUT_DRUG_NAME` | str | Назва відсутнього препарату |
| `INN_ID` | int | ID МНН |
| `INN_NAME` | str | Назва МНН |
| `NFC1_ID` | str | Фармацевтична форма відсутнього препарату |
| `SUBSTITUTE_DRUG_ID` | float | ID субституту |
| `SUBSTITUTE_DRUG_NAME` | str | Назва субституту |
| `SUBSTITUTE_NFC1_ID` | str | Фармацевтична форма субституту |
| `SAME_NFC1` | bool | Чи збігається форма субституту з оригіналом |
| `AGG_SUBSTITUTE_SHARE` | float | LIFT-зважена частка субституту (0–1) |
| `MARKETS_COUNT` | int | К-сть ринків, де пара зустрічається |
| `SUBSTITUTE_RANK` | int | Ранг субституту (1 = найбільша частка) |

### 6.3. substitute_summary.csv

| Колонка | Тип | Опис |
|---------|-----|------|
| `STOCKOUT_DRUG_ID` | int | ID відсутнього препарату |
| `STOCKOUT_DRUG_NAME` | str | Назва препарату |
| `INN_ID` | int | ID МНН |
| `INN_NAME` | str | Назва МНН |
| `NFC1_ID` | str | Фармацевтична форма |
| `N_SUBSTITUTES` | int | Кількість унікальних субститутів |
| `TOP_SUBSTITUTE_ID` | float | ID субституту #1 (найбільша частка) |
| `TOP_SUBSTITUTE_NAME` | str | Назва субституту #1 |
| `TOP_SUBSTITUTE_SHARE` | float | Частка субституту #1 (0–1) |
| `TOTAL_MARKETS_COVERED` | int | Максимальна кількість ринків по будь-якому субституту |
| `AVG_MARKETS_PER_SUBSTITUTE` | float | Середня кількість ринків per субститут |

---

## 7. ВАЛІДАЦІЯ

| # | Перевірка | Опис |
|---|-----------|------|
| 1 | `SHARE_RANGE` | Всі `AGG_SUBSTITUTE_SHARE` в [0, 1] |
| 2 | `SHARE_SUM_INVARIANT` | `SUM(AGG_SHARE per drug)` = 1.0 (±0.01) |
| 3 | `NO_NAN_STOCKOUT_DRUG_ID` | Немає NaN |
| 4 | `NO_NAN_SUBSTITUTE_DRUG_ID` | Немає NaN |
| 5 | `NO_NAN_AGG_SUBSTITUTE_SHARE` | Немає NaN |
| 6 | `NO_DUPLICATE_PAIRS` | Унікальність `(STOCKOUT_DRUG_ID, SUBSTITUTE_DRUG_ID)` |
| 7 | `RANK1_COUNT` | К-сть rank-1 = к-сть унікальних `STOCKOUT_DRUG_ID` |

**SHARE_SUM_INVARIANT** — ключова перевірка методологічної правильності агрегації.

---

## 8. EDGE CASES

| Ситуація | Поведінка |
|----------|-----------|
| Порожня папка `market_substitution_{ID}/` | Ринок пропускається (`skipped`) |
| `INTERNAL_LIFT = 0` для препарату | Пара не включається в агрегацію |
| Препарат є в `sub_drugs` але не в `drug_coefficients` | Виключається (не пройшов Step 3.1) |
| `SUBSTITUTE_SHARE = NaN` | Рядок виключається при обробці ринку |

---

## 9. НАВІГАЦІЯ

| Ресурс | Посилання |
|--------|-----------|
| Pipeline Phase 3 | [00_PIPELINE_PHASE_3.md](./00_PIPELINE_PHASE_3.md) |
| Drug Coefficients (Step 3.1) | [01_DRUG_COEFFICIENTS.md](./01_DRUG_COEFFICIENTS.md) |
| Phase 2 Statistical Methodology | [../02_substitution_coefficients/02_01_STATISTICAL_METHODOLOGY.md](../02_substitution_coefficients/02_01_STATISTICAL_METHODOLOGY.md) |
| Phase 2 Pipeline | [../02_substitution_coefficients/00_PIPELINE_PHASE_2.md](../02_substitution_coefficients/00_PIPELINE_PHASE_2.md) |
