# LIN 从节点一致性测试（ISO 17987-6）

CANoe 的 “LIN Slave Conformance Tester” 测试模块按 LDF 生成测试规格（xml），用例由 Vector 自带的 CAPL 测试库执行。用例编号是 ISO 17987-6 的 PT-CT 号。

以下内容在 CANoe 12.0.75 上取得。标“实测”的跑过，标“源码”的来自测试库源码或帮助，没有上机。

## 一、资料在哪里（默认安装位置）

| 资料 | 位置 |
| --- | --- |
| 测试库（明文 CAPL） | `C:\Users\Public\Documents\Vector\CANoe\12.0 (x64)\Reusable\LINCaplLibs\`。字段读取在 `LCT_Slave_IUTDataLib.cin`，复位与弹窗在 `LCT_Slave_UtilitiesLib.cin`，ISO 17987 用例在 `LIN2.1_Slave_Conformance_Test_Lib.can` |
| 传输层服务定义 | `C:\ProgramData\Vector\CANoe\12.0 (x64)\LinCTServices.ini`（全局，对所有工程生效） |
| 帮助 | `<安装目录>\Help01\CANoeCANalyzer.chm`。解包：`hh.exe -decompile <目标目录> <chm 路径>`。设置页在 `Topics/CANoeCANalyzer/LIN/LINSlaveConformanceTest/`，COM 说明在 `Topics/COMInterface/` |
| 示例工程 | `C:\Users\Public\Documents\Vector\CANoe\Sample Configurations 12.0.75\LIN\LINSlaveConformanceTest\` |
| 报告导出工具 | `C:\Program Files (x86)\Vector CANoe Test Report Viewer 12.0\TestReportXmlExporter.exe` |

CANoe 12 的帮助只有 LIN 1.x、2.0、2.1、J2602 四个设置页，ISO 17987 沿用 2.1 页。测试规格标记为 `ISO17987:2015`。

## 二、标准流程

1. 用户在界面完成：导入 LDF，网络硬件里 LIN 通道设为 Master 和正确波特率，测试模块里选好从节点。
2. 只读探测：`python -I scripts/canoe_probe.py`。
3. 用户在界面设置脚本改不了的两项（见第四节）。
4. 脚本写入其余被测件设置，调用 `GenerateTestCases()`，再关闭不适用的用例：`ct_com.py disable <编号...>`。
5. 核对生成的规格 xml 里的实际字段（第三节），再请用户确认接线和供电。
6. 开跑：`ct_com.py run <超时秒数> <要关闭的编号...>`。会先启动测量，再关闭一次用例，然后启动测试，结束后报告状态。
7. 停止测量，导出报告：`ct_report.py <输出目录> <报告...>`。
8. 失败用例对照测试库源码的前置检查找原因（第七节）。

## 三、测试规格 xml 的字段编码（源码）

生成的规格里，每个字段是一条 `<sysvardef name="...">值</sysvardef>`。**跑前先核对这里的实际值**：用户在界面只选了从节点、没改 IUT Settings 页时，字段会沿用旧工程的值（实测）。

| xml 字段 | 取值 |
| --- | --- |
| `HWInit` | 0 I/O Cab（CANoe 12 未实现）；1 手动；2 软件复位（等总线空闲）；3 不复位；4 VH11xx；5 VT7001 |
| `DeviceClass` | 1 Class B（引出 RxD、TxD）；2 Class C（集成收发器，只能从 LIN 总线接入） |
| `IUTPersistentConfigurationType` | 0 无效；1 固定（界面 Readonly，预配置节点）；2 可配置（界面 Writeable，可用 B6 保存）；3 无配置（界面 None） |
| `SaveConfigurationSupport` | 1 = 支持 B6 |
| `ConditionalChangeNADSupport` | 1 = 支持 B3 |
| `InvalidReadByIdNotAnswered` | 1 = 供应商号或功能号不符的 ReadByIdentifier 不应答（对应 ini 的 `InvalidReadByIDAnswered = 0`）。它不管“不支持的标识符回负响应”这件事 |
| `DiagRespNotLostOnDiagRequestError` | 1 = 收到有错误的主机请求后，不放弃进行中的诊断（对应 ini 的 `DiagRespLostOnDiagRequestError = 0`） |
| `UsesInterbyteSpaces` | 只影响 PT-CT 38 里翻转“字节间隔位”的 8 个变体（38.3、38.6 … 38.24）。为 0 时这些变体直接判失败 |
| `ReconfigureBeforeTest` | 1 = 每个用例开始时，先发 AssignNAD，再分配全部帧的 PID |
| `WaitForBusIdleTime` | 只在 `HWInit = 2` 时使用 |
| `PowerOffTime`、`IUTInitTime` | `HWInit = 3` 时生成器写 0；通过 COM 写入的值在不复位方式下读回也是 0（实测） |
| `IsDatabaseVersionSpecified` 等 | 生成器按 LDF 的 `LDF_file_revision` 自动填写（实测） |
| `SyncBreakLengthDft` 等三项 | 只有 LIN 1.3 测试库读取，ISO 17987 不用 |
| 帧表 `FramePubUC*`、`FrameSubUC*`、`StatusFrame*` | 生成器从 LDF 自动填，槽位上限 60；ISO 17987 下 MsgID 为 65535（实测） |

## 四、用 COM 写设置、选用例、开跑（实测）

脚本 `scripts/ct_com.py` 已实现。要点：

```python
t = w.CastTo(w.CastTo(env.TestModules, "ITestModules2").LinSlaveConformanceTesters.Item(1),
             "ILinSlaveConformanceTester3")
