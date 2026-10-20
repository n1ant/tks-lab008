#!/usr/bin/env python3

import argparse
import socket
import time


DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 5001

DEFAULT_DATA_SIZE = 100 * 1024 * 1024  # 100 MiB
DEFAULT_SEND_BUFFER = 64 * 1024

HEADER_SIZE = 8


def create_client_socket(
    send_buffer: int,
    recv_buffer: int,
) -> socket.socket:
    """
    Создаёт и настраивает TCP-сокет клиента.
    """

    client_socket = socket.socket(
        socket.AF_INET,
        socket.SOCK_STREAM,
    )

    client_socket.setsockopt(
        socket.SOL_SOCKET,
        socket.SO_SNDBUF,
        send_buffer,
    )

    client_socket.setsockopt(
        socket.SOL_SOCKET,
        socket.SO_RCVBUF,
        recv_buffer,
    )

    return client_socket


def generate_data(
    size: int,
    chunk_size: int,
) -> bytes:
    """
    Создаёт блок данных для передачи.

    Для эксперимента содержимое данных не имеет значения,
    поэтому используется повторяющийся байтовый шаблон.
    """

    pattern = b"LAB8_TCP_DATA"

    repeats = (
        chunk_size // len(pattern) + 1
    )

    return (
        pattern * repeats
    )[:chunk_size]


def send_all_data(
    client_socket: socket.socket,
    total_bytes: int,
    chunk_size: int,
) -> float:
    """
    Передаёт total_bytes данных через TCP.

    Возвращает продолжительность передачи
    полезных данных.
    """

    data_chunk = generate_data(
        size=chunk_size,
        chunk_size=chunk_size,
    )

    bytes_sent = 0

    start_time = time.perf_counter()

    while bytes_sent < total_bytes:
        remaining = total_bytes - bytes_sent

        chunk = data_chunk

        if remaining < len(chunk):
            chunk = chunk[:remaining]

        client_socket.sendall(chunk)

        bytes_sent += len(chunk)

    elapsed = time.perf_counter() - start_time

    return elapsed


def receive_result(
    client_socket: socket.socket,
) -> str:
    """
    Получает от сервера строку с результатами.
    """

    result = b""

    while True:
        chunk = client_socket.recv(4096)

        if not chunk:
            break

        result += chunk

    return result.decode(
        "ascii",
        errors="replace",
    )


def print_socket_parameters(
    client_socket: socket.socket,
) -> None:
    """
    Выводит фактически установленные размеры
    TCP-буферов.
    """

    actual_send_buffer = client_socket.getsockopt(
        socket.SOL_SOCKET,
        socket.SO_SNDBUF,
    )

    actual_recv_buffer = client_socket.getsockopt(
        socket.SOL_SOCKET,
        socket.SO_RCVBUF,
    )

    print(
        f"[CLIENT] SO_SNDBUF = "
        f"{actual_send_buffer} bytes"
    )

    print(
        f"[CLIENT] SO_RCVBUF = "
        f"{actual_recv_buffer} bytes"
    )


def send_header(
    client_socket: socket.socket,
    total_bytes: int,
) -> None:
    """
    Передаёт серверу размер последующего блока данных.

    Размер хранится в первых 8 байтах TCP-потока.
    """

    header = total_bytes.to_bytes(
        HEADER_SIZE,
        byteorder="big",
        signed=False,
    )

    client_socket.sendall(header)


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "TCP client for laboratory work №8"
        )
    )

    parser.add_argument(
        "--host",
        default=DEFAULT_HOST,
        help=(
            f"Server address "
            f"(default: {DEFAULT_HOST})"
        ),
    )

    parser.add_argument(
        "--port",
        type=int,
        default=DEFAULT_PORT,
        help=(
            f"Server port "
            f"(default: {DEFAULT_PORT})"
        ),
    )

    parser.add_argument(
        "--size",
        type=int,
        default=DEFAULT_DATA_SIZE,
        help=(
            "Amount of data to transfer in bytes "
            f"(default: {DEFAULT_DATA_SIZE})"
        ),
    )

    parser.add_argument(
        "--send-buffer",
        type=int,
        default=DEFAULT_SEND_BUFFER,
        help=(
            "Requested SO_SNDBUF size in bytes "
            f"(default: {DEFAULT_SEND_BUFFER})"
        ),
    )

    parser.add_argument(
        "--recv-buffer",
        type=int,
        default=DEFAULT_SEND_BUFFER,
        help=(
            "Requested SO_RCVBUF size in bytes "
            f"(default: {DEFAULT_SEND_BUFFER})"
        ),
    )

    parser.add_argument(
        "--chunk-size",
        type=int,
        default=64 * 1024,
        help=(
            "Size of one send() block in bytes "
            "(default: 65536)"
        ),
    )

    return parser.parse_args()


def main() -> None:
    args = parse_arguments()

    if args.size <= 0:
        raise ValueError(
            "Data size must be greater than zero."
        )

    if args.chunk_size <= 0:
        raise ValueError(
            "Chunk size must be greater than zero."
        )

    print(
        f"[CLIENT] Connecting to "
        f"{args.host}:{args.port}"
    )

    client_socket = create_client_socket(
        send_buffer=args.send_buffer,
        recv_buffer=args.recv_buffer,
    )

    try:
        client_socket.connect(
            (args.host, args.port)
        )

        print("[CLIENT] Connected.")

        print_socket_parameters(
            client_socket
        )

        print(
            f"[CLIENT] Data size: "
            f"{args.size} bytes "
            f"({args.size / 1024 / 1024:.2f} MiB)"
        )

        print(
            f"[CLIENT] Send chunk: "
            f"{args.chunk_size} bytes"
        )

        # Сначала сообщаем серверу,
        # сколько данных он должен принять.
        send_header(
            client_socket,
            args.size,
        )

        print(
            "[CLIENT] Sending data..."
        )

        elapsed = send_all_data(
            client_socket=client_socket,
            total_bytes=args.size,
            chunk_size=args.chunk_size,
        )

        throughput_bps = (
            args.size * 8 / elapsed
        )

        throughput_mbps = (
            throughput_bps / 1_000_000
        )

        print(
            f"[CLIENT] Transfer time: "
            f"{elapsed:.6f} s"
        )

        print(
            f"[CLIENT] Throughput: "
            f"{throughput_bps:.2f} bit/s"
        )

        print(
            f"[CLIENT] Throughput: "
            f"{throughput_mbps:.2f} Mbit/s"
        )

        print(
            "[CLIENT] Waiting for server result..."
        )

        result = receive_result(
            client_socket
        )

        if result:
            print(
                "[CLIENT] Server result:"
            )
            print(result)

    except ConnectionRefusedError:
        print(
            "[CLIENT] Connection refused. "
            "Is the server running?"
        )

    except ConnectionResetError:
        print(
            "[CLIENT] Connection was reset "
            "by the server."
        )

    finally:
        client_socket.close()

        print(
            "[CLIENT] Connection closed."
        )


if __name__ == "__main__":
    main()