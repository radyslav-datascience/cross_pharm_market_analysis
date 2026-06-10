# DATA DICTIONARY - cross_pharm_market_analysis

> **Версія:** 1.0 | **Створено:** 31.01.2026

**Див. також:**
- [03_RESEARCH_METHODS.md](./03_RESEARCH_METHODS.md) — методологія та формули
- [01_BUSINESS_CONTEXT.md](../00_ai_rules/01_BUSINESS_CONTEXT.md) — глосарій термінів

---

## 1. ІДЕНТИФІКАТОРИ

| Технічна назва | Людська назва | Опис |
|----------------|---------------|------|
| `CLIENT_ID` | ID цільової аптеки | ID аптеки з назви файлу (Rd2_{CLIENT_ID}.csv) |
| `ORG_ID` | ID аптеки-продавця | Аптека, що здійснила продаж |
| `DRUGS_ID` | ID препарату | Унікальний Morion ID препарату |
| `DRUGS_NAME` | Назва препарату | Повна назва препарату |
| `INN_ID` | ID МНН групи | Код групи діючої речовини |
| `INN_NAME` | Назва МНН | Міжнародна непатентована назва |
| `EVENT_ID` | ID події | Унікальний: `{CLIENT_ID}_{DRUGS_ID}_{NNNN}` |

---

## 2. ФОРМИ ВИПУСКУ (NFC)

| Технічна назва | Людська назва | Опис |
|----------------|---------------|------|
| `NFC_ID` | ID форми (детальний) | Специфічна форма випуску (14 категорій) |
| `NFC1_ID` | ID форми (широкий) | Широка категорія форми (9 категорій) |
| `NFC1_NAME` | Назва категорії | Текстова назва NFC1 категорії |
| `SAME_NFC1` | Та сама форма? | Boolean: чи substitute тієї ж форми |
| `STOCKOUT_NFC1_ID` | Форма stockout | NFC1 препарату, що був відсутній |
| `SUBSTITUTE_NFC1_ID` | Форма substitute | NFC1 препарату-замінника |

---

## 3. ЧАСОВІ КОЛОНКИ

| Технічна назва | Людська назва | Опис |
|----------------|---------------|------|
| `PERIOD_ID` | ID періоду | Закодована дата (YYYYNNNNN) |
| `Date` | Дата тижня | Дата понеділка тижня |
| `PRE_START` | Початок PRE | Перший тиждень PRE-періоду |
| `PRE_END` | Кінець PRE | Останній тиждень PRE-періоду |
| `PRE_WEEKS` | Тижнів PRE | Кількість тижнів PRE-періоду |
| `STOCKOUT_START` | Початок stock-out | Перший тиждень відсутності |
| `STOCKOUT_END` | Кінець stock-out | Останній тиждень відсутності |
| `STOCKOUT_WEEKS` | Тижнів stock-out | Тривалість stock-out |
| `POST_START` | Початок POST | Перший тиждень після відновлення |
| `POST_END` | Кінець POST | Останній тиждень POST-періоду |
| `POST_WEEKS` | Тижнів POST | Кількість тижнів POST-періоду |

---

## 4. КІЛЬКІСНІ ПОКАЗНИКИ

| Технічна назва | Людська назва | Опис |
|----------------|---------------|------|
| `Q` | Кількість | Кількість проданих упаковок |
| `V` | Вартість | Сума продажів (грн) |
| `MARKET_TOTAL_DRUGS_PACK` | Ринок (кількість) | Сума Q по всіх конкурентах |
| `MARKET_TOTAL_DRUGS_REVENUE` | Ринок (вартість) | Сума V по всіх конкурентах |
| `NOTSOLD_PERCENT` | % без продажів | Частка тижнів з Q=0 |

---

## 5. DiD РОЗРАХУНКИ

### Базові розрахунки

