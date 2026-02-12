# =============================================================================
# FULL PIPELINE RUNNER - cross_pharm_market_analysis
# =============================================================================
# Файл: exec_scripts/run_full_pipeline.py
# Дата: 2026-02-12
# Опис: Запуск повного пайплайну з підтримкою паралельного виконання
# =============================================================================

"""
Автоматизований запуск повного пайплайну дослідження.

Порядок виконання:
    Phase 1 — Per-Market DiD Processing:
        Step 0: Preprocessing (довідники, списки INN/NFC/аптек) — ПОСЛІДОВНО
        Steps 1-5: Per-market обробка — ПАРАЛЕЛЬНО (ProcessPoolExecutor)
            Step 1: Data Aggregation (тижнева агрегація per market)
            Step 2: Stockout Detection (виявлення стокаутів)
            Step 3: DiD Analysis (Difference-in-Differences)
            Step 4: Substitute Analysis (частки субститутів)
            Step 5: Reports & Cross-Market Export (звіти + cross_market CSV)

    Phase 2 — Cross-Market Aggregation:
        Step 6: Data Preparation (коефіцієнти субституції) — ПОСЛІДОВНО

Використання:
    # Повний пайплайн (всі кроки, паралельно):
    python exec_scripts/run_full_pipeline.py

    # Послідовне виконання (для дебагу):
    python exec_scripts/run_full_pipeline.py --sequential

    # З певного кроку:
    python exec_scripts/run_full_pipeline.py --from-step 3

    # Задати кількість workers:
    python exec_scripts/run_full_pipeline.py --workers 3

    # Тільки Phase 2 (якщо Phase 1 вже виконано):
    python exec_scripts/run_full_pipeline.py --from-step 7

Примітки:
    - Перед запуском помістіть raw-файли (Rd2_*.csv) в data/raw/
    - Step 0 (preprocessing) завжди виконується послідовно
    - Steps 1-5 виконуються паралельно для кожного ринку
    - Step 6 (Phase 2) виконується послідовно після Steps 1-5
    - При помилці на preprocessing пайплайн зупиняється
    - Помилка одного ринку в Steps 1-5 не зупиняє решту
"""

import sys
import subprocess
import time
import argparse
from pathlib import Path
from datetime import datetime


# =============================================================================
# PATHS
# =============================================================================

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent

PHASE1_DIR = SCRIPT_DIR / "01_did_processing"
PHASE2_DIR = SCRIPT_DIR / "02_substitution_coefficients"

RAW_DATA_PATH = PROJECT_ROOT / "data" / "raw"
RAW_FILE_PATTERN = "Rd2_*.csv"

# Додаємо project root до sys.path
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


# =============================================================================
# PIPELINE DEFINITION
# =============================================================================

# Послідовні кроки (preprocessing + Phase 2)
SEQUENTIAL_STEPS = {
    0: {
        "name": "Preprocessing",
        "script": PHASE1_DIR / "01_preproc.py",
        "args": [],
        "description": "Довідники: INN, NFC, drugs, аптеки, статистика ринків",
    },
    7: {
        "name": "Data Preparation (Coefficients)",
        "script": PHASE2_DIR / "01_data_preparation.py",
        "args": [],
        "description": "Коефіцієнти субституції (трикутна матриця, xlsx бізнес-звіт)",
    },
}

# Per-market кроки (для послідовного fallback)
SEQUENTIAL_MARKET_STEPS = {
    1: {"name": "Data Aggregation", "script": PHASE1_DIR / "02_01_data_aggregation.py", "args": ["--all"]},
    2: {"name": "Stockout Detection", "script": PHASE1_DIR / "02_02_stockout_detection.py", "args": ["--all"]},
    3: {"name": "DiD Analysis", "script": PHASE1_DIR / "02_03_did_analysis.py", "args": ["--all"]},
    4: {"name": "Substitute Analysis", "script": PHASE1_DIR / "02_04_substitute_analysis.py", "args": ["--all"]},
    5: {"name": "Reports & Cross-Market", "script": PHASE1_DIR / "02_05_reports_cross_market.py", "args": ["--all"]},
}

# Per-market кроки для паралельного виконання
PER_MARKET_STEPS = [1, 2, 3, 4, 5]


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def check_raw_data() -> int:
    """Перевірити наявність raw-файлів. Повертає кількість знайдених."""
    raw_files = sorted(RAW_DATA_PATH.glob(RAW_FILE_PATTERN))
    return len(raw_files)


