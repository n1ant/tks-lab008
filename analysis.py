"""
Анализ результатов лабораторной работы №8.

Функции модуля:
    - загрузка сырых результатов из CSV;
    - группировка измерений;
    - расчёт среднего значения;
    - расчёт минимума и максимума;
    - расчёт стандартного отклонения;
    - расчёт BDP (bandwidth-delay product);
    - определение заметного снижения пропускной способности;
    - сохранение сводной таблицы.

Модуль не изменяет исходный CSV с сырыми измерениями.
"""

import argparse
import csv
import math
import os
from collections import defaultdict
from dataclasses import dataclass

from config import (
    RESULTS_CSV,
    RESULTS_DIR,
    format_bytes,
    format_delay,
)


# ---------------------------------------------------------------------------
# Структура результата
# ---------------------------------------------------------------------------

@dataclass
class AnalysisResult:
    """Сводный результат для одной комбинации буфера и задержки."""

    buffer_size: int
    delay_ms: int
    repetitions: int

    mean_mbps: float
    min_mbps: float
    max_mbps: float
    stddev_mbps: float

    bdp_bits: float
    bdp_bytes: float

    reduction_percent: float = 0.0


# ---------------------------------------------------------------------------
# Загрузка данных
# ---------------------------------------------------------------------------

def load_results(csv_path: str = RESULTS_CSV) -> list[dict]:
    """
    Загружает сырые результаты из CSV.
    """

    if not os.path.exists(csv_path):
        raise FileNotFoundError(
            f"Файл результатов не найден: {csv_path}"
        )

    with open(
        csv_path,
        "r",
        newline="",
        encoding="utf-8",
    ) as file:

        reader = csv.DictReader(file)

        rows = []

        for row in reader:
            rows.append(
                {
                    "buffer_size": int(row["buffer_size"]),
                    "delay_ms": int(row["delay_ms"]),
                    "data_size": int(row["data_size"]),
                    "elapsed_seconds": float(
                        row["elapsed_seconds"]
                    ),
                    "throughput_mbps": float(
                        row["throughput_mbps"]
                    ),
                }
            )

    if not rows:
        raise ValueError(
            "CSV-файл не содержит результатов измерений."
        )

    return rows


# ---------------------------------------------------------------------------
# Статистика
# ---------------------------------------------------------------------------

def mean(values: list[float]) -> float:
    """Среднее арифметическое."""
    if not values:
        return 0.0

    return sum(values) / len(values)


def standard_deviation(values: list[float]) -> float:
    """
    Выборочное стандартное отклонение.

    При одном измерении возвращается 0.
    """
    if len(values) <= 1:
        return 0.0

    average = mean(values)

    variance = sum(
        (value - average) ** 2
        for value in values
    ) / (len(values) - 1)

    return math.sqrt(variance)


def group_results(
    rows: list[dict],
) -> dict[tuple[int, int], list[float]]:
    """
    Группирует результаты по комбинации:

        размер буфера + задержка.
    """

    groups = defaultdict(list)

    for row in rows:
        key = (
            row["buffer_size"],
            row["delay_ms"],
        )

        groups[key].append(
            row["throughput_mbps"]
        )

    return dict(groups)


# ---------------------------------------------------------------------------
# Bandwidth-Delay Product
# ---------------------------------------------------------------------------

def calculate_bdp(
    throughput_mbps: float,
    delay_ms: float,
) -> tuple[float, float]:
    """
    Рассчитывает bandwidth-delay product.

    throughput_mbps:
        пропускная способность в Мбит/с.

    delay_ms:
        задержка в миллисекундах.

    Возвращает:
        (BDP в битах, BDP в байтах)
    """

    throughput_bits_per_second = (
        throughput_mbps * 1_000_000
    )

    delay_seconds = delay_ms / 1000

    bdp_bits = (
        throughput_bits_per_second
        * delay_seconds
    )

    bdp_bytes = bdp_bits / 8

    return bdp_bits, bdp_bytes


# ---------------------------------------------------------------------------
# Формирование сводных результатов
# ---------------------------------------------------------------------------

