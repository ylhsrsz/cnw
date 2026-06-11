#!/usr/bin/env python3
import argparse
import socket
import struct
import threading
from datetime import datetime


TYPE_INITIALIZATION = 1
TYPE_AGREE = 2
TYPE_REVERSE_REQUEST = 3
TYPE_REVERSE_ANSWER = 4

INIT_STRUCT = struct.Struct("!HI")
TYPE_STRUCT = struct.Struct("!H")
FRAME_HEADER = struct.Struct("!HI")


def now_text() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]


class Logger:
    def __init__(self, path: str) -> None:
        self.path = path
        self.lock = threading.Lock()
        with open(self.path, "w", encoding="utf-8") as handle:
            handle.write("")

    def log(self, message: str) -> None:
        line = f"[{now_text()}] {message}"
        with self.lock:
            with open(self.path, "a", encoding="utf-8") as handle:
                handle.write(line + "\n")
        print(line, flush=True)


def recv_exact(sock: socket.socket, size: int) -> bytes:
    chunks = bytearray()
    while len(chunks) < size:
        chunk = sock.recv(size - len(chunks))
        if not chunk:
            raise ConnectionError("peer closed the connection")
        chunks.extend(chunk)
    return bytes(chunks)


def recv_frame(sock: socket.socket) -> tuple[int, bytes]:
    header = recv_exact(sock, FRAME_HEADER.size)
    frame_type, payload_len = FRAME_HEADER.unpack(header)
    payload = recv_exact(sock, payload_len) if payload_len else b""
    return frame_type, payload


def send_frame(sock: socket.socket, frame_type: int, payload: bytes) -> None:
    sock.sendall(FRAME_HEADER.pack(frame_type, len(payload)) + payload)


def handle_client(conn: socket.socket, addr: tuple[str, int], logger: Logger) -> None:
    peer = f"{addr[0]}:{addr[1]}"
    chunk_count = 0
    try:
        frame_type, payload = recv_frame(conn)
        if frame_type != TYPE_INITIALIZATION or len(payload) != 4:
            raise ValueError("expected initialization frame")
        total_chunks = struct.unpack("!I", payload)[0]
        logger.log(f"{peer} recv Initialization, expected_chunks={total_chunks}")

        send_frame(conn, TYPE_AGREE, b"")
        logger.log(f"{peer} send agree")

        while True:
            frame_type, payload = recv_frame(conn)
            if frame_type != TYPE_REVERSE_REQUEST:
                raise ValueError(f"unexpected frame type {frame_type}")
            if not payload:
                break

            chunk_count += 1
            reversed_payload = payload[::-1]
            logger.log(
                f"{peer} recv reverseRequest #{chunk_count}, "
                f"payload_len={len(payload)}"
            )
            send_frame(conn, TYPE_REVERSE_ANSWER, reversed_payload)
            logger.log(
                f"{peer} send reverseAnswer #{chunk_count}, "
                f"payload_len={len(reversed_payload)}"
            )

            if chunk_count >= total_chunks:
                break
    except ConnectionError as exc:
        logger.log(f"{peer} disconnected: {exc}")
    except Exception as exc:  # pragma: no cover - defensive logging
        logger.log(f"{peer} error: {exc}")
    finally:
        conn.close()
        logger.log(f"{peer} closed after {chunk_count} reverseRequest frames")


def serve(host: str, port: int, log_path: str) -> None:
    logger = Logger(log_path)
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((host, port))
    server.listen()
    logger.log(f"listening on {host}:{port}")

    try:
        while True:
            conn, addr = server.accept()
            logger.log(f"accepted connection from {addr[0]}:{addr[1]}")
            worker = threading.Thread(
                target=handle_client,
                args=(conn, addr, logger),
                daemon=True,
            )
            worker.start()
    except KeyboardInterrupt:
        logger.log("server interrupted by user")
    finally:
        server.close()
        logger.log("server stopped")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Task1 TCP reverse server")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=9001)
    parser.add_argument("--log", default="run_log.txt")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    serve(args.host, args.port, args.log)
