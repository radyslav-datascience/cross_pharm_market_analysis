# Опис колонок - Phase 1 Step 1: Data Aggregation

> **Версія:** 1.0 | **Оновлено:** 28.01.2026

---

## 1. Агреговані дані per INN

**Файли:** `inn_{INN_ID}_{CLIENT_ID}.csv`
**Приклад:** `inn_350_28670.csv`

| Колонка | Тип | Опис |
|---------|-----|------|
| `PHARM_ID` | int | ID аптеки (ORG_ID). TARGET або конкурент |
| `DRUGS_ID` | int | ID препарату |
| `Date` | date | Дата (понеділок тижня, вирівняно) |
| `Q` | float | Кількість проданих упаковок за тиждень |
| `V` | float | Виручка (грн) за тиждень |
| `DRUGS_NAME` | str | Назва препарату |
| `INN_NAME` | str | Міжнародна непатентована назва (МНН) |
| `INN_ID` | int | ID МНН групи |
| `NFC1_ID` | str | Форма випуску (рівень 1) |
| `NFC_ID` | str | Форма випуску (детальна) |

**Особливості:**
- Дані після GAP FILLING: пропущені тижні заповнені Q=0, V=0
- Тижнева агрегація: кожен рядок = один тиждень
- Містить ВСІ аптеки: цільову (PHARM_ID = CLIENT_ID) та конкурентів

---

## 2. Статистика per DRUGS_ID

**Файли:** `stats_inn_{CLIENT_ID}/stats_inn_{INN_ID}.csv`
**Приклад:** `stats_inn_28670/stats_inn_350.csv`

| Колонка | Тип | Опис |
|---------|-----|------|
| `CLIENT_ID` | int | ID цільової аптеки (ринку) |
| `INN_ID` | int | ID МНН групи |
| `INN_NAME` | str | Назва МНН групи |
| `DRUGS_ID` | int | ID препарату |
| `DRUGS_NAME` | str | Назва препарату |
| `DATE_START` | date | Перша дата продажів (YYYY-MM-DD) |
| `DATE_END` | date | Остання дата продажів (YYYY-MM-DD) |
| `DATE_DIFF` | int | Кількість днів між DATE_START та DATE_END |
| `WEEKS_TOTAL` | int | Загальна кількість тижнів в даних |
| `WEEKS_WITH_SALES` | int | Кількість тижнів з продажами (Q > 0) |
| `SALES_RATIO` | float | Частка тижнів з продажами (0.0 - 1.0) |
| `TOTAL_Q` | float | Загальна кількість проданих упаковок |

**Формули:**
```
DATE_DIFF = (DATE_END - DATE_START).days + 1
WEEKS_TOTAL = count of weekly records
WEEKS_WITH_SALES = count of weeks where Q > 0
SALES_RATIO = WEEKS_WITH_SALES / WEEKS_TOTAL
```

**Примітка:** Статистика розраховується ТІЛЬКИ для цільової аптеки (PHARM_ID = CLIENT_ID)

---

## 3. Зведена статистика

**Файл:** `stats_inn_{CLIENT_ID}/summary.csv`

Містить всі рядки з усіх `stats_inn_{INN_ID}.csv` об'єднані в один файл.
Колонки ідентичні до секції 2.

---

## 4. Агрегована статистика per INN

**Файл:** `stats_inn_{CLIENT_ID}/inn_summary.csv`

| Колонка | Тип | Опис |
|---------|-----|------|
| `INN_ID` | int | ID МНН групи |
| `INN_NAME` | str | Назва МНН групи |
| `DRUGS_COUNT` | int | Кількість унікальних препаратів в групі |
| `DATE_START` | date | Найраніша дата серед всіх препаратів |
| `DATE_END` | date | Найпізніша дата серед всіх препаратів |
| `WEEKS_TOTAL` | int | Сума WEEKS_TOTAL по всіх препаратах |
| `WEEKS_WITH_SALES` | int | Сума WEEKS_WITH_SALES по всіх препаратах |
| `TOTAL_Q` | float | Сума TOTAL_Q по всіх препаратах |
| `AVG_SALES_RATIO` | float | Середній SALES_RATIO по групі |

**Формула:**
```
AVG_SALES_RATIO = WEEKS_WITH_SALES / WEEKS_TOTAL (агреговано по всіх препаратах)
```

---

## 5. Структура папок

```
01_per_market/{CLIENT_ID}/01_aggregation_{CLIENT_ID}/
├── inn_{INN_ID}_{CLIENT_ID}.csv      # Агреговані дані (всі аптеки)
├── inn_{INN_ID}_{CLIENT_ID}.csv
├── ...
└── stats_inn_{CLIENT_ID}/            # Статистика (тільки TARGET)
    ├── stats_inn_{INN_ID}.csv        # Per DRUGS_ID
    ├── summary.csv                   # Всі препарати разом
    └── inn_summary.csv               # Агреговано per INN
```

---

## 6. Приклад даних

### inn_350_28670.csv (перші 3 рядки)
```csv
PHARM_ID,DRUGS_ID,Date,Q,V,DRUGS_NAME,INN_NAME,INN_ID,NFC1_ID,NFC_ID
28670,51182,2023-01-16,0.14,92.37,"ГЛУТАРГИН...",АРГИНИН,350,"Парентеральні",Інфузії
28670,51182,2023-01-23,0.00,0.00,"ГЛУТАРГИН...",АРГИНИН,350,"Парентеральні",Інфузії
28753,51182,2023-01-16,0.28,184.74,"ГЛУТАРГИН...",АРГИНИН,350,"Парентеральні",Інфузії
```

### stats_inn_350.csv (приклад)
```csv
CLIENT_ID,INN_ID,INN_NAME,DRUGS_ID,DRUGS_NAME,DATE_START,DATE_END,DATE_DIFF,WEEKS_TOTAL,WEEKS_WITH_SALES,SALES_RATIO,TOTAL_Q
28670,350,АРГИНИН,51182,"ГЛУТАРГИН...",2023-01-16,2025-12-22,1072,153,27,0.176,12.5
```
