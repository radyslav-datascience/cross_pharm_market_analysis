# Опис колонок - Phase 1 Step 2: Stockout Detection

> **Версія:** 1.0 | **Оновлено:** 28.01.2026

---

## 1. Валідовані stock-out події

**Файли:** `stockout_events_{CLIENT_ID}.csv`
**Приклад:** `stockout_events_28670.csv`

| Колонка | Тип | Опис |
|---------|-----|------|
| `EVENT_ID` | str | Унікальний ID події (формат: `{CLIENT_ID}_{INN_ID}_{counter:04d}`) |
| `CLIENT_ID` | int | ID цільової аптеки (ринку) |
| `INN_ID` | int | ID МНН групи |
| `INN_NAME` | str | Назва МНН групи |
| `DRUGS_ID` | int | ID препарату |
| `DRUGS_NAME` | str | Назва препарату |
| `NFC1_ID` | str | Форма випуску (рівень 1) |
| `NFC_ID` | str | Форма випуску (детальна) |
| `STOCKOUT_START` | date | Дата початку stock-out (YYYY-MM-DD) |
| `STOCKOUT_END` | date | Дата закінчення stock-out (YYYY-MM-DD) |
| `STOCKOUT_WEEKS` | int | Тривалість stock-out в тижнях |
| `PRE_START` | date | Початок PRE-періоду (YYYY-MM-DD) |
| `PRE_END` | date | Кінець PRE-періоду (YYYY-MM-DD) |
| `PRE_WEEKS` | int | Кількість тижнів у PRE-періоді (фактична) |
| `PRE_AVG_Q` | float | Середні тижневі продажі в PRE-періоді (baseline для DiD) |
| `MARKET_DURING_Q` | float | Сумарні продажі конкурентів під час stock-out |

**Формули:**
```
STOCKOUT_WEEKS = кількість послідовних тижнів з Q=0
PRE_START = STOCKOUT_START - (MIN_PRE_PERIOD_WEEKS * 7 днів)
PRE_END = STOCKOUT_START - 7 днів
PRE_AVG_Q = SUM(Q в PRE-періоді) / PRE_WEEKS
MARKET_DURING_Q = SUM(MARKET_TOTAL_DRUGS_PACK) під час stock-out
```

**Особливості:**
- Містить ТІЛЬКИ валідовані події (пройшли 3-рівневу валідацію)
- PRE_AVG_Q використовується як baseline для DiD аналізу
- MARKET_DURING_Q підтверджує активність ринку під час stock-out

---

## 2. Статистика per INN

**Файли:** `_stats/stockout_per_inn_{CLIENT_ID}.csv`
**Приклад:** `_stats/stockout_per_inn_28670.csv`

| Колонка | Тип | Опис |
|---------|-----|------|
| `INN_ID` | int | ID МНН групи |
| `INN_NAME` | str | Назва МНН групи |
| `DRUGS_COUNT` | int | Кількість унікальних препаратів в INN групі |
| `RAW_EVENTS` | int | Кількість ідентифікованих stock-out подій (до валідації) |
| `VALID_EVENTS` | int | Кількість валідованих stock-out подій |
| `VALIDATION_RATE` | float | Відсоток валідованих подій (%) |

**Формула:**
```
VALIDATION_RATE = (VALID_EVENTS / RAW_EVENTS) * 100
```

**Примітка:** Низький VALIDATION_RATE може вказувати на:
- Малу активність ринку (no_market_activity)
- Відсутність PRE-періоду продажів (no_pre_sales)
- Відсутність конкурентів (no_competitors)

---

## 3. Зведена статистика ринку

**Файли:** `_stats/stockout_summary_{CLIENT_ID}.csv`
**Приклад:** `_stats/stockout_summary_28670.csv`

| Колонка | Тип | Опис |
|---------|-----|------|
| `CLIENT_ID` | int | ID цільової аптеки (ринку) |
| `INN_COUNT` | int | Кількість оброблених INN груп |
| `TOTAL_RAW_EVENTS` | int | Загальна кількість ідентифікованих подій |
| `VALID_EVENTS` | int | Загальна кількість валідованих подій |
| `REJECTED_NO_MARKET` | int | Відхилено: ринок неактивний під час stock-out |
| `REJECTED_NO_PRE_SALES` | int | Відхилено: немає продажів у PRE-періоді |
| `REJECTED_NO_COMPETITORS` | int | Відхилено: конкуренти не продавали препарат |
| `VALIDATION_RATE` | float | Відсоток валідованих подій (%) |
| `UNIQUE_DRUGS` | int | Кількість унікальних препаратів з валідними подіями |
| `AVG_STOCKOUT_WEEKS` | float | Середня тривалість stock-out (тижнів) |
| `TIMESTAMP` | datetime | Час створення файлу |

