#!/usr/bin/env python3

import argparse
import socket
import time


DEFAULT_HOST = "0.0.0.0"
DEFAULT_PORT = 5001
DEFAULT_BUFFER_SIZE = 64 * 1024


def create_server_socket(
    host: str,
    port: int,
    recv_buffer: int,
    send_buffer: int,
) -> socket.socket:
    """
    Создаёт и настраивает TCP-сокет сервера.
    """

    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    # Разрешаем повторное использование адреса после завершения
    # предыдущего запуска сервера.
    server_socket.setsockopt(
        socket.SOL_SOCKET,
        socket.SO_REUSEADDR,
        1,
    )

    # Размеры TCP socket buffers.
    server_socket.setsockopt(
        socket.SOL_SOCKET,
        socket.SO_RCVBUF,
        recv_buffer,
    )

    server_socket.setsockopt(
        socket.SOL_SOCKET,
        socket.SO_SNDBUF,
        send_buffer,
    )

    server_socket.bind((host, port))
    server_socket.listen(1)

    return server_socket


def receive_data(
    client_socket: socket.socket,
    expected_bytes: int,
    recv_chunk_size: int,
) -> tuple[int, float]:
    """
    Принимает expected_bytes данных от клиента.

    Возвращает:
        received_bytes — фактически принятое количество байт;
        elapsed — время приёма.
    """

    received_bytes = 0

    start_time = time.perf_counter()

    while received_bytes < expected_bytes:
        remaining = expected_bytes - received_bytes

        chunk_size = min(
            recv_chunk_size,
            remaining,
        )

        data = client_socket.recv(chunk_size)

        if not data:
            # Клиент закрыл соединение раньше времени.
            break

        received_bytes += len(data)

    elapsed = time.perf_counter() - start_time

    return received_bytes, elapsed


def send_result(
    client_socket: socket.socket,
    received_bytes: int,
    elapsed: float,
) -> None:
    """
    Отправляет клиенту результат измерения.
    """

    message = (
        f"received={received_bytes};"
        f"elapsed={elapsed:.9f}"
    )

    client_socket.sendall(message.encode("ascii"))


def print_socket_parameters(
    client_socket: socket.socket,
) -> None:
    """
    Выводит фактически установленные ОС размеры
    TCP-буферов сокета.
    """

    actual_recv_buffer = client_socket.getsockopt(
        socket.SOL_SOCKET,
        socket.SO_RCVBUF,
    )

    actual_send_buffer = client_socket.getsockopt(
        socket.SOL_SOCKET,
        socket.SO_SNDBUF,
    )

    print(
        f"[SERVER] SO_RCVBUF = {actual_recv_buffer} bytes"
    )

    print(
        f"[SERVER] SO_SNDBUF = {actual_send_buffer} bytes"
    )


def handle_client(
    client_socket: socket.socket,
    recv_chunk_size: int,
) -> None:
    """
    Обрабатывает одно TCP-соединение.

    Первые 8 байт сообщения содержат ожидаемый объём данных
    в формате unsigned 64-bit integer.
    """

    print_socket_parameters(client_socket)

    header = b""

    while len(header) < 8:
        chunk = client_socket.recv(8 - len(header))

        if not chunk:
            print("[SERVER] Client disconnected before sending header.")
            return

        header += chunk

    expected_bytes = int.from_bytes(
        header,
        byteorder="big",
        signed=False,
    )

    print(
        f"[SERVER] Expected data: "
        f"{expected_bytes} bytes"
    )

    received_bytes, elapsed = receive_data(
        client_socket=client_socket,
        expected_bytes=expected_bytes,
        recv_chunk_size=recv_chunk_size,
    )

    print(
        f"[SERVER] Received: "
        f"{received_bytes} bytes"
    )

    print(
        f"[SERVER] Receive time: "
        f"{elapsed:.6f} s"
    )

    if elapsed > 0:
        throughput_bps = (
            received_bytes * 8 / elapsed
        )

        throughput_mbps = throughput_bps / 1_000_000

        print(
            f"[SERVER] Throughput: "
            f"{throughput_bps:.2f} bit/s "
            f"({throughput_mbps:.2f} Mbit/s)"
        )

    send_result(
        client_socket=client_socket,
        received_bytes=received_bytes,
        elapsed=elapsed,
    )


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "TCP server for laboratory work №8"
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
            f"TCP port "
            f"(default: {DEFAULT_PORT})"
        ),
    )

    parser.add_argument(
        "--recv-buffer",
        type=int,
        default=DEFAULT_BUFFER_SIZE,
        help=(
            "Requested SO_RCVBUF size in bytes "
            f"(default: {DEFAULT_BUFFER_SIZE})"
        ),
    )

    parser.add_argument(
        "--send-buffer",
        type=int,
        default=DEFAULT_BUFFER_SIZE,
        help=(
            "Requested SO_SNDBUF size in bytes "
            f"(default: {DEFAULT_BUFFER_SIZE})"
        ),
    )

    parser.add_argument(
        "--recv-chunk",
        type=int,
        default=64 * 1024,
        help=(
            "Maximum size of one recv() call "
            "(default: 65536)"
        ),
    )

    return parser.parse_args()


def main() -> None:
    args = parse_arguments()

    server_socket = create_server_socket(
        host=args.host,
        port=args.port,
        recv_buffer=args.recv_buffer,
        send_buffer=args.send_buffer,
    )

    print(
        f"[SERVER] Listening on "
        f"{args.host}:{args.port}"
    )

    print(
        f"[SERVER] Requested SO_RCVBUF: "
        f"{args.recv_buffer} bytes"
    )

    print(
        f"[SERVER] Requested SO_SNDBUF: "
        f"{args.send_buffer} bytes"
    )

    try:
        while True:
            client_socket, client_address = (
                server_socket.accept()
            )

            print(
                f"\n[SERVER] Connection from "
                f"{client_address[0]}:"
                f"{client_address[1]}"
            )

            try:
                handle_client(
                    client_socket=client_socket,
                    recv_chunk_size=args.recv_chunk,
                )

            except ConnectionResetError:
                print(
                    "[SERVER] Connection reset by client."
                )

            except Exception as error:
                print(
                    f"[SERVER] Client error: {error}"
                )

            finally:
                client_socket.close()

                print(
                    "[SERVER] Connection closed."
                )

    except KeyboardInterrupt:
        print("\n[SERVER] Stopped by user.")

    finally:
        server_socket.close()


if __name__ == "__main__":
    main()