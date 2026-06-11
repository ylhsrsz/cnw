# Task1 TCP 抓包说明文档

**页眉：** `2026春计网课程实习抓包说明 | 创建者学号后四位：2308`

**页脚：** `创建者：2308 | 页码：第 __ 页 | 提交日期：____-__-__`

**创建者学号后四位：2308**

## 1. 文档信息

- 任务名称：Task1 TCP Socket Programming
- 文档名称：`tcp_packet_capture_2308.md`
- 配套抓包文件：`resources/pcap/task1/task1_tcp_capture_2308.pcapng`
- 配套日志目录：`resources/logs/task1/`
- 配套截图目录：`resources/images/task1/`

## 2. 实验目的

1. 验证 TCP 任务中客户端与服务端的报文交互过程。
2. 观察 `Initialization / agree / reverseRequest / reverseAnswer` 四类报文。
3. 将 Wireshark 抓包证据与程序日志证据对应起来。
4. 说明程序在随机分块发送场景下的报文表现。

## 3. 实验环境

- 操作系统：
- Python 版本：
- Wireshark 版本：
- 客户端 IP：
- 服务端 IP：
- 监听端口：
- 输入文件名：
- 输出文件名：
- `Lmin`：
- `Lmax`：
- `seed`：

## 4. 抓包准备

### 4.1 工具准备

- 已安装 Wireshark；
- 已确认抓包网卡；
- 已准备客户端与服务端运行命令；
- 已开启终端日志观察窗口。

### 4.2 过滤条件

建议填写实际使用的过滤器：

```text
tcp.port == 9001
```

如果实际端口不同，请替换为真实端口号。

## 5. 操作流程

### 5.1 服务端启动

记录实际命令：

```bash
python task1/reversetcpserver.py --host 127.0.0.1 --port 9001 --log task1/run_log_server.txt
```

记录启动时间：

- 服务端启动时间：

### 5.2 客户端启动

记录实际命令：

```bash
python task1/reversetcpclient.py --host 127.0.0.1 --port 9001 --input sample.txt --output task1/reversed_output.txt --lmin 40 --lmax 80 --seed 42 --log task1/run_log_client.txt
```

记录启动时间：

- 客户端启动时间：

### 5.3 抓包步骤

1. 在 Wireshark 中选择正确网卡并开始抓包。
2. 启动 TCP 服务端。
3. 启动 TCP 客户端。
4. 观察四类关键报文是否出现。
5. 客户端运行结束后停止抓包。
6. 保存抓包文件到 `resources/pcap/task1/`。
7. 截取关键报文截图到 `resources/images/task1/`。

## 6. 关键报文分析

### 6.1 Initialization 报文

- 截图文件：
- 报文时间戳：
- 说明：
  - 客户端发送初始化报文；
  - 报文中携带总块数 `N`；
  - 该时间戳应与客户端日志中 `send Initialization` 对应。

### 6.2 agree 报文

- 截图文件：
- 报文时间戳：
- 说明：
  - 服务端确认初始化成功；
  - 应与服务端日志中的 `send agree` 对应。

### 6.3 reverseRequest 报文

- 截图文件：
- 报文时间戳：
- 报文编号：
- 对应字节范围：
- 说明：
  - 客户端发送随机长度数据块；
  - 长度应处于 `Lmin` 到 `Lmax` 范围内；
  - 可结合日志说明该块对应原文件的哪一段。

### 6.4 reverseAnswer 报文

- 截图文件：
- 报文时间戳：
- 报文编号：
- 说明：
  - 服务端返回该数据块的反转结果；
  - 应与客户端日志中的 `recv reverseAnswer` 对应。

## 7. 日志与抓包互证

请在本节填写至少 2 组互证关系：

### 7.1 互证样例一

- 抓包时间戳：
- 日志时间戳：
- 对应事件：
- 结论：

### 7.2 互证样例二

- 抓包时间戳：
- 日志时间戳：
- 对应事件：
- 结论：

## 8. 程序结果验证

- 输出文件路径：`task1/reversed_output.txt`
- 校验方式：
  - 对比输出文件是否等于原文件完整反转；
  - 对照客户端输出与服务端返回内容是否一致。

记录结果：

- 是否验证通过：
- 验证方法：
- 结论：

## 9. 问题与解决方案

建议从以下角度填写：

1. 随机分块如何保证长度合法；
2. 四类报文如何在抓包中识别；
3. 日志时间与抓包时间如何对应；
4. 若存在粘包/分段现象，如何解释。

## 10. 结论

请总结：

- 是否成功完成 Task1 抓包；
- 是否完整观察到四类报文；
- 程序行为是否与协议设计一致；
- 日志与抓包是否能相互印证。
