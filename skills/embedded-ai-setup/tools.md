# 工具清单

## 选工具的标准

AI 最擅长处理文本。选工具时，优先选能用文本和 AI 交互的，也就是对 AI 友好的工具：

- 有命令行、开发包或公开的通信协议。
- 不需要图形界面就能运行，输出结果能被程序读取。
- 不光能下命令，还能查询状态。
- 不和 IDE 争抢资源，不需要更换驱动。

## 清单

链接核实于 2026-11-03（逻辑分析仪一节 2026-11-04）。软件的版本、许可和安装方法以官方页面为准。

### 前置软件

| 工具 | 用途 | 获取地址 |
| --- | --- | --- |
| PowerShell 7 | 运行脚本和各工具的命令行 | https://github.com/PowerShell/PowerShell |
| Python 3 | 写测试脚本，运行 pyOCD 等 Python 工具 | https://www.python.org/downloads/ |
| Git for Windows（含 Git Bash） | 版本管理；很多智能体用 Git Bash 执行命令 | https://git-scm.com/downloads/win |
| Node.js | 运行用 npm 分发的工具，例如 chrome-devtools-mcp | https://nodejs.org/ |

### MCU 开发

| 工具 | 让 AI 能做什么 | 获取地址 | 要用户本人做的事 |
| --- | --- | --- | --- |
| Keil MDK | 用命令行模式编译、烧录，不打开界面；AI 自己读编译日志、改错 | https://www.keil.arm.com/ | 商业软件，要申请许可证；安装要管理员权限 |
| 芯片支持包（CMSIS-Pack） | 提供烧录算法和寄存器描述文件（SVD），AI 用 SVD 看懂寄存器每一位的含义 | https://www.keil.arm.com/packs/ ，或芯片厂商官网 | 告诉 AI 用的是哪颗芯片 |
| SEGGER J-Link 软件包 | 用命令行工具连接芯片，CPU 不停机，在后台读寄存器和内存 | https://www.segger.com/downloads/jlink/ | 要有 J-Link 调试器；安装要管理员权限（含 USB 驱动） |
| pyOCD | 不经过 IDE 直接烧录和读写内存，烧完马上接着测试 | https://github.com/pyocd/pyOCD | 无 |
| dbgprobe-mcp-server | 让 AI 自己打断点、单步执行、暂停和继续（MCP 服务） | https://github.com/es617/dbgprobe-mcp-server | 注册到智能体后，重开一次会话 |

### 电源和总线

| 工具 | 让 AI 能做什么 | 获取地址 | 要用户本人做的事 |
| --- | --- | --- | --- |
| FNIRSI DPS-150 数控电源 | 通过 USB 虚拟串口上电、断电、设电压和限流、缓升缓降、记录电流；能测上电和下电时的复位 | https://www.fnirsi.com/ | 购买硬件，接好 USB 线 |
| 图莫斯 USB2XXX（LIN/CAN 工具） | 用官方动态库发帧、收帧，用 Python 写自动测试脚本 | https://gitee.com/toomoss/usb2can_lin_pwm_example （官方二次开发示例和动态库） | 购买硬件，接好总线 |

### 硬件设计

| 工具 | 让 AI 能做什么 | 获取地址 | 要用户本人做的事 |
| --- | --- | --- | --- |
| 嘉立创 EDA 专业版 | 画原理图和 PCB | https://pro.lceda.cn/ | 注册账号 |
| easyeda-agent | 让 AI 读写原理图和 PCB，读回网表，跑设计规则检查（DRC） | https://github.com/zhoushoujianwork/easyeda-agent | 在 EDA 里装好连接器插件，并允许外部交互 |

### 资料整理

| 工具 | 让 AI 能做什么 | 获取地址 |
| --- | --- | --- |
| MinerU | 用 OCR 把 PDF 识别成文本草稿，再由 AI 校准成 Markdown | https://github.com/opendatalab/MinerU |
| Unlimited-OCR | 同上，可以和 MinerU 互相对照 | https://github.com/baidu/Unlimited-OCR |

