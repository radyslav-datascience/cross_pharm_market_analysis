# KNOWN ISSUES & LESSONS LEARNED

> **Версія:** 1.2 | **Оновлено:** 10.02.2026

---

## КРИТИЧНІ ПОМИЛКИ (УНИКАТИ!)

### 1. Gap Filling — ОБОВ'ЯЗКОВИЙ

**Проблема:** Без gap filling stock-out детекція працює некоректно.

**Симптом:** Категорія "UNKNOWN", рекомендація "Insufficient data".

**Рішення:** Заповнити пропущені тижні нулями:
```python
# Для кожного препарату створити повний ряд тижнів
all_weeks = pd.date_range(start=date_min, end=date_max, freq='W-MON')
df_full = df_drug.reindex(all_weeks)
df_full['Q'] = df_full['Q'].fillna(0)
```

**Перевірка:** Після gap filling кожен препарат має безперервний часовий ряд.

---

### 2. Stock-out = рядки з Q=0, НЕ відсутні рядки

**Проблема:** Після gap filling всі рядки є (з Q=0), тому шукати "відсутні рядки" — неправильно.

**НЕПРАВИЛЬНО:**
```python
if week not in weeks_with_sales:  # Після gap filling всі тижні є!
```

**ПРАВИЛЬНО:**
```python
df_drug['has_sales'] = df_drug['Q'] > 0
stockout_weeks = df_drug[~df_drug['has_sales']]
```

---

### 3. Target Pharmacy — фільтрувати по ORG_ID == CLIENT_ID

**Проблема:** В даних є продажі як цільової аптеки, так і конкурентів.

**НЕПРАВИЛЬНО:**
```python
df_target = df  # Всі продажі включають конкурентів!
```

**ПРАВИЛЬНО:**
```python
df_target = df[df['ORG_ID'] == df['CLIENT_ID']]  # Тільки цільова аптека
df_competitors = df[df['ORG_ID'] != df['CLIENT_ID']]  # Конкуренти
```

---

### 4. POST-період — перевіряти наявність

**Проблема:** Не всі stock-out події мають валідний POST-період.

**Рішення:**
- Мінімум N тижнів POST з продажами (визначено в config)
- Gap між stock-out та POST ≤ M тижнів
- Якщо POST невалідний — подію відфільтрувати

---

### 5. Phantom Substitutes — фільтрувати

**Проблема:** Substitute mapping може включати препарати, які не продавались в аптеці під час stockout.

**Симптом:** Substitutes з 0% SUBSTITUTE_SHARE у звіті.

**Рішення:** Перевіряти наявність даних substitute під час stockout періоду:
```python
def has_data_during_periods(df, drug_id, stockout_periods):
    drug_data = df[df['DRUGS_ID'] == drug_id]
    for start, end in stockout_periods:
        period_data = drug_data[(drug_data['Date'] >= start) &
                                (drug_data['Date'] <= end)]
        if len(period_data) > 0:
            return True
    return False
```

---

### 6. Zero-LIFT Substitutes — фільтрувати

**Проблема:** Substitutes з TOTAL_LIFT = 0 не мають цінності для аналізу.

**Бізнес-логіка:** Показувати препарати, які ніхто не обирав — не допомагає приймати рішення.

**Рішення:**
```python
df_agg = df_agg[df_agg['TOTAL_LIFT'] > 0].copy()
```

---

### 7. Каскадний вплив змін

**Проблема:** Зміни в ранніх етапах впливають на всі наступні.

**Правило:** При зміні Stage N — перезапустити всі Stage > N.

---

## МУЛЬТИ-РИНКОВІ ПРОБЛЕМИ

> Ця секція буде доповнюватись по мірі виявлення проблем під час розробки.

### 8. INN групи можуть відрізнятись між ринками

**Проблема:** Не всі INN групи присутні на всіх ринках.

**Рішення:** Динамічна валідація INN при обробці кожного ринку.

---

### 9. Мала кількість ринків для статистики

**Проблема:** При coverage < 50% довірчі інтервали занадто широкі.

**Рішення:** Використовувати мінімальний поріг кількості ринків для статистично значущих висновків. Препарати з низьким coverage класифікувати як "INSUFFICIENT_DATA".

---

### 10. [PLACEHOLDER] Нові проблеми

> Додавати нові проблеми по мірі виявлення у форматі:
> - **Проблема:** опис
> - **Симптом:** як виявляється
> - **Рішення:** код або процес

---

## МЕТОДОЛОГІЧНІ НЮАНСИ

### NFC Compatibility Filter

**Правило:** Не всі форми випуску взаємозамінні.

```
ORAL_GROUP (можуть замінювати одна одну):
  ✅ Пероральні тверді → Пероральні рідкі
  ✅ Таблетки → Капсули

EXACT_MATCH (тільки на себе):
  ❌ Ін'єкції НЕ замінюють Таблетки
  ❌ Мазі НЕ замінюють Капсули
```

---

### Валідація інваріантів

**Завжди перевіряти:**
```python
# Per-market: SHARE сума = 1.0
assert abs(SHARE_INTERNAL + SHARE_LOST - 1.0) < 0.001

# Cross-market: Coverage в межах [0, 1]
assert 0 <= MARKET_COVERAGE <= 1

# Довірчий інтервал: lower <= mean <= upper
assert CI_LOWER <= MEAN_SHARE <= CI_UPPER
```

---

## ТИПОВІ ПОМИЛКИ ПРИ РОЗРОБЦІ

### 1. Зміна READ-ONLY файлів
- `docs/00_ai_rules/*` — не змінювати без дозволу
- `project_core/did_config/*` — узгоджувати зміни параметрів

### 2. Не перевіряти результати
- Після кожного етапу перевіряти статистику
- Порівнювати з очікуваними значеннями

### 3. Ігнорувати edge cases
- Препарати з 0 продажами
- Ринки з неповними даними
- INN групи, що є тільки на одному ринку

---

## КОРИСНІ ФАЙЛИ

- `project_core/utility_functions/did_utils.py` — DiD функції
- `project_core/utility_functions/etl_utils.py` — ETL функції
- `project_core/did_config/nfc_compatibility.py` — NFC фільтр
- `project_core/did_config/classification_thresholds.py` — пороги класифікації
- `project_core/data_config/paths_config.py` — шляхи до даних
