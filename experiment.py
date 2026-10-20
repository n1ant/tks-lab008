"""
Автоматическое проведение экспериментов лабораторной работы №8.

Исследуется влияние:
    - размера TCP-буфера;
    - искусственной сетевой задержки

на пропускную способность TCP.

Для каждой комбинации:
    задержка × размер буфера

выполняется заданное количество повторений.
"""

import argparse
import csv
import os
import socket
import subprocess
import sys
import time
from dataclasses import asdict

from config import (
    BUFFER_SIZES,
    DATA_SIZE,
    DELAY_VALUES_MS,
    REPETITIONS,
    RESULTS_CSV,
    SEND_CHUNK_SIZE,
    SERVER_HOST,
    SERVER_PORT,
    format_bytes,
    format_delay,
)
from network import network_delay


# ---------------------------------------------------------------------------
# Запуск TCP-сервера
# ---------------------------------------------------------------------------

def start_server(
    buffer_size: int,
    log_file=None,
) -> subprocess.Popen:
    """
    Запускает tcp_server.py отдельным процессом.

    Размеры приёмного и передающего буферов устанавливаются
    одинаковыми для конкретного эксперимента.
    """
    command = [
        sys.executable,
        "tcp_server.py",
        "--host",
        SERVER_HOST,
        "--port",
        str(SERVER_PORT),
        "--recv-buffer",
        str(buffer_size),
        "--send-buffer",
        str(buffer_size),
    ]

    stdout = log_file if log_file is not None else subprocess.DEVNULL

    process = subprocess.Popen(
        command,
        stdout=stdout,
        stderr=subprocess.STDOUT,
        text=True,
    )

    # Даём серверу время открыть порт.
    time.sleep(0.3)

    if process.poll() is not None:
        raise RuntimeError(
            "TCP-сервер завершился сразу после запуска."
        )

    return process


def stop_server(process: subprocess.Popen) -> None:
    """Корректно останавливает TCP-сервер."""
    if process.poll() is None:
        process.terminate()

        try:
            process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()


# ---------------------------------------------------------------------------
# Проверка доступности сервера
# ---------------------------------------------------------------------------

def wait_for_server(
    host: str,
    port: int,
    timeout: float = 5.0,
) -> bool:
    """
    Проверяет, доступен ли TCP-порт сервера.
    """
    deadline = time.monotonic() + timeout

    while time.monotonic() < deadline:
        try:
            with socket.create_connection(
                (host, port),
                timeout=0.5,
            ):
                return True

        except OSError:
            time.sleep(0.1)

    return False


# ---------------------------------------------------------------------------
# Одно измерение
# ---------------------------------------------------------------------------

def run_single_measurement(
    buffer_size: int,
    delay_ms: int,
) -> dict:
    """
    Выполняет одно TCP-измерение.

    Возвращает словарь с параметрами эксперимента
    и измеренной пропускной способностью.
    """

    server = None

    try:
        server = start_server(buffer_size)

        if not wait_for_server(
            SERVER_HOST,
            SERVER_PORT,
        ):
            raise RuntimeError(
                "TCP-сервер не стал доступен."
            )

        # Задержка устанавливается только на время эксперимента.
        with network_delay("lo", delay_ms):

            start_time = time.perf_counter()

            command = [
                sys.executable,
                "tcp_client.py",
                "--host",
                SERVER_HOST,
                "--port",
                str(SERVER_PORT),
                "--size",
                str(DATA_SIZE),
                "--send-buffer",
                str(buffer_size),
                "--recv-buffer",
                str(buffer_size),
                "--chunk-size",
                str(SEND_CHUNK_SIZE),
            ]

            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                check=False,
            )

            elapsed_total = time.perf_counter() - start_time

        if result.returncode != 0:
            raise RuntimeError(
                "TCP-клиент завершился с ошибкой:\n"
                f"{result.stderr}"
            )

        throughput_mbps = calculate_throughput(
            DATA_SIZE,
            elapsed_total,
        )

        return {
            "buffer_size": buffer_size,
            "delay_ms": delay_ms,
            "data_size": DATA_SIZE,
            "elapsed_seconds": elapsed_total,
            "throughput_mbps": throughput_mbps,
        }

    finally:
        if server is not None:
            stop_server(server)


# ---------------------------------------------------------------------------
# Расчёт пропускной способности
# ---------------------------------------------------------------------------

def calculate_throughput(
    bytes_transferred: int,
    elapsed_seconds: float,
) -> float:
    """
    Рассчитывает пропускную способность в Мбит/с.
    """
    if elapsed_seconds <= 0:
        return 0.0

    bits = bytes_transferred * 8

    return bits / elapsed_seconds / 1_000_000


# ---------------------------------------------------------------------------
# CSV
# ---------------------------------------------------------------------------

def prepare_results_directory() -> None:
    """Создаёт каталог для результатов."""
    directory = os.path.dirname(RESULTS_CSV)

    if directory:
        os.makedirs(directory, exist_ok=True)


