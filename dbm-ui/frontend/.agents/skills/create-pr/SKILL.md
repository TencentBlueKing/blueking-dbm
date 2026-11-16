---
name: create-pr
description: 把当前分支从个人 fork 向上游 TencentBlueKing/blueking-dbm 创建 Pull Request
disable-model-invocation: true
---

# 创建 Pull Request

**Input**：`/create-pr` 之后可选传入目标分支与 issue 编号，顺序不限。

- 形如 `#12345` 或纯数字的入参为 issue 编号，未传入时从提交标题末尾的 `#\d+` 提取。
- 其余入参为目标分支（如 `frontend_dev`、`frontend_master`、`v1.5.0`），未传入时用 **AskQuestion tool**
  询问，`frontend_dev` 作为推荐项。

**输出方式**：创建成功后在对话中给出 PR 链接、标题与正文；创建前必须先让用户确认预览。

## 执行流程

用 **TodoWrite tool** 跟踪以下清单并逐项推进：

```
- [ ] 1. 解析仓库：上游仓库、个人 fork、当前分支、目标分支
- [ ] 2. 前置检查：工作区、提交规范、是否已有 PR
- [ ] 3. 收集改动：提交列表与 diff
- [ ] 4. 确认 Test plan 的验证项
- [ ] 5. 生成标题与正文，预览并确认
- [ ] 6. 推送分支并创建 PR
```

### 1. 解析仓库

```bash
git remote -v
git branch --show-current
```

- 上游仓库（`-R`）：取 URL 指向 `TencentBlueKing/blueking-dbm` 的远端，名称优先 `upstream`，其次 `base`。
- 个人 fork（`--head` 的 owner）：取 `origin` 的 github.com 远端 owner。
- `git.woa.com` 等非 GitHub 远端一律忽略。
- 目标分支先 `git fetch <上游远端> <目标分支> --quiet`，再用 `git rev-parse --verify <上游远端>/<目标分支>`
  校验存在；不存在时终止并提示分支名可能写错。

### 2. 前置检查

逐项检查，命中即用 **AskQuestion tool** 让用户决定，不擅自处理：

| 检查项                   | 命令                                                                | 命中时                                                       |
| ------------------------ | ------------------------------------------------------------------- | ------------------------------------------------------------ |
| 工作区有未提交改动       | `git status --porcelain`                                            | 询问：先提交 / 忽略继续（未提交部分不进 PR） / 终止          |
| 本分支相对目标分支无提交 | `git log <上游>/<目标>..HEAD --oneline` 为空                        | 直接终止，说明没有可提交的改动                               |
| 提交信息不合规           | 见下方正则                                                          | 列出不合规的提交，询问：终止去修 / 忽略继续                  |
| 多条提交                 | 提交数 > 1                                                          | 提示仓库约定一个 PR 对应一条提交，询问：终止去 rebase / 继续 |
| 已存在同分支 PR          | `gh pr list -R <上游> --head <分支> --state open --json number,url` | 询问：更新已有 PR 的正文 / 终止                              |

提交信息正则（与上游 `commit_message_check.yml` 一致，CI 按它检查全部提交）：

```
^(feat|fix|perf|refactor|docs|test|style|chore)(\(.+\))?: .{1,100} #\d+$
```

不要自动 rebase、amend 或 force push，改写历史只由用户自己执行。

### 3. 收集改动

```bash
git log <上游>/<目标>..HEAD --format='%h|%s%n%b'
git diff <上游>/<目标>...HEAD --stat
git diff <上游>/<目标>...HEAD
```

diff 过大时先看 `--stat`，再按目录挑关键文件读，不要只凭提交标题写 Summary。

### 4. 确认 Test plan 的验证项

AGENTS.md 约定验证命令执行前要经用户确认，所以这里用 **AskQuestion tool**（多选）询问本次要跑哪些：

- `yarn type-check`
- 改动文件 `npx eslint <改动文件>`
- 改了 `.less` 时 `npx stylelint <改动文件>`
- `yarn build`
- 都不跑

只对 `dbm-ui/frontend` 下的改动文件跑 eslint / stylelint。命令失败时把失败摘要给用户，询问「终止去修 / 如实写入 Test
plan 继续」；目标分支自身存在的既有错误要与本次改动区分开写。

### 5. 生成标题与正文

**标题**：

- 单条提交：直接用该提交标题。
- 多条提交：按主要改动类型合成一条，格式与提交一致：`<type>(frontend): <描述> #<issue>`。
- 没有 issue 编号时询问用户，不编造编号。

**正文模板**（两个段落标题固定为 `## Summary` 与 `## Test plan`，不改名、不增删段落）：

```markdown
## Summary

- <结论式短句：改了什么、为什么改>
- <结论式短句>

关联：#<issue>

## Test plan

- [x] `yarn type-check` 通过
- [x] 改动文件 ESLint 通过
- [ ] <页面>：<操作>，预期 <结果>
- [ ] <页面>：<操作>，预期 <结果>
```

Summary 规则：

- 2 到 5 条，每条一句，写「做了什么 + 目的」，按用户可感知的影响组织，不按文件罗列。
- 涉及公共代码（`components/`、`hooks/`、`services/`）或影响多个 DB 的改动，单列一条说明影响范围。
- cherry-pick 类 PR 写明源提交 hash 与源分支。
- 不贴大段代码，不写 diff 里没有体现的内容。

Test plan 规则：

- `[x]` 只用于第 4 步本次真实执行并通过的命令；没跑的命令不写成 `[x]`，也不写「已验证」。
- 第 4 步选择「都不跑」时，自动化检查项写成 `[ ]` 保留，提示 reviewer 尚未执行。
- 运行时验证项一律 `[ ]`，每条写清「哪个页面 + 哪个操作 + 预期结果」，从 diff 推导真实受影响的入口，至少一条。
- 纯文档、配置类改动没有运行时入口时，写一条 `[ ]` 说明需人工确认的点，不留空段。

## 约定

- 只做提 PR 相关的操作：不改代码、不改写提交历史、不改 `agent-flow.config.json`。
- 正文语言用中文，段落标题保持英文 `Summary` / `Test plan`。
- 最终回复给出 PR 链接，并列出 Test plan 中仍为 `[ ]` 待人工确认的项。
