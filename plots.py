"""
Plotting results for laboratory work №8.

Исследование влияния размера TCP-буфера
и задержки на пропускную способность.
"""

import argparse
import csv
import os
from collections import defaultdict

import matplotlib.pyplot as plt

from config import FIGURES_DIR, RESULTS_DIR, format_bytes


def load_analysis(filename: str) -> list[dict]:
    """Загружает результаты анализа из CSV."""
    if not os.path.exists(filename):
        raise FileNotFoundError(
            f"Файл с результатами не найден: {filename}"
        )

    rows = []

    with open(filename, "r", encoding="utf-8", newline="") as file:
        reader = csv.DictReader(file)

        for row in reader:
            rows.append(
                {
                    "buffer_size": int(row["buffer_size"]),
                    "delay_ms": int(row["delay_ms"]),
                    "mean_mbps": float(row["mean_mbps"]),
                    "min_mbps": float(row["min_mbps"]),
                    "max_mbps": float(row["max_mbps"]),
                }
            )

    if not rows:
        raise ValueError("Файл результатов пуст.")

    return rows


def prepare_figures_directory() -> None:
    """Создаёт каталог для графиков."""
    os.makedirs(FIGURES_DIR, exist_ok=True)


def sort_rows(rows: list[dict]) -> list[dict]:
    """Сортирует результаты по задержке и размеру буфера."""
    return sorted(
        rows,
        key=lambda row: (row["delay_ms"], row["buffer_size"]),
    )


def plot_zero_delay(rows: list[dict]) -> str:
    """
    Строит график зависимости пропускной способности
    от размера TCP-буфера при нулевой задержке.
    """
    zero_delay_rows = [
        row for row in rows
        if row["delay_ms"] == 0
    ]

    if not zero_delay_rows:
        raise ValueError(
            "В результатах отсутствуют измерения для задержки 0 мс."
        )

    zero_delay_rows.sort(key=lambda row: row["buffer_size"])

    buffers = [row["buffer_size"] for row in zero_delay_rows]
    throughput = [row["mean_mbps"] for row in zero_delay_rows]

    labels = [
        format_bytes(buffer_size)
        for buffer_size in buffers
    ]

    plt.figure(figsize=(10, 6))

    plt.plot(
        labels,
        throughput,
        marker="o",
        linewidth=2,
    )

    plt.xlabel("Размер TCP-буфера")
    plt.ylabel("Средняя пропускная способность, Мбит/с")
    plt.title(
        "Зависимость пропускной способности "
        "от размера TCP-буфера (задержка 0 мс)"
    )

    plt.grid(True, alpha=0.3)
    plt.tight_layout()

    filename = os.path.join(
        FIGURES_DIR,
        "throughput_vs_buffer_0ms.png",
    )

    plt.savefig(filename, dpi=150)
    plt.close()

    return filename


def plot_delay_family(rows: list[dict]) -> str:
    """
    Строит общий график зависимости пропускной способности
    от размера буфера для всех исследованных задержек.
    """
    grouped = defaultdict(list)

    for row in rows:
        grouped[row["delay_ms"]].append(row)

    plt.figure(figsize=(11, 7))

    for delay_ms in sorted(grouped):
        delay_rows = sorted(
            grouped[delay_ms],
            key=lambda row: row["buffer_size"],
        )

        buffers = [
            row["buffer_size"]
            for row in delay_rows
        ]

        throughput = [
            row["mean_mbps"]
            for row in delay_rows
        ]

        labels = [
            format_bytes(buffer_size)
            for buffer_size in buffers
        ]

        plt.plot(
            labels,
            throughput,
            marker="o",
            linewidth=2,
            label=f"{delay_ms} мс",
        )

    plt.xlabel("Размер TCP-буфера")
    plt.ylabel("Средняя пропускная способность, Мбит/с")
    plt.title(
        "Влияние размера TCP-буфера и задержки "
        "на пропускную способность"
    )

    plt.grid(True, alpha=0.3)
    plt.legend(title="Задержка")

    plt.tight_layout()

    filename = os.path.join(
        FIGURES_DIR,
        "throughput_vs_buffer_all_delays.png",
    )

    plt.savefig(filename, dpi=150)
    plt.close()

    return filename


def plot_each_delay(rows: list[dict]) -> list[str]:
    """
    Создаёт отдельный график для каждой задержки.
    """
    grouped = defaultdict(list)

    for row in rows:
        grouped[row["delay_ms"]].append(row)

    filenames = []

    for delay_ms in sorted(grouped):
        delay_rows = sorted(
            grouped[delay_ms],
            key=lambda row: row["buffer_size"],
        )

        buffers = [
            row["buffer_size"]
            for row in delay_rows
        ]

        throughput = [
            row["mean_mbps"]
            for row in delay_rows
        ]

        labels = [
            format_bytes(buffer_size)
            for buffer_size in buffers
        ]

        plt.figure(figsize=(10, 6))

        plt.plot(
            labels,
            throughput,
            marker="o",
            linewidth=2,
        )

        plt.xlabel("Размер TCP-буфера")
        plt.ylabel("Средняя пропускная способность, Мбит/с")
        plt.title(
            f"Пропускная способность "
            f"при задержке {delay_ms} мс"
        )

        plt.grid(True, alpha=0.3)
        plt.tight_layout()

        filename = os.path.join(
            FIGURES_DIR,
            f"throughput_vs_buffer_{delay_ms}ms.png",
        )

        plt.savefig(filename, dpi=150)
        plt.close()

        filenames.append(filename)

    return filenames


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Построение графиков для лабораторной работы №8"
        )
    )

    parser.add_argument(
        "--input",
        default=os.path.join(
            RESULTS_DIR,
            "analysis.csv",
        ),
        help="CSV-файл с результатами анализа",
    )

    args = parser.parse_args()

    prepare_figures_directory()

    rows = load_analysis(args.input)

    zero_delay_file = plot_zero_delay(rows)
    all_delays_file = plot_delay_family(rows)
    individual_files = plot_each_delay(rows)

    print("Графики успешно созданы:")
    print(f"  - {zero_delay_file}")
    print(f"  - {all_delays_file}")

    for filename in individual_files:
        print(f"  - {filename}")


if __name__ == "__main__":
    main()