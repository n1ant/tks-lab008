"""
Configuration for laboratory work №8.

Исследование влияния размера TCP-буфера
и задержки на пропускную способность.
"""

from dataclasses import dataclass


# ---------------------------------------------------------------------------
# Network parameters
# ---------------------------------------------------------------------------

SERVER_HOST = "127.0.0.1"
SERVER_PORT = 5001


# ---------------------------------------------------------------------------
# Data transfer parameters
# ---------------------------------------------------------------------------

# Объём данных для одного измерения.
# 100 MiB достаточно велик, чтобы измерительный интервал
# не был слишком коротким.
DATA_SIZE = 100 * 1024 * 1024


# Размер блока, передаваемого одним вызовом send().
SEND_CHUNK_SIZE = 64 * 1024


# Размер блока, используемого сервером при recv().
RECV_CHUNK_SIZE = 64 * 1024


# ---------------------------------------------------------------------------
# TCP buffer sizes
# ---------------------------------------------------------------------------

# Размеры буферов, которые будут исследоваться
# в задании 1 и задании 2.
BUFFER_SIZES = [
    16 * 1024,        # 16 KiB
    64 * 1024,        # 64 KiB
    256 * 1024,       # 256 KiB
    1024 * 1024,      # 1 MiB
    4 * 1024 * 1024,  # 4 MiB
    16 * 1024 * 1024, # 16 MiB
]


# ---------------------------------------------------------------------------
# Artificial network delay
# ---------------------------------------------------------------------------

# Значения задержки для эксперимента.
#
# Здесь указываются значения в миллисекундах.
# Фактическое применение задержки будет реализовано
# отдельно через network.py.
DELAY_VALUES_MS = [
    0,
    10,
    25,
    50,
    100,
]


# ---------------------------------------------------------------------------
# Number of repetitions
# ---------------------------------------------------------------------------

# Методичка требует не менее пяти повторений
# для каждой комбинации задержки и размера буфера.
REPETITIONS = 5


# ---------------------------------------------------------------------------
# Results
# ---------------------------------------------------------------------------

RESULTS_DIR = "results"
RAW_RESULTS_DIR = "results/raw"
FIGURES_DIR = "results/figures"

RESULTS_CSV = "results/raw/measurements.csv"


# ---------------------------------------------------------------------------
# Experiment description
# ---------------------------------------------------------------------------

LAB_NUMBER = 8

LAB_TITLE = (
    "Исследование влияния размера TCP-буфера "
    "и задержки на пропускную способность"
)


# ---------------------------------------------------------------------------
# Experiment configuration
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ExperimentConfig:
    """
    Набор параметров одного эксперимента.
    """

    buffer_size: int
    delay_ms: int
    repetitions: int = REPETITIONS
    data_size: int = DATA_SIZE
    send_chunk_size: int = SEND_CHUNK_SIZE
    recv_chunk_size: int = RECV_CHUNK_SIZE


def create_experiment_configs() -> list[ExperimentConfig]:
    """
    Создаёт полный набор комбинаций параметров
    для задания 2.

    Каждая комбинация:
        размер TCP-буфера × задержка.
    """

    configs = []

    for delay_ms in DELAY_VALUES_MS:
        for buffer_size in BUFFER_SIZES:
            configs.append(
                ExperimentConfig(
                    buffer_size=buffer_size,
                    delay_ms=delay_ms,
                )
            )

    return configs


# ---------------------------------------------------------------------------
# Utility functions
# ---------------------------------------------------------------------------

def format_bytes(value: int) -> str:
    """
    Переводит количество байт в удобный для вывода формат.
    """

    units = [
        "B",
        "KiB",
        "MiB",
        "GiB",
    ]

    size = float(value)

    for unit in units:
        if size < 1024 or unit == units[-1]:
            return f"{size:.2f} {unit}"

        size /= 1024

    return f"{size:.2f} GiB"


def format_delay(delay_ms: int) -> str:
    """
    Форматирует задержку для вывода.
    """

    if delay_ms == 0:
        return "0 ms"

    if delay_ms < 1000:
        return f"{delay_ms} ms"

    return f"{delay_ms / 1000:.2f} s"


def print_configuration() -> None:
    """
    Выводит текущую конфигурацию лабораторной работы.
    """

    print("=" * 60)
    print(f"Лабораторная работа №{LAB_NUMBER}")
    print(LAB_TITLE)
    print("=" * 60)

    print(
        f"Server: "
        f"{SERVER_HOST}:{SERVER_PORT}"
    )

    print(
        f"Data size: "
        f"{format_bytes(DATA_SIZE)}"
    )

    print(
        f"Send chunk: "
        f"{format_bytes(SEND_CHUNK_SIZE)}"
    )

    print(
        f"Receive chunk: "
        f"{format_bytes(RECV_CHUNK_SIZE)}"
    )

    print()

    print("Buffer sizes:")

    for buffer_size in BUFFER_SIZES:
        print(
            f"  - {format_bytes(buffer_size)}"
        )

    print()

    print("Delay values:")

    for delay_ms in DELAY_VALUES_MS:
        print(
            f"  - {format_delay(delay_ms)}"
        )

    print()

    print(
        f"Repetitions: {REPETITIONS}"
    )

    print("=" * 60)


if __name__ == "__main__":
    print_configuration()