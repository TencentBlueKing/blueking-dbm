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
- **存量**：`src/views/db-manage` 下已清零（命中命令的输出里剩下的行，要么是注释掉的旧代码，要么是下面这类真布尔转发点）
- **不是命中**：`CreateValidateSelect.vue` 自己 `try / catch` 后 `return true / false`，暴露的是货真价实的
  `Promise<boolean>`。调它的 `KeyValuePair.vue` 用 `Promise.all([...]).every((item) => item)` 判断是**对的**，不要改。
  判定方法：顺着 ref 找到组件的 `defineExpose`，确认 `validate` 是直接转发 `DbForm` / `EditableTable`，还是包了一层
  `catch`
- **核实**：2026-09-21

## 补充

转发点的变量名各不相同（`tableRef` / `editableTableRef` / `renameListRef` / `currentTableRef`），按变量名搜必然漏，要按
`\.validate\(` 全量扫再按形态分类。

把返回类型从 `Promise<boolean>` 改成 `Promise<void>` 是更诚实的形态，但会牵动所有 `defineExpose` 的 `Exposes`
声明与 `Awaited<ReturnType<...>>` 推导，范围很大，未做。