def save_result(
    result: dict,
    csv_path: str = RESULTS_CSV,
) -> None:
    """
    Добавляет результат одного измерения в CSV.
    """
    prepare_results_directory()

    file_exists = os.path.exists(csv_path)

    fieldnames = [
        "buffer_size",
        "delay_ms",
        "data_size",
        "elapsed_seconds",
        "throughput_mbps",
    ]

    with open(
        csv_path,
        "a",
        newline="",
        encoding="utf-8",
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=fieldnames,
        )

        if not file_exists:
            writer.writeheader()

        writer.writerow(result)


# ---------------------------------------------------------------------------
# Вывод информации
# ---------------------------------------------------------------------------

def print_measurement_result(
    result: dict,
    repetition: int,
    total_repetitions: int,
) -> None:
    """Выводит результат одного измерения."""
    print(
        f"    Повторение "
        f"{repetition}/{total_repetitions}: "
        f"{result['throughput_mbps']:.2f} Мбит/с "
        f"({result['elapsed_seconds']:.3f} с)"
    )


def print_experiment_header(
    buffer_size: int,
    delay_ms: int,
) -> None:
    """Выводит параметры текущей комбинации."""
    print()
    print("-" * 60)
    print(
        f"Буфер: {format_bytes(buffer_size)} | "
        f"Задержка: {format_delay(delay_ms)}"
    )
    print("-" * 60)


# ---------------------------------------------------------------------------
# Серия экспериментов
# ---------------------------------------------------------------------------

def run_experiments(
    buffer_sizes: list[int],
    delay_values: list[int],
    repetitions: int,
) -> None:
    """
    Выполняет полную серию измерений.

    Для каждой комбинации:
        buffer_size × delay_ms

    выполняется repetitions измерений.
    """

    total = (
        len(buffer_sizes)
        * len(delay_values)
        * repetitions
    )

    current = 0

    print("=" * 60)
    print("ЛАБОРАТОРНАЯ РАБОТА №8")
    print("Серия TCP-измерений")
    print("=" * 60)
    print(
        f"Размеров буфера: {len(buffer_sizes)}"
    )
    print(
        f"Значений задержки: {len(delay_values)}"
    )
    print(
        f"Повторений: {repetitions}"
    )
    print(
        f"Всего измерений: {total}"
    )
    print("=" * 60)

    for delay_ms in delay_values:

        for buffer_size in buffer_sizes:

            print_experiment_header(
                buffer_size,
                delay_ms,
            )

            for repetition in range(
                1,
                repetitions + 1,
            ):
                current += 1

                print(
                    f"  [{current}/{total}] "
                    f"Запуск измерения..."
                )

                try:
                    result = run_single_measurement(
                        buffer_size=buffer_size,
                        delay_ms=delay_ms,
                    )

                    save_result(result)

                    print_measurement_result(
                        result=result,
                        repetition=repetition,
                        total_repetitions=repetitions,
                    )

                except Exception as exc:
                    print(
                        f"    ОШИБКА: {exc}"
                    )

    print()
    print("=" * 60)
    print("Серия измерений завершена.")
    print(f"Результаты: {RESULTS_CSV}")
    print("=" * 60)


# ---------------------------------------------------------------------------
# Аргументы командной строки
# ---------------------------------------------------------------------------

def parse_arguments() -> argparse.Namespace:
    """Разбирает аргументы командной строки."""
    parser = argparse.ArgumentParser(
        description=(
            "Серия TCP-измерений для лабораторной работы №8."
        )
    )

    parser.add_argument(
        "--buffer",
        type=int,
        nargs="+",
        help=(
            "Размеры буфера в байтах. "
            "Если не указано — используются значения из config.py."
        ),
    )

    parser.add_argument(
        "--delay",
        type=int,
        nargs="+",
        help=(
            "Задержки в миллисекундах. "
            "Если не указано — используются значения из config.py."
        ),
    )

    parser.add_argument(
        "--repetitions",
        type=int,
        default=REPETITIONS,
        help="Количество повторений каждого измерения.",
    )

    return parser.parse_args()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    """Точка входа."""
    args = parse_arguments()

    buffer_sizes = (
        args.buffer
        if args.buffer
        else BUFFER_SIZES
    )

    delay_values = (
        args.delay
        if args.delay
        else DELAY_VALUES_MS
    )

    if args.repetitions < 1:
        raise SystemExit(
            "Количество повторений должно быть >= 1."
        )

    if any(value <= 0 for value in buffer_sizes):
        raise SystemExit(
            "Размер буфера должен быть положительным."
        )

    if any(value < 0 for value in delay_values):
        raise SystemExit(
            "Задержка не может быть отрицательной."
        )

    run_experiments(
        buffer_sizes=buffer_sizes,
        delay_values=delay_values,
        repetitions=args.repetitions,
    )


if __name__ == "__main__":
    main()