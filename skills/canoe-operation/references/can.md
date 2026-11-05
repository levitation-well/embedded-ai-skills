# CAN 相关操作

> 状态：本篇全部未实测，内容来自 CANoe 12 的类型库。做第一个 CAN 项目时，把实测结果写进“已验证”。

数据库：CAN 用 DBC 文件描述报文、信号和节点，作用相当于 LIN 的 LDF。

## 类型库中与 CAN 相关的通用接口（未实测）

| 用途 | 接口 |
| --- | --- |
| 读写信号值 | `app.Bus.GetSignal(通道, 报文名, 信号名)`，属性 `Value`、`RawValue` |
| 读取报文 | `app.Bus.GetMessage(...)` |
| 波特率 | `app.Bus.Baudrate` |
| 数据库管理 | 配置的数据库集合 `Databases`：`Add`、`AddToChannel`、`Remove` |
| 记录与导出 | 测量设置中的 `LoggingCollection`；`Exporter` 可导出 CSV、MDF、ASCII |
| 测试模块 | 通用测试模块接口 `ITSTestModule6`：`Start`、`Stop`、`Verdict`、`Report` |

## 已验证

（暂无）

## 已知风险

（暂无）
