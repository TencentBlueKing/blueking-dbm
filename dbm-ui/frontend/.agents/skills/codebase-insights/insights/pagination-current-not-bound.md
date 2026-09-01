# 分页状态各写一份：18 处没把 current 传给分页组件

状态：未处理

## 现象

`bk-pagination` 与本地 `DbPagination` 都只认 `modelValue`，不认 `current`。业务侧的分页状态对象里普遍叫
`current`，通过 `v-bind="pagination"` 整体透传时它会落到根 div 上变成一个无意义的 DOM 属性，组件自己维护的当前页不会被覆盖。

后果：凡是只写 `v-bind="pagination"`、没有额外写 `:model-value="pagination.current"`
的调用点，外部改 `pagination.current` 都只影响请求参数，不影响页码条显示。两种表现：

- 筛选条件变化时代码把 `pagination.current` 重置为 1，请求回到第一页，但页码条仍高亮在旧页；
- 从 URL 恢复页码时请求取的是 URL 里的页，页码条却显示第 1 页。

分页状态对象本身也是各写一份：35 个文件各自 `reactive({...})`，字段与取值已经漂移（有的带
`align` / `layout`，有的不带；`limitList` 有三套取值）。

## 证据

绑定情况（`rg "<(Bk|Db)Pagination"` 共 56 处 —— 部分调用点已换成本地 `DbPagination`，只统计 `<BkPagination`
会漏。其中 38 处写了 `:model-value`，18 处没写）：

| 位置                                                                       | 是否绑定 current                     | 外部是否改写 current                                             |
| -------------------------------------------------------------------------- | ------------------------------------ | ---------------------------------------------------------------- |
| `src/components/db-table/IndexNew.vue:58-62`                               | 否，只有 `v-bind="pagination"`       | 是，`IndexNew.vue:479` 筛选变化时 `pagination.current = 1`       |
| `src/views/ticket-center/common/ticket-table/Index.vue:274-278`             | 否，只有 `v-bind="pagination"`       | 是，`common/hooks/use-fetch-data.ts:31` 从 URL 写回 `current`     |
| `src/components/cluster-selector/components/tendbha/Index.vue:44-48`        | 是，`:model-value="pagination.current"` | 是，`useClusterData.ts` 内维护                                   |

分页状态对象的取值漂移（同一语义、独立定义）：

| 位置                                                                        | limitList                     | 其它字段                        |
| --------------------------------------------------------------------------- | ----------------------------- | ------------------------------- |
| `src/components/db-table/hooks/use-pagination.ts:14-21`                     | `[10,20,50,100,200,500]`      | `align: 'right'`、`layout`      |
| `src/views/ticket-center/common/hooks/use-fetch-data.ts:19-25`              | `[10,20,50,100,200,500]`      | `remote: true`，无 align/layout |
| `src/components/cluster-selector/components/tendbha/useClusterData.ts:34-41` | `[10,20,50,100,500]`          | `remote: true`、`small: true`   |
| `src/components/instance-selector/components/tendb-cluster/table/useTableData.ts:41-49` | `[10,20,50,100]`   | `align: 'right'`、`layout`、`remote: true` |

`rg -l -U "reactive\(\{[^}]*limitList" src` 命中 34 个文件，加上 `db-table/hooks/use-pagination.ts`（写法是
`reactive<Pagination>({`，不在上面的命中里）共 35 处独立定义。

## 项目里已有的正确做法

`src/components/db-table/hooks/use-pagination.ts` 是唯一被抽出来的分页状态 hook：它同时给出 `pagination`、`onChange`、
`onLimitChange`，`onChange` 里带 `pagination.current === pageValue` 的去重判断，`onLimitChange` 会把 `current`
重置为 1。这套抽象是对的，但只有 `db-table` 自己在用，且它自己的模板恰好也漏了 `:model-value`。

`cluster-selector` / `instance-selector` 两批调用点都写了 `:model-value="pagination.current"`，是绑定这一侧的正确样板。

## 建议方向（未采纳）

- 给 18 处补 `:model-value="pagination.current"` 是最小修复，能立刻消掉「重置后页码条不动」。
- 更彻底的做法是把分页状态字段名对齐组件契约（`current` → `modelValue`），让 `v-bind` 直接生效，但要连带改 35
  处定义和所有读 `pagination.current` 的地方，范围很大。
- 不推荐在分页组件里新增 `current` prop 当 `modelValue` 的别名：两个入口写同一份状态，谁优先无法自解释，之后每个调用点都要先判断自己走的是哪条路。

## 待查证

- 只逐个读过 `db-table/IndexNew.vue`、`ticket-center/common/ticket-table/Index.vue` 与
  `cluster-selector/components/tendbha/*`；另外 16 处未绑定 `:model-value` 的调用点只确认了「没写」，没有逐个确认它们是否真的会从外部改写 `current`（不改写的话就没有可见后果）。
- 56 / 38 / 18 三个数字来自 `rg` 对 `<BkPagination` 与 `<DbPagination` 两个标签的统计，抽查了上表 3 处；没有逐个核对全部 56 处。
- 本地 `DbPagination`（`src/components/bkui-vue/pagination/Index.vue`）与 `bk-pagination` 一样只认
  `modelValue`，替换调用点时会原样继承这个问题。
