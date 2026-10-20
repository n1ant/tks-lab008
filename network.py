"""
Управление искусственной сетевой задержкой для лабораторной работы №8.

Для Linux используется tc/netem.

Пример:
    sudo python3 network.py --interface lo --delay 50

Для удаления задержки:
    sudo python3 network.py --interface lo --clear
"""

import argparse
import shutil
import subprocess
from contextlib import contextmanager


class NetworkError(RuntimeError):
    """Ошибка при изменении параметров сети."""


def check_tc_available() -> None:
    """Проверяет наличие утилиты tc."""
    if shutil.which("tc") is None:
        raise NetworkError(
            "Утилита 'tc' не найдена. "
            "Установите пакет iproute2."
        )


def run_command(command: list[str]) -> subprocess.CompletedProcess:
    """
    Выполняет системную команду.

    При ошибке выбрасывается NetworkError
    с текстом stderr.
    """
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError as exc:
        raise NetworkError(
            f"Не удалось выполнить команду: {exc}"
        ) from exc

    if result.returncode != 0:
        error = result.stderr.strip()

        raise NetworkError(
            f"Команда завершилась с ошибкой:\n"
            f"{' '.join(command)}\n"
            f"{error}"
        )

    return result


def apply_delay(interface: str, delay_ms: int) -> None:
    """
    Устанавливает искусственную задержку на интерфейсе.

    Используется Linux tc/netem.

    Например:
        tc qdisc replace dev lo root netem delay 50ms
    """
    if delay_ms < 0:
        raise ValueError("Задержка не может быть отрицательной.")

    check_tc_available()

    if not interface:
        raise ValueError("Не указан сетевой интерфейс.")

    command = [
        "tc",
        "qdisc",
        "replace",
        "dev",
        interface,
        "root",
        "netem",
        "delay",
        f"{delay_ms}ms",
    ]

    run_command(command)

    print(
        f"[NET] Интерфейс {interface}: "
        f"задержка установлена на {delay_ms} мс"
    )


def remove_delay(interface: str) -> None:
    """
    Удаляет искусственную задержку с интерфейса.

    Если qdisc netem отсутствует, это не считается
    критической ошибкой.
    """
    check_tc_available()

    command = [
        "tc",
        "qdisc",
        "del",
        "dev",
        interface,
        "root",
    ]

    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError as exc:
        raise NetworkError(
            f"Не удалось выполнить команду: {exc}"
        ) from exc

    if result.returncode != 0:
        error = result.stderr.strip()

        # qdisc может отсутствовать — тогда удалять нечего.
        if (
            "No such file or directory" in error
            or "Cannot find device" in error
        ):
            return

        raise NetworkError(
            f"Не удалось удалить сетевую задержку:\n"
            f"{error}"
        )

    print(
        f"[NET] Интерфейс {interface}: "
        f"искусственная задержка удалена"
    )


def get_qdisc(interface: str) -> str:
    """
    Возвращает текущее состояние qdisc интерфейса.
    """
    check_tc_available()

    command = [
        "tc",
        "qdisc",
        "show",
        "dev",
        interface,
    ]

    result = run_command(command)
    return result.stdout.strip()


@contextmanager
def network_delay(interface: str, delay_ms: int):
    """
    Контекстный менеджер для безопасного применения задержки.

    Задержка устанавливается перед экспериментом
    и гарантированно удаляется после него.
    """
    apply_delay(interface, delay_ms)

    try:
        yield
    finally:
        remove_delay(interface)


def parse_arguments() -> argparse.Namespace:
    """Разбор аргументов командной строки."""
    parser = argparse.ArgumentParser(
        description=(
            "Управление искусственной сетевой задержкой "
            "через Linux tc/netem."
        )
    )

    parser.add_argument(
        "--interface",
        required=True,
        help="Сетевой интерфейс, например lo или eth0",
    )

    parser.add_argument(
        "--delay",
        type=int,
        default=0,
        help="Задержка в миллисекундах",
    )

    parser.add_argument(
        "--clear",
        action="store_true",
        help="Удалить текущий qdisc с интерфейса",
    )

    parser.add_argument(
        "--show",
        action="store_true",
        help="Показать текущий qdisc интерфейса",
    )

    return parser.parse_args()


def main() -> None:
    """Точка входа для запуска из командной строки."""
    args = parse_arguments()

    try:
        if args.show:
            print(get_qdisc(args.interface))
            return

        if args.clear:
            remove_delay(args.interface)
            return

        apply_delay(
            interface=args.interface,
            delay_ms=args.delay,
        )

    except (NetworkError, ValueError) as exc:
        print(f"[ERROR] {exc}")
        raise SystemExit(1)


if __name__ == "__main__":
    main()