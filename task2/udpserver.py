#!/usr/bin/env python3
import argparse
import random
import socket
import struct
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


TYPE_CONNECT = 1
TYPE_CONNECT_ACK = 2
TYPE_DATA = 3
TYPE_ACK = 4
TYPE_FIN = 5
TYPE_FIN_ACK = 6

XOR_MASK = 0x5A3C

CONNECT_STRUCT = struct.Struct("!B H I I")
CONNECT_ACK_STRUCT = struct.Struct("!B B 8s")
DATA_HEADER = struct.Struct("!B I I H")
ACK_STRUCT = struct.Struct("!B I 8s")
FIN_STRUCT = struct.Struct("!B I")
FIN_ACK_STRUCT = struct.Struct("!B I")


def now_text() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]


def server_clock_text() -> bytes:
    return datetime.now().strftime("%H-%M-%S").encode("ascii")


class Logger:
    def __init__(self, path: str) -> None:
        self.path = path
        Path(self.path).write_text("", encoding="utf-8")

    def log(self, message: str) -> None:
        line = f"[{now_text()}] {message}"
        with open(self.path, "a", encoding="utf-8") as handle:
            handle.write(line + "\n")
        print(line, flush=True)


@dataclass
class Session:
    addr: tuple[str, int]
    total_bytes: int
    total_chunks: int
    expected_seq: int = 1
    last_acked_seq: int = 0
    payload: bytearray | None = None

    def __post_init__(self) -> None:
        if self.payload is None:
            self.payload = bytearray()


class LossModel:
    def __init__(self, loss_rate: float, drop_seqs: set[int]) -> None:
        self.loss_rate = loss_rate
        self.drop_seqs = set(drop_seqs)
        self.random = random.Random(42)
        self.dropped_once: set[int] = set()

    def should_drop(self, seq: int) -> bool:
        if seq in self.dropped_once:
            return False
        if seq in self.drop_seqs:
            self.dropped_once.add(seq)
            return True
        if self.loss_rate > 0 and self.random.random() < self.loss_rate:
            self.dropped_once.add(seq)
            return True
        return False


def parse_drop_seqs(raw: str) -> set[int]:
    if not raw:
        return set()
    return {int(item.strip()) for item in raw.split(",") if item.strip()}


def serve(host: str, port: int, output_path: str, log_path: str, loss_rate: float, drop_seqs: set[int]) -> None:
    logger = Logger(log_path)
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((host, port))
    loss_model = LossModel(loss_rate=loss_rate, drop_seqs=drop_seqs)
    session: Session | None = None
    logger.log(f"listening on {host}:{port}")

    try:
        while True:
            packet, addr = sock.recvfrom(4096)
            if not packet:
                continue
            packet_type = packet[0]

            if packet_type == TYPE_CONNECT:
                _, student_token, total_bytes, total_chunks = CONNECT_STRUCT.unpack(packet)
                recovered = student_token ^ XOR_MASK
                valid = 0 <= recovered <= 9999
                session = Session(addr=addr, total_bytes=total_bytes, total_chunks=total_chunks)
                logger.log(
                    f"recv CONNECT from {addr}, token=0x{student_token:04x}, "
                    f"recovered_last4={recovered}, total_bytes={total_bytes}, "
                    f"total_chunks={total_chunks}, valid={valid}"
                )
                status = 1 if valid else 0
                sock.sendto(CONNECT_ACK_STRUCT.pack(TYPE_CONNECT_ACK, status, server_clock_text()), addr)
                logger.log(f"send CONNECT_ACK to {addr}, status={status}")
                continue

            if session is None or addr != session.addr:
                logger.log(f"ignore packet from unexpected peer {addr}")
                continue

            if packet_type == TYPE_DATA:
                header = packet[:DATA_HEADER.size]
                _, seq, offset, payload_len = DATA_HEADER.unpack(header)
                payload = packet[DATA_HEADER.size:]
                if len(payload) != payload_len:
                    logger.log(f"ignore DATA #{seq}: payload length mismatch")
                    continue

                logger.log(
                    f"recv DATA #{seq}, bytes={offset}-{offset + payload_len - 1}, "
                    f"payload_len={payload_len}"
                )

                if loss_model.should_drop(seq):
                    logger.log(f"simulate loss for DATA #{seq}")
                    continue

                if seq == session.expected_seq:
                    session.payload.extend(payload)
                    session.last_acked_seq = seq
                    session.expected_seq += 1
                else:
                    logger.log(
                        f"discard out-of-order DATA #{seq}, expected_seq={session.expected_seq}"
                    )

                sock.sendto(
                    ACK_STRUCT.pack(TYPE_ACK, session.last_acked_seq, server_clock_text()),
                    addr,
                )
                logger.log(f"send ACK cumulative_seq={session.last_acked_seq}")
                continue

            if packet_type == TYPE_FIN:
                _, total_received = FIN_STRUCT.unpack(packet)
                Path(output_path).write_bytes(bytes(session.payload))
                logger.log(
                    f"recv FIN, declared_bytes={total_received}, "
                    f"actual_bytes={len(session.payload)}"
                )
                sock.sendto(FIN_ACK_STRUCT.pack(TYPE_FIN_ACK, len(session.payload)), addr)
                logger.log(f"send FIN_ACK, saved file to {output_path}")
                session = None
                continue

            logger.log(f"ignore unknown packet type {packet_type}")
    except KeyboardInterrupt:
        logger.log("server interrupted by user")
    finally:
        sock.close()
        logger.log("server stopped")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Task2 reliable UDP server")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=9002)
    parser.add_argument("--output", default="udp_received_output.txt")
    parser.add_argument("--log", default="run_log.txt")
    parser.add_argument("--loss-rate", type=float, default=0.15)
    parser.add_argument("--drop-seqs", default="")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    serve(
        host=args.host,
        port=args.port,
        output_path=args.output,
        log_path=args.log,
        loss_rate=args.loss_rate,
        drop_seqs=parse_drop_seqs(args.drop_seqs),
    )
