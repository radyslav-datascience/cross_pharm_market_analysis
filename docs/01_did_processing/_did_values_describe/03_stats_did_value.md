# Опис колонок - Phase 1 Step 3: DiD Analysis

> **Версія:** 1.1 | **Оновлено:** 03.02.2026

---

## 1. Результати DiD per Event

**Файли:** `did_results_{CLIENT_ID}.csv`
**Приклад:** `did_results_28670.csv`

| Колонка | Тип | Опис |
|---------|-----|------|
| `EVENT_ID` | str | Унікальний ID події (формат: `{CLIENT_ID}_{INN_ID}_{NNNN}`) |
| `CLIENT_ID` | int | ID цільової аптеки (ринку) |
| `INN_ID` | int | ID МНН групи |
| `INN_NAME` | str | Назва МНН групи |
| `DRUGS_ID` | int | ID препарату (TARGET) |
| `DRUGS_NAME` | str | Назва препарату |
| `NFC1_ID` | str | Форма випуску (рівень 1) |
| `NFC_ID` | str | Форма випуску (детальна) |
| `STOCKOUT_START` | date | Початок stock-out |
| `STOCKOUT_END` | date | Кінець stock-out |
| `STOCKOUT_WEEKS` | int | Тривалість stock-out (тижні) |
| `PRE_START` | date | Початок PRE-періоду |
| `PRE_END` | date | Кінець PRE-періоду |
| `PRE_WEEKS` | int | Тривалість PRE-періоду (тижні) |
| `PRE_AVG_Q` | float | Середні продажі TARGET за тиждень у PRE-періоді |
| `POST_START` | date | Початок POST-періоду |
| `POST_END` | date | Кінець POST-періоду |
| `POST_WEEKS` | int | Тривалість POST-періоду (тижні) |
| `POST_STATUS` | str | Статус POST-періоду (valid/no_recovery/insufficient_data) |
| `MARKET_PRE` | float | Продажі ринку в PRE-періоді |
| `MARKET_DURING` | float | Продажі ринку під час stock-out |
| `MARKET_GROWTH` | float | Коефіцієнт росту ринку |
| `INTERNAL_LIFT` | float | LIFT substitutes в TARGET аптеці |
| `LOST_SALES` | float | LIFT конкурентів (втрачені продажі) |
| `TOTAL_EFFECT` | float | Загальний ефект (INTERNAL_LIFT + LOST_SALES) |
| `SHARE_INTERNAL` | float | Частка внутрішньої субституції (0.0-1.0) |
| `SHARE_LOST` | float | Частка втрачених продажів (0.0-1.0) |
| `SUBSTITUTES_COUNT` | int | Кількість валідних substitutes |
| `SUBSTITUTES_WITH_LIFT` | int | Кількість substitutes з позитивним LIFT |
| `LIFT_SAME_NFC1` | float | LIFT substitutes тієї ж форми випуску |
| `LIFT_DIFF_NFC1` | float | LIFT substitutes іншої форми випуску |
| `SHARE_SAME_NFC1` | float | Частка LIFT від тієї ж форми (0.0-1.0) |
| `SHARE_DIFF_NFC1` | float | Частка LIFT від іншої форми (0.0-1.0) |

**Формули:**
```
MARKET_GROWTH = MARKET_DURING / MARKET_PRE
EXPECTED = SALES_PRE × MARKET_GROWTH
LIFT = max(0, ACTUAL - EXPECTED)
INTERNAL_LIFT = Σ LIFT (substitutes в TARGET аптеці)
LOST_SALES = LIFT конкурентів (збільшення продажів target препарату у конкурентів)
TOTAL_EFFECT = INTERNAL_LIFT + LOST_SALES
SHARE_INTERNAL = INTERNAL_LIFT / TOTAL_EFFECT
SHARE_LOST = LOST_SALES / TOTAL_EFFECT
```

**Інваріанти:**
- `SHARE_INTERNAL + SHARE_LOST = 1.0`
- `SHARE_SAME_NFC1 + SHARE_DIFF_NFC1 = 1.0` (якщо INTERNAL_LIFT > 0)

---

## 2. Mapping Target → Substitutes

**Файли:** `substitute_mapping_{CLIENT_ID}.csv`
**Приклад:** `substitute_mapping_28670.csv`