s = t.IUTSettings                     # IIUTSettings2
i = t.IUTInitializationSettings       # IIUTInitializationSettings
s.DeviceClass = 2                     # 1 B，2 C
s.SupportsConditionalChangeNAD = 1    # 1 不支持，2 支持但无正响应，3 支持且有正响应
s.SendsWakeupSignal = False
s.SupportsInterbyteSpace = False
i.ResetType = 1                       # COM 编码：1 不复位，2 VH11xx，3 VT7001，4 手动，5 软件
t.GenerateTestCases()                 # 约 1 秒，改设置后必须调用
group = w.CastTo(t.Sequence.Item(g), "ITestGroup")       # 属性 Name、Enabled、Sequence
case  = w.CastTo(group.Sequence.Item(c), "ITestCase")    # 属性 Ident（PT-CT 号）、Enabled、Verdict
```

- **COM 改不了的两项**：`IUTSettings` 只有 DeviceClass、FunctionID、InitialNAD、ReconfigureBeforeEachTestCase、SendsWakeupSignal、SupplierID、SupportsAssignNAD、SupportsConditionalChangeNAD、SupportsInterbyteSpace、VariantID。“支持 SaveConfiguration”和“持久化方式”只能在界面的 IUT Settings 页设置。
- **COM 和 xml 的编码不同**：复位方式在 COM 里是 `ResetType`（1 不复位、4 手动），在 xml 里是 `HWInit`（3 不复位、1 手动），不要混用。
- **关闭用例的坑**：给组设 `Enabled = True` 会把组内用例全部重新启用。先把所有组启用一次，再逐个设用例。
- **开跑顺序**：`StartOnMeasurement` 默认为 False。先 `Measurement.Start()`，等 `Running` 变为 True，再调用测试器的 `Start()`。实测启动测量不会重新生成规格，关闭状态得以保留。保险起见，`ct_com.py run` 在测量启动后会再关闭一次用例。
- **用 COM 选的用例不持久**：测量停止后，用例的启用状态恢复为界面里保存的选择（实测）。每次开跑都要重新设置，`ct_com.py run` 已这样做。要长期保存，须在界面里勾选并保存配置。
- **进度**：轮询启用用例的 `Verdict`（0 表示还没有结论）和测试器的 `Verdict`（1 通过，2 失败）。
- 官方帮助原文：改了 Settings 后，“the Sequence property is not updated until GenerateTestCases method is called or the measurement is started”。

## 五、传输层服务文件 `LinCTServices.ini`（源码）

传输层用例（Transport Layer 组）发的请求、期待的响应，不在界面里逐项填写，而是来自这个全局 ini。界面 IUT Settings 页 Transport Layer 的 Edit 按钮打开的就是它。

- 三组服务：`[FunctionalRequest]`（功能寻址，NAD = 0x7E）、`[SegmentedRequest]`（多帧请求）、`[SegmentedResponse]`（多帧响应）。
- **长度和数据都不含 SID、RSID**：`RequestLen`、`D1…Dn`、`ResponseLen`、`R1…Rn` 都从 SID 后面第一个字节算起。源码注释原文：“dataLength does not include SID/RSID”。
- 分段数 = ceil((长度 - 4) / 6) + 1。多帧请求至少 3 段，多帧响应至少 2 段。SID 有效范围 0x00–0xAF、0xB8–0xFE。
- `[FunctionalRequest]` 没有响应项：测试库不期待功能寻址的应答。
- `[_TP_Settings]` 里的 `CheckSegmentedResponseLength` 和 `CheckSegmentedResponseContent` 是 Vector 附加的检查，规范不要求。见第七节 PT-CT 82。
- 示例见 `templates/LinCTServices.example.ini`。改之前先备份原文件，测完恢复。

## 六、读取报告（实测）

- `.vtestreport` 是加密的 SQLite，运行中旁边有 `-wal`、`-shm` 文件，不能直接读。
- 导出：`TestReportXmlExporter.exe -r=<报告> -e=<输出.xml>`。不需要加密狗，也不需要连接 CANoe。`scripts/ct_report.py` 会先复制再导出。
- 运行中看进度：把 `.vtestreport`、`-wal`、`-shm` 三个文件一起复制到别处，再导出副本，不影响测试。根节点 `reportrunstate` 为 `TestRunning` 或 `TestComplete`。
- 用例结论在 `testcase/verdict@result`；没执行的用例是 `skipped` 元素。报告头里有 CANoe 版本、数据库路径、接口型号、序列号、驱动和 LIN 固件版本。
- **局限**：导出的 XML 只有每个用例的结论，没有测试步骤、失败原因原文和总线报文。失败原因要从测试库源码的前置检查推断（第七节）。报告查看器的 .NET 程序集没有公开读取步骤的接口。

## 七、已知的判定特点（实测 + 源码）

| 用例 | 现象 | 原因 | 处理 |
| --- | --- | --- | --- |
| PT-CT 24 上电初始化时间 | 失败 | 前置检查只接受 VH11xx 或 VT7001，原文 “No automatic reset is configured!” | 没有这两种硬件时注明为测试设备限制并关闭 |
| PT-CT 44、45、46、48 事件触发帧 | LDF 没有事件触发帧时仍会执行，直接判失败 | 原文 “no such a frame is defined!” | 不适用，关闭 |
| PT-CT 56–59 发唤醒 | 节点不发唤醒时，`SendsWakeUpSequencies` 填 0 或 1 都判失败 | 填 0 时原文 “IUT does not support sending wakeup signal” | 不支持，关闭 |
| PT-CT 77–79 保存配置 | `SaveConfigurationSupport = 0` 时直接判失败，不会停用 | 前置检查 | 在界面勾选后单独运行；78、79 内部要断电 |
| PT-CT 82 多帧请求 | `CheckSegmentedResponseLength = 1` 时必然失败 | 它拿多帧请求的应答长度，去比 `[SegmentedResponse]` 的 `ResponseLen`，两组服务不同时永远不相等 | 设为 0 后通过（实测）。PT-CT 88 仍检查响应内容 |
| PT-CT 38 字节间隔变体 | 节点把应答一次写入 UART 发送缓冲、字节间隔为 0 时，8 个变体时过时不过 | 翻转位落在停止位或下一字节起始位的边沿附近，结果取决于时序抖动 | `UsesInterbyteSpaces = 0` 并关闭。ISO 17987-3 允许间隔为 0 |
| 休眠组（PT-CT 53、55、64–66） | 设置错误时（声称会发唤醒）可能误判通过 | — | 以正确设置下的结果为准 |
| B3 ConditionalChangeNAD | ISO 17987 用例里没有 B3 用例 | — | 误标支持不会造成失败 |

## 八、供电与复位（手册 + 源码 + 实测）

- **LIN 插件的 D-SUB9 引脚 9（VB+）是输入**：Accessories 手册图例为 “Positive supply voltage for electrically decoupled cabs/piggybacks”，并注 “VB+ optional”。它只给插件自己的收发器供电，不能给被测板供电（实测确认）。
- **接法**：被测板用外部 12 V；引脚 9 可接同一个 12 V，引脚 3（VB-）接被测板地，引脚 7 接 LIN。手册建议插件和其他节点用同一电源，避免节点间交叉电流。
- **复位时机**：每个用例开始前都按 `HWInit` 复位。选手动时，每个用例都会弹出 Yes/No 窗口，等人断电再上电。
- **用例内部断电**：只有 PT-CT 24、78、79。24 只接受 VH11xx 或 VT7001；78、79 允许手动。
- **`HWInit = 0`（I/O Cab）**：CANoe 12 没有实现，会报 “Trying to trigger unknown IUT reset type”。
- **VN1630A CH5**：引脚 8 数字输出（开漏，外部电压最高 32 V，最大 500 mA，有短路和过压保护），引脚 9 数字地。测试库只在 Vector 的演示自动化里用 `IO::VN1600_1::DOUT` 触发唤醒和事件触发帧，不用于复位。设 `LINSlaveConformanceTestAutomation::EnableAutoAnswer = 1` 只会跳过确认弹窗，不会真的断电。
- **手动复位弹窗**：由 `Util_Toggle_IUT_Power_Manual` 调用 `testWaitForTesterConfirmation` 弹出，文字固定：“Please perform IUT initialization (HW-reset). Press 'Yes' when the initialization is done or press 'No' to skip this test.”。配合可编程电源，可以用 UI 自动化识别这个窗口，自动断电、上电后再点 Yes（未实测）。

## 九、已知风险

- 2026-11-05：在 LDF 尚未导入、从节点尚未选择的工程上读取测试器的 `ChannelNumber`、`SlaveNodeName` 时报“发生意外”，随后 CANoe 退出。LDF 导入后，读写 `IUTSettings`、`Sequence` 和调用 `GenerateTestCases`、`Start` 都正常。

## 十、待验证

- 测试模块 Report 页能否输出带测试步骤的 XML 报告。
- 用 UI 自动化加可编程电源，自动处理手动复位弹窗。
