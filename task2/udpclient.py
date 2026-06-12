#!/usr/bin/env python3
import argparse
import random
import socket
import struct
import time
import pandas as pd
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
WINDOW_BYTES = 400

CONNECT_STRUCT = struct.Struct("!B H I I")
CONNECT_ACK_STRUCT = struct.Struct("!B B 8s")
DATA_HEADER = struct.Struct("!B I I H")
ACK_STRUCT = struct.Struct("!B I 8s")
FIN_STRUCT = struct.Struct("!B I")
FIN_ACK_STRUCT = struct.Struct("!B I")


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


@dataclass
class Chunk:
    seq: int
    start: int
    end: int
    data: bytes

    @property
    def size(self) -> int:
        return len(self.data)


def split_chunks(payload: bytes, min_len: int, max_len: int, seed: int | None) -> list[Chunk]:
    if min_len <= 0 or max_len <= 0 or min_len > max_len:
        raise ValueError("require 0 < min_len <= max_len")
    if min_len < 40 or max_len > 80:
        raise ValueError("task2 requires each UDP payload to stay within 40..80 bytes")

    rng = random.Random(seed)
    chunks: list[Chunk] = []
    start = 0
    seq = 1
    while start < len(payload):
        remaining = len(payload) - start
        if remaining < min_len:
            raise ValueError("input file is too small for the required 40..80 byte UDP payloads")

        if min_len <= remaining <= max_len:
            size = remaining
        else:
            # Always leave a valid tail, so the last packet also stays within 40..80 bytes.
            size = rng.randint(min_len, min(max_len, remaining - min_len))

        end = start + size
        chunks.append(Chunk(seq=seq, start=start, end=end, data=payload[start:end]))
        start = end
        seq += 1
    return chunks


def student_token(last4: int) -> int:
    if not 0 <= last4 <= 9999:
        raise ValueError("student-id-last4 must be within 0..9999")
    return last4 ^ XOR_MASK


def packet_for_chunk(chunk: Chunk) -> bytes:
    header = DATA_HEADER.pack(TYPE_DATA, chunk.seq, chunk.start, chunk.size)
    return header + chunk.data


def outstanding_window(chunks: list[Chunk], base_index: int, next_index: int) -> int:
    return sum(chunks[i].size for i in range(base_index, next_index))


def send_reliable(
    sock: socket.socket,
    server: tuple[str, int],
    chunks: list[Chunk],
    timeout_ms: int,
    logger: Logger,
) -> tuple[int, list[float]]:
    base_index = 0
    next_index = 0
    sent_at: dict[int, float] = {}
    
    total_transmissions = 0
    rtt_list: list[float] = []

    while base_index < len(chunks):
        while next_index < len(chunks):
            window_size = outstanding_window(chunks, base_index, next_index)
            candidate = chunks[next_index]
            if window_size + candidate.size > WINDOW_BYTES:
                break
            sock.sendto(packet_for_chunk(candidate), server)
            total_transmissions += 1
            sent_at[candidate.seq] = time.perf_counter()
            print(f"第 {candidate.seq} 个（第 {candidate.start}~{candidate.end - 1} 字节）client端已经发送")
            logger.log(
                f"send DATA #{candidate.seq}, bytes={candidate.start}-{candidate.end - 1}, "
                f"payload_len={candidate.size}"
            )
            next_index += 1

        oldest_seq = chunks[base_index].seq
        elapsed_ms = (time.perf_counter() - sent_at[oldest_seq]) * 1000
        remaining_ms = max(0.0, timeout_ms - elapsed_ms)
        sock.settimeout(remaining_ms / 1000 if remaining_ms else 0.001)

        try:
            packet, _ = sock.recvfrom(2048)
        except socket.timeout:
            logger.log(f"timeout on DATA #{oldest_seq}")
            for index in range(base_index, next_index):
                chunk = chunks[index]
                sock.sendto(packet_for_chunk(chunk), server)
                total_transmissions += 1
                sent_at[chunk.seq] = time.perf_counter()
                print(f"重传第 {chunk.seq} 个（第 {chunk.start}~{chunk.end - 1} 字节）数据包")
                logger.log(
                    f"retransmit DATA #{chunk.seq}, bytes={chunk.start}-{chunk.end - 1}, "
                    f"payload_len={chunk.size}"
                )
            continue

        packet_type = packet[0]
        if packet_type != TYPE_ACK:
            logger.log(f"ignore non-ACK packet type {packet_type}")
            continue

        _, ack_seq, server_clock = ACK_STRUCT.unpack(packet)
        if ack_seq < oldest_seq:
            logger.log(f"recv duplicate ACK cumulative_seq={ack_seq}")
            continue

        acked_chunk = chunks[ack_seq - 1]
        rtt_ms = (time.perf_counter() - sent_at[ack_seq]) * 1000
        rtt_list.append(rtt_ms)
        print(
            f"第 {ack_seq} 个（第 {acked_chunk.start}~{acked_chunk.end - 1} 字节）"
            f" server 端已经收到，RTT 是 {rtt_ms:.1f} ms，server 时间 {server_clock.decode('ascii')}"
        )
        logger.log(
            f"recv ACK cumulative_seq={ack_seq}, ack_bytes={acked_chunk.start}-{acked_chunk.end - 1}, "
            f"server_clock={server_clock.decode('ascii')}, rtt_ms={rtt_ms:.3f}"
        )
        base_index = ack_seq
        
    return total_transmissions, rtt_list


