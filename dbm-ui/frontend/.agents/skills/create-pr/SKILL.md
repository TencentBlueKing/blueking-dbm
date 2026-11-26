---
name: create-pr
description: >-
  把当前分支从个人 fork 向上游 TencentBlueKing/blueking-dbm 创建 Pull Request。
  当用户要求创建、提交或发起 PR / Pull Request，或输入 /create-pr 时使用。
---

# 创建 Pull Request

**Input**：`/create-pr` 后可带目标分支与 issue 编号。`#数字` 或纯数字为 issue（缺省时从提交标题末尾 `#\d+`
提取），其余为目标分支（缺省时用 AskQuestion 询问，推荐 `frontend_dev`）。

**核心约定**：PR head 一律是「基于上游目标分支新建的临时分支 + cherry-pick 源分支提交」，不直接推源分支。
这样每个 PR 只含目标 commit 的改动，与源分支上其他无关提交、与源分支领先/落后目标分支的状态完全隔离。

**输出**：创建前必须让用户预览标题与正文；创建成功后给出 PR 链接。

## 执行流程

用 TodoWrite 跟踪：

```
1. 解析仓库 → 2. 前置检查 → 3. 收集改动 → 4. 确认验证项 → 5. 生成标题正文并预览
→ 6. 建临时分支并 cherry-pick → 7. 推送并创建 PR，清理临时分支
```

### 1. 解析仓库

```bash
git remote -v
git branch --show-current
```

- 上游（`-R`）：URL 指向 `TencentBlueKing/blueking-dbm` 的远端，优先 `upstream`，其次 `base`。
- fork（`--head` owner）：`origin` 的 github.com owner；`git.woa.com` 等非 GitHub 远端忽略。
- 目标分支：`git fetch <上游> <目标> --quiet` 后用 `git rev-parse --verify <上游>/<目标>` 校验，不存在则终止。

### 2. 前置检查

命中即用 AskQuestion 让用户决定，不擅自处理：

| 检查项 | 命令 | 命中时 |
| --- | --- | --- |
| 工作区有未提交改动 | `git status --porcelain` | 询问：先提交 / 忽略继续 / 终止 |
| 相对目标分支无提交 | `git log <上游>/<目标>..HEAD --oneline` 为空 | 直接终止 |
| 提交信息不合规 | 见下方正则 | 列出不合规提交，询问：终止去修 / 忽略继续 |
| 多条提交 | 提交数 > 1 | 询问：终止去 rebase / 继续 |
| 已存在同内容 PR | `gh pr list -R <上游> --head <临时分支> --state open --json number,url` | 直接终止，给出链接 |

提交信息正则（与上游 `commit_message_check.yml` 一致）：

```
^(feat|fix|perf|refactor|docs|test|style|chore)(\(.+\))?: .{1,100} #\d+$
```

不要 rebase、amend 或 force push 源分支。

### 3. 收集改动

```bash
git log <上游>/<目标>..HEAD --format='%h|%s%n%b' --reverse
git diff <上游>/<目标>...HEAD --stat
git diff <上游>/<目标>...HEAD
```

`--reverse` 的输出顺序即第 6 步 cherry-pick 顺序。diff 过大先看 `--stat` 再挑关键文件读，不要只凭提交标题写 Summary。

### 4. 确认验证项

用 AskQuestion 多选本次要跑哪些（执行前须经用户确认）：

- `yarn type-check`
- `npx eslint <改动文件>`（仅 `dbm-ui/frontend` 下）
- 改了 `.less` 时 `npx stylelint <改动文件>`
- `yarn build`
- 都不跑

失败时把摘要给用户，询问「终止去修 / 如实写入 Test plan 继续」；目标分支既有错误与本次改动区分开写。

### 5. 生成标题与正文

标题：单条提交直接用提交标题；多条按主要改动合成 `<type>(frontend): <描述> #<issue>`；无 issue 询问用户，不编造。

正文模板（段落标题固定 `## Summary` / `## Test plan`，不改名、不增删）：

