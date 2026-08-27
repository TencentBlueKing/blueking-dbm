# 表格 validate 的失败协议：声明是布尔，实际是 reject

状态：已处理（`EditableTable` 侧 148 处调用点已按 reject 协议改写；`DbForm` 侧 4 处同类死判断与「暴露了 validate 但无人调用」的页面未处理）

## 现象

`EditableTable.validate()` 的类型声明是 `Promise<boolean>`，实际协议是**失败 reject、成功 resolve `true`**，与
`DbForm.validate()` 一致。但页面层压倒性地按「resolve 布尔」写：148 处调用点里只有 13 处依赖 reject，其余 135 处都在判断返回值。

这些判断是**死代码**：`await` 遇到 rejected promise 会抛出，`if (!result) return` 永远进不去。行为上恰好没错（失败一样阻断提单），代价是控制台一条未捕获
rejection，以及后来者会照着错误的假设继续复制。

## 证据

### 1. 协议本身

- `src/components/editable-table/Column.vue`：`runValidate` 的 `setValidateError` 返回 `Promise.reject(false)`，成功路径 resolve `true`。
- `src/components/editable-table/Index.vue`：`validateColumnList` 是 `Promise.all(...).then(() => true)`，任一单元格 reject 即整体 reject。
- `src/components/db-form/index.vue:120-127`：`validate` 在 catch 里滚动到错误项后 `return Promise.reject(error)`。协议相同。
- 类型声明 `Promise<boolean>` 是误导来源：`boolean` 让人以为失败会 resolve `false`，实际上永远只会 resolve `true`。

### 2. 页面层的五种写法（本次已统一为 `.then()`）

| 形态 | 处数 | 说明 |
| ---------------------------------------------------- | ---- | -------------------------- |
| `const x = await t.validate(); if (!x) return;` | 66 | 判断恒不成立 |
| `const x = await t.validate(); if (x) { 提单 }` | 48 | 判断恒成立 |
| `async getValue() { ...; if (!x) return 兜底; }` | 19 | 兜底 `[]` / `{ infos: [] }` / `Promise.reject([])` 均不可达 |
| `.validate().then((x) => { if (x) {...} return 兜底; })` | 13 | 同上 |
| `try { await ...; if (!x) throw new Error(); }` | 2 | 唯一真正处理失败的写法（catch 里 messageError） |

同一个仓库里同时存在这五种形态，说明契约从来没被写清楚过，每个作者都按自己的猜测写了一遍。

### 3. 契约不明导致的自我防御写法

`SQLSERVER_FULL_MIGRATE/components/edit-rename-info/components/RenameList.vue` 与
`SQLSERVER_ROLLBACK/components/final-db-column/components/edit-rename-info/components/RenameList.vue` 转发表格 validate 时写成：

```ts
return tableRef.value?.validate()?.then((res) => res) ?? Promise.resolve(false);
```

`then((res) => res)` 是恒等变换，`?? Promise.resolve(false)` 又给出了第三种失败表达。作者显然不确定
`validate()` 返回的是什么。

### 4. 间接转发放大了搜索难度

把表格 `validate` 转发出去的组件（`validate: () => ...validate()`）：

- `views/db-manage/sqlserver/SQLSERVER_IMPORT_SQLFILE/components/backup/Index.vue:111`
- `views/db-manage/sqlserver/SQLSERVER_IMPORT_SQLFILE/components/execute-objects/Index.vue:156`
- `views/db-manage/common/sql-execute/mysql-backup/Index.vue:112`
- `views/db-manage/sqlserver/SQLSERVER_DATA_EXPORT/components/DbFormItem.vue:120`
- `views/db-manage/mongodb/MONGODB_INSTANCE_RELOAD/components/{instance,host,cluster}/Index.vue:209 / 182 / 158`

转发点的变量名各不相同（`tableRef` / `editableTableRef` / `renameListRef` / `currentTableRef`），按变量名搜索必然漏；本次是按
`\.validate\(` 全量扫 + 形态分类才收齐的。

### 5. 暴露了 validate 但没人调用（未处理）

- `views/db-manage/sqlserver/SQLSERVER_DATA_EXPORT/Index.vue:60` 的 `<DbFormItem>` 没有挂 ref，提交处只
  `await formRef.value!.validate()`，`DbFormItem.vue:120` 暴露的表格校验永远不会执行。
- `views/db-manage/mysql/MYSQL_IMPORT_SQLFILE/steps/step1/Index.vue:186` 与
  `views/db-manage/tendb-cluster/TENDBCLUSTER_IMPORT_SQLFILE/steps/step1/Index.vue:185` 都只
  `formRef.value!.validate().then(...)`，`mysql-backup/Index.vue:112` 暴露的 validate 无调用方。
- `views/db-manage/mongodb/MONGODB_INSTANCE_RELOAD/Index.vue` 原先写的是
  `await Promise.all([tableRef.validate, currentTableRef.value!.validate])`——传的是方法引用而非调用结果，表格校验从未生效。本次已改为
  `tableRef.validate().then(...)`（同一行还重复校验了同一个表格实例）。该文件 170 行附近另有一处 `console.log` 未清理。

## 结论

问题不是「有人写错了」，而是**类型声明与运行时协议不一致**：`Promise<boolean>` 描述不了「失败 reject」这件事，声明反而成了错误写法的依据。

已做：
- `Column.validate` / `Index.validate*` 加注释明确「与 DbForm 一致：失败 reject、成功 resolve(true)」。
- 148 处调用点统一为 `.then(() => { ... })`，删掉不可达的布尔判断与兜底返回。

未做（下次动到再说）：
- 把返回类型从 `Promise<boolean>` 改成更诚实的形态（如 `Promise<void>`）。这会牵动所有 `defineExpose` 的
  `Exposes` 声明与 `Awaited<ReturnType<...>>` 推导，范围比这次还大。
- `DbForm` 侧同样的死判断 4 处：`MYSQL_DUMP_DATA/Index.vue:276`、`TENDBCLUSTER_DUMP_DATA/Index.vue:276`、
  `SQLSERVER_DATA_EXPORT/Index.vue:199`、`REDIS_SCALE_UPDOWN/components/target-capacity-column/cluster-deploy-plan/Index.vue:244`。
- 失败时的未捕获 rejection 全站存在（form 与表格都一样）。不建议逐处加 `.catch(() => {})`：reject 值是
  `false` / Error 混杂，静默 catch 会把真实异常（validator 抛错）一起吞掉。

## 待查证

- 148 处是按 `\.validate\(` 全量扫描 `src/views`、`src/components` 后按形态分类得到的；`formRef` 一侧只核对了上面列出的 4 处，其余未逐一确认。
- 第 5 节三处「暴露了 validate 但无人调用」是读代码得出的结论，未在页面上实测。
- 其他有 `validate` 语义的组件（`nodeStatusListRef`、`resourceTagSelector`、`noticeMethodRef` 等）用同步布尔还是 Promise，未核实。
