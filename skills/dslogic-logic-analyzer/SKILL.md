---
name: dslogic-logic-analyzer
description: 让 AI 不开界面直接操作梦源 DSLogic 逻辑分析仪的手册：采集（阈值、硬件触发、流模式和缓存模式）、LIN 解码与时序测量、调用 sigrok 解码其他协议、保存日志，以及和图莫斯 LIN 工具做收发闭环测试。抓波形、量脉宽/波特率/帧间隔、验证 LIN/UART/SPI/I2C 报文，或评估逻辑分析仪 MCP 方案时使用。
---

# DSLogic 逻辑分析仪

AI 用命令行直接采集、解码、测量，不开 DSView 界面。2026-11 在 **DSLogic U2Basic**（USB `2A0E:0035`，16 通道）上实测通过；同一驱动库支持的其他 DSLogic 型号理论上可用，未实测。

采集用 logic-agent 自带的 `dslab.exe`（基于 DSView 1.3.2 的驱动库），解码和测量由本 skill 的脚本在本地完成。为什么选这条路、各家 MCP 为什么不用，见 [tools.md](tools.md)。

| 脚本和命令 | 作用 |
|---|---|
| `la.py devices` | 找设备，列出采样率和默认阈值 |
| `la.py capture --ch N --rate R --dur T [--trig D1=F] [--buffer]` | 采集，存 VCD，打印每个通道的翻转数和高低电平宽度范围 |
| `la.py lin <运行目录> --ch N` | 解 LIN：PID 校验、增强/经典校验和、Break 位数、波特率、帧间隔，写 `lin_D<N>.tsv` |
| `la.py pulses <运行目录> --ch N [--at T --span T]` | 查窗口内每段电平和宽度，算周期、频率、占空比 |
| `la.py decode <运行目录> -P "uart:rx=D1:baudrate=19200,lin"` | 调用 sigrok-cli 的 150 多个协议解码器 |
| `lin_loop_test.py` | 和图莫斯 LIN 工具做收发闭环测试 |

运行方式：`python -I <本 skill>\scripts\la.py <命令> ...`。每次最后一行是 `RESULT: OK` 或 `RESULT: FAIL <原因>`。

每次采集生成一个运行目录（按时间命名），里面有：

- `capture.vcd`：只记电平翻转，很小；
- `capture.raw`、`meta.json`（采样率等）；
- `la_args.json`：本次参数；
- 解码出的 TSV。

## 准备

第一次使用前确认三件事，缺哪项就按 [tools.md](tools.md) 的安装一节补：

1. 装过 DSView，并且 DSView 能认出分析仪。它装的 WinUSB 驱动本 skill 直接用，不要换驱动。
2. logic-agent 已下载解压，`scripts\la_config.json` 写好路径。格式参考 `la_config.example.json`，也可以用环境变量 `LOGIC_AGENT_RUNTIME`、`LA_CAPTURES`、`TOOMOSS_SDK` 代替。
3. 运行 `python -I scripts\la.py devices`，看到设备名和 `RESULT: OK`。

`FAIL ... 正开着并占着分析仪` 表示 DSView 或 ALL LOGIC 开着。USB 同一时间只能给一个程序，请用户关掉。

接线以用户说的为准，没说就问：哪个 DSLogic 通道接哪根线，地接在哪。不知道接在哪个通道时，开 16 个通道采一次，翻转最多的就是。

## 采集

- **阈值 `--vth`**：脚本默认 2.0 V。dslab 每次打开设备都把阈值复位成 1.0 V，不会记住上次的设置，所以每次都要传。12 V 的 LIN 总线用 1.0 V 会把 Break 采成一串十几微秒的毛刺，因为显性电平就在 1 V 附近。3.3 V、5 V 逻辑用 1.0–2.0 V 都行。
- **流模式（默认）和缓存模式**：
  - 流模式边采边传，U2Basic 最高 20 MHz，能采几秒到几十秒，适合抓一串帧、量帧间隔。
  - `--buffer` 是缓存模式，数据先存在分析仪内存里，最高 100 MHz，但窗口短（100 MHz 下 0.2 s 实测没问题），适合量单个边沿、位宽。
