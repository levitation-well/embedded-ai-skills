---
name: canoe-operation
description: 用 Python 自动化接口（COM）操作 Vector CANoe 12 的手册，以 LIN 从节点一致性测试（ISO 17987-6）为主，兼顾 CAN：附着到正在运行的 CANoe、写入被测件设置、生成和挑选用例、启动测试、导出并分析报告，以及测试库字段编码、传输层服务文件、供电与复位、已知的判定特点。用户提到 CANoe、LDF、DBC、LIN 一致性测试、PT-CT 用例、vtestreport 报告、自动化 CANoe 时使用。每次使用后按“维护规则”更新本 skill。
---

# CANoe 操作

AI 通过 COM 接口操作 CANoe，不点界面。2026-11 在 **CANoe 12.0.75 + VN1630A（CH1 装 LIN 插件）** 上实测，完成过一轮 ISO 17987-6 从节点一致性测试：131 个用例，从改设置、选用例、开跑到导出报告全部由脚本执行。

| 文件 | 内容 | 状态 |
| --- | --- | --- |
| `SKILL.md` | 前置条件、通用接口、安全规则、维护规则 | 已实测 |
| [references/lin-conformance.md](references/lin-conformance.md) | LIN 从节点一致性测试：设置、字段编码、选用例、开跑、报告、判定特点、供电与复位 | 大部分已实测 |
| [references/can.md](references/can.md) | CAN 相关接口 | 未实测 |
| [log.md](log.md) | 经验日志 | 持续追加 |
| `scripts/canoe_probe.py` | 只读探测：列出测试环境和测试模块 | 已实测 |
| `scripts/ct_com.py` | 一致性测试器：列出、关闭用例，启动测试并等待结束 | 已实测 |
| `scripts/ct_report.py` | 复制报告、导出 XML、汇总结论 | 已实测 |
| `templates/LinCTServices.example.ini` | 传输层用例服务定义文件的示例 | 示例 |
| `local.md` | 本机说明（安装位置、工程路径、分工），各人自建，不入库 | — |

先读本文件，再按任务读对应的参考文件。本机有 `local.md` 时一并读取。

## 一、前置条件

1. **许可**：Vector 加密狗已插入。未插入时创建 `CANoe.Application` 会报 `0x80080005`。
2. **CANoe 已打开目标配置**。脚本只附着到正在运行的实例，不调用 `Open`，避免打断用户当前的窗口。
3. **Python 装有 pywin32**，普通权限即可。运行时加 `PYTHONIOENCODING=utf-8`，避免中文乱码。
4. **安装位置**：从注册表 `HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\*` 中 `DisplayName` 含 “CANoe” 的项读取 `InstallLocation`。帮助文件在 `<安装目录>\Help01\`。

## 二、通用接口（实测）

```python
import win32com.client as w
from win32com.client import gencache
app = gencache.EnsureDispatch("CANoe.Application")   # 附着到正在运行的 CANoe
app.Version.major, app.Version.minor, app.Version.Build
app.Configuration.FullName
app.Measurement.Running / app.Measurement.Start() / app.Measurement.Stop()
env = w.CastTo(app.Configuration.TestSetup.TestEnvironments.Item(1), "ITestEnvironment2")
```

- 集合下标从 1 开始。
- 必须用 `gencache.EnsureDispatch`，并用 `CastTo` 切换到带版本号的接口（如 `ITestEnvironment2`、`ITestModules2`）。直接 `Dispatch` 拿到的是旧接口，属性会缺失。
- 查某个对象有哪些属性：`type(obj)._prop_map_get_`（可读）、`_prop_map_put_`（可写）。按名称在 gencache 模块里找接口不可靠，要从实际拿到的对象上取。
- 用 `python -I` 运行时，当前目录不在搜索路径里，导入同目录脚本前先把目录加进 `sys.path`。

## 三、安全规则

- **启动测量或测试前，须用户确认接线和供电。** `Measurement.Start` 会占用接口卡并向总线发数据。
- 不要用 `Quit` 关闭用户正在用的 CANoe，除非用户明确同意。
- 测试结束后，自己启动的测量要自己停掉。
- 读取未验证过的属性前，先做只读探测。曾导致 CANoe 退出的属性，写进参考文件的“已知风险”。
- `.cfg`、`.tse` 的主体是 Vector 专有格式，不要手改。
- 修改全局文件（如 `LinCTServices.ini`）前先备份，测试结束后恢复。它对本机所有工程生效。

## 四、文件格式

| 文件 | 能否直接读写 |
| --- | --- |
| `.ldf`、`.dbc`、测试规格 `.xml`、CAPL 源码 `.can`/`.cin`、`LinCTServices.ini` | 纯文本，可以 |
| `.cfg`、`.tse` | 不要手改 |
| `.vtestreport` | 加密的 SQLite，不能直接读；用 `TestReportXmlExporter.exe` 导出，见 LIN 参考文件 |
| `.cbf` | CAPL 编译产物，不读 |

## 五、维护规则（每次使用后执行）

1. **实测后立即写回**：接口能用、报错、行为和预期不符，都写进对应参考文件，注明日期。
2. **区分来源**：只来自类型库、帮助或源码的内容标“未实测”；实测过的写明日期。
3. **通用与专门分开**：和总线无关的写进本文件；只属于某种总线的写进对应参考文件。
4. **记日志**：在 `log.md` 最上面加一条：日期、现象、原因、做法。
5. **脚本同步**：改了接口写法，同步改 `scripts/` 并实测一次。
6. **脱敏**：本仓库公开。不写项目代号、客户名、未公开的芯片型号和参数、本机路径、账号、测试报告原件。本机特有的内容写进 `local.md`。
7. **告知用户**：回复末尾用一行说明本次更新了哪部分。
