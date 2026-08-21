---
name: tapd-todo
description: 根据 TAPD 单据/需求 ID 拉取需求与备注，生成 OpenSpec 变更提案
disable-model-invocation: true
---

# TAPD 需求转 OpenSpec 变更提案

**Input**：`/tapd-todo` 之后的参数为 TAPD 单据/需求 ID（短 ID、长 ID）或需求链接。若未提供，用 **AskQuestion
tool**（开放式提问）询问："请提供 TAPD 需求 ID 或需求链接。"

本项目前端与后端为**分开的两个仓库**，联调依赖 TAPD 备注同步：在哪个仓库运行本命令，就把该端记为
`SELF`（优先实现），对端记为 `PEER`（需其确认/配合的方案写入 TAPD 备注）。

## 前置依赖

- MCP 服务 `user-tapd_mcp_http`（TAPD）：需处于 `ready` 状态；若为 `needsAuth` 或调用报鉴权错误，先调用其 `mcp_auth`
  再重试。
- `openspec` CLI（用于创建变更与产物）。
- 项目根目录存在 `agent-flow.config.json`（含 `projectId` 与 `members` 角色成员配置）。

TAPD 工具统一调用方式：先用 `lookup_tool_param_schema` 获取参数 schema（不确定用哪个工具时先用 `lookup_tapd_tool`
语义检索），再用 `proxy_execute_tool` 执行。下文只点名要用的工具，参数一律以 schema 为准。

## 执行流程

用 **TodoWrite tool** 跟踪以下清单并逐项推进：

```
- [ ] 1. 读取 agent-flow.config.json 获取 projectId、成员角色配置，并判定当前仓库方向（前端/后端）
- [ ] 2. 拉取需求数据：长 ID → 需求详情 → 子需求 → 备注/评论（顺序不可颠倒，先读懂描述再读备注）
- [ ] 3. 按评论人角色解读备注，据此校正实现方案（按仓库方向优先实现本端）
- [ ] 4. 需求澄清结束后，将本端实现方案精简备注到 TAPD
- [ ] 5. 以长 ID 为标记创建 OpenSpec 变更
- [ ] 6. 依次生成 proposal / specs / design / tasks
- [ ] 7. 严格校验并汇报
```

### 1. 读取配置并判定仓库方向

按 `agent-flow-config` skill 读取项目根目录
`agent-flow.config.json`（成员昵称解析、缺失与非法配置的处理均以该 skill 为准）：`projectId` 作为 TAPD
`workspace_id`；`members` 用于解读评论意图与撰写评论时 @ 对应角色，本命令只用其 `tapdname`。

判定当前仓库方向（决定 `SELF` / `PEER`）：

- 优先读 `repoType` 字段（`frontend` / `backend`）。
- 无该字段时按仓库特征推断：存在 `package.json` + `src/`（Vue/TS 等）→ 前端；存在
  `manage.py`/`go.mod`/`pom.xml`/`requirements.txt` 等后端工程标志 → 后端。
- 仍无法确定时，向用户确认当前是前端还是后端仓库。

### 2. 拉取需求数据

按下列顺序依次拉取，**顺序不可颠倒**：需求描述是主输入，备注是对它的补充与联调修订，必须先读懂描述再读备注。

1. **需求 ID**：TAPD 长 ID 为 19 位。用户给短 ID 时不用单独转换，`stories_get` 的 `id`
   参数支持短 ID 自动转长 ID；用户给需求链接（形如
   `https://tapd.woa.com/tapd_fe/{workspace_id}/story/detail/{long_id}`）时，只取链接末尾的长 ID，**不要用链接里的
   `workspace_id`**——它是 TAPD 项目 ID，与 `agent-flow.config.json` 的 `projectId` 是两套体系，`workspace_id`
   始终用配置文件里的 `projectId`。
2. **需求详情**：用 `stories_get` 按 ID 取标题、状态、描述。返回 `count`
   为 0 说明需求不存在或不在当前项目，停止并告知用户核对 ID。描述（`description`）是生成提案的核心输入。
3. **子需求**：详情里的 `children_id` 非空（不为 `""` 或 `"|"`）时，再用 `stories_get`
   按父需求拉子需求，其标题/描述用于细化 specs 与 tasks；为空跳过。
4. **备注/评论**：用 `comments_get`
   拉该 story（`entry_type=story`）的评论，超过单页时翻页拉全；无评论则跳过。备注中常见联调信息：`PEER`
   已确认/待确认的接口契约、字段定义、状态枚举、时间点、边界与依赖等。

### 3. 按角色解读备注并校正方案

用评论作者字段（如 `author`/`created_by`）与 `members`
匹配出角色，再据角色理解该条评论真正想表达什么，不要只按字面理解：

| 角色         | 评论意图通常指向                                                       |
| ------------ | ---------------------------------------------------------------------- |
| `product`    | 需求范围、业务规则、交互与文案口径、验收标准、优先级——是需求侧的裁定者 |
| `backend`    | 接口契约、字段与类型、状态枚举、数据来源与时序、性能与边界             |
| `frontend`   | 页面交互、展示形态、前端依赖的接口/字段诉求、兼容与降级                |
| 未匹配到角色 | 按内容推断角色后再解读，并在方案中标注该结论来源不确定                 |

冲突处理：需求范围/验收口径以 `product`
的评论为准；各端技术实现细节以该端角色（`backend`/`frontend`）的评论为准；同角色多条评论以最新一条为准；备注与需求描述冲突时以最新备注为准（备注通常是后续联调修订），并在 proposal/design 中注明该调整来源。

