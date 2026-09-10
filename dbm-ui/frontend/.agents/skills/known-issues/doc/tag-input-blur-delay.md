# 不用 `setTimeout` 等标签输入失焦落值

**已下沉到 ESLint**，不在 `checks.md` 索引里。`eslint.config.mjs` 的 `no-restricted-syntax` 会在
`setTimeout(..., 210)` 上报 warning，提示信息指回本篇。本篇只保留改法。

用 `warn` 而不是 `error`，是因为存量 3 处里有 1 处的改法没验证过（见下）。`error`
会让只想改隔壁一行的人被卡住，最后必然是加一行 `eslint-disable` 把信号彻底抹掉。改法验证过之后再提到 `error`。

- **命中**：ESLint 报错；或人工排查时 `rg -n ', 210\)' src`。注意实际代码是跨行的，按
  `setTimeout.*210` 单行搜会一个都搜不到
- **为什么**：210ms 是排在 bkui `BkTagInput` 内部 200ms 之后的经验值（bkui 在 blur 后延时 200ms
  才把输入框里的残留文字提交成标签，需开 `allowAutoMatch`）。这个数字既没有常量也没有类型约束，bkui
  改了延时实现不会报错、不会 lint 失败，只会在批量编辑确认时静默拿到旧值
- **改成**：换成自研 `DbTagInput` 并订阅 `@blur`——它已改为同步提交残留输入，`emit('blur', residualValue, tagList)`
  把残留输入与提交后的标签列表一并给出。样板见 `src/components/editable-table/edit/` 下 `Input.vue` / `Select.vue` /
  `TagInput.vue` / `DatePicker.vue` / `Textarea.vue` 五个控件：失焦时调 `columnContext.blur()` +
  `columnContext.validate('blur')` 再 `emits('blur')`，父级订阅事件而不是猜时间。
  **改完要人工验证**：批量编辑页填入未回车的残留文字后直接点确认，预期取到的是最新值
- **不要**把 bkui 的 200 提成共享常量再让业务方 `+10`：常量化只是让魔法数字有了名字，时序耦合还在
- **存量**：3 处
  - `src/views/db-manage/common/batch-edit-column/Index.vue` —— 挂 `BkTagInput` 且开了 `allow-auto-match`，按上面的改法改
  - `src/views/db-manage/common/batch-edit-column-new/Index.vue` —— 同上
  - `src/views/staff-manage/common/BatchEdit.vue` —— 同一个「tippy 弹层 + 确认时延时 210ms」的拷贝，但里面挂的是
    `MemberSelector` 不是 `BkTagInput`。**这处的改法未验证**：`MemberSelector` 有没有等价的
    `@blur` 契约没查过，命中只报告
- **核实**：2026-09-10

## 补充

`BkTagInput` → `DbTagInput` 的替换在本仓库发生过（commit `5bd174001`，mysql 与 tendb-cluster
分区管理）。自研组件原先在 blur 后也延时 200ms，且延时里做的事与 bkui **语义相反**——丢弃残留文字而不是提交；这个矛盾已消除，所以现在换过去不再有「残留输入被丢掉」的风险，210ms 只会退化成纯多余的等待。
