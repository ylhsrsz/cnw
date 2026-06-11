# 2026 春计网课程实习

本仓库按文档要求提供两个 Python 版本任务：

- `task1`：TCP socket programming
- `task2`：UDP socket programming

## 目录结构

```text
task1/
  reversetcpclient.py
  reversetcpserver.py
task2/
  udpclient.py
  udpserver.py
README.md
```

## Task1

实现要点：

- 采用 4 类报文：
  - `Initialization (Type=1)`：客户端先发送总块数 `N`
  - `agree (Type=2)`：服务端确认
  - `reverseRequest (Type=3)`：客户端发送待反转的数据块
  - `reverseAnswer (Type=4)`：服务端返回反转后的块
- 客户端按 `Lmin..Lmax` 随机分块
- 服务端支持多客户端并发，使用线程处理
- 运行时自动生成 `run_log.txt`
- 客户端最终输出整个原文件的“完整反转结果”

### 运行

服务端：

```bash
python task1/reversetcpserver.py --host 0.0.0.0 --port 9001 --log task1/run_log.txt
```

客户端：

```bash
python task1/reversetcpclient.py --host 127.0.0.1 --port 9001 --input sample.txt --output task1/reversed_output.txt --lmin 40 --lmax 80 --seed 42 --log task1/run_log.txt
```

## Task2

实现要点：

- 基于 UDP 自定义应用层协议
- 增加“连接建立”阶段，模拟面向连接过程
- 客户端使用固定 `400` 字节发送窗口
- 每个数据包数据部分限制在 `40..80` 字节
- 使用累计确认与超时重传，整体行为接近 GBN
- 仅考虑 `client => server` 数据传输方向的不可靠性
- 服务端支持通过 `--loss-rate` 或 `--drop-seqs` 模拟丢包
- 运行时自动生成 `run_log.txt`

### 协议设计

- `CONNECT (Type=1)`：`type(1) + student_token(2) + total_bytes(4) + total_chunks(4)`
- `CONNECT_ACK (Type=2)`：`type(1) + status(1) + server_clock(8, HH-MM-SS)`
- `DATA (Type=3)`：`type(1) + seq(4) + offset(4) + payload_len(2) + payload`
- `ACK (Type=4)`：`type(1) + cumulative_seq(4) + server_clock(8, HH-MM-SS)`
- `FIN (Type=5)`：`type(1) + total_bytes(4)`
- `FIN_ACK (Type=6)`：`type(1) + saved_bytes(4)`

说明：

- `student_token = (学号后4位) XOR 0x5A3C`
- 服务端会把接收到的数据保存为输出文件
- 客户端会打印每次确认和重传信息

### 运行

服务端：

```bash
python task2/udpserver.py --host 0.0.0.0 --port 9002 --output task2/udp_received_output.txt --log task2/run_log.txt --loss-rate 0.15
```

客户端：

```bash
python task2/udpclient.py --host 127.0.0.1 --port 9002 --input sample.txt --chunk-min 40 --chunk-max 80 --seed 42 --timeout-ms 300 --student-id-last4 1234 --log task2/run_log.txt
```

## 验证建议

- 使用只包含 ASCII 可打印字符的文本文件测试
- 启动服务端后再启动客户端
- 对 `task1` 检查输出文件是否等于原文件完整反转
- 对 `task2` 检查服务端保存文件是否与原文件一致
- 如需抓包，可用 Wireshark 过滤对应端口
