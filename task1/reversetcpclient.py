#!/usr/bin/env python3
import argparse
import random
import socket
import struct
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


TYPE_INITIALIZATION = 1
TYPE_AGREE = 2
TYPE_REVERSE_REQUEST = 3
TYPE_REVERSE_ANSWER = 4

FRAME_HEADER = struct.Struct("!HI")


def now_text() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]


class Logger:
    def __init__(self, path: str) -> None:
        self.path = path
        Path(self.path).write_text("", encoding="utf-8")

    def log(self, message: str) -> None:
        line = f"[{now_text()}] {message}"
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


@dataclass
class Chunk:
    index: int
    start: int
    end: int
    data: bytes


def split_chunks(payload: bytes, lmin: int, lmax: int, seed: int | None) -> list[Chunk]:
    if lmin <= 0 or lmax <= 0 or lmin > lmax:
        raise ValueError("require 0 < Lmin <= Lmax")

    rng = random.Random(seed)
    chunks: list[Chunk] = []
    start = 0
    index = 1
    while start < len(payload):
        block_len = rng.randint(lmin, lmax)
        end = min(start + block_len, len(payload))
        chunks.append(Chunk(index=index, start=start, end=end, data=payload[start:end]))
        start = end
        index += 1
    return chunks


def run_client(
    host: str,
    port: int,
    input_path: str,
    output_path: str,
    lmin: int,
    lmax: int,
    seed: int | None,
    log_path: str,
) -> None:
    logger = Logger(log_path)
    original = Path(input_path).read_bytes()
    chunks = split_chunks(original, lmin, lmax, seed)
    responses: dict[int, bytes] = {}

    with socket.create_connection((host, port)) as sock:
        logger.log(f"connected to {host}:{port}")

        send_frame(sock, TYPE_INITIALIZATION, struct.pack("!I", len(chunks)))
        logger.log(f"send Initialization, chunk_count={len(chunks)}")

        frame_type, payload = recv_frame(sock)
        if frame_type != TYPE_AGREE or payload:
            raise ValueError("server did not return agree frame")
        logger.log("recv agree")

        for chunk in chunks:
            send_frame(sock, TYPE_REVERSE_REQUEST, chunk.data)
            logger.log(
                f"send reverseRequest #{chunk.index}, "
                f"bytes={chunk.start}-{chunk.end - 1}, payload_len={len(chunk.data)}"
            )

            frame_type, payload = recv_frame(sock)
            if frame_type != TYPE_REVERSE_ANSWER:
                raise ValueError(f"unexpected frame type {frame_type}")
            logger.log(
                f"recv reverseAnswer #{chunk.index}, "
                f"bytes={chunk.start}-{chunk.end - 1}, payload_len={len(payload)}"
            )
            # Print to stdout in the specific format required by the assignment
            print(f"{chunk.index}:{payload.decode('ascii', errors='replace')}", flush=True)
            responses[chunk.index] = payload

        # A trailing empty request cleanly marks the end of the stream.
        send_frame(sock, TYPE_REVERSE_REQUEST, b"")
        logger.log("send reverseRequest EOF marker")

    # reverse(chunk_n) + ... + reverse(chunk_1) => full file reverse
    fully_reversed = b"".join(responses[index] for index in range(len(chunks), 0, -1))
    Path(output_path).write_bytes(fully_reversed)
    logger.log(
        f"write reversed output to {output_path}, original_size={len(original)}, "
        f"output_size={len(fully_reversed)}"
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Task1 TCP reverse client")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=9001)
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", default="reversed_output.txt")
    parser.add_argument("--lmin", type=int, default=40)
    parser.add_argument("--lmax", type=int, default=80)
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--log", default="run_log.txt")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    run_client(
        host=args.host,
        port=args.port,
        input_path=args.input,
        output_path=args.output,
        lmin=args.lmin,
        lmax=args.lmax,
        seed=args.seed,
        log_path=args.log,
    )
