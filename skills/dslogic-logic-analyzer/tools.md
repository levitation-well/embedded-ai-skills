# 安装与方案评估

[SKILL.md](SKILL.md) 的附属参考：要装什么、怎么装，以及评估过的接入方案。

## 安装

| 工具 | 用途 | 获取 |
| --- | --- | --- |
| DSView | 梦源官方上位机；安装时会装好 WinUSB 驱动，本 skill 直接用这个驱动 | https://www.dreamsourcelab.com/download/ |
| logic-agent（npm 包 `logic-agent-mcp`） | 使用其中的 `dslab.exe`（采集）、`sigrok-cli.exe` 和协议解码器（解码） | https://github.com/chenyingchun0312/logic-agent |
| Python 3.10 以上 | 运行本 skill 的脚本，只用标准库 | https://www.python.org/downloads/ |
| 图莫斯 USB2XXX 二次开发示例（可选） | 闭环测试用：`sdk\libs\windows\x86_64` 里的 `USB2XXX.dll` | https://gitee.com/toomoss/usb2can_lin_pwm_example |

logic-agent 建议下载固定版本，不要用 `npx`，因为 `npx` 每次都会拉最新版：

```powershell
mkdir $env:USERPROFILE\.local\logic-agent-1.2.1; cd $env:USERPROFILE\.local\logic-agent-1.2.1
npm pack logic-agent-mcp@1.2.1 --ignore-scripts
tar -xzf logic-agent-mcp-1.2.1.tgz
```

解压后的 `package\runtime` 就是 `la_config.json` 里的 `runtime`。

包里还有两个程序，**U2Basic 等非 Plus 型号不要运行**：

- `INSTALL-DRIVER.cmd`：用 Zadig 换驱动；DSView 已经装好驱动，不需要换。
- `FIRMWARE-RECOVER.cmd`：刷固件，只针对 DSLogic Plus。

## 方案评估（2026-11 实测，设备 DSLogic U2Basic）

测试方法：图莫斯 LIN 工具发 7 种帧 × 5 轮，逻辑分析仪采集后，逐帧和发送清单比对。

| 方案 | 实测结果 | 结论 |
| --- | --- | --- |
| **dslab 命令行（logic-agent 自带）+ 本地解码** | 流模式 1 MHz 35/35；缓存模式 100 MHz 7/7；硬件触发可用，阈值可设，不用开界面，每次 2–5 s；VCD 只记翻转（0.3 s 的波形约 5 KB） | **选用**，即本 skill |
| ALL LOGIC 1.4.0 的 MCP（https://github.com/Doukeyi-X/ALL-LOGIC ，HTTP `127.0.0.1:10110`，14 个工具） | 流模式 35/35，缓存模式 20 MHz 7/7，阈值可设 | 能用，但问题较多，见下 |
| logic-agent 1.2.1 的 MCP（stdio，10 个工具） | 能采集、能触发，工具设计最好：结果有上限，原始数据按编号存盘，LIN 解码可设波特率；但没有阈值参数，固定 1.0 V，在 12 V 的 LIN 总线上解出 0 帧 | 只适合 3.3/5 V 逻辑信号；以后加了阈值参数，就是最合适的 MCP |
| sigrok-cli、PulseView 上游，以及基于 sigrok 的 MCP | libsigrok 的 dreamsourcelab-dslogic 驱动只认 PID 0x0001/0x0003/0x0020/0x0021，没有 U2Basic（0x0035） | 梦源新款不能采集；sigrok-cli 只用来解码文件 |
| heng5411/dslogic-mcp | 纯 Python 移植的驱动，只支持 U3Pro16、U3Pro32 | U2 系列不能用 |
| zeng-andrew/instrument-mcp | 逻辑分析仪只支持 U3Pro16；代码里有连接云端的模块 | 不推荐 |
| felixfinal/agent-dsviewer-logic-analyzer、phil16021/DSView_rust | 目前只有 Linux 版本 | Windows 上不能用 |
| DSView 界面手动导出 + AI 读文件 | 能用，但每次都要人操作 | 兜底；logic-agent MCP 的 `import_csv` 能读 DSView 导出的 CSV |

ALL LOGIC 的 MCP 有五个问题：

- 必须开着界面程序；
- 没有触发参数，缓存模式下实际开始记录比 `start_capture` 返回晚约 50 ms；
- 只开 1 个通道时，导出超过约 50 万样本程序会崩溃；
- 内置解码器不能设波特率，LIN、UART 19200 解不出来，解码结果也不带时间；
- 导出的 CSV 每个样本一行，500 万样本有 61 MB。

ALL LOGIC 的安全注意：程序一启动就开 MCP，不鉴权，还返回 `Access-Control-Allow-Origin: *`。也就是说，浏览器里任何网页都能调用它的 `export_csv`，在任意路径写文件。不用时请关掉程序。

## 正点原子 ATK-Logic（只做了调研，未实测）

- **hugelzhang/atk-logic-mcp**：目前唯一专门为 ATK-Logic（USB `1A86:FFCC`，DL16 等）写的 MCP，13 个工具，MIT 许可。代价有三条：
  - 要用 Zadig 把驱动换成 WinUSB，换了以后原厂上位机用不了，要换回驱动才能恢复；
  - 作者注明硬件触发不生效；
  - 项目很新很小，用前先审它的源码和安装脚本。
- **ALL LOGIC 1.4.0**：发布说明写明支持 ATK-Logic（DL16 等），MCP 的情况和上面相同。
- **CapnRon/alientek-dl16-sigrok-pulseview**：给 sigrok 加了 DL16 驱动的社区分支，只在 Linux 上验证过。
- 正点原子官方上位机源码 `alientek-openedv/atk-logic`：只有界面，没有命令行或脚本接口。

建议：拿到正点原子设备后，先试 ALL LOGIC，它不用换驱动；再判断是否值得为 atk-logic-mcp 换驱动。