| Колонка | Тип | Опис |
|---------|-----|------|
| `EVENT_ID` | str | ID події |
| `CLIENT_ID` | int | ID цільової аптеки |
| `INN_ID` | int | ID МНН групи |
| `INN_NAME` | str | Назва МНН групи |
| `TARGET_DRUGS_ID` | int | ID target препарату |
| `TARGET_DRUGS_NAME` | str | Назва target препарату |
| `TARGET_NFC1_ID` | str | Форма випуску target |
| `SUBSTITUTE_DRUGS_ID` | int | ID substitute препарату |
| `SUBSTITUTE_DRUGS_NAME` | str | Назва substitute |
| `SUBSTITUTE_NFC1_ID` | str | Форма випуску substitute |
| `SAME_NFC1` | bool | Чи однакова форма випуску |
| `NFC_GROUP` | str | Група сумісності (ORAL / EXACT_MATCH) |

**Фільтри:**
1. **NFC Compatibility Filter:** форма випуску повинна бути сумісною
   - ORAL_GROUP: пероральні форми взаємозамінні
   - EXACT_MATCH: інші форми — тільки та сама форма
2. **Phantom Filter:** substitute повинен мати дані під час stock-out

---

## 3. Статистика per INN

**Файл:** `_stats/did_summary_{CLIENT_ID}.csv`
**Приклад:** `did_summary_28670.csv`

| Колонка | Тип | Опис |
|---------|-----|------|
| `INN_ID` | int | ID МНН групи |
| `INN_NAME` | str | Назва МНН групи |
| `EVENTS` | int | Кількість валідних DiD подій |
| `DRUGS` | int | Кількість унікальних препаратів |
| `AVG_SHARE_INTERNAL` | float | Середній SHARE_INTERNAL по групі |
| `AVG_SHARE_LOST` | float | Середній SHARE_LOST по групі |
| `AVG_SHARE_SAME_NFC1` | float | Середній SHARE_SAME_NFC1 |
| `TOTAL_INTERNAL_LIFT` | float | Сумарний INTERNAL_LIFT |
| `TOTAL_LOST_SALES` | float | Сумарний LOST_SALES |

---

## 4. Статистика per DRUGS з класифікацією

**Файл:** `_stats/drugs_summary_{CLIENT_ID}.csv`
**Приклад:** `drugs_summary_28670.csv`

| Колонка | Тип | Опис |
|---------|-----|------|
| `DRUGS_ID` | int | ID препарату |
| `DRUGS_NAME` | str | Назва препарату |
| `INN_ID` | int | ID МНН групи |
| `INN_NAME` | str | Назва МНН групи |
| `NFC1_ID` | str | Форма випуску |
| `EVENTS_COUNT` | int | Кількість stock-out подій |
| `SHARE_INTERNAL` | float | Середній SHARE_INTERNAL |
| `SHARE_LOST` | float | Середній SHARE_LOST |
| `SHARE_SAME_NFC1` | float | Середній SHARE_SAME_NFC1 |
| `SHARE_DIFF_NFC1` | float | Середній SHARE_DIFF_NFC1 |
| `INTERNAL_LIFT` | float | Сумарний INTERNAL_LIFT |
| `LOST_SALES` | float | Сумарний LOST_SALES |
| `TOTAL_EFFECT` | float | Сумарний ефект |
| `AVG_STOCKOUT_WEEKS` | float | Середня тривалість stock-out |
| `CLASSIFICATION` | str | Класифікація препарату |

**Класифікація:**
```
CRITICAL:      SHARE_LOST > 40%     → тримати в асортименті
SUBSTITUTABLE: SHARE_INTERNAL > 60% → можна замінити
MODERATE:      між порогами         → потребує додаткового аналізу
UNKNOWN:       NaN значення         → недостатньо даних
```

---

## 5. Метадані обробки

**Файл:** `_stats/did_metadata_{CLIENT_ID}.csv`
**Приклад:** `did_metadata_28670.csv`

