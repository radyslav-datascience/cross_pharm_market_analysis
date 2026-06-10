# PHASE 3: Final Output

> **Версія:** 1.0 | **Створено:** 27.04.2026

---

## ПРИЗНАЧЕННЯ

Цей документ описує **Phase 3 (Final Output)** — формування фінальних файлів для Power BI на основі результатів Phase 2.

**Phase 3 використовує результати Phase 2** для побудови ready-to-use таблиць:
- Коефіцієнти субституції per drug (з фільтрацією за мінімальною кількістю ринків)
- LIFT-зважені частки субститутів cross-market

---

## ЗАГАЛЬНА КОНЦЕПЦІЯ

Phase 3 відповідає на питання:

```
1. Які препарати мають достатньо надійний коефіцієнт субституції (>= N ринків)?
2. Яка частка субституту при stock-out конкретного препарату (across markets)?
```

**Ключова ідея:** Взяти вже розраховані Phase 2 медіани (після IQR-фільтрації) та
агрегувати частки субститутів з усіх ринків LIFT-зваженим методом.

---

## PIPELINE OVERVIEW

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         PHASE 3: FINAL OUTPUT                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  Step 3.1                               Step 3.2                            │
│  ─────────                              ─────────                           │
│  Drug Coefficients              →       Substitute Shares                   │
│                                                                              │
│  - Читає drug_statistics.csv            - Читає drug_coefficients.csv       │
│    (Phase 2, після IQR)                   (Step 3.1 output)                 │
│  - Фільтр: MARKET_COUNT >= 20           - Збирає sub_drugs_{ID}.csv         │
│  - Кольорове кодування                    з усіх market_substitution_{ID}/  │
│    HIGH/MEDIUM/LOW                      - LIFT-зважена агрегація            │
│  - CSV + XLSX бізнес-звіт               - Інваріант: SUM_SHARE = 1.0       │
│                                         - CSV + XLSX бізнес-звіт            │
│                                                                              │
│  [01_drug_coefficients.py]              [02_substitute_shares.py]           │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## STEP 3.1: DRUG COEFFICIENTS

### Мета
Відібрати препарати з достатньою кількістю ринків та сформувати ready-to-import таблицю коефіцієнтів для Power BI.

### Ключова логіка

**1. Джерело медіани**
```
drug_statistics.csv (Phase 2 Step 2.1)
→ MEDIAN_SHARE_INTERNAL (розраховано після IQR-фільтрації outliers)
→ Перейменовується в MEDIAN_SUBSTITUTION_COEF
```

> Медіана береться з Phase 2, а НЕ перераховується з широкої матриці
> `researched_drugs_coefficients.csv` — та матриця містить outliers.

**2. Фільтр**
```
Приймаються: MARKET_COUNT_TOTAL >= MIN_MARKET_COUNT (= 20)
Відхиляються: MARKET_COUNT_TOTAL < 20
```

Поріг 20 походить з Sequential Analyzer (Study 02) як мінімум спостережень
для стабільного визначення типу розподілу.

**3. Кольорове кодування (XLSX)**
```
HIGH   (>= 70%): зелений
MEDIUM (40-70%): жовтий
LOW    (< 40%):  червоний
```

### Детальна документація
→ [01_DRUG_COEFFICIENTS.md](./01_DRUG_COEFFICIENTS.md)

---

## STEP 3.2: SUBSTITUTE SHARES

### Мета
Агрегувати частки субститутів з усіх ринків у єдину таблицю для Power BI.

### Ключова логіка

**LIFT-зважена агрегація**
```
Для кожного ринку:
  TOTAL_LIFT = SUBSTITUTE_SHARE (decimal) × INTERNAL_LIFT

Cross-market:
  AGG_SUBSTITUTE_SHARE = SUM(TOTAL_LIFT per pair) / SUM(INTERNAL_LIFT per market per drug)
```

**INTERNAL_LIFT дедублікація**
```
INTERNAL_LIFT — drug-level метрика (однакова для всіх субститутів одного препарату
на одному ринку). При агрегації дедублікується по (CLIENT_ID, STOCKOUT_DRUG_ID)
→ уникає завищення знаменника.
```

**Інваріант**
```
SUM(AGG_SUBSTITUTE_SHARE per stockout drug) = 1.0  (±ε = 0.01)
```

