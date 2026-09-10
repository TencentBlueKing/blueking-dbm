# validate 失败走 reject，不 resolve `false`

- **命中**：`rg -n '(const|let) \w+ = await [^;]*\.validate\(' src`，以及
  `rg -n 'Promise\.all\(\[[^]]*\.validate\(' src`。命中的是把 `DbForm` / `EditableTable` 的 `.validate()`
  返回值当布尔用的三种形态——`const x = await ref.validate(); if (!x) return;`、`if (x) { 提单 }`、
  `(await Promise.all([...])).every((i) => i)`
- **为什么**：失败时 promise 直接 reject，`await` 会抛出，布尔判断是永远进不去的死代码，还会留一条未捕获
  rejection。类型声明 `Promise<boolean>` 是误导来源——`boolean` 让人以为失败会 resolve `false`，实际成功路径只会
  resolve `true`
- **改成**：`ref.validate().then(() => { ... })`，删掉布尔判断和不可达的兜底返回（`[]` / `{ infos: [] }` /
  `Promise.resolve(false)`）
- **不要**逐处加 `.catch(() => {})` 去消未捕获 rejection：reject 值是 `false` 与 Error 混杂，静默 catch
  会把 validator 自己抛的真实异常一起吞掉
- **存量**：`EditableTable` 侧调用点已统一；`DbForm` 侧 5 处未改（命中命令的输出里另有 2 行是注释掉的旧代码，不算）
  - `src/views/db-manage/mysql/MYSQL_DUMP_DATA/Index.vue`
  - `src/views/db-manage/tendb-cluster/TENDBCLUSTER_DUMP_DATA/Index.vue`
  - `src/views/db-manage/sqlserver/SQLSERVER_DATA_EXPORT/Index.vue`
  - `src/views/db-manage/redis/REDIS_SCALE_UPDOWN/components/target-capacity-column/cluster-deploy-plan/Index.vue`
  - `src/views/db-manage/common/cluster-batch-add-tag/components/tag-operation/components/key-value-mode/components/KeyValuePair.vue`
- **核实**：2026-09-10

## 补充

转发点的变量名各不相同（`tableRef` / `editableTableRef` / `renameListRef` / `currentTableRef`），按变量名搜必然漏，要按
`\.validate\(` 全量扫再按形态分类。

把返回类型从 `Promise<boolean>` 改成 `Promise<void>` 是更诚实的形态，但会牵动所有 `defineExpose` 的 `Exposes`
声明与 `Awaited<ReturnType<...>>` 推导，范围很大，未做。
