# ПЛАН ВДОСКОНАЛЕННЯ ПРОЕКТУ

> **Версія:** 1.0 | **Створено:** 31.01.2026

---

## МЕТА ПЛАНУ

Вдосконалення проекту `mass_market_analysis_test` для:
1. Повної верифікації розрахунків з оригінальним проектом `med_prod_research`
2. Створення повної технічної документації
3. Виведення проекту як автономного дослідження
4. Масштабування на 90+ локальних ринків

---

## ФАЗА 1: ВЕРИФІКАЦІЯ ТА ДОКУМЕНТАЦІЯ

### 1.1 Верифікація розрахунків

**Мета:** Переконатись, що всі розрахунки в `mass_market_analysis_test` ідентичні логіці `med_prod_research`.

**Етапи верифікації:**

| Етап | Скрипт | Ключові формули для перевірки |
|------|--------|-------------------------------|
| Step 1 | `02_01_data_aggregation.py` | Gap filling, week alignment, MARKET_TOTAL |
| Step 2 | `02_02_stockout_detection.py` | Stock-out criteria, PRE/POST periods |
| Step 3 | `02_03_did_analysis.py` | EXPECTED, LIFT, SHARE_INTERNAL, SHARE_LOST |
| Step 4 | `02_04_substitute_analysis.py` | SUBSTITUTE_SHARE, Zero-LIFT filter |
| Step 5 | `02_05_reports_cross_market.py` | CLASSIFICATION logic, report structure |

**Чек-лист верифікації для кожного етапу:**
- [ ] Порівняти формули з оригінальними notebooks
- [ ] Перевірити обробку edge cases (нулі, NaN, порожні дані)
- [ ] Перевірити пороги та константи
- [ ] Валідація інваріантів (суми = 100%)
- [ ] Порівняти вихідні результати на тестових даних

---

### 1.2 Створення технічної документації

**Структура документації (за аналогією з `med_prod_research/docs`):**

```
mass_market_analysis_test/docs/
│
├── 00_ai_rules/                    # Вже існує
│   ├── 00_CLAUDE_RULES.md          # ✅ Існує
│   ├── 01_BUSINESS_CONTEXT.md      # ✅ Існує
│   ├── 02_KNOWN_ISSUES.md          # ✅ Існує
│   └── 03_PROJECT_MAP.md           # ✅ Існує (v1.8)
│
├── 01_tech_description/            # СТВОРИТИ
│   ├── 00_PIPELINE_OVERVIEW.md     # Огляд pipeline та ключові формули
│   ├── 01_DATA_AGREGATION.md       # Методологія агрегації
│   ├── 02_STOCKOUT_DETECTION.md    # Методологія детекції stock-out
│   ├── 03_DID_NFC_ANALYSIS.md      # Методологія DiD
│   ├── 04_SUBSTITUTE_SHARE_ANALYSIS.md  # Методологія SUBSTITUTE_SHARE
│   └── 05_REPORTS_AND_GRAPHS.md    # Структура звітів
│
├── _project_history/               # Історія проекту
│   └── 00_WORK_HISTORY.md          # ✅ Існує
│
└── _values_describe/               # Вже існує (визначення змінних)
    ├── 01_stats_inn_value.md       # ✅
    ├── 02_stats_stockout_value.md  # ✅
    ├── 03_stats_did_value.md       # ✅
    ├── 04_stats_substitute_value.md # ✅
    └── 05_stats_reports_value.md   # ✅
```

**Пріоритети документації:**
1. `01_tech_description/00_PIPELINE_OVERVIEW.md` — загальний огляд
2. `01_tech_description/03_DID_NFC_ANALYSIS.md` — ключова методологія
3. `02_project_instructions/02_DATA_DICTIONARY.md` — словник термінів
4. Інші документи — по мірі необхідності

---

### 1.3 Підготовка до автоматизації

**Завдання:**

1. **Batch Runner Script:**
   - Створити `run_full_pipeline.py` для послідовного виконання всіх етапів
   - Параметр `--market_id` або `--all`
   - Обробка помилок та відновлення після збоїв

2. **Валідація вхідних даних:**
   - Перевірка формату CSV перед обробкою
   - Перевірка наявності обов'язкових колонок
   - Логування попереджень при аномаліях

3. **Логування:**
   - Timestamps для кожного етапу
   - Статистика обробки (кількість записів, час)
   - Summary log для моніторингу 90+ аптек

4. **Конфігурація:**
   - Винести всі пороги в єдиний config файл
   - Документувати значення за замовчуванням

---

## ФАЗА 2: АВТОНОМНІСТЬ ТА МАСШТАБУВАННЯ

### 2.1 Виведення проекту з `med_prod_research`

**Завдання:**

1. **Перенесення папки:**
   ```
   /Users/radyslav/data_analysis/proxima/med_prod_research/mass_market_analysis_test
   ↓
   /Users/radyslav/data_analysis/proxima/substitution_coeff_research
   ```

2. **Перейменування проекту:**
   - Нова назва: `substitution_coeff_research`
   - Відображає основну мету — розрахунок коефіцієнтів субституції

3. **Видалення залежностей від `med_prod_research`:**
   - Перевірити всі imports
   - Перенести необхідні utility functions
   - Оновити paths в конфігурації

4. **Створення власного `requirements.txt`:**
   - pandas, numpy
   - openpyxl (для Excel)
   - інші залежності

