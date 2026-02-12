# =============================================================================
# FULL PIPELINE RUNNER - cross_pharm_market_analysis
# =============================================================================
# Файл: exec_scripts/run_full_pipeline.py
# Дата: 2026-02-11
# Опис: Послідовний запуск всіх скриптів обробки даних (Phase 1 + Phase 2)
# =============================================================================

"""
Автоматизований запуск повного пайплайну дослідження.

Порядок виконання:
    Phase 1 — Per-Market DiD Processing:
        Step 0: Preprocessing (довідники, списки INN/NFC/аптек)
        Step 1: Data Aggregation (тижнева агрегація per market)
        Step 2: Stockout Detection (виявлення стокаутів)
        Step 3: DiD Analysis (Difference-in-Differences)
        Step 4: Substitute Analysis (частки субститутів)
        Step 5: Reports & Cross-Market Export (звіти + cross_market CSV)

    Phase 2 — Cross-Market Aggregation:
        Step 1: Data Preparation (коефіцієнти субституції)

Використання:
    # Повний пайплайн (всі кроки):
    python exec_scripts/run_full_pipeline.py

    # З певного кроку (пропустити вже виконані):
    python exec_scripts/run_full_pipeline.py --from-step 3

    # Тільки Phase 2 (якщо Phase 1 вже виконано):
    python exec_scripts/run_full_pipeline.py --from-step 7

Примітки:
    - Перед запуском помістіть raw-файли (Rd2_*.csv) в data/raw/
    - Кожен крок перевіряє наявність результатів попереднього кроку
    - При помилці на будь-якому кроці пайплайн зупиняється
    - Логи кожного кроку виводяться в реальному часі
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


# =============================================================================
# PIPELINE DEFINITION
# =============================================================================

PIPELINE_STEPS = [
    {
        "step": 1,
        "phase": 1,
        "name": "Preprocessing",
        "script": PHASE1_DIR / "01_preproc.py",
        "args": [],
        "description": "Довідники: INN, NFC, drugs, аптеки, статистика ринків",
    },
    {
        "step": 2,
        "phase": 1,
        "name": "Data Aggregation",
        "script": PHASE1_DIR / "02_01_data_aggregation.py",
        "args": ["--all"],
        "description": "Тижнева агрегація продажів per market",
    },
    {
        "step": 3,
        "phase": 1,
        "name": "Stockout Detection",
        "script": PHASE1_DIR / "02_02_stockout_detection.py",
        "args": ["--all"],
        "description": "Виявлення стокаут-подій (3-рівнева валідація)",
    },
    {
        "step": 4,
        "phase": 1,
        "name": "DiD Analysis",
        "script": PHASE1_DIR / "02_03_did_analysis.py",
        "args": ["--all"],
        "description": "Difference-in-Differences аналіз + класифікація препаратів",
    },
    {
        "step": 5,
        "phase": 1,
        "name": "Substitute Analysis",
        "script": PHASE1_DIR / "02_04_substitute_analysis.py",
        "args": ["--all"],
        "description": "Розрахунок часток субститутів (SUBSTITUTE_SHARE)",
    },
    {
        "step": 6,
        "phase": 1,
        "name": "Reports & Cross-Market Export",
        "script": PHASE1_DIR / "02_05_reports_cross_market.py",
        "args": ["--all"],
        "description": "Excel-звіти + cross_market CSV для Phase 2",
    },
    {
        "step": 7,
        "phase": 2,
        "name": "Data Preparation (Coefficients)",
        "script": PHASE2_DIR / "01_data_preparation.py",
        "args": [],
        "description": "Коефіцієнти субституції (трикутна матриця, xlsx бізнес-звіт)",
    },
]


# =============================================================================
# PIPELINE RUNNER
# =============================================================================

def check_raw_data() -> int:
    """Перевірити наявність raw-файлів. Повертає кількість знайдених."""
    raw_files = sorted(RAW_DATA_PATH.glob(RAW_FILE_PATTERN))
    return len(raw_files)


def run_step(step_info: dict, python_exe: str) -> bool:
    """
    Запустити один крок пайплайну.

    Returns:
        True якщо крок завершився успішно, False якщо помилка.
    """
    step_num = step_info["step"]
    phase = step_info["phase"]
    name = step_info["name"]
    script = step_info["script"]
    args = step_info["args"]
    description = step_info["description"]

    print()
    print("=" * 70)
    print(f"  STEP {step_num}/7 — Phase {phase}: {name}")
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
            print(f"\n  [FAILED] Step {step_num} ({name}) — exit code {result.returncode}")
            return False

        print(f"\n  [OK] Step {step_num} ({name}) — completed successfully")
        return True

    except Exception as e:
        print(f"\n  [ERROR] Step {step_num} ({name}): {e}")
        return False


def run_pipeline(from_step: int = 1) -> bool:
    """
    Запустити повний пайплайн починаючи з заданого кроку.

    Args:
        from_step: Номер кроку з якого починати (1-7).

    Returns:
        True якщо всі кроки завершились успішно.
    """
    python_exe = sys.executable
    total_steps = len(PIPELINE_STEPS)
    steps_to_run = [s for s in PIPELINE_STEPS if s["step"] >= from_step]

    print()
    print("#" * 70)
    print("#" + " " * 68 + "#")
    print("#   CROSS-PHARM MARKET ANALYSIS — FULL PIPELINE" + " " * 20 + "#")
    print("#" + " " * 68 + "#")
    print("#" * 70)
    print()
    print(f"  Started:      {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  Python:       {python_exe}")
    print(f"  Project root: {PROJECT_ROOT}")
    print(f"  Steps:        {from_step}–{total_steps} ({len(steps_to_run)} of {total_steps})")

    # Перевірка raw-даних
    raw_count = check_raw_data()
    print(f"  Raw files:    {raw_count} (in data/raw/)")

    if raw_count == 0:
        print("\n  [ERROR] No raw data files found (Rd2_*.csv)!")
        print(f"  Place raw files in: {RAW_DATA_PATH}")
        return False

    if from_step > 1:
        print(f"\n  [INFO] Skipping steps 1–{from_step - 1} (--from-step {from_step})")

    # Запуск кроків
    pipeline_start = time.time()
    step_times = []

    for step_info in steps_to_run:
        step_start = time.time()
        success = run_step(step_info, python_exe)
        step_elapsed = time.time() - step_start
        step_times.append((step_info["step"], step_info["name"], step_elapsed, success))

        if not success:
            print()
            print("!" * 70)
            print(f"  PIPELINE STOPPED at Step {step_info['step']} ({step_info['name']})")
            print(f"  Fix the issue and re-run with: --from-step {step_info['step']}")
            print("!" * 70)
            return False

    # Підсумок
    pipeline_elapsed = time.time() - pipeline_start

    print()
    print()
    print("#" * 70)
    print("#   PIPELINE COMPLETED SUCCESSFULLY" + " " * 33 + "#")
    print("#" * 70)
    print()
    print(f"  Finished: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  Total time: {format_time(pipeline_elapsed)}")
    print()
    print("  Step timings:")
    for step_num, name, elapsed, _ in step_times:
        print(f"    Step {step_num}. {name:<40} {format_time(elapsed)}")
    print()
    print("  Output locations:")
    print(f"    Per-market data:   data/processed_data/01_per_market/")
    print(f"    Market reports:    results/data_reports/")
    print(f"    Cross-market CSV:  results/cross_market_data/")
    print(f"    Coefficients:      results/substitution_research/01_preparation/")
    print(f"    Business reports:  results/substitution_research/01_preparation/prep_business_reports/")
    print()

    return True


def format_time(seconds: float) -> str:
    """Форматувати час у читабельний рядок."""
    if seconds < 60:
        return f"{seconds:.1f}s"
    minutes = int(seconds // 60)
    secs = seconds % 60
    return f"{minutes}m {secs:.1f}s"


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

Examples:
  python exec_scripts/run_full_pipeline.py              # Full pipeline
  python exec_scripts/run_full_pipeline.py --from-step 3  # From stockout detection
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

    args = parser.parse_args()
    success = run_pipeline(from_step=args.from_step)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
