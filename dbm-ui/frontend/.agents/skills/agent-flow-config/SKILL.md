---
name: agent-flow-config
description: >-
  读、写或新增项目根目录 agent-flow.config.json 配置时使用，包含配置分层、成员人名解析（tapdname / githubname / git
  提交身份）与新增配置项规范。
---

# agent-flow Config

项目根目录 `agent-flow.config.json`（注意不是 `agent-flow-config.json`）是各 `/command`
与 skill 共用的配置源，读写均遵循本文规则。

## 配置结构

```json
{
  "projectId": "<TAPD 项目 ID>",
  "repoType": "frontend",
  "members": {
    "product": ["<tapdname>"],
    "backend": ["<tapdname>:<githubname>"],
    "frontend": ["<tapdname>:<githubname>"]
  },
  "weeklyReport": { "period": "2w", "branches": ["<分支名或 glob>"] }
}
```

- 被两个及以上命令读取的配置放顶层（如
  `projectId`、`repoType`、`members`）；只被单个命令读取的放与命令同名的节点：`/weekly-report` →
  `weeklyReport`，`/tapd-todo` → `tapdTodo`。
- 节点内字段不重复命令名前缀：写 `weeklyReport.period`，不写 `weeklyReport.reportPeriod`。

## 读写规则

- 文件不存在时告知用户所需的最小配置，不臆造默认值继续跑。
- 每个配置项都要有明确缺省行为：缺失或非法时取文档写明的默认值，不静默失败。
- 缺失或非法的节点或字段要**先用 `AskQuestion`
  让用户确认取值**（把文档默认值作为推荐项），拿到答复后再把确认结果写入配置文件，然后继续执行；不要先写入再确认，也不要只在汇报里提示补齐。
- 用户跳过确认（取消或不作答）时不写入配置文件，再用 `AskQuestion` 追问一次「是否按默认值 `<默认值>`
  继续本次执行」：选「是」则按默认值继续，但仍不写入配置文件，并在汇报里说明配置仍缺失；选「否」或再次跳过则**立即终止本次任务**，只回复缺失的配置项与待补齐的取值，不执行后续任何步骤。
- 写入保持 JSON 严格合法（无注释、无尾逗号）；改完用 `node -e "require('./agent-flow.config.json')"` 校验，再
  `npx prettier --write agent-flow.config.json`。
- 只增改本次相关的键，不动其他命令的节点、不重排既有键。
- 改动字段后同步更新读取它的命令/skill 文档（读取路径、取值表、缺省行为）；重命名或迁移字段要 `rg '<旧键名>' .cursor`
  清残留。
- 文档与示例只用占位符，不写入真实成员昵称、账号或项目 ID。

## 新增配置项

按顺序判断：只服务一个命令 → 放该命令节点；多个命令要读 → 放顶层；能从环境推断（如仓库方向可由 `package.json` + `src/`
或 `manage.py`/`go.mod`/`pom.xml` 判定）→ 不加配置；只为「以后可能用到」→ 不加。

新增时必须同时定下取值格式、缺省值、非法值处理，三者缺一不算完成。

## 成员人名解析

`members` 按角色分组（`product` / `backend` / `frontend`），成员格式 `[tapdname]:[githubname]`，以**第一个** `:`
分割、两侧去空格；任一段可省略（`tapdname` / `:githubname`），但不能同时为空。

| 场景                         | 用哪段                                            |
| ---------------------------- | ------------------------------------------------- |
| TAPD 评论 @ 人、按作者定角色 | `tapdname`（只有 `githubname` 的成员无法 @）      |
| 汇报 / 周报 @ 人             | `tapdname` 优先，缺失时用 `githubname` 并提示补齐 |
| GitHub PR / issue / API 查询 | `githubname`                                      |
| 匹配 git 提交作者            | 提交邮箱（见下）                                  |

某角色缺失或为空时：按角色定位成员的逻辑改为按内容推断，需要 @ 却无配置时跳过并提示补齐。

### git 提交身份

`githubname` 不等于本地 commit 的作者名（`user.name`），直接用 `--author=<githubname>` 会漏统计。先解析提交邮箱：

```bash
gh api "repos/<owner>/<repo>/commits?author=<githubname>&per_page=100" \
  --jq '[.[].commit.author.email] | unique | join(" ")'
```

- `owner/repo` 取 github.com 远端，多远端时优先 `upstream`/`base`，其次 `origin`。
- 一个成员可能有多个邮箱（`@users.noreply.github.com` 与私人邮箱），全部纳入候选；归属以提交邮箱 `%ae`
  为准，对不上再退回作者名匹配。
- `gh` 未登录或查无结果时降级为作者名匹配，并说明该成员统计口径可能不全。
- 归属不到任何成员的作者：列出作者名与提交条数请用户确认，不擅自归并、不静默丢弃。
