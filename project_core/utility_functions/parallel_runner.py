# =============================================================================
# PARALLEL RUNNER - cross_pharm_market_analysis
# =============================================================================
# Файл: project_core/utility_functions/parallel_runner.py
# Дата: 2026-02-12
# Опис: Модуль паралельного виконання per-market обробки через ProcessPoolExecutor
# =============================================================================

"""
Паралельний runner для обробки локальних ринків.

Архітектура:
    - ProcessPoolExecutor (окремі процеси, GIL-free для CPU-bound задач)
    - Кожен worker обробляє один повний ринок (Steps 1-5)
    - Контроль пам'яті: обмеження по кількості workers через machine_parameters
    - Fail-safe: помилка одного ринку не зупиняє решту

Використання:
    from project_core.utility_functions.parallel_runner import (
        run_markets_parallel,
        process_single_market_pipeline
    )

    results = run_markets_parallel(
        market_ids=[28670, 28753, 79021],
        steps=[1, 2, 3, 4, 5]
    )

Документація:
    docs/_project_tech_parameters/_asynchronous_computing.md
"""

import sys
import time
import traceback
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional, Callable, Tuple
from concurrent.futures import ProcessPoolExecutor, as_completed, TimeoutError

# Додаємо project root до sys.path
_CURRENT_FILE = Path(__file__).resolve()
PROJECT_ROOT = _CURRENT_FILE.parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


# =============================================================================
# MARKET PROCESSING FUNCTIONS (виконуються у worker-процесах)
# =============================================================================

def process_single_market_pipeline(
    client_id: int,
    steps: Optional[List[int]] = None
) -> Dict[str, Any]:
    """
    Обробка одного ринку через повний пайплайн (Steps 1-5).

    Виконується в окремому процесі. Імпорти всередині функції
    для коректної серіалізації через ProcessPoolExecutor.

    Args:
        client_id: ID цільової аптеки
        steps: Список кроків для виконання (1-5). None = всі.

    Returns:
        Dict з результатами обробки:
            - client_id: ID ринку
            - status: 'success' | 'error'
            - steps_completed: список завершених кроків
            - elapsed_seconds: час обробки
            - error: опис помилки (якщо status='error')
            - step_times: час кожного кроку
    """
    if steps is None:
        steps = [1, 2, 3, 4, 5]

    start_time = time.time()
    result = {
        'client_id': client_id,
        'status': 'success',
        'steps_completed': [],
        'step_times': {},
        'elapsed_seconds': 0,
        'error': None
    }

    # Імпорти всередині worker-процесу (після fork)
    import sys
    from pathlib import Path
    _project_root = Path(__file__).resolve().parent.parent.parent
    if str(_project_root) not in sys.path:
        sys.path.insert(0, str(_project_root))

    # Імпорт exec_scripts (шляхи до скриптів додаємо для коректної роботи)
    _exec_did_path = str(_project_root / "exec_scripts" / "01_did_processing")
    _exec_sub_path = str(_project_root / "exec_scripts" / "02_substitution_coefficients")
    if _exec_did_path not in sys.path:
        sys.path.insert(0, _exec_did_path)
    if _exec_sub_path not in sys.path:
        sys.path.insert(0, _exec_sub_path)

    try:
        # === Step 1: Data Aggregation ===
        if 1 in steps:
            step_start = time.time()
            # Імпортуємо модуль напряму з exec_scripts
            import importlib
            step1 = importlib.import_module('02_01_data_aggregation')
            step1.process_market(client_id)
            result['steps_completed'].append(1)
            result['step_times'][1] = round(time.time() - step_start, 2)

        # === Step 2: Stockout Detection ===
        if 2 in steps:
            step_start = time.time()
            step2 = importlib.import_module('02_02_stockout_detection')
            step2.process_market_stockout(client_id)
            result['steps_completed'].append(2)
            result['step_times'][2] = round(time.time() - step_start, 2)

        # === Step 3: DiD Analysis ===
        if 3 in steps:
            step_start = time.time()
            step3 = importlib.import_module('02_03_did_analysis')
            step3.process_market_did(client_id)
            result['steps_completed'].append(3)
            result['step_times'][3] = round(time.time() - step_start, 2)

        # === Step 4: Substitute Analysis ===
        if 4 in steps:
            step_start = time.time()
            step4 = importlib.import_module('02_04_substitute_analysis')
            step4.process_market(client_id)
            result['steps_completed'].append(4)
            result['step_times'][4] = round(time.time() - step_start, 2)

        # === Step 5: Reports & Cross-Market ===
        if 5 in steps:
            step_start = time.time()
            step5 = importlib.import_module('02_05_reports_cross_market')
            step5.process_market(client_id)
            result['steps_completed'].append(5)
            result['step_times'][5] = round(time.time() - step_start, 2)

    except Exception as e:
        result['status'] = 'error'
        result['error'] = f"{type(e).__name__}: {e}"
        # Додаємо traceback для дебагу
        result['traceback'] = traceback.format_exc()

    result['elapsed_seconds'] = round(time.time() - start_time, 2)
    return result


