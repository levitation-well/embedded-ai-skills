# embedded-ai-skills

让 AI 辅助嵌入式开发的环境指引：用 AI 做嵌入式开发需要哪些工具，每个工具能让 AI 做什么，从哪里获取。

适用场景：Cortex-M 微控制器的编译、烧录、调试，LIN/CAN 总线测试，原理图和 PCB 设计。第一版按 Windows 编写。

## 内容

| skill | 作用 |
| --- | --- |
| [embedded-ai-setup](skills/embedded-ai-setup/SKILL.md) | 先提醒你为 AI 准备知识库，再列出推荐的工具，逐项问你要不要，给出官方获取地址 |

本仓库只做指引，不打包任何厂商软件、驱动或动态库。工具请从官方渠道获取，并遵守各自的许可条款。

## 安装

先克隆仓库，再把 skill 链接到智能体读取 skill 的目录。下面以克隆到 `D:\embedded-ai-skills` 为例。

**Claude Code**（读 `%USERPROFILE%\.claude\skills`）：

```bat
mklink /J "%USERPROFILE%\.claude\skills\embedded-ai-setup" "D:\embedded-ai-skills\skills\embedded-ai-setup"
```

**Codex 等读 `%USERPROFILE%\.agents\skills` 的智能体**：

```bat
mklink /J "%USERPROFILE%\.agents\skills\embedded-ai-setup" "D:\embedded-ai-skills\skills\embedded-ai-setup"
```

删除链接时用 `rmdir`，不要用递归删除，否则会顺着链接删掉仓库里的文件。

## 使用

在智能体里说“帮我配置嵌入式 AI 环境”即可。

## 许可

[MIT](LICENSE)。工具清单里的第三方软件和硬件，各有自己的许可条款，与本仓库无关。