def format_time(seconds: float) -> str:
    """Форматувати час у читабельний рядок."""
    if seconds < 60:
        return f"{seconds:.1f}s"
    minutes = int(seconds // 60)
    secs = seconds % 60
    return f"{minutes}m {secs:.1f}s"


def run_sequential_step(step_info: dict, python_exe: str) -> bool:
    """
    Запустити один послідовний крок пайплайну.

    Returns:
        True якщо крок завершився успішно.
    """
    name = step_info["name"]
    script = step_info["script"]
    args = step_info["args"]
    description = step_info["description"]

    print()
    print("=" * 70)
    print(f"  {name}")
    print(f"  {description}")
    print(f"  Script: {script.relative_to(PROJECT_ROOT)}")
    print(f"  Started: {datetime.now().strftime('%H:%M:%S')}")
    print("=" * 70)

    if not script.exists():
        print(f"  [ERROR] Script not found: {script}")
        return False

    cmd = [python_exe, str(script)] + args

    try:
        result = subprocess.run(
            cmd,
            cwd=str(PROJECT_ROOT),
            check=False,
        )

        if result.returncode != 0:
            print(f"\n  [FAILED] {name} — exit code {result.returncode}")
            return False

        print(f"\n  [OK] {name} — completed successfully")
        return True

    except Exception as e:
        print(f"\n  [ERROR] {name}: {e}")
        return False


# =============================================================================
# PIPELINE EXECUTION
# =============================================================================

def run_pipeline(
    from_step: int = 1,
    parallel: bool = True,
    max_workers: int = None
) -> bool:
    """
    Запустити повний пайплайн.

    Args:
        from_step: Номер кроку з якого починати (1-7).
        parallel: Використовувати паралельне виконання для Steps 1-5.
        max_workers: Кількість workers (None = auto).

    Returns:
        True якщо всі кроки завершились успішно.
    """
    python_exe = sys.executable
    mode_str = "PARALLEL" if parallel else "SEQUENTIAL"

    print()
    print("#" * 70)
    print("#" + " " * 68 + "#")
    print("#   CROSS-PHARM MARKET ANALYSIS — FULL PIPELINE" + " " * 20 + "#")
    print(f"#   Mode: {mode_str:<58}#")
    print("#" + " " * 68 + "#")
    print("#" * 70)
    print()
    print(f"  Started:      {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  Python:       {python_exe}")
    print(f"  Project root: {PROJECT_ROOT}")

    # Перевірка raw-даних
    raw_count = check_raw_data()
    print(f"  Raw files:    {raw_count} (in data/raw/)")

    if raw_count == 0:
        print("\n  [ERROR] No raw data files found (Rd2_*.csv)!")
        print(f"  Place raw files in: {RAW_DATA_PATH}")
        return False

    pipeline_start = time.time()
    step_timings = []

    # =====================================================
    # STEP 0: Preprocessing (завжди послідовно)
    # =====================================================
    if from_step <= 1:
        step_start = time.time()
        success = run_sequential_step(SEQUENTIAL_STEPS[0], python_exe)
        elapsed = time.time() - step_start
        step_timings.append(("Step 0: Preprocessing", elapsed, success))

        if not success:
            print("\n  [CRITICAL] Preprocessing failed. Pipeline stopped.")
            return False

    # =====================================================
    # STEPS 1-5: Per-market processing
    # =====================================================
    per_market_steps_to_run = [s for s in PER_MARKET_STEPS if s >= from_step and s <= 5]

    if per_market_steps_to_run:
        if from_step > 1 and from_step <= 5:
            print(f"\n  [INFO] Starting per-market processing from Step {from_step}")

        step_start = time.time()

        if parallel:
            # === ПАРАЛЕЛЬНЕ ВИКОНАННЯ ===
            from project_core.utility_functions.parallel_runner import run_markets_parallel
            from project_core.data_config.paths_config import load_target_pharmacies

            try:
                target_pharmacies = load_target_pharmacies()
            except FileNotFoundError as e:
                print(f"\n  [ERROR] {e}")
                print("  Run preprocessing first: python exec_scripts/run_full_pipeline.py --from-step 1")
                return False

            summary = run_markets_parallel(
                market_ids=target_pharmacies,
                steps=per_market_steps_to_run,
                max_workers=max_workers,
                show_progress=True
            )

            elapsed = time.time() - step_start
            steps_label = f"Steps {per_market_steps_to_run[0]}-{per_market_steps_to_run[-1]}"
            step_timings.append((
                f"{steps_label} (parallel, {summary['max_workers']}w, {summary['successful_count']}/{summary['total_markets']} ok)",
                elapsed,
                summary['failed_count'] == 0
            ))

            if summary['failed_count'] > 0:
                print(f"\n  [WARNING] {summary['failed_count']} markets failed")
                print("  Phase 2 will proceed with available data.")

        else:
            # === ПОСЛІДОВНЕ ВИКОНАННЯ (legacy / debug mode) ===
            for step_num in per_market_steps_to_run:
                step_info = SEQUENTIAL_MARKET_STEPS[step_num]
                ss = time.time()
                success = run_sequential_step({
                    "name": f"Step {step_num}: {step_info['name']}",
                    "script": step_info["script"],
                    "args": step_info["args"],
                    "description": step_info["name"],
                }, python_exe)
                se = time.time() - ss
                step_timings.append((f"Step {step_num}: {step_info['name']}", se, success))

                if not success:
                    print(f"\n  [FAILED] Pipeline stopped at Step {step_num}")
                    print(f"  Fix and re-run with: --from-step {step_num}")
                    return False

    # =====================================================
    # STEP 7: Phase 2 — Data Preparation (послідовно)
    # =====================================================
    if from_step <= 7:
        step_start = time.time()
        success = run_sequential_step(SEQUENTIAL_STEPS[7], python_exe)
        elapsed = time.time() - step_start
        step_timings.append(("Step 7: Phase 2 Data Preparation", elapsed, success))

        if not success:
            print("\n  [WARNING] Phase 2 (Data Preparation) failed")

    # =====================================================
    # ПІДСУМОК
    # =====================================================
    pipeline_elapsed = time.time() - pipeline_start

    print()
    print()
    print("#" * 70)
    print("#   PIPELINE COMPLETED" + " " * 47 + "#")
    print("#" * 70)
    print()
    print(f"  Finished: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  Total time: {format_time(pipeline_elapsed)}")
    print()
    print("  Step timings:")
    for name, elapsed, success in step_timings:
        status = "OK" if success else "FAILED"
        print(f"    {name:<55} {format_time(elapsed):>8}  [{status}]")
    print()
    print("  Output locations:")
    print(f"    Per-market data:   data/processed_data/01_per_market/")
    print(f"    Market reports:    results/data_reports/")
    print(f"    Cross-market data: results/cross_market_data/market_substitution_*/")
    print(f"    Coefficients:      results/substitution_research/01_preparation/")
    print()

    all_success = all(s for _, _, s in step_timings)
    return all_success


# =============================================================================
# CLI
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Run full analysis pipeline (Phase 1 + Phase 2)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Steps:
  1  Preprocessing          — довідники INN/NFC/drugs/аптеки
  2  Data Aggregation       — тижнева агрегація per market  
  3  Stockout Detection     — виявлення стокаут-подій
  4  DiD Analysis           — Difference-in-Differences
  5  Substitute Analysis    — частки субститутів
  6  Reports & Export       — Excel-звіти + cross_market CSV
  7  Data Preparation       — коефіцієнти субституції (Phase 2)

Modes:
  Default (parallel):   Steps 1-5 run in parallel via ProcessPoolExecutor
  --sequential:         All steps run sequentially (legacy mode, for debugging)

Examples:
  python exec_scripts/run_full_pipeline.py              # Full pipeline, parallel
  python exec_scripts/run_full_pipeline.py --sequential  # Full pipeline, sequential
  python exec_scripts/run_full_pipeline.py --from-step 3  # From stockout detection
  python exec_scripts/run_full_pipeline.py --workers 3    # Limit parallel workers
  python exec_scripts/run_full_pipeline.py --from-step 7  # Phase 2 only
        """
    )

    parser.add_argument(
        '--from-step',
        type=int,
        default=1,
        choices=range(1, 8),
        metavar='N',
        help='Start from step N (1-7). Default: 1 (full pipeline)'
    )

    parser.add_argument(
        '--sequential',
        action='store_true',
        help='Run all steps sequentially (disable parallel execution)'
    )

    parser.add_argument(
        '--workers', '-w',
        type=int,
        default=None,
        metavar='N',
        help='Number of parallel workers (default: auto from machine_parameters)'
    )

    args = parser.parse_args()

    parallel = not args.sequential
    success = run_pipeline(
        from_step=args.from_step,
        parallel=parallel,
        max_workers=args.workers
    )
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
