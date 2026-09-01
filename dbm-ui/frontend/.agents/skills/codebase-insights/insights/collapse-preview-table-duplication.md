# 折叠预览表各写一份：头部留白、计数语义、分页配置已经三套

状态：未处理

## 现象

「折叠头部（下箭头 + 计数 + 右侧「...」下拉批量操作）+ 本地分页表格」这个组合在项目里至少有 5 处独立实现，没有任何一处复用另一处。
它们视觉上想做成同一个东西（同样的 42px 高、同样的 `#f0f1f5` 底、同样的 `#3a84ff` 数字），但每一处的留白、hover 效果、
计数口径、分页配置都在各自演化。

后果有两类。视觉上，同一套 IP 预览表在申请单页（big-data-host-table）和授权弹窗（ip-selector）里左右留白差 2~6px、
「...」按钮 hover 一处变灰一处变蓝。功能上，头部计数在搜索场景下三处口径不一致：
`RenderHostTable` 显示筛选后条数，`es-host-table` 显示筛选前的总条数（标签却写着「已筛选」），
`HdfsHostTable` 因为漏了 `v-else` 会同时渲染出「已筛选」和「共」两个词。

## 证据

同一语义的 5 处独立实现：

| 位置 | 头部留白 | 「...」hover | 计数文案与取值 | 分页 | maxHeight |
| --- | --- | --- | --- | --- | --- |
| `src/components/ip-selector/components/CollapseTable.vue:136-144` | `padding: 0 16px` | `background-color: @bg-disable`（#dcdee5）+ `border-radius: 2px` | `共 n 个`，取 `data.length` | 组件内 `reactive`，`limitList: [10,20,50,100]`、`align: 'right'` | 474 |
| `src/views/db-manage/common/cluster-authorize/components/TargetInstances.vue:391-399` | `padding: 0 16px` | 同上（`:429`） | `共 n 个`，取 `state.tableData.length` | 组件内 `reactive`，同上取值 | 无 |
| `src/views/db-manage/common/big-data-host-table/RenderHostTable.vue:302-311` | `padding-right: 12px; padding-left: 18px` | `color: #3a84ff; background: #e1ecff`（`:323-337`） | `已筛选/共 n 台`，取 `serachList.length`（筛选后，`:32-33`） | `useLocalPagination`，无 `limitList` | 无 |
| `src/views/db-manage/common/big-data-host-table/HdfsHostTable.vue:376-385` | 同上 | 同上（`:397`） | `已筛选 共 n 台`——`{{ t('共') }}` 少了 `v-else`（`:32-34`），取 `serachList.length` | 同上 | 无 |
| `src/views/db-manage/common/big-data-host-table/es-host-table/index.vue:419-428` | 同上 | 同上（`:440`） | `已筛选/共 n 台`，取 `props.data.length`（筛选前，`:35-36`） | 同上 | 无 |

底色、字号、字色三处取值其实相同，但一边走设计令牌、一边写字面量，改令牌只会改到一半：

- `CollapseTable.vue:141-143`：`font-size: @font-size-mini`、`background-color: @bg-dark-gray`；`:134` `color: @default-color`
- `RenderHostTable.vue:307-310`：`font-size: 12px`、`color: #63656e`、`background: #f0f1f5`
- `src/styles/variables.less:19,27,51`：`@default-color: #63656e`、`@font-size-mini: 12px`、`@bg-dark-gray: #f0f1f5`

分页那一份 hook 三个 big-data 表在用，另两处没用：

- `src/views/db-manage/common/big-data-host-table/hook/useLocalPagination.ts:22-84`，被
  `RenderHostTable.vue:210`、`HdfsHostTable.vue:300`、`es-host-table/index.vue:285` 复用
- `CollapseTable.vue:97-115` 与 `TargetInstances.vue:260-266`、`:284-310` 各自手写了同样的
  `slice` + `watchEffect` 重置 current

`.table-footer` 这个包裹层被抄了四份，只有三份有对应样式：`RenderHostTable.vue:346-350`、
`HdfsHostTable.vue:427-431`、`es-host-table/index.vue:463-467` 都定义了
`display: flex; justify-content: flex-end; margin-top: 12px`，
而删除前的 `src/components/db-collapse-table/DBCollapseTable.vue` 也写了 `<div class="table-footer">` 却全项目搜不到对应样式，
是抄漏的空壳（本次删除组件时已一并去掉）。

## 项目里已有的正确做法

`useLocalPagination.ts` 是这套模式里唯一被抽出来的部分，接口设计是对的（吃一个 `Ref<HostInfo[]>`，吐出
`data`/`pagination`/`searchKey`/`serachList` 与两个 handler，并在 `searchKey` 变化时把 `current` 重置为 1）。
它的问题是入参类型写死成 `HostInfo[]`，所以只有 big-data 那三个主机表能用，集群维度的
`TargetInstances`、白名单维度的 `PreviewWhitelist` 用不了，只能各自手写。

头部那部分暂无正确做法，5 处都是从别处复制来的。

## 建议方向（未采纳）

- 最小收敛是先统一计数口径与 `HdfsHostTable` 漏掉的 `v-else`，这三处是用户能直接看到的错，跟要不要抽组件无关。
- 把 `useLocalPagination` 的入参泛型化（`<T>(originalData: Ref<T[]>, matcher: (item: T, key: string) => boolean)`）
  比抽头部组件容易得多，能立刻覆盖到 5 处中的 5 处。
- 不推荐直接把 `CollapseTable.vue` 提回 `src/components/` 当公共组件：本次删除 `db-collapse-table`
  正是因为它把 title 插槽、operations 下拉、tableProps 透传、分页四件事捆在一个 props 面上，
  调用方要么被迫接受全套、要么只能传空对象绕过（删除前 `IpSelector` 的 `tableProps` prop 就是这样：
  对外暴露却零调用方）。要抽也应该只抽头部，把表格与分页留给调用方。

## 待查证

- 只逐个读了上表 5 处。`rg -l "collapse-header|db-icon-down-shape"` 另外还命中 12 个文件
  （`ApplyCollapse.vue`、`FlowCollapse.vue`、`db-card/index.vue`、`toolbox-new/menu/Index.vue` 等），
  这些看名字是别的折叠场景（申请单折叠块、流程折叠块、卡片），没有确认它们是否也复制了同一套头部样式。
- 「视觉上左右留白差 2~6px」是读样式值推出来的（`0 16px` vs `12px/18px`），没有实际截图比对。
- `es-host-table` 的计数取 `props.data.length` 是否是刻意为之（比如它的搜索框由 `searchable` 控制、
  某些调用方不开搜索）没有查调用方确认。