def run_client(
    host: str,
    port: int,
    input_path: str,
    chunk_min: int,
    chunk_max: int,
    seed: int | None,
    timeout_ms: int,
    student_last4: int,
    log_path: str,
) -> None:
    logger = Logger(log_path)
    payload = Path(input_path).read_bytes()
    chunks = split_chunks(payload, chunk_min, chunk_max, seed)
    server = (host, port)

    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.connect(server)

        connect_packet = CONNECT_STRUCT.pack(
            TYPE_CONNECT,
            student_token(student_last4),
            len(payload),
            len(chunks),
        )
        sock.send(connect_packet)
        logger.log(
            f"send CONNECT, total_bytes={len(payload)}, total_chunks={len(chunks)}, "
            f"student_last4={student_last4}"
        )

        sock.settimeout(2.0)
        packet = sock.recv(CONNECT_ACK_STRUCT.size)
        packet_type, status, server_clock = CONNECT_ACK_STRUCT.unpack(packet)
        if packet_type != TYPE_CONNECT_ACK or status != 1:
            raise RuntimeError("connection establishment failed")
        logger.log(f"recv CONNECT_ACK, server_clock={server_clock.decode('ascii')}")

        total_transmissions, rtt_list = send_reliable(sock, server, chunks, timeout_ms, logger)

        fin_packet = FIN_STRUCT.pack(TYPE_FIN, len(payload))
        sock.send(fin_packet)
        logger.log(f"send FIN, total_bytes={len(payload)}")

        sock.settimeout(2.0)
        packet = sock.recv(FIN_ACK_STRUCT.size)
        packet_type, actual_size = FIN_ACK_STRUCT.unpack(packet)
        if packet_type != TYPE_FIN_ACK:
            raise RuntimeError("server did not return FIN_ACK")
        logger.log(f"recv FIN_ACK, server_saved_bytes={actual_size}")

        print("\n【汇总】信息：")
        loss_rate = 1.0 - (len(chunks) / total_transmissions) if total_transmissions > 0 else 0.0
        print(f"-丢包率：{loss_rate * 100:.2f}%。按“{len(chunks)}÷实际发送的udppacketnumber({total_transmissions})”计算。")
        
        if rtt_list:
            df = pd.DataFrame(rtt_list, columns=['RTT'])
            max_rtt = df['RTT'].max()
            min_rtt = df['RTT'].min()
            avg_rtt = df['RTT'].mean()
            std_rtt = df['RTT'].std() if len(rtt_list) > 1 else 0.0
            print(f"-整个过程中的最大RTT：{max_rtt:.2f} ms")
            print(f"-整个过程中的最小RTT：{min_rtt:.2f} ms")
            print(f"-整个过程中的平均RTT：{avg_rtt:.2f} ms")
            print(f"-整个过程中的RTT标准差：{std_rtt:.2f} ms")

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Task2 reliable UDP client")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=9002)
    parser.add_argument("--input", required=True)
    parser.add_argument("--chunk-min", type=int, default=40)
    parser.add_argument("--chunk-max", type=int, default=80)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--timeout-ms", type=int, default=300)
    parser.add_argument("--student-id-last4", type=int, default=1234)
    parser.add_argument("--log", default="run_log.txt")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    run_client(
        host=args.host,
        port=args.port,
        input_path=args.input,
        chunk_min=args.chunk_min,
        chunk_max=args.chunk_max,
        seed=args.seed,
        timeout_ms=args.timeout_ms,
        student_last4=args.student_id_last4,
        log_path=args.log,
    )
