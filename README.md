# 2026 春计网课程实习

本仓库按文档要求提供两个 Python 版本任务，分别是基于 TCP 的文本分块反转（Task1）和基于 UDP 的可靠传输（Task2）。

## 目录结构

```text
task1/
  reversetcpclient.py
  reversetcpserver.py
  README.md
task2/
  udpclient.py
  udpserver.py
  README.md
README.md (本文档)
```

## 任务说明

*   **Task1** 的详细说明、协议设计与运行步骤，请查看 [task1/README.md](./task1/README.md)
*   **Task2** 的详细说明、协议设计与运行步骤，请查看 [task2/README.md](./task2/README.md)

## 通用验证建议

- 使用只包含 ASCII 可打印字符的文本文件（如 `sample.txt`）进行测试。
- 始终**先启动服务端，再启动客户端**。
- 如需抓包分析，请提前配置好 Wireshark（选择本地回环网卡 `Loopback`），并使用对应的端口过滤规则（`tcp port 9001` 或 `udp port 9002`）。