def _process_market_wrapper(args: Tuple) -> Dict[str, Any]:
    """
    Wrapper для ProcessPoolExecutor.map() — розпаковує аргументи.

    Args:
        args: Tuple (client_id, steps)

    Returns:
        Dict з результатами
    """
    client_id, steps = args
    return process_single_market_pipeline(client_id, steps)


# =============================================================================
# PARALLEL EXECUTION ENGINE
# =============================================================================

def run_markets_parallel(
    market_ids: List[int],
    steps: Optional[List[int]] = None,
    max_workers: Optional[int] = None,
    timeout_per_market: Optional[int] = None,
    show_progress: bool = True
) -> Dict[str, Any]:
    """
    Паралельна обробка списку ринків через ProcessPoolExecutor.

    Args:
        market_ids: Список ID цільових аптек
        steps: Кроки пайплайну для виконання (1-5). None = всі.
        max_workers: Кількість паралельних процесів.
                     None = auto (з machine_parameters).
        timeout_per_market: Таймаут на один ринок (секунди).
                           None = auto (з machine_parameters).
        show_progress: Показувати прогрес

    Returns:
        Dict з результатами:
            - successful: список успішних результатів
            - failed: список помилок
            - total_time: загальний час
            - markets_per_second: середня швидкість
    """
    if steps is None:
        steps = [1, 2, 3, 4, 5]

    # Завантажуємо параметри машини
    from project_core.calculation_parameters_config.machine_parameters import (
        OPTIMAL_WORKERS, MARKET_TIMEOUT_SEC
    )

    if max_workers is None:
        max_workers = OPTIMAL_WORKERS
    if timeout_per_market is None:
        timeout_per_market = MARKET_TIMEOUT_SEC

    total_markets = len(market_ids)

    if show_progress:
        print()
        print("=" * 70)
        print("  PARALLEL PIPELINE EXECUTION")
        print("=" * 70)
        print(f"  Markets:     {total_markets}")
        print(f"  Workers:     {max_workers}")
        print(f"  Steps:       {steps}")
        print(f"  Timeout:     {timeout_per_market}s per market")
        print(f"  Started:     {datetime.now().strftime('%H:%M:%S')}")
        print("=" * 70)

    pipeline_start = time.time()
    successful = []
    failed = []

    # Підготовка аргументів для workers
    tasks = [(cid, steps) for cid in market_ids]

    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        # Submit всі задачі
        future_to_market = {}
        for client_id, step_list in tasks:
            future = executor.submit(process_single_market_pipeline, client_id, step_list)
            future_to_market[future] = client_id

        # Збираємо результати по мірі завершення
        completed = 0
        for future in as_completed(future_to_market):
            client_id = future_to_market[future]
            completed += 1

            try:
                result = future.result(timeout=timeout_per_market)

                if result['status'] == 'success':
                    successful.append(result)
                    status_str = f"OK ({result['elapsed_seconds']:.1f}s)"
                else:
                    failed.append(result)
                    status_str = f"FAILED: {result['error']}"

            except TimeoutError:
                failed.append({
                    'client_id': client_id,
                    'status': 'error',
                    'error': f'Timeout after {timeout_per_market}s',
                    'elapsed_seconds': timeout_per_market,
                    'steps_completed': [],
                    'step_times': {}
                })
                status_str = f"TIMEOUT ({timeout_per_market}s)"

            except Exception as e:
                failed.append({
                    'client_id': client_id,
                    'status': 'error',
                    'error': f'{type(e).__name__}: {e}',
                    'elapsed_seconds': 0,
                    'steps_completed': [],
                    'step_times': {}
                })
                status_str = f"ERROR: {type(e).__name__}"

            if show_progress:
                print(f"  [{completed}/{total_markets}] Market {client_id}: {status_str}")

    pipeline_elapsed = time.time() - pipeline_start

    # Підсумок
    summary = {
        'successful': successful,
        'failed': failed,
        'total_markets': total_markets,
        'successful_count': len(successful),
        'failed_count': len(failed),
        'total_time': round(pipeline_elapsed, 2),
        'markets_per_second': round(total_markets / pipeline_elapsed, 3) if pipeline_elapsed > 0 else 0,
        'max_workers': max_workers,
        'steps': steps
    }

    if show_progress:
        print()
        print("=" * 70)
        print("  PARALLEL EXECUTION COMPLETED")
        print("=" * 70)
        print(f"  Finished:      {datetime.now().strftime('%H:%M:%S')}")
        print(f"  Total time:    {_format_time(pipeline_elapsed)}")
        print(f"  Successful:    {len(successful)}/{total_markets}")
        print(f"  Failed:        {len(failed)}/{total_markets}")

        if successful:
            avg_time = sum(r['elapsed_seconds'] for r in successful) / len(successful)
            max_time = max(r['elapsed_seconds'] for r in successful)
            min_time = min(r['elapsed_seconds'] for r in successful)
            print(f"  Avg per market: {_format_time(avg_time)}")
            print(f"  Min / Max:     {_format_time(min_time)} / {_format_time(max_time)}")

            # Порівняння з послідовним виконанням
            sequential_estimate = sum(r['elapsed_seconds'] for r in successful)
            if sequential_estimate > 0:
                speedup = sequential_estimate / pipeline_elapsed
                print(f"  Sequential est: {_format_time(sequential_estimate)}")
                print(f"  Speedup:       {speedup:.1f}x")

        if failed:
            print(f"\n  FAILED MARKETS:")
            for r in failed:
                print(f"    {r['client_id']}: {r['error']}")

        print("=" * 70)

    return summary


