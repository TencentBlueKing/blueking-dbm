# 筛选值全链路只能是逗号分隔字符串

- **命中**：`rg -n 'value: (true|false)' src` 命中筛选选项声明；或搜索栏与列筛选之间互传的值是数组。
  `MultipleSelect` 的 `value` prop 已经声明成 `value?: string`，直接写字面量数组会被 TS
  拦下，漏进来的都是经 bkui table `column.filter` 配置对象这类未收窄的通道传进去的
- **为什么**：`MultipleSelect`（`src/components/db-table/components/MultipleSelect.vue`）内部直接
  `props.value.split(',')`，传数组会抛错；选项 `value` 是布尔时，面板内部 `split`
  出来的是字符串数组，与选项值匹配不上，勾选态回显不出来
- **改成**：选项 `value` 一律字符串；表格 `@change` 回来的值在入口处归一
  `Array.isArray(v) ? v.join(',') : v`。完整规范见 `.agents/rules/search-filter-sync.mdc` 的「值形态」一节
- **不要**在 `MultipleSelect` 内部加 `Array.isArray` 兜底：兜底之后调用方就没有统一形态的压力了，
  而回显不出来的那半个问题（布尔选项值）兜底也解决不了
- **存量**：`version-files/v2` 已修。`db-manage`、`resource-manage` 等模块用同一套 `db-table` +
  `db-quick-search` 组合，未排查
- **核实**：2026-09-10

## 补充

这类不一致长期不暴露，是因为前端过滤时对筛选值和行属性双向 `toString()`
后比较，布尔和 `'true'` 都能匹配上；只有需要把值**回传**给筛选面板时才会崩，所以很难从现象反查到源头。

修复 `version-files/v2` 时踩到的具体形态：`enable` 一个字段同时存在布尔 `true`、字符串 `'true'`、逗号串
`'true,false'` 三种表示，编解码散在搜索栏选项声明、表头选项声明、双向同步的两个回调、消费端兜底分支四处。
统一为逗号串后，两个同步回调各剩一行。