**Формули:**
```
TOTAL_RAW_EVENTS = VALID_EVENTS + REJECTED_NO_MARKET + REJECTED_NO_PRE_SALES + REJECTED_NO_COMPETITORS
VALIDATION_RATE = (VALID_EVENTS / TOTAL_RAW_EVENTS) * 100
AVG_STOCKOUT_WEEKS = MEAN(STOCKOUT_WEEKS) по всіх валідних подіях
```

---

## 4. 3-рівнева валідація

Кожна ідентифікована stock-out подія проходить 3 рівні валідації:

| Рівень | Назва | Перевірка | Причина відхилення |
|--------|-------|-----------|-------------------|
| 1 | Market Activity | `MARKET_TOTAL_DRUGS_PACK > 0` під час stock-out | `no_market_activity` |
| 2 | PRE-period Sales | `Q > 0` в PRE-періоді, `PRE_WEEKS >= MIN_PRE_PERIOD_WEEKS` | `no_pre_sales` |
| 3 | Competitors Availability | Конкуренти продавали препарат під час stock-out | `no_competitors` |

**Логіка:**
- Рівень 1: Якщо весь ринок INN неактивний — це не stock-out, а сезонність/тренд
- Рівень 2: Без PRE-періоду неможливо розрахувати baseline для DiD
- Рівень 3: Якщо конкуренти не продавали — немає з чим порівнювати

---

## 5. Параметри детекції

Параметри задаються в `project_core/did_config/stockout_params.py`:

| Параметр | Значення | Опис |
|----------|----------|------|
| `MIN_STOCKOUT_WEEKS` | 1 | Мінімальна тривалість stock-out для реєстрації |
| `MIN_PRE_PERIOD_WEEKS` | 4 | Мінімальна кількість тижнів у PRE-періоді |

---

## 6. Структура папок

```
01_per_market/{CLIENT_ID}/02_stockout_{CLIENT_ID}/
├── stockout_events_{CLIENT_ID}.csv    # Валідовані події
└── _stats/
    ├── stockout_summary_{CLIENT_ID}.csv    # Загальна статистика
    └── stockout_per_inn_{CLIENT_ID}.csv    # Статистика per INN
```

---

## 7. Приклад даних

### stockout_events_28670.csv (перші 2 рядки)
```csv
EVENT_ID,CLIENT_ID,INN_ID,INN_NAME,DRUGS_ID,DRUGS_NAME,NFC1_ID,NFC_ID,STOCKOUT_START,STOCKOUT_END,STOCKOUT_WEEKS,PRE_START,PRE_END,PRE_WEEKS,PRE_AVG_Q,MARKET_DURING_Q
28670_106853_0001,28670,106853,ИПРАТРОПИЯ БРОМИД+ФЕНОТЕРОЛ,17794,"БЕРОДУАЛ®...",Для введения в легкие,Жидкости,2023-03-13,2023-11-13,36,2023-02-13,2023-03-06,4,0.25,147.47
28670_106853_0002,28670,106853,ИПРАТРОПИЯ БРОМИД+ФЕНОТЕРОЛ,17794,"БЕРОДУАЛ®...",Для введения в легкие,Жидкости,2023-11-27,2024-02-19,13,2023-10-30,2023-11-20,4,0.25,128.61
```

### stockout_summary_28670.csv (приклад)
```csv
CLIENT_ID,INN_COUNT,TOTAL_RAW_EVENTS,VALID_EVENTS,REJECTED_NO_MARKET,REJECTED_NO_PRE_SALES,REJECTED_NO_COMPETITORS,VALIDATION_RATE,UNIQUE_DRUGS,AVG_STOCKOUT_WEEKS,TIMESTAMP
28670,20,1615,1299,157,159,0,80.4,150,7.7,2026-01-28 13:41:54
```

### stockout_per_inn_28670.csv (приклад)
```csv
INN_ID,INN_NAME,DRUGS_COUNT,RAW_EVENTS,VALID_EVENTS,VALIDATION_RATE
3138,ИБУПРОФЕН,32,295,253,85.8
3170,ДИКЛОФЕНАК,36,313,237,75.7
3016,МЕСАЛАЗИН,2,22,4,18.2
```