def run_markets_sequential(
    market_ids: List[int],
    steps: Optional[List[int]] = None,
    show_progress: bool = True
) -> Dict[str, Any]:
    """
    Послідовна обробка списку ринків (fallback / benchmark).

    Використовує ту саму функцію process_single_market_pipeline,
    але без ProcessPoolExecutor — для дебагу та порівняння швидкості.

    Args:
        market_ids: Список ID цільових аптек
        steps: Кроки пайплайну (1-5). None = всі.
        show_progress: Показувати прогрес

    Returns:
        Dict з результатами (той самий формат що й run_markets_parallel)
    """
    if steps is None:
        steps = [1, 2, 3, 4, 5]

    total_markets = len(market_ids)

    if show_progress:
        print()
        print("=" * 70)
        print("  SEQUENTIAL PIPELINE EXECUTION")
        print("=" * 70)
        print(f"  Markets: {total_markets}")
        print(f"  Steps:   {steps}")
        print(f"  Started: {datetime.now().strftime('%H:%M:%S')}")
        print("=" * 70)

    pipeline_start = time.time()
    successful = []
    failed = []

    for i, client_id in enumerate(market_ids):
        result = process_single_market_pipeline(client_id, steps)

        if result['status'] == 'success':
            successful.append(result)
            status_str = f"OK ({result['elapsed_seconds']:.1f}s)"
        else:
            failed.append(result)
            status_str = f"FAILED: {result['error']}"

        if show_progress:
            print(f"  [{i+1}/{total_markets}] Market {client_id}: {status_str}")

    pipeline_elapsed = time.time() - pipeline_start

    summary = {
        'successful': successful,
        'failed': failed,
        'total_markets': total_markets,
        'successful_count': len(successful),
        'failed_count': len(failed),
        'total_time': round(pipeline_elapsed, 2),
        'markets_per_second': round(total_markets / pipeline_elapsed, 3) if pipeline_elapsed > 0 else 0,
        'max_workers': 1,
        'steps': steps
    }

    if show_progress:
        print()
        print(f"  Total time: {_format_time(pipeline_elapsed)}")
        print(f"  Successful: {len(successful)}/{total_markets}")
        if failed:
            print(f"  Failed: {len(failed)}")
        print("=" * 70)

    return summary


# =============================================================================
# UTILITIES
# =============================================================================

def _format_time(seconds: float) -> str:
    """Форматувати час у читабельний рядок."""
    if seconds < 60:
        return f"{seconds:.1f}s"
    minutes = int(seconds // 60)
    secs = seconds % 60
    return f"{minutes}m {secs:.1f}s"


# =============================================================================
# ТЕСТУВАННЯ
# =============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("PARALLEL RUNNER - cross_pharm_market_analysis")
    print("=" * 60)
    print()

    from project_core.calculation_parameters_config.machine_parameters import (
        OPTIMAL_WORKERS, MAX_WORKERS, CPU_PHYSICAL_CORES, AVAILABLE_RAM_GB
    )

    print(f"Machine parameters:")
    print(f"  CPU cores:     {CPU_PHYSICAL_CORES}")
    print(f"  Available RAM: {AVAILABLE_RAM_GB} GB")
    print(f"  Max workers:   {MAX_WORKERS}")
    print(f"  Optimal:       {OPTIMAL_WORKERS}")
    print()
    print("Ready for parallel execution!")
