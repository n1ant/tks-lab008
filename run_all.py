"""
Полный запуск лабораторной работы №8.

Последовательно выполняет:
1. Измерения пропускной способности.
2. Анализ результатов.
3. Построение графиков.

Перед запуском убедитесь, что:
- установлен Python 3;
- установлен matplotlib;
- доступна команда tc;
- для изменения сетевой задержки есть права root.
"""

import argparse
import os
import subprocess
import sys

from config import (
    BUFFER_SIZES,
    DELAY_VALUES_MS,
    REPETITIONS,
    RESULTS_DIR,
    RESULTS_CSV,
    FIGURES_DIR,
)


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


def run_script(script_name: str, args: list[str] | None = None) -> None:
    """
    Запускает Python-скрипт и завершает выполнение
    при ошибке.
    """
    command = [
        sys.executable,
        os.path.join(SCRIPT_DIR, script_name),
    ]

    if args:
        command.extend(args)

    print()
    print("=" * 70)
    print(f"Запуск: {script_name}")
    print("=" * 70)

    result = subprocess.run(command)

    if result.returncode != 0:
        raise RuntimeError(
            f"Скрипт {script_name} завершился "
            f"с кодом {result.returncode}."
        )


def prepare_directories() -> None:
    """Создаёт необходимые каталоги результатов."""
    os.makedirs(RESULTS_DIR, exist_ok=True)
    os.makedirs(FIGURES_DIR, exist_ok=True)


def print_experiment_summary() -> None:
    """Показывает объём предстоящего эксперимента."""
    total_measurements = (
        len(BUFFER_SIZES)
        * len(DELAY_VALUES_MS)
        * REPETITIONS
    )

    print()
    print("Параметры полного эксперимента:")
    print(f"  Размеров буфера: {len(BUFFER_SIZES)}")
    print(f"  Значений задержки: {len(DELAY_VALUES_MS)}")
    print(f"  Повторений: {REPETITIONS}")
    print(f"  Всего измерений: {total_measurements}")
    print()


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Полный запуск лабораторной работы №8"
        )
    )

    parser.add_argument(
        "--skip-experiment",
        action="store_true",
        help=(
            "Не выполнять измерения, "
            "использовать уже имеющиеся результаты"
        ),
    )

    parser.add_argument(
        "--skip-analysis",
        action="store_true",
        help=(
            "Не выполнять анализ, "
            "использовать существующий analysis.csv"
        ),
    )

    parser.add_argument(
        "--repetitions",
        type=int,
        default=None,
        help="Количество повторений одного измерения",
    )

    args = parser.parse_args()

    if args.repetitions is not None and args.repetitions <= 0:
        raise ValueError(
            "Количество повторений должно быть положительным."
        )

    prepare_directories()

    print("=" * 70)
    print("ЛАБОРАТОРНАЯ РАБОТА №8")
    print(
        "Исследование влияния размера TCP-буфера "
        "и задержки на пропускную способность"
    )
    print("=" * 70)

    print_experiment_summary()

    # ------------------------------------------------------------
    # Этап 1. Эксперимент
    # ------------------------------------------------------------

    if not args.skip_experiment:
        experiment_args = []

        if args.repetitions is not None:
            experiment_args.extend(
                [
                    "--repetitions",
                    str(args.repetitions),
                ]
            )

        run_script(
            "experiment.py",
            experiment_args,
        )
    else:
        print()
        print("Этап измерений пропущен.")

        if not os.path.exists(RESULTS_CSV):
            raise FileNotFoundError(
                f"Файл результатов не найден: {RESULTS_CSV}"
            )

    # ------------------------------------------------------------
    # Этап 2. Анализ
    # ------------------------------------------------------------

    if not args.skip_analysis:
        run_script("analysis.py")
    else:
        print()
        print("Этап анализа пропущен.")

    # ------------------------------------------------------------
    # Этап 3. Графики
    # ------------------------------------------------------------

    run_script("plots.py")

    # ------------------------------------------------------------
    # Завершение
    # ------------------------------------------------------------

    print()
    print("=" * 70)
    print("ЛАБОРАТОРНАЯ РАБОТА №8 ЗАВЕРШЕНА")
    print("=" * 70)

    print()
    print("Результаты:")
    print(f"  Измерения: {RESULTS_CSV}")
    print(f"  Анализ:    {RESULTS_DIR}/analysis.csv")
    print(f"  Графики:   {FIGURES_DIR}/")
    print()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print()
        print("Выполнение прервано пользователем.")
        sys.exit(130)
    except Exception as error:
        print()
        print(f"ОШИБКА: {error}")
        sys.exit(1)