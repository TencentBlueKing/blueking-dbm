# 检查项索引

改 `src/` 下文件前扫一遍本表。A 类按代码特征判断，B 类先看路径前缀，路径对不上直接跳过。

**扫完必须在回复里写一行**：`known-issues: 已扫，命中 N 条`（N 为 0 也要写）。不写等于没扫。

- A 类命中在**本次已经碰到的代码**里 → 直接修掉，回复里说明
- A 类命中在同文件其它位置、或其它文件 → 只报告，不动手
- B 类一律只报告，不动手

## A 类：命中即修

- [validate 失败走 reject，不 resolve `false`](doc/validate-failure-contract.md)
  —— 用到 `DbForm` / `EditableTable` 的 `.validate()`，且返回值被当布尔判断
- [分页组件不认 `current`，必须显式绑 `:model-value`](doc/pagination-model-value.md)
  —— `<BkPagination>` / `<DbPagination>` 只写了 `v-bind="pagination"`
- [筛选值全链路只能是逗号分隔字符串](doc/filter-value-encoding.md)
  —— 搜索栏与表格列筛选之间传值，或给 `MultipleSelect` 传 `value` / 写选项 `value`

## B 类：只报告，改法未定

- `views/db-manage/common/{cluster,instance}-table/**`、任何新增表格列
  —— [新增表格列不要再造一个宽度取值](doc/table-column-width.md)
- 任何写 `shortcuts: [` 的地方
  —— [时间范围快捷选项同目录共用一份常量](doc/datetime-range-shortcuts.md)
- 做拖拽改宽度的面板、侧栏、弹窗
  —— [可拖拽改宽度不要用 `table-detail-dialog/hooks/use-resize.ts`](doc/resize-panel-width.md)
- `components/db-quick-search/**/value-menu/**`、`components/db-table/components/**`
  —— [筛选下拉面板有两套同源拷贝](doc/filter-panel-fork.md)
- `components/ip-selector/components/CollapseTable.vue`、`db-manage/common/big-data-host-table/**`、
  `db-manage/common/cluster-authorize/components/TargetInstances.vue`，或新写「折叠头部 + 本地分页表」
  —— [折叠预览表有 5 份独立实现](doc/collapse-preview-table-fork.md)
- `views/task-history/detail/**` 的重试 / 跳过 / 强制失败 / 确认继续
  —— [任务流节点操作有四个独立入口](doc/node-operation-fork.md)

## 已下沉到工具，不用再扫

- `setTimeout(..., 210)` 等标签输入失焦 → `eslint.config.mjs` 的 `no-restricted-syntax`，
  报错信息指向 [doc/tag-input-blur-delay.md](doc/tag-input-blur-delay.md)
