# Task2: UDP Socket Programming

实现基于 UDP 的“可靠传输”实验。

## 运行环境

- **Python版本**: Python 3.6+
- **第三方库**: 无 (仅使用 Python 标准库 `socket`, `struct`, `time`, `random`, `argparse`)
- **网络**: 支持本地回环 (`127.0.0.1`) 或局域网通信

## 功能特性

- 基于 UDP 自定义应用层协议，实现可靠传输。
- 增加“连接建立”阶段，模拟 TCP 面向连接过程。
- 客户端使用固定 `400` 字节发送窗口。
- 每个数据包数据部分限制在 `40..80` 字节。
- 使用累计确认与超时重传，整体行为接近 GBN（Go-Back-N）。
- 仅考虑 `client => server` 数据传输方向的不可靠性。
- 服务端支持通过 `--loss-rate` 或 `--drop-seqs` 模拟网络丢包。
- 运行时自动生成 `run_log.txt`。

## 协议设计

- `CONNECT (Type=1)`：`type(1) + student_token(2) + total_bytes(4) + total_chunks(4)`
- `CONNECT_ACK (Type=2)`：`type(1) + status(1) + server_clock(8, HH-MM-SS)`
- `DATA (Type=3)`：`type(1) + seq(4) + offset(4) + payload_len(2) + payload`
- `ACK (Type=4)`：`type(1) + cumulative_seq(4) + server_clock(8, HH-MM-SS)`
- `FIN (Type=5)`：`type(1) + total_bytes(4)`
- `FIN_ACK (Type=6)`：`type(1) + saved_bytes(4)`

*(注：`student_token = (学号后4位) XOR 0x5A3C`)*

## 文件结构

- `udpserver.py`：UDP 服务端代码
- `udpclient.py`：UDP 客户端代码

## 运行操作步骤

**1. 启动服务端**
打开终端，进入项目根目录，运行（设置 15% 的模拟丢包率）：
```bash
python task2/udpserver.py --host 127.0.0.1 --port 9002 --output task2/udp_received_output.txt --log task2/run_log_server.txt --loss-rate 0.15
```

**配置选项：**
*   `--host`: 绑定的 IP 地址 (默认 `127.0.0.1`)
*   `--port`: 监听的 UDP 端口 (默认 `9002`)
*   `--output`: 接收完毕后保存的完整文件路径
*   `--log`: 日志文件保存路径 (默认 `run_log.txt`)
*   `--loss-rate`: 模拟丢包率，取值 `0.0` 到 `1.0` (默认 `0.0`)
*   `--drop-seqs`: 指定强制丢弃的序列号列表，用于精准测试重传 (例如 `--drop-seqs 1 3 5`)

**2. 启动客户端**
再打开一个终端，进入项目根目录，运行（请替换 `--student-id-last4` 为你的学号后四位，如 2308）：
```bash
python task2/udpclient.py --host 127.0.0.1 --port 9002 --input sample.txt --chunk-min 40 --chunk-max 80 --seed 42 --timeout-ms 300 --student-id-last4 2308 --log task2/run_log_client.txt
```

**配置选项：**
*   `--host`: 服务端的 IP 地址 (默认 `127.0.0.1`)
*   `--port`: 服务端的 UDP 端口 (默认 `9002`)
*   `--input`: 待发送的原始文本文件路径
*   `--chunk-min`: 随机分块的最小字节数 (默认 `40`)
*   `--chunk-max`: 随机分块的最大字节数 (默认 `80`)
*   `--seed`: 随机数种子 (默认 `42`)
*   `--timeout-ms`: 超时重传时间，单位毫秒 (默认 `300`)
*   `--student-id-last4`: 学号后四位，必须提供
*   `--log`: 日志文件保存路径 (默认 `run_log.txt`)

## 验证方法

运行结束后，检查服务端生成的 `udp_received_output.txt` 文件，其内容应与原始输入文件（如 `sample.txt`）完全一致。客户端日志中应能观察到由于丢包触发的超时重传行为。可配合 Wireshark（过滤条件：`udp port 9002`）抓包分析协议交互与重传过程。