- **触发**：`--trig D1=F` 表示通道 1 出现下降沿时开始记录，正好是 LIN 的 Break 起点。`--trig-pos` 是触发点在窗口里的百分比位置，默认 1%。
- **和别的程序配合**：先启动采集，等 1–2 s，再发信号。dslab 打开设备要约 1.5 s，信号来得太早就等不到触发，最后超时失败。

## 和图莫斯做收发闭环测试

验证"发出去的帧在总线上长什么样"或"收发是否一致"时，用 `scripts\lin_loop_test.py`：

```
python -I scripts\lin_loop_test.py [--la-ch 1] [--lin-ch 0] [--rate 1M --dur 3s | --buffer --rate 100M --dur 0.2s] [--ids 2A,2B,...]
```

脚本的流程：

1. 启动 `la.py capture`，通道下降沿触发，等 2 s 让 dslab 打开设备。
2. 用图莫斯 `LIN_EX_MasterWrite` 发 7 种帧，覆盖数据 1/2/4/8 字节、增强和经典校验、只有帧头，共 5 轮。
3. 解码，和发送清单逐帧比对 ID、数据、校验类型，比对表写进运行目录的 `loop_compare.tsv`。

图莫斯 SDK 是官方二次开发示例里的 `sdk\libs\windows\x86_64`（含 `USB2XXX.dll`），获取地址见 [tools.md](tools.md)。

发帧前先看工程的 LDF，避开总线上从机会响应的 ID（用 `--ids` 换），也不要发诊断帧 0x3C：首字节 0x00 会让从机进入睡眠。

## 读结果

- **先看统计**：`lin` 的统计行包括错误帧数、波特率偏差、Break 位数、帧间隔。逐帧细节在 TSV 里，表格交给用户时直接给 TSV。
- **波特率精度取决于采样率**：1 MHz 下时间分辨率是 1 µs，用 8 位 Sync 算出的波特率只能精确到 ±0.3%，所以会在 19185 和 19231 之间跳。20 MHz 以上能精确到 ±0.01%。
- **在总线上量占空比会偏**：只有一个阈值时，总线下降沿慢、上升沿在低端快。2.0 V 阈值量到的显性位是 50 µs、隐性位是 54 µs（标称 52.1 µs），偏差来自阈值的位置，不是发送端的问题。
  - ISO 17987-4 的占空比 D1/D2 要在两个指定的电压阈值上量，用示波器。逻辑分析仪只用来判断报文内容和大致时序。
  - 量 MCU 的 TXD/RXD（逻辑电平）时没有这个问题。
- **其他协议用 `decode`**：`-P` 里的通道写 `D<n>`。脚本会把它换成 sigrok 读 VCD 时用的名字 `logic.<n>`，并按实际采样率降采样，不降采样会慢 4 倍左右。解码器名和选项查 `<logic-agent 运行目录>\decoders\<名字>\pd.py`。

## 已知坑

- **sigrok-cli 上游和 PulseView 不支持 DSLogic U2、U3 系列**：libsigrok 的 dreamsourcelab-dslogic 驱动只认 DSLogic、Pro、Plus、Basic 四个老型号。sigrok-cli 只用来解码文件，采集走 dslab。
- **logic-agent 1.2.1 的 MCP 没有阈值参数**：固定 1.0 V 采集，接 12 V 总线时采到的波形是错的（见阈值一条）。它的 MCP 只适合 3.3/5 V 逻辑信号；量总线用本 skill 的 `la.py`。
- **ALL LOGIC 1.4.0 的 MCP**：只开 1 个通道时，`export_csv` 超过约 50 万样本程序会崩溃；没有触发参数；内置解码器不能设波特率。

## 维护

用的时候发现新现象、新坑或新做法，写进 [log.md](log.md) 顶部，格式是"日期 — 现象 → 原因 → 做法"。同样的事出现第二次，就提炼进本文件对应的小节。
