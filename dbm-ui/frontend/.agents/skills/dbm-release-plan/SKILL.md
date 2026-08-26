---
name: dbm-release-plan
description: >-
  生成 frontend_master 待合入 v1.5.0 的 commit 发布计划记录。当用户需要发布计划、 发版记录、核对 frontend_master
  还有哪些提交未合入 v1.5.0，或给出 release PR 链接 要求生成 commit 清单时使用。是否已合入的判定逻辑：以 commit msg
  尾部的 issue id （如 #19152）在 v1.5.0 历史中是否存在相同 issue id 的提交为准（识别 cherry-pick）。
disable-model-invocation: true
---

# dbm-release-plan

生成 `frontend_master` 相对 `v1.5.0` 的发布计划 commit 记录。

## 判定逻辑

1. 用 `git log base/v1.5.0..base/frontend_master --no-merges` 拿到 `frontend_master` 领先的所有提交。
2. 从每条 commit msg 尾部提取 issue id（`#数字`，取最后一个匹配）。
3. 在 `v1.5.0` 历史中 `--grep` 搜索相同 issue id：
   - 搜到 → **已合入**（通常是被 cherry-pick 过去，SHA 不同但 issue id 相同）
   - 搜不到 → **未合入**，列入发布计划
4. 无 issue id 的提交单独标注，需人工确认。

## 远程仓库约定

- `base` 指向 `TencentBlueKing/blueking-dbm`（主仓库）。
- 若本地无 `base` 远程，先通过 `git remote -v` 找到指向主仓库的远程名，下文命令中的 `base/` 全部替换为该远程名。

## 执行步骤

### 1. 拉取最新分支

```bash
git fetch base frontend_master v1.5.0
```

### 2. 生成 commit 状态列表

在仓库根目录执行（zsh/bash 均可）：

```bash
for sha in $(git log base/v1.5.0..base/frontend_master --no-merges --pretty=format:"%h"); do
  info=$(git log -1 --pretty=format:"%an|%s" $sha)
  msg=$(echo "$info" | cut -d'|' -f2)
  issue=$(echo "$msg" | grep -oE "#[0-9]+" | tail -1)
  st="未合入"
  if [ -z "$issue" ]; then
    st="无issue"
  elif [ -n "$(git log base/v1.5.0 --no-merges --pretty=format:%h --grep="$issue" | head -1)" ]; then
    st="已合入"
  fi
  echo "$st|$info"
done
```

注意：不要用 `status` 作为变量名，zsh 中它是只读变量。

### 3. 输出报告

只输出未合入的提交，格式：

```markdown
## 本次发布计划（N 个）

| 作者 | 提交信息 |
| ---- | -------- |
| ...  | ...      |
```

- 标题带未合入个数，表格列 `作者 | 提交信息`，提交信息中保留 issue id 以便追溯。
- 已合入、无issue 的提交不输出，仅在存在异常（如无 issue id）时用一句话提醒。

如需追溯已合入提交在 v1.5.0 中的对应 commit：

```bash
git log base/v1.5.0 --no-merges --pretty=format:"%h %s" --grep="#<issue id>"
```

## 注意事项

- 全程只读操作，不要切换分支、不要修改工作区。
- issue id 取 commit msg 中**最后一个** `#数字`（标题里可能引用多个 issue，约定尾部编号为准）。
- `--grep` 匹配的是完整 commit message，若担心正文误匹配，可人工复核已合入条目。
- 版本号分支名（`v1.5.0`）和源分支名（`frontend_master`）按用户当次需求替换。