| Технічна назва | Людська назва | Опис | Формула |
|----------------|---------------|------|---------|
| `PRE_AVG_Q` | Продажі PRE | Середні продажі до stock-out | AVG(Q) за PRE-період |
| `MARKET_PRE` | Ринок PRE | Продажі конкурентів до stock-out | SUM(MARKET_Q) за PRE |
| `MARKET_DURING` | Ринок DURING | Продажі конкурентів під час stock-out | SUM(MARKET_Q) за DURING |
| `MARKET_GROWTH` | Ріст ринку | Коефіцієнт тренду ринку | MARKET_DURING / MARKET_PRE |
| `EXPECTED` | Очікувані продажі | Counterfactual без stock-out | PRE_AVG_Q × MARKET_GROWTH |
| `LIFT` | Додаткові продажі | Ефект від stock-out | max(0, ACTUAL - EXPECTED) |

### Агреговані LIFT

| Технічна назва | Людська назва | Опис |
|----------------|---------------|------|
| `INTERNAL_LIFT` | Внутрішній LIFT | Сума LIFT всіх substitutes |
| `LOST_SALES` | Втрачені продажі | Сума LIFT у конкурентів |
| `TOTAL_EFFECT` | Загальний ефект | INTERNAL_LIFT + LOST_SALES |
| `LIFT_SAME_NFC1` | LIFT тієї ж форми | LIFT substitutes з однаковою NFC1 |
| `LIFT_DIFF_NFC1` | LIFT іншої форми | LIFT substitutes з різною NFC1 |
| `TOTAL_LIFT` | Сумарний LIFT | Агрегований LIFT substitute по всіх подіях |

---

## 6. SHARE МЕТРИКИ

### Per-Market SHARE

| Технічна назва | Людська назва | Опис | Діапазон |
|----------------|---------------|------|----------|
| `SHARE_INTERNAL` | Частка внутрішня | % попиту що залишився в аптеці | [0, 1] |
| `SHARE_LOST` | Частка втрачена | % попиту що пішов до конкурентів | [0, 1] |

### NFC SHARE

| Технічна назва | Людська назва | Опис | Діапазон |
|----------------|---------------|------|----------|
| `SHARE_SAME_NFC1` | Частка тієї ж форми | % substitutes тієї ж NFC1 | [0, 1] |
| `SHARE_DIFF_NFC1` | Частка іншої форми | % substitutes іншої NFC1 | [0, 1] |

### SUBSTITUTE SHARE

| Технічна назва | Людська назва | Опис | Діапазон |
|----------------|---------------|------|----------|
| `SUBSTITUTE_SHARE` | Частка substitute | % конкретного substitute в INTERNAL_LIFT | [0, 100] |
| `AGG_SHARE_SAME_NFC1` | Агр. частка (та сама) | Сума SHARE substitutes тієї ж форми | [0, 100] |
| `AGG_SHARE_DIFF_NFC1` | Агр. частка (інша) | Сума SHARE substitutes іншої форми | [0, 100] |

---

## 7. CROSS-MARKET МЕТРИКИ (Phase 2)

| Технічна назва | Людська назва | Опис | Діапазон |
|----------------|---------------|------|----------|
| `MARKET_COVERAGE` | Покриття ринків | % ринків, де присутній препарат | [0, 1] |
| `MEAN_SHARE_INTERNAL` | Середнє SHARE | Середнє значення SHARE_INTERNAL | [0, 1] |
| `STD_SHARE_INTERNAL` | Стд. відхилення | Варіативність SHARE_INTERNAL | ≥ 0 |
| `CI_95_LOWER` | Нижня межа CI | 95% довірчий інтервал (нижня) | [0, 1] |
| `CI_95_UPPER` | Верхня межа CI | 95% довірчий інтервал (верхня) | [0, 1] |

---

## 8. КЛАСИФІКАЦІЯ

### Per-Market

| Технічна назва | Людська назва | Опис | Значення |
|----------------|---------------|------|----------|
| `PER_MARKET_CLASSIFICATION` | Класифікація | Категорія на рівні ринку | CRITICAL / SUBSTITUTABLE / MIXED |
| `RECOMMENDATION` | Рекомендація | Бізнес-рекомендація | KEEP / CONSIDER_REMOVAL / REVIEW |

### Cross-Market (Phase 2)

