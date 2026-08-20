---
name: tapd-todo
description:
  根据 TAPD 单据/需求 ID 生成 OpenSpec 变更提案。当用户提供 TAPD 单据 ID、需求 ID、story ID，或给出 TAPD
  需求链接并希望据此生成变更提案/方案时使用。流程：读取项目 tapd-config.json 获取 projectId、判定当前仓库方向（前端/后端）、校验
  TAPD 项目、短 ID 转长 ID、拉取需求详情、拉取需求备注/评论（后于需求描述理解）、结合备注校正方案、以长 ID 为标记创建 OpenSpec
  变更。本项目前后端分仓，联调需借助 TAPD 备注同步：在本端仓库优先实现本端方案，需对端确认的部分写入 TAPD 备注。
---

# TAPD 需求转 OpenSpec 变更提案

用户提供 TAPD 单据/需求 ID（短 ID、长 ID 或需求链接）时，按下述流程拉取需求并生成 OpenSpec 变更提案。

> 本项目前端与后端为**分开的两个仓库**，方案联调依赖 TAPD 备注同步：在哪个仓库运行本 skill，就优先实现哪一端的方案；需要对端确认/配合的内容，写入 TAPD
> 备注供对端理解与实现。

## 前置依赖

- MCP 服务 `user-tapd_mcp_http`（TAPD）：需处于 `ready` 状态；若为 `needsAuth` 或调用报鉴权错误，先调用其 `mcp_auth`
  再重试。
- `openspec` CLI（用于创建变更与产物）。
- 项目根目录存在 `tapd-config.json`。

## 执行流程

复制以下清单并逐项推进：

```
- [ ] 1. 读取 tapd-config.json 获取 projectId，并判定当前仓库方向（前端/后端）
- [ ] 2. 校验 TAPD 项目有效
- [ ] 3. 短 ID 转长 ID（长 ID 直接跳过）
- [ ] 4. 拉取需求详情并确认存在（第一优先：先理解需求描述）
- [ ] 5. 如有子任务则一并拉取
- [ ] 6. 拉取需求备注/评论（第二优先：务必在理解需求描述之后再读，顺序不可颠倒）
- [ ] 7. 结合备注信息校正与优化实现方案（按仓库方向优先实现本端）
- [ ] 8. 以长 ID 为标记创建 OpenSpec 变更
- [ ] 9. 依次生成 proposal / specs / design / tasks
- [ ] 10. 严格校验并汇报
```

### 1. 读取 projectId 并判定仓库方向

读取项目根目录 `tapd-config.json`，取 `projectId` 作为 TAPD `workspace_id`。

同时判定当前仓库属于**前端**还是**后端**（决定后续「优先实现本端、备注对端」的方向）：

- 优先读取 `tapd-config.json` 的 `repoType` 字段（`frontend` / `backend`）。
- 无该字段时按仓库特征推断：存在 `package.json` + `src/`（Vue/TS 等）→ 前端；存在 `manage.py`/`go.mod`/`pom.xml`/`requirements.txt`
  等后端工程标志 → 后端。
- 仍无法确定时，向用户确认当前是前端还是后端仓库。

记 `SELF` 为本端（当前仓库方向），`PEER` 为对端；后续实现优先做 `SELF`，需要 `PEER` 确认/配合的内容写入 TAPD 备注。

### 2. 校验 TAPD 项目

通过 `proxy_execute_tool` 执行 `workspace_get`，确认项目存在且 `status` 正常：

```
tool_name: workspace_get
tool_args: { "workspace_id": <projectId> }
```

TAPD 工具统一调用方式：先用 `lookup_tool_param_schema` 获取参数 schema（不确定用哪个工具时先用 `lookup_tapd_tool`
语义检索），再用 `proxy_execute_tool` 执行。

### 3. 短 ID 转长 ID

TAPD 长 ID 为 19 位。若用户给的是 9 位及以下短 ID，先转换：

```
tool_name: tapd_id_get
tool_args: { "short_id": <短ID>, "type": "story" }
```

取返回的
`long_id`。用户直接给 19 位长 ID 或从链接中解析出长 ID 时跳过本步。需求链接格式：`https://tapd.woa.com/tapd_fe/{workspace_id}/story/detail/{long_id}`。

### 4. 拉取需求详情

执行 `stories_get` 确认需求存在并获取内容（标题、状态、描述等）：

```
tool_name: stories_get
tool_args: { "workspace_id": <projectId>, "id": "<long_id>", "with_v_status": "1" }
```

`count` 为 0 表示需求不存在，停止并告知用户核对 ID。需求描述（`description`）是生成提案的核心输入。

### 5. 拉取子任务（如有）

判断该需求是否有子任务：返回的 `children_id` 字段非空（不为 `""` 或
`"|"`）即表示存在子需求/子任务。有则一并拉取，作为提案的补充输入（子任务标题/描述用于细化 specs 与 tasks）：

```
tool_name: stories_get
tool_args: { "workspace_id": <projectId>, "parent_id": "<long_id>", "with_v_status": "1" }
```

说明：

- 「子任务」优先按子需求处理（通过 `parent_id` 查询父需求下的子级）。
- 若用户明确指的是需求关联的任务（task），改用
  `tasks_get`（`tool_args: { "workspace_id": <projectId>, "story_id": "<long_id>" }`）。
- 递归：若子需求自身 `children_id` 仍非空，按需继续下钻拉取。
- `children_id` 为空则跳过本步。