### 可选

| 工具 | 让 AI 能做什么 | 获取地址 |
| --- | --- | --- |
| chrome-devtools-mcp | 让 AI 操作已登录的 Chrome，例如查在线资料、下载手册 | https://github.com/ChromeDevTools/chrome-devtools-mcp |

### 逻辑分析仪

逻辑分析仪接入 AI，目的是让 AI 拿到原始采样，自己算脉宽、波特率、帧间隔，再和代码、手册对照，而不是看一张截图。选方案时看三点：不开界面能不能采集，能不能设阈值和触发，输出是不是只记电平翻转的文件（例如 VCD，几秒的波形只有几 KB）。

下表核实于 2026-11-04，“实测”指在梦源 DSLogic U2Basic 上，用 LIN 工具发帧、逐帧比对过。

| 方案 | 让 AI 能做什么 | 获取地址 | 实测与注意 |
| --- | --- | --- | --- |
| 梦源 DSLogic + logic-agent 自带的 dslab 命令行（推荐） | 不开界面采集，设阈值、硬件触发，输出 VCD；AI 用脚本解码和测量。同一个包里的 sigrok-cli 能解 150 多种协议 | https://github.com/chenyingchun0312/logic-agent （npm 包 `logic-agent-mcp`） | 实测流模式 1 MHz 采几秒、缓存模式 100 MHz，收发帧全部一致。用 `npm pack` 下载固定版本后解压使用 |
| logic-agent 的 MCP | 采集后按编号存盘，只返回统计和有上限的解码结果，不把整段波形塞给 AI | 同上 | 工具设计好。1.2.1 版不能设阈值，固定 1.0 V，适合 3.3 V、5 V 逻辑信号；直接量 12 V 的 LIN 总线会采错 |
| ALL LOGIC（基于 DSView 修改，支持梦源、正点原子、Sipeed 等多家） | 界面程序内置 HTTP MCP，能配置、采集、导出 CSV | https://github.com/Doukeyi-X/ALL-LOGIC | 实测能采集和导出。没有触发参数；内置解码器不能设波特率；只开 1 个通道时导出大量样本会崩溃。MCP 默认开启、不鉴权、允许任何网页跨域调用，不用时关掉程序 |
| 正点原子 ATK-Logic：atk-logic-mcp | 专为正点原子逻辑分析仪写的 MCP，能采集、解码、保存 | https://github.com/hugelzhang/atk-logic-mcp | 未实测。要用 Zadig 换驱动，换了以后原厂上位机不能用；作者注明硬件触发不生效 |

不推荐用来接 AI 的：

- **sigrok-cli、PulseView 和基于它们的 MCP，用在梦源新款上**：sigrok 上游只支持 DSLogic、Pro、Plus、Basic 四个老型号，不支持 U2、U3 系列。买设备前先查 sigrok 的设备支持列表；已支持的型号走 sigrok 是最成熟的路线。
- **dslogic-mcp（heng5411）**：只支持 U3Pro16、U3Pro32。
- **agent-dsviewer-logic-analyzer、DSView_rust**：目前只有 Linux 版本。
- **只靠界面导出再让 AI 读文件**：能用，但每次都要人操作，只作兜底。

使用时注意：

- 逻辑分析仪同一时间只能被一个程序占用，用命令行或 MCP 前先关掉 DSView 等上位机。
- 采集的原始数据用脚本分析，只把统计结果和出错的那几帧交给 AI。
- 逻辑分析仪只有一个阈值，量不准边沿斜率和占空比。例如 LIN 一致性测试的占空比要在两个指定电压上量，需要用示波器。

### 示波器

不推荐具体型号，选支持 SCPI 指令的型号即可，AI 能通过 SCPI 读取测量结果。
