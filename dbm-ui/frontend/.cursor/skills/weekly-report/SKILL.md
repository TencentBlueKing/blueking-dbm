---
name: weekly-report
description: 按 agent-flow.config.json 的周期与分支配置汇总本端成员 commit，生成精简周报并直接输出在对话中
disable-model-invocation: true
---

# Git 提交周报

**Input**：`/weekly-report` 之后可选传入周期与分支，二者均覆盖配置，未传入的部分用 `agent-flow.config.json` 的
`weeklyReport.period` / `weeklyReport.branches`。

- 形如 `1w` / `2w` / `3w` 的入参为周期，传入非法值时提示合法取值并改用配置值。
- 其余入参为分支，可传多个（空格或逗号分隔），支持 glob（如 `release/*`）。

**输出方式**：周报**不写入任何文件**，直接作为最终回复输出在对话中。

## 前置依赖

- 项目根目录存在 `agent-flow.config.json`（含公共配置 `repoType`、`members` 与本命令专属配置 `weeklyReport`）。
- 当前目录在 git 仓库内，且能读取到远端分支（必要时先
  `git fetch --all --quiet`，失败不阻塞，用本地已有 ref 继续并在末尾说明）。
- `gh` CLI 已登录（用于把 `githubname` 解析成 git 提交邮箱）。不可用时按 `agent-flow-config` skill 的降级规则处理。

## 执行流程

用 **TodoWrite tool** 跟踪以下清单并逐项推进：

```
- [ ] 1. 读取配置：repoType、members、weeklyReport.period / weeklyReport.branches（或入参覆盖）
- [ ] 2. 计算周期起止日期
- [ ] 3. 解析成员 git 身份（githubname → 提交邮箱）
- [ ] 4. 在分支范围内拉取本端成员在周期内的提交
- [ ] 5. 识别未匹配作者与无提交成员
- [ ] 6. 按需求编号合并归类，直接在对话中输出周报
```

### 1. 读取配置

按 `agent-flow-config` skill 读取
`agent-flow.config.json`（配置分层、成员昵称解析、缺失与非法配置的处理均以该 skill 为准），本命令用到
`repoType`、`members` 与 `weeklyReport` 节点：

- `repoType` 决定统计对象：只统计 `members[repoType]` 的成员，其他角色不统计。无该字段时按仓库特征推断（`package.json` +
  `src/` → 前端；`manage.py`/`go.mod`/`pom.xml` → 后端），仍无法确定则询问用户。
- `weeklyReport.period` 取值与含义（周一为一周起点）：

| 值   | 含义                 | 起始日                    |
| ---- | -------------------- | ------------------------- |
| `1w` | 当前周内             | 本周一                    |
| `2w` | 上一周 + 当前周      | 上周一（本周一 - 7）      |
| `3w` | 包含当前周的最近三周 | 前两周周一（本周一 - 14） |

`weeklyReport` 节点或 `period` 缺失、取值非法时默认值为 `1w`。

- `weeklyReport.branches` 为统计的分支范围，字符串数组，元素是分支名或 glob（如
  `master`、`release/*`），同名的本地与远端分支一并纳入。
- 缺失或为 `[]` 时表示**全部本地与远端分支**，这是默认口径，无需确认直接继续。
- 取值非法（不是数组、元素不是字符串或为空串）时默认口径同样为「全部分支」。

### 2. 计算周期起止

```bash
# N 为周期数：1w→1、2w→2、3w→3
D=$(date +%u)                                      # 1=周一
S=$(date -v-$(( (D-1) + 7*(N-1) ))d +%F 2>/dev/null || date -d "$(( (D-1) + 7*(N-1) )) days ago" +%F)
```

`S` 为起始日（周一），截止时间为当前时刻。

### 3. 解析成员 git 身份

按 `agent-flow-config` skill 的「git 提交身份」把每个成员的 `githubname`
解析成提交邮箱集合（含降级与归属规则），作为第 4 步 `--author` 的身份候选。

### 4. 拉取提交

在 `agent-flow.config.json` 所在目录执行（pathspec 用
`.`，自动把统计范围限定到本端代码目录，避免统计到成员在对端目录的提交）：

