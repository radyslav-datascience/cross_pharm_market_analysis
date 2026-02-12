# Асинхронні обчислення — cross_pharm_market_analysis

> Документ описує підхід до паралельного виконання пайплайну обробки фармацевтичних ринків.

---

## 1. Передумови

Пайплайн Phase 1 (DID Processing) обробляє кожен ринок **незалежно** один від одного:
- Step 2 (Aggregation), Step 3 (Stockout), Step 4 (DID), Step 5 (Substitute), Step 6 (Reports)

**Виняток:** Step 1 (Preprocessing) та фінальна агрегація — виконуються один раз для всіх ринків.

Це означає, що Steps 2–6 можна виконувати **паралельно** для різних ринків без конфліктів.

---

## 2. Поточний стан

| Характеристика | Значення |
|---|---|
| Тип виконання | Послідовний (sequential) |
| Час на 99 ринків | ~125 хв (оцінка) |
| Найповільніший крок | Step 5 — Substitute Analysis (~99 хв) |
| Другий за повільністю | Step 2 — Data Aggregation (~26 хв) |

---

## 3. Цільова архітектура

### 3.1. Модель паралелізму

```
ProcessPoolExecutor (concurrent.futures)
├── Worker 1: process_full_market(market_A)
├── Worker 2: process_full_market(market_B)
├── Worker 3: process_full_market(market_C)
├── Worker 4: process_full_market(market_D)
└── Worker 5: process_full_market(market_E)
```

### 3.2. Чому ProcessPoolExecutor?

| Альтернатива | Оцінка |
|---|---|
| `threading` | ❌ GIL блокує CPU-bound обчислення |
| `multiprocessing.Pool` | ⚠️ Працює, але менш зручний API |
| `ProcessPoolExecutor` | ✅ Чистий API, timeout per task, futures |
| `asyncio` | ❌ Для I/O-bound, не для CPU-bound pandas |
| `dask` / `ray` | ❌ Зайвий overhead для 99 задач |

### 3.3. Функція process_full_market()

Ключова одиниця роботи — обробка **одного ринку**:

```
process_full_market(client_id: int) -> dict
    │
    ├── Step 2: data_aggregation(client_id)
    ├── Step 3: stockout_detection(client_id)
    ├── Step 4: did_analysis(client_id)
    ├── Step 5: substitute_analysis(client_id)
    └── Step 6: reports(client_id)
    │
    └── return {"client_id": client_id, "status": "success", "time": elapsed}
```

Кожен worker обробляє свій ринок повністю (Steps 2–6), читаючи дані з `data/processed_data/00_preproc_results/` та записуючи результати в `results/`.

---

## 4. Безпека паралельних операцій

### 4.1. Файлова ізоляція

Кожен ринок працює зі своїми файлами:
- Вхід: `data/raw/Rd2_{client_id}.csv`
- Проміжні: `data/processed_data/01_per_market/{client_id}/`
- Вихід: `results/cross_market_data/cross_market_{client_id}.csv`

**Ніякі два workers не пишуть в один файл** → немає конфліктів запису.

### 4.2. Спільні ресурси (тільки на читання)

Файли, які читаються **всіма workers**, але не змінюються:
- `data/processed_data/00_preproc_results/drugs_list.csv`
- `data/processed_data/00_preproc_results/inn_list.csv`
- Конфігурації з `project_core/`

Read-only доступ не потребує синхронізації.

### 4.3. Потенційні ризики

| Ризик | Мітігація |
|---|---|
| OOM (Out of Memory) | `RAM_PER_WORKER_GB` × `MAX_WORKERS` ≤ `AVAILABLE_RAM_GB` |
| Один ринок зависає | `MARKET_TIMEOUT_SEC` у конфігурації |
| Ринок падає з помилкою | try/except → лог помилки → продовжуємо інші |
| Лог-файли конфліктують | Кожен worker пише в свій лог або використовує queue logging |

---

## 5. Очікуваний приріст продуктивності

### 5.1. Теоретичний максимум

При 5 workers і ідеальному розподілі:
- Час = (Total Sequential Time) / 5
- ~125 хв / 5 = **~25 хв**

### 5.2. Реалістична оцінка

З урахуванням overhead на fork/join, I/O, дисбалансу навантаження:
- Очікуваний speedup: **3.5–4.5×**
- Очікуваний час: **28–35 хв** (для 99 ринків)
- З оптимізацією Step 5 (vectorization): **15–20 хв**

### 5.3. Комбінований ефект оптимізацій

| Оптимізація | Speedup | Час (99 ринків) |
|---|---|---|
| Без змін (baseline) | 1× | ~125 хв |
| Тільки parallelization (5 workers) | ~4× | ~30 хв |
| Тільки vectorization Step 5 | ~3× | ~40 хв |
| Parallelization + vectorization | ~10–12× | **~10–12 хв** |

---

## 6. Структура запуску

### 6.1. Повний пайплайн

```
run_full_pipeline.py
│
├── Step 1: Preprocessing (sequential, один раз)
│       ↓
├── Steps 2–6: ProcessPoolExecutor
│       ├── market_1 → process_full_market(market_1)
│       ├── market_2 → process_full_market(market_2)
│       ├── ...
│       └── market_N → process_full_market(market_N)
│       ↓
└── Step 7: Data Preparation for Phase 2 (sequential, один раз)
```

### 6.2. Аргументи CLI

```
python run_full_pipeline.py                     # Повний запуск
python run_full_pipeline.py --from-step 2       # З кроку 2
python run_full_pipeline.py --workers 3         # Обмежити workers
python run_full_pipeline.py --markets 28670,79021  # Тільки конкретні ринки
```

---

## 7. Обробка помилок

Стратегія: **fail-safe per market** — якщо один ринок падає, інші продовжують.

```
results = {
    "success": [(28670, 12.3s), (79021, 8.7s), ...],
    "failed":  [(99617, "KeyError: 'zero_weeks'"), ...],
    "timeout": [(12345, "Exceeded 600s"), ...]
}
```

Фінальний звіт у консолі:
```
Pipeline completed: 96/99 success, 2 failed, 1 timeout
Total time: 14 min 32 sec
Failed markets: [99617, 12345, 88888]
```

---

## 8. Конфігурація

Всі параметри паралелізму знаходяться у:

**`project_core/calculation_parameters_config/machine_parameters.py`**

| Параметр | Поточне значення | Опис |
|---|---|---|
| `MAX_WORKERS` | 5 | Максимум workers |
| `CPU_PHYSICAL_CORES` | 6 | Фізичні ядра |
| `AVAILABLE_RAM_GB` | 12 | Доступна RAM |
| `RAM_PER_WORKER_GB` | 0.5 | Пік RAM на worker |
| `MARKET_TIMEOUT_SEC` | 600 | Таймаут на ринок |
| `OPTIMAL_WORKERS` | auto | Розрахунок через `get_optimal_workers()` |

Документація параметрів: `docs/_project_tech_parameters/_computing_machine_parameters.md`

---

## 9. Порядок імплементації

1. ✅ Створити `machine_parameters.py` конфігурацію
2. ✅ Документація (цей файл + `_computing_machine_parameters.md`)
3. ⏳ Оптимізувати Step 5 (vectorize LIFT calculation)
4. ⏳ Оптимізувати Step 2 (vectorize `fill_gaps`)
5. ⏳ Створити `process_full_market()` функцію
6. ⏳ Переписати `run_full_pipeline.py` з `ProcessPoolExecutor`
7. ⏳ Тест на 20 ринках, порівняння з еталоном