```markdown
## Summary

- <结论式短句：做了什么 + 目的>
- <结论式短句>

关联：#<issue>

## Test plan

- [x] `yarn type-check` 通过
- [x] 改动文件 ESLint 通过
- [ ] <页面>：<操作>，预期 <结果>
```

- Summary 2–5 条，按用户可感知影响组织，不按文件罗列；涉及公共代码（`components/`、`hooks/`、`services/`）
  或跨多 DB 时单列一条说明影响范围；不贴大段代码，不写 diff 未体现的内容。
- `[x]` 只用于本次真实跑过的命令；「都不跑」时自动化项保留 `[ ]`；运行时验证项一律 `[ ]`，写清
  「页面 + 操作 + 预期结果」，至少一条；纯文档/配置改动写一条 `[ ]` 说明人工确认点。

### 6. 建临时分支并 cherry-pick

临时分支命名 `<源分支>-to-<目标分支>`（如 `feat-foo-to-frontend_dev`），重名追加短 hash。

```bash
git fetch <上游> <目标> --quiet
git checkout -b <临时分支> <上游>/<目标>
git cherry-pick <commit-1> <commit-2> ...   # 顺序与第 3 步 --reverse 输出完全一致
```

完成后 `git log <上游>/<目标>..HEAD --oneline` 自检，应只列出本次目标 commit。源分支历史保持不动。

**冲突解决**：目标是在目标分支最新代码上完整保留源 commit 意图，不是"能提交就行"。

1. 先读懂两侧：`git show <正在pick的commit> -- <文件>` 看源意图，`git log <上游>/<目标> -p -n 5 -- <文件>`
   看目标侧演进，说清两侧在做什么再改。
2. 合并语义：禁止整文件 `--ours`/`--theirs`；双方结构性改动（重命名、参数新增、分支调整）都保留，源 commit
   的功能/条件/字段/文案全在，且不覆盖目标侧新逻辑。
3. 自检后 continue：`git diff <源分支> -- <冲突文件>` 剩余差异应只来自目标侧；无 `<<<<<<<` 残留；
   `git add` 后 `git -c core.editor=true cherry-pick --continue`，提交信息保持原样。
4. 提交信息不加"解决冲突"字样；最终回复单独列出冲突文件与合并思路，提示 reviewer 重点看。
5. 仅以下情况允许 abort（`git cherry-pick --abort` → 切回源分支 → 删临时分支 → 把冲突点交给用户）：
   双方实现互斥无法判断行为；源依赖的接口在目标侧已删且无等价替代；解决需新增源 commit 之外的业务判断。

### 7. 推送并创建 PR，清理临时分支

```bash
git push -u origin <临时分支>
gh pr create -R <上游> --base <目标分支> --head <fork-owner>:<临时分支> --title "<标题>" --body "<正文>"
```

`gh pr create` 成功后清理本地临时分支：

- 只删本次新建的临时分支，源分支、目标分支、其他已有分支不删。
- 只删本地分支，不删 fork 远端分支（PR head 指向它，删了会关 PR；合入后在 GitHub 页面 Delete branch）。
- 创建失败时保留分支便于重试，并在回复中说明。

```bash
git checkout <源分支>
# 本地与远端一致才删除；不一致说明有未推送提交，保留并提示
[ "$(git rev-parse <临时分支>)" = "$(git rev-parse origin/<临时分支>)" ] && git branch -D <临时分支>
```

用 `git worktree add` 检出的，先 `git worktree remove <路径>` 再删分支。最终回复列出已删分支，保留的分支说明原因。

## 约定

- 只做提 PR 相关操作：不改业务代码（第 6 步解决冲突除外）、不改写源分支历史、不改 `agent-flow.config.json`；
  分支新建只限第 6 步临时分支，删除只限第 7 步临时分支。
- 正文用中文，段落标题保持英文 `Summary` / `Test plan`。
- 最终回复给出 PR 链接，并列出 Test plan 中仍为 `[ ]` 待人工确认的项。