def create_analysis(
    rows: list[dict],
) -> list[AnalysisResult]:
    """
    Создаёт сводную статистику для всех комбинаций.
    """

    groups = group_results(rows)

    results = []

    # Сначала формируем статистику.
    for (buffer_size, delay_ms), values in sorted(
        groups.items()
    ):
        average = mean(values)

        bdp_bits, bdp_bytes = calculate_bdp(
            throughput_mbps=average,
            delay_ms=delay_ms,
        )

        result = AnalysisResult(
            buffer_size=buffer_size,
            delay_ms=delay_ms,
            repetitions=len(values),
            mean_mbps=average,
            min_mbps=min(values),
            max_mbps=max(values),
            stddev_mbps=standard_deviation(values),
            bdp_bits=bdp_bits,
            bdp_bytes=bdp_bytes,
        )

        results.append(result)

    # Рассчитываем снижение относительно максимальной
    # средней скорости при конкретной задержке.
    for delay_ms in sorted(
        {result.delay_ms for result in results}
    ):
        delay_results = [
            result
            for result in results
            if result.delay_ms == delay_ms
        ]

        if not delay_results:
            continue

        reference_speed = max(
            result.mean_mbps
            for result in delay_results
        )

        for result in delay_results:
            if reference_speed <= 0:
                result.reduction_percent = 0.0
            else:
                result.reduction_percent = (
                    1
                    - result.mean_mbps
                    / reference_speed
                ) * 100

    return results


# ---------------------------------------------------------------------------
# Поиск заметного снижения
# ---------------------------------------------------------------------------

def find_significant_reductions(
    results: list[AnalysisResult],
    threshold_percent: float = 20.0,
) -> list[AnalysisResult]:
    """
    Находит комбинации параметров, где пропускная
    способность снизилась не менее чем на threshold_percent.

    По умолчанию используется порог 20%.

    Это рабочий критерий анализа, а не отдельное
    численное требование методички.
    """

    return [
        result
        for result in results
        if result.reduction_percent
        >= threshold_percent
    ]


# ---------------------------------------------------------------------------
# Сохранение сводной таблицы
# ---------------------------------------------------------------------------

def save_summary(
    results: list[AnalysisResult],
    output_path: str,
) -> None:
    """
    Сохраняет сводные результаты в CSV.
    """

    directory = os.path.dirname(output_path)

    if directory:
        os.makedirs(
            directory,
            exist_ok=True,
        )

    fieldnames = [
        "buffer_size",
        "delay_ms",
        "repetitions",
        "mean_mbps",
        "min_mbps",
        "max_mbps",
        "stddev_mbps",
        "bdp_bits",
        "bdp_bytes",
        "reduction_percent",
    ]

    with open(
        output_path,
        "w",
        newline="",
        encoding="utf-8",
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=fieldnames,
        )

        writer.writeheader()

        for result in results:
            writer.writerow(
                {
                    "buffer_size": result.buffer_size,
                    "delay_ms": result.delay_ms,
                    "repetitions": result.repetitions,
                    "mean_mbps": (
                        f"{result.mean_mbps:.6f}"
                    ),
                    "min_mbps": (
                        f"{result.min_mbps:.6f}"
                    ),
                    "max_mbps": (
                        f"{result.max_mbps:.6f}"
                    ),
                    "stddev_mbps": (
                        f"{result.stddev_mbps:.6f}"
                    ),
                    "bdp_bits": (
                        f"{result.bdp_bits:.3f}"
                    ),
                    "bdp_bytes": (
                        f"{result.bdp_bytes:.3f}"
                    ),
                    "reduction_percent": (
                        f"{result.reduction_percent:.3f}"
                    ),
                }
            )


# ---------------------------------------------------------------------------
# Вывод результатов
# ---------------------------------------------------------------------------