据此校正实现方案：

- 备注中已明确的对端契约/约定：作为**确定输入**并入方案（接口、字段、枚举、流程按备注对齐，不再臆造）。
- 备注中仍待对端确认的点：在 design 的 Open Questions 与 tasks 中显式标注「待 `PEER` 确认」。

### 4. 需求澄清结束后备注本端方案

第 3 步方案定稿（即需求澄清结束）后，把 `SELF` 端将要实现的方案以**精简**形式备注到 TAPD，便于产品与 `PEER`
高效对齐。执行 `comments_create`，遵循「TAPD 评论撰写规范」。

只写关键内容，控制在一屏内：

```markdown
【<SELF 端>方案｜需求 <long_id>】

## 接口定义

- `GET /apis/xxx/` 用途：xxx（`PEER` 提供）

## 字段定义

| 字段  | 类型   | 说明 |
| ----- | ------ | ---- |
| `xxx` | string | xxx  |

## 改动方案

- xxx 页面新增 xxx，复用 xxx 组件
- xxx 逻辑调整为 xxx

## 待确认

- @<产品成员> xxx 场景的口径确认
- @<对端成员> xxx 接口是否可提供 xxx 字段
```

约束：

- 本步只写 `SELF` 端方案与需要 `PEER` 配合的诉求；`PEER` 端的详细实现方案在 `/openspec-apply-change`
  阶段另行备注，两者不重复。
- 不贴代码、不复述需求描述、不展开备注中已确认过的内容（只写增量）。
- 无「待确认」项时省略该段，不做无意义的 @。
- 备注失败（鉴权/接口报错）不阻塞后续步骤，在最终汇报中说明。

### 5-7. 生成 OpenSpec 变更提案

按 `/openspec-propose` 执行：store 选择、产物必需集合与依赖顺序、`skipped` 与条件产物的跳过规则等流程细节均以该 skill 和
`openspec instructions` 的返回为准，本节只补充 TAPD 相关约定，不重复流程。

- **变更名**：固定用长 ID 作标记，`openspec new change "story-<long_id>"`（例：`story-1020452995135891652`）。
- **内容映射**：需求描述（含已拉取的子需求标题/描述）→
  proposal（Why/What/Capabilities/Impact）；子需求可作为 capability 拆分或 tasks 任务项的依据；每个 `spec.md` 用
  `### Requirement:` + `#### Scenario:`（场景必须 4 个 `#`）；design 结合本仓库实际代码给出技术决策；tasks 用
  `- [ ] X.Y` 可勾选任务。
- **关联标记**：proposal 与 design 中标注关联的 TAPD 需求长 ID。
- **收尾**：`openspec validate "story-<long_id>" --strict`
  通过后汇报变更名称、位置、产物清单。本命令只产出规划产物、不改动项目代码，汇报后停止，等用户另行发起
  `/openspec-apply-change` 再进入实现。

## TAPD 评论撰写规范

所有写入 TAPD 的评论（第 4 步的本端方案、`/openspec-apply-change` 阶段的对端方案）统一遵循：

- 需要**产品**拍板的点（需求范围、业务规则、验收口径）@ `members.product` 的成员；需要**后端**确认的点 @
  `members.backend`；需要**前端**确认的点 @ `members.frontend`。
- @ 用成员的 `tapdname`，不用 `githubname`。
- @ 写在具体待确认条目上（`@张三 xxx 是否 xxx`），不在开头笼统 @ 一串人。
- 一个角色配置多个成员时，只 @ 与该问题直接相关的成员；无法判断则全部 @。
- 正文出现 @ 时，`comments_create` 必须带 `notify="1"`，否则被 @ 的成员收不到通知；无 @ 时不传 `notify`。
- 使用 Markdown，中文表述，与需求语言一致。

## openspec-apply-change 阶段：对端方案处理（本端优先）

执行 `/openspec-apply-change` 实现任务时，若发现改动涉及 **`PEER`
端方案变动**（新增/变更接口、字段、状态枚举、存储、流程、交互契约等），先向用户提供一个可选项，由用户确认后再继续：

> 检测到本次改动涉及 `PEER` 端方案变动。是否采用「**本端优先**」模式：生成 `PEER`
> 端实现详细方案并备注到 TAPD 单，本次仅开发实现 `SELF` 端部分？

- **用户选择「是」（本端优先）**：
  1. 生成 `PEER` 端实现详细方案（接口定义、请求/响应字段、状态与枚举、流程与边界、对 `SELF`
     端的契约影响）；与第 2 步读到的对端约定、第 4 步已备注的内容对齐，只补充增量，避免重复或冲突。
  2. 通过 `comments_create` 备注到对应需求单，遵循「TAPD 评论撰写规范」。
  3. 本次**仅实现 `SELF` 端部分**，`PEER` 端相关任务在 `tasks.md` 中标注为「待 `PEER` / 本端优先，暂缓」并跳过实现。
- **用户选择「否」**：按原计划推进（前后端一并处理或按用户指示）。

## 约定

- 变更标记一律使用长 ID（`story-<long_id>`），不用短 ID；内容语言与需求一致（本项目为中文）。
- 阅读顺序恒定：先需求描述，后备注/评论；读评论先定角色再解读意图。
- 不臆造对端契约：`PEER` 端接口/协议未明确的部分，在 design 的 Open Questions 与 tasks 中显式标注「待确认」。
- 写入 TAPD 的备注只保留关键内容（接口定义、字段定义、改动方案、待确认），按角色 @ 到人并带 `notify="1"`。
