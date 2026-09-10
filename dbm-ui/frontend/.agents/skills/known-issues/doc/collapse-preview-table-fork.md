# 折叠预览表有 5 份独立实现，计数口径已经不一致

- **命中**：新写「折叠头部（箭头 + 计数 + 右侧批量操作）+ 本地分页表格」这个组合；或改到下方存量 5 处之一的计数、分页、留白
- **为什么**：头部计数三处写法三个结果——用户看到的数字和表里的行数对不上
- **改成**：计数标签是「已筛选」时必须取筛选后条数，样板是
  `src/views/db-manage/common/big-data-host-table/RenderHostTable.vue`（`v-if/v-else` 切词 +
  `serachList.length`），三处里只有它是对的。本地分页用 `@hooks` 的 `useLocalPagination`——它是泛型
  `<T>` 且过滤条件由调用方传 predicate，任何维度都能用。**抽公共头部组件的方案未定**
- **不要**把 `CollapseTable.vue` 提回 `src/components/` 当公共组件：此前删掉的 `db-collapse-table`
  正是因为把 title 插槽、operations 下拉、tableProps 透传、分页四件事捆在一个 props
  面上，调用方要么被迫接受全套、要么传空对象绕过。要抽也应该只抽头部，表格与分页留给调用方
- **存量**：5 处，分两组。带本地搜索、计数会出错的 3 处：
  - `src/views/db-manage/common/big-data-host-table/RenderHostTable.vue` —— 正确，抄它
  - `src/views/db-manage/common/big-data-host-table/HdfsHostTable.vue` —— 漏了 `v-else`，「已筛选」和「共」会同时渲染
  - `src/views/db-manage/common/big-data-host-table/es-host-table/index.vue` —— `v-else` 有，但数字取的是
    `props.data.length`，是筛选前的条数

  无本地搜索、只显示 `共n个` 全量条数的 2 处（不涉及计数口径，但头部与分页仍是各写一份）：
  - `src/components/ip-selector/components/CollapseTable.vue`
  - `src/views/db-manage/common/cluster-authorize/components/TargetInstances.vue`
- **核实**：2026-09-10

## 补充

分页 hook 也是两份：`src/hooks/useLocalPagination.ts` 是泛型版（`<T>` + `callback: (rule, data) => boolean`），
`src/views/db-manage/common/big-data-host-table/hook/useLocalPagination.ts` 是把入参写死成 `HostInfo[]`、把过滤条件写死成
`searchRule.test(item.ip)` 的拷贝。两者其余逻辑逐行相同，泛型版是严格超集。上面 3 个 big-data
表 import 的都是局部那份，全局那份反而没人在这条链路上用；`TargetInstances.vue` 则两个都没用，自己手写
`slice`。所以「换成 `@hooks` 那份」是纯收敛，不需要新写代码。

底色、字号、字色三处取值其实相同，但一边走设计令牌、一边写字面量，改令牌只会改到一半：`CollapseTable.vue` 用
`@font-size-mini` / `@bg-dark-gray` / `@default-color`，`RenderHostTable.vue` 写的是 `12px` / `#f0f1f5` /
`#63656e`（对应 `src/styles/variables.less` 里的同名变量，值完全一致）。

头部留白也差 2~6px：`CollapseTable.vue` 与 `TargetInstances.vue` 是 `padding: 0 16px`，三个 big-data 表是
`padding-right: 12px; padding-left: 18px`。「...」按钮 hover 一处变灰（`@bg-disable`）一处变蓝（`#e1ecff`）。