def print_summary(
    results: list[AnalysisResult],
) -> None:
    """Выводит сводную таблицу в консоль."""

    print()
    print("=" * 100)
    print("СВОДНЫЕ РЕЗУЛЬТАТЫ")
    print("=" * 100)

    header = (
        f"{'Буфер':>12} "
        f"{'Задержка':>10} "
        f"{'N':>4} "
        f"{'Среднее':>12} "
        f"{'Мин.':>12} "
        f"{'Макс.':>12} "
        f"{'σ':>10} "
        f"{'BDP':>14} "
        f"{'Снижение':>11}"
    )

    print(header)
    print("-" * 100)

    for result in results:
        print(
            f"{format_bytes(result.buffer_size):>12} "
            f"{format_delay(result.delay_ms):>10} "
            f"{result.repetitions:>4} "
            f"{result.mean_mbps:>10.2f} "
            f"Мбит/с "
            f"{result.min_mbps:>10.2f} "
            f"{result.max_mbps:>10.2f} "
            f"{result.stddev_mbps:>10.2f} "
            f"{format_bytes(int(result.bdp_bytes)):>14} "
            f"{result.reduction_percent:>9.1f}%"
        )

    print("=" * 100)


def print_bdp_comparison(
    results: list[AnalysisResult],
) -> None:
    """
    Выводит отдельную информацию для сопоставления
    размера буфера с рассчитанным BDP.
    """

    print()
    print("=" * 80)
    print("СОПОСТАВЛЕНИЕ TCP-БУФЕРА И BDP")
    print("=" * 80)

    for result in results:

        if result.bdp_bytes <= 0:
            status = "BDP не определяется при нулевой задержке"
        elif result.buffer_size < result.bdp_bytes:
            status = "буфер меньше BDP"
        else:
            status = "буфер не меньше BDP"

        print(
            f"Буфер: {format_bytes(result.buffer_size):>12} | "
            f"задержка: {format_delay(result.delay_ms):>8} | "
            f"BDP: {format_bytes(int(result.bdp_bytes)):>12} | "
            f"{status}"
        )

    print("=" * 80)


def print_significant_reductions(
    results: list[AnalysisResult],
    threshold_percent: float,
) -> None:
    """Выводит комбинации с заметным снижением скорости."""

    significant = find_significant_reductions(
        results,
        threshold_percent,
    )

    print()
    print("=" * 80)
    print(
        "КОМБИНАЦИИ С ЗАМЕТНЫМ СНИЖЕНИЕМ "
        f"ПРОПУСКНОЙ СПОСОБНОСТИ (≥ {threshold_percent:.0f}%)"
    )
    print("=" * 80)

    if not significant:
        print("Таких комбинаций не обнаружено.")
    else:
        for result in significant:
            print(
                f"Буфер {format_bytes(result.buffer_size)}, "
                f"задержка {format_delay(result.delay_ms)}: "
                f"{result.mean_mbps:.2f} Мбит/с, "
                f"снижение {result.reduction_percent:.1f}%"
            )

    print("=" * 80)


# ---------------------------------------------------------------------------
# Аргументы командной строки
# ---------------------------------------------------------------------------

def parse_arguments() -> argparse.Namespace:
    """Разбор аргументов командной строки."""

    parser = argparse.ArgumentParser(
        description=(
            "Анализ результатов лабораторной работы №8."
        )
    )

    parser.add_argument(
        "--input",
        default=RESULTS_CSV,
        help=(
            "CSV с исходными результатами."
        ),
    )

    parser.add_argument(
        "--output",
        default=(
            f"{RESULTS_DIR}/analysis.csv"
        ),
        help=(
            "CSV для сводных результатов."
        ),
    )

    parser.add_argument(
        "--threshold",
        type=float,
        default=20.0,
        help=(
            "Порог заметного снижения в процентах."
        ),
    )

    return parser.parse_args()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    """Точка входа."""

    args = parse_arguments()

    if args.threshold < 0:
        raise SystemExit(
            "Порог снижения не может быть отрицательным."
        )

    rows = load_results(
        csv_path=args.input,
    )

    results = create_analysis(rows)

    save_summary(
        results=results,
        output_path=args.output,
    )

    print_summary(results)

    print_bdp_comparison(results)

    print_significant_reductions(
        results=results,
        threshold_percent=args.threshold,
    )

    print()
    print(
        f"Сводные результаты сохранены: "
        f"{args.output}"
    )


if __name__ == "__main__":
    main()