### Детальна документація
→ [02_SUBSTITUTE_SHARES.md](./02_SUBSTITUTE_SHARES.md)

---

## КЛЮЧОВІ ФОРМУЛИ

| Метрика | Формула | Опис |
|---------|---------|------|
| `MEDIAN_SUBSTITUTION_COEF` | `MEDIAN_SHARE_INTERNAL` з Phase 2 | Після IQR-фільтрації |
| `TOTAL_LIFT` | `SUBSTITUTE_SHARE × INTERNAL_LIFT` | Per ринок, per пара |
| `AGG_SUBSTITUTE_SHARE` | `SUM(TOTAL_LIFT) / SUM(INTERNAL_LIFT)` | Cross-market, LIFT-зважена |

---

## ІНВАРІАНТИ (ЗАВЖДИ ПЕРЕВІРЯТИ)

```
Step 3.1:
- 0 <= MEDIAN_SUBSTITUTION_COEF <= 1
- Accepted + Rejected = Total (completeness)
- Немає DRUGS_ID одночасно в обох групах
- Всі accepted мають MARKET_COUNT >= 20

Step 3.2:
- 0 <= AGG_SUBSTITUTE_SHARE <= 1
- SUM(AGG_SUBSTITUTE_SHARE per drug) = 1.0  (±0.01)
- Немає дублікатів пар (STOCKOUT_DRUG_ID, SUBSTITUTE_DRUG_ID)
- Кількість rank-1 субститутів = кількість унікальних STOCKOUT_DRUG_ID
```

---

## КОНФІГУРАЦІЯ

| Параметр | Значення | Джерело |
|----------|----------|---------|
| `MIN_MARKET_COUNT` | 20 | Константа в `01_drug_coefficients.py` |
| `COEF_HIGH_THRESHOLD` | 0.70 | Константа в `01_drug_coefficients.py` |
| `COEF_MEDIUM_THRESHOLD` | 0.40 | Константа в `01_drug_coefficients.py` |
| `SHARE_SUM_EPSILON` | 0.01 | Допустима похибка float у `02_substitute_shares.py` |

---

## СТРУКТУРА СКРИПТІВ

| Скрипт | Опис |
|--------|------|
| `exec_scripts/03_final_output/01_drug_coefficients.py` | Step 3.1: Drug coefficients |
| `exec_scripts/03_final_output/02_substitute_shares.py` | Step 3.2: Substitute shares |

**Виконання (строгий порядок):**
```bash
python exec_scripts/03_final_output/01_drug_coefficients.py
python exec_scripts/03_final_output/02_substitute_shares.py
```

> Step 3.2 залежить від виходу Step 3.1 (читає `drug_coefficients.csv`)

---

## ЗВ'ЯЗОК З PHASE 2

```
PHASE 2 (Cross-Market Aggregation)
    │
    │  Вихід: drug_statistics.csv (MEDIAN_SHARE_INTERNAL, MARKET_COUNT_TOTAL)
    │         cross_market_data/market_substitution_{ID}/sub_drugs_{ID}.csv
    │         cross_market_data/market_substitution_{ID}/sub_coef_{ID}.csv
    │
    ▼
PHASE 3 (Final Output for Power BI)
    │
    │  Step 3.1: Фільтрація + коефіцієнти → drug_coefficients.csv
    │  Step 3.2: Агрегація субститутів    → substitute_shares.csv + substitute_summary.csv
    │
    ▼
Power BI (готові до імпорту таблиці)
```

---

## НАВІГАЦІЯ

| Ресурс | Посилання |
|--------|-----------|
| Drug Coefficients (Step 3.1) | [01_DRUG_COEFFICIENTS.md](./01_DRUG_COEFFICIENTS.md) |
| Substitute Shares (Step 3.2) | [02_SUBSTITUTE_SHARES.md](./02_SUBSTITUTE_SHARES.md) |
| Phase 2 документація | [../02_substitution_coefficients/00_PIPELINE_PHASE_2.md](../02_substitution_coefficients/00_PIPELINE_PHASE_2.md) |
| Загальний бізнес-контекст | [../00_ai_rules/01_BUSINESS_CONTEXT.md](../00_ai_rules/01_BUSINESS_CONTEXT.md) |
