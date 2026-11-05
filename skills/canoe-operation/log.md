# 经验日志

新条目加在最上面。格式：`日期 — 现象 → 原因 → 做法`。只记实测过的事。同一件事出现第二次，就提炼进 SKILL.md 或参考文件，这里的条目缩成一行“已提炼到 X”。

---

- 2026-11-05 — 测量停止后读用例状态，脚本关闭的用例恢复成了界面里的选择；不复位方式下写入的 PowerOffTime、IUTInitTime 读回为 0 → COM 的用例选择只在当次运行有效 → 已写进 references/lin-conformance.md 第三、四节，`ct_com.py run` 每次开跑前重新设置。
- 2026-11-05 — **第一次完整跑通 ISO 17987-6 从节点一致性测试**（CANoe 12.0.75，VN1630A，LIN 插件在 CH1，被测件为 Class C 预配置从节点，131 个用例）。前三轮由人在界面操作，第四轮由脚本全程执行。以下已提炼到 references/lin-conformance.md：
  - 只在界面选从节点、不改 IUT Settings 页时，字段沿用旧工程的值，三轮都没生效；改用 COM 写入后才生效。跑前须核对生成的规格 xml。
  - PT-CT 82 在 `CheckSegmentedResponseLength = 1` 时必然失败，设为 0 后通过。
  - 事件触发帧、唤醒、保存配置三类用例在不支持时直接判失败，不会自动停用。
  - 给组设 `Enabled = True` 会把组内用例全部重新启用。
  - `.vtestreport` 是加密 SQLite，用 `TestReportXmlExporter.exe` 导出，但只有结论，没有步骤。
  - LIN 插件的 VB+ 不能给被测板供电。
- 2026-11-05 — 在 LDF 尚未导入的工程上读 `ChannelNumber`、`SlaveNodeName`，CANoe 退出 → 推测是没有从节点 → 先在界面导入 LDF、选好从节点，再读测试器属性。