| Параметр | Опис |
|----------|------|
| `CLIENT_ID` | ID цільової аптеки |
| `GENERATION_TIMESTAMP` | Час генерації |
| `MIN_POST_PERIOD_WEEKS` | Мінімальна тривалість POST-періоду |
| `MAX_POST_GAP_WEEKS` | Максимальний gap до відновлення |
| `CRITICAL_THRESHOLD` | Поріг для CRITICAL (40%) |
| `SUBSTITUTABLE_THRESHOLD` | Поріг для SUBSTITUTABLE (60%) |
| `TOTAL_EVENTS` | Загальна кількість DiD подій |
| `TOTAL_UNIQUE_DRUGS` | Кількість унікальних препаратів |
| `TOTAL_INN_GROUPS` | Кількість INN груп |
| `AVG_SHARE_INTERNAL` | Середній SHARE_INTERNAL по ринку |
| `AVG_SHARE_LOST` | Середній SHARE_LOST по ринку |
| `CRITICAL_DRUGS` | Кількість CRITICAL препаратів |
| `SUBSTITUTABLE_DRUGS` | Кількість SUBSTITUTABLE препаратів |
| `MODERATE_DRUGS` | Кількість MODERATE препаратів |
| `UNKNOWN_DRUGS` | Кількість UNKNOWN препаратів |

---

## 6. Структура папок

```
01_per_market/{CLIENT_ID}/03_did_analysis_{CLIENT_ID}/
├── did_results_{CLIENT_ID}.csv       # DiD результати per event
├── substitute_mapping_{CLIENT_ID}.csv # Mapping target → substitutes
└── _stats/
    ├── did_summary_{CLIENT_ID}.csv    # Per INN статистика
    ├── drugs_summary_{CLIENT_ID}.csv  # Per DRUGS + класифікація
    └── did_metadata_{CLIENT_ID}.csv   # Параметри та метадані
```

---

## 7. Валідація та фільтри

### Причини відхилення подій

| Причина | Опис |
|---------|------|
| `no_post_period` | Немає валідного POST-періоду (продажі не відновились) |
| `no_substitutes` | Немає валідних substitutes (NFC + Phantom filter) |
| `no_effect` | TOTAL_EFFECT < MIN_TOTAL_FOR_SHARE |

### Параметри валідації

- `MIN_POST_PERIOD_WEEKS = 4` — мінімальна тривалість POST
- `MAX_POST_GAP_WEEKS = 2` — максимальний gap до відновлення
- `MIN_TOTAL_FOR_SHARE = 0.001` — мінімальний ефект для розрахунку SHARE

---

## 8. Приклад даних

### did_results_28670.csv (перші 3 рядки)
```csv
EVENT_ID,CLIENT_ID,INN_ID,INN_NAME,DRUGS_ID,DRUGS_NAME,...,SHARE_INTERNAL,SHARE_LOST
28670_350_0980,28670,350,АРГИНИН,51182,"ГЛУТАРГИН...",0.0,1.0
28670_350_0981,28670,350,АРГИНИН,51182,"ГЛУТАРГИН...",0.526806,0.473194
28670_350_0982,28670,350,АРГИНИН,51182,"ГЛУТАРГИН...",0.0,1.0
```

### drugs_summary_28670.csv (приклад)
```csv
DRUGS_ID,DRUGS_NAME,INN_ID,INN_NAME,NFC1_ID,EVENTS_COUNT,SHARE_INTERNAL,SHARE_LOST,CLASSIFICATION
4043,"ТРОКСЕВАЗИН...",2733,ТРОКСЕРУТИН,"Местно действующие...",18,0.2008,0.7992,CRITICAL
4954,"ИБУПРОФЕН...",3138,ИБУПРОФЕН,Пероральные твердые обычные,13,0.6587,0.3413,SUBSTITUTABLE
```

---

## 9. Бізнес-інтерпретація

### SHARE_INTERNAL vs SHARE_LOST

- **Високий SHARE_INTERNAL** (>60%): клієнти залишаються в аптеці, купуючи substitute
- **Високий SHARE_LOST** (>40%): клієнти йдуть до конкурентів

### Рекомендації по класифікації

| Клас | Дія | Пріоритет |
|------|-----|-----------|
| CRITICAL | Тримати в асортименті | Високий |
| SUBSTITUTABLE | Можна вивести, є замінники | Низький |
| MODERATE | Потребує моніторингу | Середній |
