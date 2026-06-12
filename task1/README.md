# Task1: TCP Socket Programming

实现基于 TCP 的“文本分块反转”实验。

## 运行环境

- **Python版本**: Python 3.6+
- **第三方库**: 无 (仅使用 Python 标准库 `socket`, `struct`, `threading`, `random`, `argparse`)
- **网络**: 支持本地回环 (`127.0.0.1`) 或局域网通信

## 功能特性

- 采用 4 类自定义报文协议：
  - `Initialization (Type=1)`：客户端先发送总块数 `N`
  - `agree (Type=2)`：服务端确认
  - `reverseRequest (Type=3)`：客户端发送待反转的数据块
  - `reverseAnswer (Type=4)`：服务端返回反转后的块
- 客户端按 `Lmin..Lmax` 随机分块发送。
- 服务端支持多客户端并发，使用线程处理。
- 客户端最终输出整个原文件的“完整反转结果”，而非单纯逐块反转。
- 客户端在控制台按照 `第x块:反转的文本` 的格式打印每个分块的接收结果。
- 运行时自动生成 `run_log.txt`，记录精确到毫秒的时间戳。

## 文件结构

- `reversetcpserver.py`：TCP 服务端代码
- `reversetcpclient.py`：TCP 客户端代码

## 运行操作步骤

**1. 启动服务端**
打开终端，进入项目根目录，运行：
```bash
python task1/reversetcpserver.py --host 127.0.0.1 --port 9001 --log task1/run_log_server.txt
```

**配置选项：**
*   `--host`: 绑定的 IP 地址 (默认 `127.0.0.1`)
*   `--port`: 监听的 TCP 端口 (默认 `9001`)
*   `--log`: 日志文件保存路径 (默认 `run_log.txt`)

**2. 启动客户端 (单次测试)**
再打开一个终端，进入项目根目录，运行：
```bash
python task1/reversetcpclient.py --host 127.0.0.1 --port 9001 --input sample.txt --output task1/reversed_output.txt --lmin 40 --lmax 80 --seed 42 --log task1/run_log_client.txt
```

**配置选项：**
*   `--host`: 服务端的 IP 地址 (默认 `127.0.0.1`)
*   `--port`: 服务端的 TCP 端口 (默认 `9001`)
*   `--input`: 待发送的原始文本文件路径
*   `--output`: 反转后文件的保存路径
*   `--lmin`: 随机分块的最小字节数 (默认 `40`)
*   `--lmax`: 随机分块的最大字节数 (默认 `80`)
*   `--seed`: 随机数种子，用于生成固定序列的随机分块 (默认 `42`)
*   `--log`: 日志文件保存路径 (默认 `run_log.txt`)

**3. 多客户端并发测试**
若要测试服务端的并发处理能力，请在启动服务端后，同时打开两个新的终端并分别运行以下命令：

终端 A (发送 sample.txt):
```bash
python task1/reversetcpclient.py --host 127.0.0.1 --port 9001 --input sample.txt --output task1/output1.txt --lmin 40 --lmax 80 --seed 42 --log task1/run_log_client1.txt
```

终端 B (发送 sample2.txt):
```bash
python task1/reversetcpclient.py --host 127.0.0.1 --port 9001 --input sample2.txt --output task1/output2.txt --lmin 20 --lmax 50 --seed 99 --log task1/run_log_client2.txt
```

## 验证方法

运行结束后，检查生成的 `reversed_output.txt` 文件，其内容应等于原始输入文件（如 `sample.txt`）整体倒序后的内容。可配合 Wireshark（过滤条件：`tcp port 9001`）抓包分析协议交互过程。