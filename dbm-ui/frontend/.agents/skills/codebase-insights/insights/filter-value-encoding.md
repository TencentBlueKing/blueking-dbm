# 筛选值在搜索栏与表头筛选之间的编解码分散

状态：已修复（仅 `version-files/v2`，其它模块未查）

## 现象

同一个筛选字段在「搜索栏（DbQuickSearch）」和「表头列筛选（TableColumn filter）」两个入口有不同的值表示，
两者之间的转换没有集中在一处，而是散在双向同步的两个回调、消费端的兜底分支、以及选项声明里。

`version-files/v2` 的版本列表里，`enable` 一个字段存在三种表示：布尔 `true`、字符串 `'true'`、逗号串 `'true,false'`。
实际后果是从搜索栏筛「是否启用」后，表头启停列的筛选面板拿到的是布尔数组，
而 `MultipleSelect` 的 `value` 只接受逗号串（`src/components/db-table/components/MultipleSelect.vue:95`
是 `props.value.split(',')`），数组上没有 `split`，面板会直接抛错；反过来表头勾选后重新打开面板也不会是勾选态，
因为 `CheckboxGroup` 的 `localValue` 是 `split` 出来的字符串数组，而选项 `value` 是布尔，两者匹配不上。

## 证据（修复前）

`enable` 一个字段的编解码分布在三个文件：

| 位置 | 做的事 | 值形态 |
| ------------------------------------- | ---------------------------------------------------- | -------------------- |
| `useVersionFilter.ts` 搜索栏选项 | `String(item.value)` 包一层 | `'true'` / `'false'` |
| `useVersionFilter.ts` 表头选项 | 直接透传 `enableOptions` | 布尔 `true` / `false` |
| `sub-version-list/Index.vue` 搜索栏 → 表格 | `split(',').map(item => item === 'true')` | 逗号串 → 布尔数组 |
| `sub-version-list/Index.vue` 表格 → 搜索栏 | `itemValue.map(String).join(',')` | 布尔数组 → 逗号串 |
| `table-list/Index.vue` 消费端兜底 | `enable === '' → []` | 空串 → 空数组（回传面板同样会崩） |

同一个 `enableOptions` 在同一个 hook 内被两个出口以不同值类型导出。当时的注释写的是
「表格列筛选的启停项是布尔数组」，与 `MultipleSelect.vue:137-139` 的 `emits('change', value.join(','))` 矛盾——
表头从来不产出布尔数组。

这些不一致长期没暴露，是因为消费端的 `checkFilterValue` 对筛选值和行属性双向 `toString()` 后比较，
布尔和 `'true'` 都能匹配上；只有需要把值**回传**给筛选面板时才会暴露。

## 修复方式

全链路统一为逗号分隔字符串：`enableOptions` 的 value 改成 `'true'` / `'false'`；
搜索栏与表头之间直接互传不再转换（`handleSearchChange` / `handleFilterValueChange` 各剩一行）；
`table-list` 在 `handleFilterChange` 入口用 `_.mapValues` 把数组归一成逗号串，
`tableFilterValue` 的类型收紧为 `Record<string, string>`，`checkFilterValue` 的数组分支随之删除。

## 项目里已有的正确做法

`useVersionFilter.ts` 的文件注释说明了它的定位：「搜索栏与表头筛选共用同一批字段，字段名同时是搜索栏的 id、
表格列的 col-key 以及前端过滤时读取的行属性，三者必须完全一致，所以集中在这里声明，不要在两边各写一份」。

它原本只统一了字段名与选项声明，值的编解码漏在外面。修复后编解码也归到了「选项 value 即最终传输形态」这一条约定上，
但这条约定目前只写在 `enableOptions` 上方的一行注释里，没有类型层面的约束。

## 待查证

- 只核实了 `enable`。`phase`、`updater` 同为 multiple 类型但值本身就是字符串，是否也有隐性转换没有逐行比对。
- 只覆盖 `version-files/v2`。`db-table` + `db-quick-search` 这套组合在 `db-manage`、`resource-manage`
  等模块也大量使用，那些地方是否有同样的多处编解码结构未确认——`MultipleSelect` 的 `value: string`
  是全局约束，任何给它传数组的调用方都会踩同一个坑。
- 未确认 tdesign 对 `type: 'multiple'` 的列点「重置」时回传空串还是空数组。当前实现用 `mapValues` 两种都归一了，
  但没有实际触发验证过。
