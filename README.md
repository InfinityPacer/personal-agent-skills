# Personal Agent Skills

这是一个个人自用的 agent skills 仓库，用来沉淀可复用的协作方式、工作流约束和技能源码。

本仓库文件是事实源。安装到具体 agent 目录中的副本只作为同步目标，不直接作为长期维护入口。

## Layout

- `docs/`：用于推导稳定 skill 行为的工作笔记。
- `.codex/agents/`：固定 subagent 角色模板，由 main agent 在具体任务中按场景拉起。
- `.claude/agents/`：Claude Code 项目级 subagent 角色模板，与 Codex agent 保持职责对等。
- `skills/`：准备验证、安装的 skill 源码目录。

固定 agent 覆盖 review/research 角色。开发或测试执行默认由 main agent 负责；只有任务可并行、低耦合且 ownership 清楚时，才临时使用 worker。

本仓库是 source of truth，不代表 checkout 内的所有文件都会自动被 Codex 发现。使用流程：

- custom agents 同步到 `~/.codex/agents/` 或项目 `.codex/agents/`。
- Claude Code 项目级 agents 保留在 `.claude/agents/`；全局使用时再按需同步到 `~/.claude/agents/`。
- Codex 全局 skill 同步到当前 Codex 版本实际扫描的 user-skill 目录，并用 `/skills` 或 `/debug-config` 验证发现结果；repo-scoped skill 使用项目 `.agents/skills/<name>`，其他兼容运行时按其发现路径同步，或打包为 plugin 后安装。

## Workflow

1. 在 `docs/` 中整理画像、偏好和反复出现的工作流问题。
2. 过滤私密信息、项目专属命令、一次性事故和只适用于单仓库的事实。
3. 先固化常用 subagent 角色，明确职责、边界、只读默认和输出格式。
4. 再将 main agent 的编排规则压缩成跨项目 skill，写入 `skills/<skill-name>/SKILL.md`。
5. 对 agents 和 skill 做隐私检查、格式检查和最小可用性验证。
6. 同步或安装到具体 agent 的发现目录。
7. 确认 custom agents 与 skill 均可被 Codex 发现，例如检查 `/debug-config`、`/skills`，并做一次只读 spawn smoke test。安装副本不是长期维护入口。

## Privacy

skill 名称、公开描述、README 和公开交付内容中不要写入个人名称、用户名、私有项目名、绝对路径、PR/issue 编号、版本号、密钥、token、本机私有配置或只对本机有效的运行细节。

profile 可以记录抽象偏好和稳定模式，不记录可反推出历史事件、账号状态或私有项目上下文的细节。