---

### 2.2 Методологія Cross-Market коефіцієнтів субституції

**Основне питання дослідження:**
> Чи препарат зберігає тенденцію замінюваності/незамінюваності на всіх локальних ринках?

**Кластеризація за MARKET_COVERAGE:**

| Кластер | Coverage | Опис | Рівень впевненості |
|---------|----------|------|-------------------|
| A | 100% | Препарат присутній на всіх ринках | Найвищий |
| B | 90-99% | Майже всі ринки | Високий |
| C | 60-89% | Більшість ринків | Середній |
| D | <60% | Менше половини ринків | Низький |

**Метрики консистентності:**

1. **Weighted Average SHARE_INTERNAL:**
   - Зважений середній по всіх ринках
   - Вага = розмір ринку (MARKET_TOTAL) або кількість stock-out подій

2. **Consistency Score:**
   - Variance або Standard Deviation SHARE_INTERNAL по ринках
   - Низька variance = консистентний препарат

3. **Confidence Interval:**
   - 95% CI для SHARE_INTERNAL
   - Вузький CI = надійна оцінка

4. **Classification Stability:**
   - % ринків з однаковою класифікацією (CRITICAL/SUBSTITUTABLE)
   - ≥80% = стабільна класифікація

**Вихідні метрики Phase 2:**

| Метрика | Опис |
|---------|------|
| `DRUGS_ID` | ID препарату |
| `MARKET_COVERAGE` | % ринків, де препарат досліджувався |
| `COVERAGE_CLUSTER` | A/B/C/D |
| `AVG_SHARE_INTERNAL` | Середня частка внутрішньої субституції |
| `WEIGHTED_AVG_SHARE_INTERNAL` | Зважена середня |
| `STD_SHARE_INTERNAL` | Стандартне відхилення |
| `CI_LOWER`, `CI_UPPER` | 95% Confidence Interval |
| `CLASSIFICATION_MODE` | Найчастіша класифікація |
| `CLASSIFICATION_STABILITY` | % ринків з однаковою класифікацією |
| `CROSS_MARKET_CLASS` | Фінальна cross-market класифікація |
| `CONFIDENCE_LEVEL` | HIGH/MEDIUM/LOW |

---

### 2.3 Тестування та очищення

**Послідовність:**

1. **Тестування на 5 поточних ринках:**
   - Запустити повний pipeline
   - Верифікувати результати
   - Протестувати cross-market агрегацію

2. **Очищення вихідних файлів:**
   - Видалити всі `data/processed_data/`
   - Видалити всі `results/`
   - Залишити тільки `data/raw/` (або видалити, якщо нові дані)

3. **Підготовка до масового запуску:**
   - Завантажити дані 90+ аптек
   - Перевірити формат та якість даних
   - Запустити preprocessing

---

## ЧЕКЛИСТ ВИКОНАННЯ

### Фаза 1

- [x] **Верифікація Step 1:** Data Aggregation (31.01.2026 — формули ідентичні)
- [x] **Верифікація Step 2:** Stockout Detection (31.01.2026 — виправлено Level 1 валідацію)
- [x] **Верифікація Step 3:** DiD Analysis (31.01.2026 — виправлено MARKET_GROWTH)
- [x] **Верифікація Step 4:** Substitute Analysis (31.01.2026 — додано INN_ID/INN_NAME)
- [x] **Верифікація Step 5:** Reports Generation (31.01.2026 — виправлено AGG_SHARE)
- [x] **Документація:** 00_PIPELINE_PHASE_1.md (створено в `01_did_processing/`)
- [x] **Документація:** 03_DID_NFC_ANALYSIS.md (створено, оновлено MARKET_GROWTH)
- [x] **Документація:** 02_DATA_DICTIONARY.md (створено в `03_project_instructions/`)
- [ ] **Автоматизація:** run_full_pipeline.py
- [ ] **Автоматизація:** input validation
- [ ] **Автоматизація:** logging system

### Фаза 2

- [ ] Перенесення проекту в `/substitution_coeff_research`
- [ ] Видалення залежностей від med_prod_research
- [ ] Створення requirements.txt
- [ ] Розробка cross-market aggregation script
- [ ] Розробка метрик консистентності
- [x] **Тестування на 5 ринках** (31.01.2026 — pipeline працює коректно)
- [ ] Очищення вихідних файлів
- [ ] Запуск на 90+ ринках

---

## ОЦІНКА РИЗИКІВ

| Ризик | Вплив | Мітигація |
|-------|-------|-----------|
| Невідповідність формул | Високий | Детальна верифікація з notebooks |
| Відсутність даних для деяких ринків | Середній | Валідація вхідних даних |
| Низька coverage для препаратів | Середній | Кластеризація за coverage |
| Помилки при масовому запуску | Високий | Batch processing з error recovery |

---

## НАВІГАЦІЯ

| Ресурс | Шлях |
|--------|------|
| Оригінальний проект | `/Users/radyslav/data_analysis/proxima/med_prod_research` |
| Поточний проект | `/Users/radyslav/data_analysis/proxima/med_prod_research/mass_market_analysis_test` |
| Work History | `docs/_project_history/00_WORK_HISTORY.md` |
| Project Map | `docs/00_ai_rules/03_PROJECT_MAP.md` |
| Оригінальна документація | `/Users/radyslav/data_analysis/proxima/med_prod_research/docs/01_tech_description/` |