| Технічна назва | Людська назва | Опис | Значення |
|----------------|---------------|------|----------|
| `CROSS_MARKET_CLASSIFICATION` | Крос-ринкова класифікація | Стабільна категорія | CRITICAL / SUBSTITUTABLE / MODERATE |

---

## 9. SUBSTITUTE MAPPING

| Технічна назва | Людська назва | Опис |
|----------------|---------------|------|
| `TARGET_DRUGS_ID` | ID target | Препарат, що був відсутній |
| `TARGET_DRUGS_NAME` | Назва target | Назва відсутнього препарату |
| `TARGET_NFC1_ID` | Форма target | NFC1 відсутнього препарату |
| `SUBSTITUTE_DRUGS_ID` | ID substitute | Препарат-замінник |
| `SUBSTITUTE_DRUGS_NAME` | Назва substitute | Назва замінника |
| `SUBSTITUTE_NFC1_ID` | Форма substitute | NFC1 замінника |
| `NFC_GROUP` | Група NFC | ORAL / EXACT_MATCH |
| `STOCKOUT_DRUG_ID` | ID stockout препарату | Синонім TARGET_DRUGS_ID |
| `STOCKOUT_DRUG_NAME` | Назва stockout препарату | Синонім TARGET_DRUGS_NAME |

---

## 10. СТАТИСТИКА

| Технічна назва | Людська назва | Опис |
|----------------|---------------|------|
| `EVENTS_COUNT` | Кількість подій | Число stock-out подій |
| `SUBSTITUTES_COUNT` | Кількість substitutes | Число valid substitutes |
| `SUBSTITUTES_WITH_LIFT` | Substitutes з LIFT | Число substitutes з LIFT > 0 |
| `STOCKOUT_DRUGS_COUNT` | К-ть stockout препаратів | Скільки препаратів замінює substitute |
| `MARKETS_COUNT` | Кількість ринків | Число ринків (Phase 2) |

---

## 11. СЛУЖБОВІ КОЛОНКИ

| Технічна назва | Людська назва | Опис |
|----------------|---------------|------|
| `IS_TARGET` | Цільова аптека? | Boolean: ORG_ID == CLIENT_ID |
| `HAS_DATA` | Є дані? | Boolean: чи є продажі в періоді |
| `IS_VALID` | Валідний? | Boolean: чи пройшла валідацію |

---

## ІНВАРІАНТИ

Для валідації результатів:

```
# Per-market
SHARE_INTERNAL + SHARE_LOST = 1.0
SHARE_SAME_NFC1 + SHARE_DIFF_NFC1 = 1.0
LIFT_SAME_NFC1 + LIFT_DIFF_NFC1 = INTERNAL_LIFT
SUM(SUBSTITUTE_SHARE) = 100% (для кожного stockout drug)

# Cross-market
0 <= MARKET_COVERAGE <= 1
CI_LOWER <= MEAN_SHARE <= CI_UPPER
```

---

## ДЖЕРЕЛА КОЛОНОК ПО КРОКАХ

| Крок | Основні колонки | Документація |
|------|-----------------|--------------|
| Raw data | CLIENT_ID, ORG_ID, DRUGS_ID, INN_ID, Q, V, PERIOD_ID | — |
| Step 1 | Date, MARKET_TOTAL_*, NOTSOLD_PERCENT | 01_DATA_AGREGATION.md |
| Step 2 | EVENT_ID, PRE_*, STOCKOUT_*, validation flags | 02_STOCKOUT_DETECTION.md |
| Step 3 | MARKET_GROWTH, LIFT, SHARE_*, CLASSIFICATION | 03_DID_NFC_ANALYSIS.md |
| Step 4 | SUBSTITUTE_SHARE, TOTAL_LIFT, EVENTS_COUNT | 04_SUBSTITUTE_SHARE_ANALYSIS.md |
| Step 5 | Агреговані для звітів, Cross-Market CSV | 05_REPORTS_AND_GRAPHS.md |
| Phase 2 | MARKET_COVERAGE, CI_95, CROSS_MARKET_* | ../02_substitution_coefficients/ |