```bash
# 分支范围 R：未指定分支时为全分支
R="--branches --remotes"
# 指定分支时，逐个分支 B 追加一对参数，把同名的本地与远端分支都纳入
R="--branches=<B1> --remotes=*/<B1> --branches=<B2> --remotes=*/<B2>"

git log $R --no-merges --since="$S 00:00:00" \
  --date=short --format='%cd|%ae|%an|%s' \
  --perl-regexp --author='<身份候选，用 | 连接>' -- . \
  | sed 's/ # Reviewed, transaction id:.*$//' | sort -u
```

约束：

- 身份候选 = 第 3 步解析出的全部邮箱 + 各成员的 `tapdname` / `githubname`（`--author` 同时匹配作者名与邮箱）。
- 归属成员以邮箱 `%ae` 为准，邮箱对不上再退回作者名匹配。
- 指定分支时先校验存在性：`git for-each-ref --format='%(refname:short)' 'refs/heads/<B>' 'refs/remotes/*/<B>'`
  无输出说明该分支不存在，把它从范围中剔除并在末尾「待确认」列出；全部分支都无匹配时终止执行，提示分支名可能写错。
- 分支范围一律用 `--branches` / `--remotes`（不用 `--all`），避免把 stash（`index on ...` / `WIP on ...`）计入。
- 用提交日期 `%cd` 过滤与展示（与 `--since` 一致），不用作者日期——周报关注的是本周期内落库的产出。
- `sort -u` + 去掉 `# Reviewed, transaction id: xxx` 尾巴，消除同一提交在多分支/多次 review 的重复。

### 5. 未匹配作者与无提交成员

再执行一次**不带 `--author`**、分支范围 `$R` 与第 4 步一致的 `git log`（输出 `%ae|%an`），取作者集合与身份候选做差集：

- **未匹配作者**：周期内有本端目录提交但归属不到任何成员。其提交**不计入正文**，在末尾「待确认」列出作者名与提交条数，请用户确认归属或补齐配置。
- **无提交成员**：配置中存在但周期内无提交，在末尾一行列出即可，不做推测。

### 6. 输出周报

**归并规则**（核心要求：不做流水账）：

- 以提交标题末尾的需求编号（`#12345`）为聚合键，同一编号的多条提交合并成**一条任务**；同一任务多人参与则 @ 全部参与成员。
- 无编号的提交按标题语义就近合并到相关任务，无法归并的单独成条。
- 标题去掉 `feat(frontend):`
  等类型前缀与编号后缀，改写为「做了什么」的结论式短句（可合并多次提交的语义，如「联调 + 验收问题处理」写成一条）。
- 按提交类型分组：`feat` → 需求与功能；`perf`/`refactor`/`style`/`chore`/`build` → 优化与重构；`fix`
  → 缺陷修复。空分组直接省略。
- 每条任务一行，末尾 @ 对应成员（`@tapdname`，多人用空格分隔）。控制在一屏内，正文条目建议不超过 20 条；同一成员的琐碎同类项（依赖升级、样式微调等）合并成一条。
- 不贴 commit hash、不列分支、不写工时、不臆造未在提交中体现的进展。

**输出模板**（直接输出在对话中，不写文件）：

```markdown
# <前端/后端>周报（<起始日> ~ <截止日>，近 <N> 周<，分支 <分支范围>>）

## 需求与功能

- <结论式短句> @<tapdname>
- <结论式短句> @<tapdname> @<tapdname>

## 优化与重构

- <结论式短句> @<tapdname>

## 缺陷修复

- <结论式短句> @<tapdname>

## 待确认

- 未匹配作者：`<author>`（<n> 条），是否归属某成员？
- 无提交成员：@<tapdname>
- 不存在的分支：`<branch>`，已从统计范围剔除
```

「待确认」段无内容时整段省略；标题里的分支只在指定了分支时标出，全分支时省略。

## 约定

- 只读操作：本命令不修改代码、不创建文件、不写 TAPD。
- 统计口径固定：本端成员 + 本端代码目录 + 周期内提交日期 + 分支范围，四者同时满足。
- 语言与项目一致（中文）；成员称呼统一用 `tapdname`。