### 6. 拉取需求备注/评论

**顺序约束**：必须先完成第 4 步对需求描述（`description`）的理解，再拉取并阅读备注/评论，两者顺序不可颠倒——需求描述是主输入，备注是对主输入的补充与联调约定。

执行 `comments_get` 拉取该需求下的全部备注/评论：

```
tool_name: comments_get
tool_args: { "workspace_id": <projectId>, "entry_type": "story", "entry_id": "<long_id>", "page": 1, "limit": 30 }
```

说明：

- 返回 `count` 为 0 表示暂无备注，跳过本步。
- 若备注较多（`count` 超过 `limit`），递增 `page` 翻页拉全。
- 备注中常见联调信息：对端（`PEER`）已确认/待确认的接口契约、字段定义、状态枚举、时间点、边界与依赖等。

### 7. 结合备注校正实现方案

在理解「需求描述 + 备注」后，据此优化和调整实现方案：

- 备注中已明确的对端契约/约定：作为**确定输入**并入方案（接口、字段、枚举、流程按备注对齐，不再臆造）。
- 备注中仍待对端确认的点：在 design 的 Open Questions 与 tasks 中显式标注「待 `PEER` 确认」。
- 备注与需求描述冲突时：以最新备注为准（备注通常是后续联调修订），并在 proposal/design 中注明该调整来源。
- 明确本次实现方向：**优先实现 `SELF` 端**；`PEER` 端的实现细节（需其确认/配合的部分）在第 8-10 步生成产物后，按「opsx-apply 阶段」写入 TAPD 备注。

### 8-10. 生成 OpenSpec 变更提案

**变更名称固定使用长 ID 作为标记**：`story-<long_id>`（例：`story-1020452995135891652`）。

遵循项目 `openspec-propose` skill 的规范生成全部产物，关键步骤：

1. 若存在已注册 store（`openspec store list --json` 有结果），后续读写命令加 `--store <id>`；否则用本地 `openspec/`。
2. 创建变更：`openspec new change "story-<long_id>"`
3. 获取构建顺序：`openspec status --change "story-<long_id>" --json`（解析 `applyRequires` 与 `artifacts` 依赖）
4. 按依赖顺序（proposal → specs/design → tasks）逐个产物：
   - `openspec instructions <artifact> --change "story-<long_id>" --json`
   - 依据返回的 `template` 结构写入 `resolvedOutputPath`；`context`/`rules` 仅作为约束，**不写入**产物文件
   - 生成后重跑 `openspec status` 确认状态
5. 内容映射：TAPD 需求描述（含已拉取的子任务标题/描述）→
   proposal（Why/What/Capabilities/Impact）；子任务可作为 capability 拆分或 tasks 任务项的依据；能力拆分为 kebab-case
   capability，每个 `specs/<capability>/spec.md` 用 `### Requirement:` + `#### Scenario:`（场景必须 4 个
   `#`）；design 结合本仓库实际代码给出技术决策；tasks 用 `- [ ] X.Y` 可勾选任务。
6. 每个产物在 proposal 与 design 中标注关联 TAPD 需求长 ID。
7. 严格校验：`openspec validate "story-<long_id>" --strict`，通过后汇报变更名称、位置、产物清单，并提示可运行
   `/opsx:apply` 进入实现。

## opsx-apply 阶段：对端方案处理（本端优先）

方向由第 1 步判定的仓库方向决定：`SELF`（本端，当前仓库）优先实现，`PEER`（对端）方案写入 TAPD 备注供其确认/实现。即：

- 在**前端仓库**运行：`SELF`=前端、`PEER`=后端 → 前端优先，后端方案备注到 TAPD。
- 在**后端仓库**运行：`SELF`=后端、`PEER`=前端 → 后端优先，前端方案备注到 TAPD。

执行 `/opsx:apply`
实现任务时，若发现改动涉及 **`PEER` 端方案变动**（新增/变更接口、字段、状态枚举、存储、流程、交互契约等），先向用户提供一个可选项，由用户确认后再继续：

> 检测到本次改动涉及 `PEER` 端方案变动。是否采用「**本端优先**」模式：生成 `PEER` 端实现详细方案并备注到 TAPD 单，本次仅开发实现
> `SELF` 端部分？

- **用户选择「是」（本端优先）**：
  1. 生成 `PEER` 端实现详细方案（接口定义、请求/响应字段、状态与枚举、流程与边界、对 `SELF` 端的契约影响）；若第 6
     步已从备注读到对端相关约定，需与之对齐、只补充增量，避免重复或冲突。
  2. 通过 TAPD `comments_create`
     将该方案备注到对应需求单：`workspace_id=<projectId>`、`entry_type="story"`、`entry_id="<long_id>"`、`description=<方案 Markdown 内容>`（@具体成员时加
     `notify="1"`）。
  3. 本次**仅实现 `SELF` 端部分**，`PEER` 端相关任务在 `tasks.md` 中标注为「待 `PEER` / 本端优先，暂缓」并跳过实现。
- **用户选择「否」**：按原计划推进（前后端一并处理或按用户指示）。

## 约定

- 变更标记一律使用长 ID（`story-<long_id>`），不用短 ID。
- 内容语言与需求一致（本项目为中文）。
- 阅读顺序恒定：先需求描述，后备注/评论；据备注校正方案，不臆造对端契约。
- `PEER` 端接口/协议未明确的部分，在 design 的 Open Questions 与 tasks 中显式标注「待确认」，不臆造字段。
