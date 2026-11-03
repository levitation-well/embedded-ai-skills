# 工具清单

## 选工具的标准

AI 最擅长处理文本。选工具时，优先选能用文本和 AI 交互的，也就是对 AI 友好的工具：

- 有命令行、开发包或公开的通信协议。
- 不需要图形界面就能运行，输出结果能被程序读取。
- 不光能下命令，还能查询状态。
- 不和 IDE 争抢资源，不需要更换驱动。

## 清单

链接核实于 2026-11-03。软件的版本、许可和安装方法以官方页面为准。

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

示波器、逻辑分析仪等仪器不推荐具体型号，选支持 SCPI 指令的型号即可，AI 能通过 SCPI 读取测量结果。
