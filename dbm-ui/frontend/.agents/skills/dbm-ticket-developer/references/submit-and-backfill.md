# 提交与回填

同一份 `details`，提交时从页面组装出去，回填时反解回页面。**两边必须逐字段对称**，所以放一篇里对照着写。

## useCreateTicket

`src/hooks/useCreateTicket.tsx`，190 处调用，覆盖全部三类入口。

```ts
const { loading: isSubmitting, run: createTicketRun } = useCreateTicket<SubmitDetails>(TicketTypes.XXX, {
  isToolbox: true,          // 默认 true
  onSuccess(ticketId) {},
  onError(rowErrors) {},    // 按行回填错误
  successMessage: '...',    // 传 false 不弹成功提示
});

createTicketRun({ details: {...}, ...formData.payload });
```

### 泛型是提交体，不是详情类型

**禁止写 `useCreateTicket<Mysql.Xxx>`。** 详情类型继承 `DetailBase`，要求 `__ticket_detail__`、`clusters`、`specs`
这些只有后端返回才有的字段，提单不传会报红。泛型应当是内联的、只描述实际提交内容的类型：

```ts
const { run } = useCreateTicket<{
  infos: { cluster_id: number; source_db_list: string[] }[];
  on_duplicate: string;
}>(TicketTypes.MYSQL_YOUR_NEW_TYPE);
```

存量 1 处例外（`MYSQL_MIGRATE_SINGLE`），不是范例。排查命令见 [review.md](review.md)。

### `isToolbox` 决定失败提示去哪

失败时 hook 总是 `eventBus.emit('db-toolbox-error', message)`，由工具箱页的固定底栏上方内联展示错误条。

**非工具箱入口（弹窗、侧滑、申请页）必须传 `isToolbox: false`**，否则那条 eventBus 没人接，用户点了提交什么反馈
都没有；传了才会额外走 `messageError` 全局提示。存量有 7 处漏传（`common/machine-*` 五个、
`doris/common/upgrade-version`、`kafka` 的 `TopicRebalance.vue`），抄模板时别抄这几个。

### 建 hook 的两种方式

传 `ticketType` → `run` 的 `ticket_type` 可选，绝大多数页面用这种。传 `undefined` → **`run` 必须传
`ticket_type`**，一个 hook 要发多种单据时用，如 `useOperateClusterBasic` 的启用 / 禁用 / 删除三合一。

### hook 已做完的事，页面不要重复处理

- 成功：置 `window.changeConfirm = false`；弹 6s 不可手动关闭的成功提示，带「查看详情」外链
- **重复单据（code `8704005`）**：弹「是否继续提交单据」，确认后带 `ignore_duplication: true` 重发
- 失败：`errors` 是字符串数组就拼接展示；是行级错误数组且传了 `onError` 就交给 `onError`
- `bk_biz_id` 不传默认 `window.PROJECT_CONFIG.BIZ_ID`

### 返回值语义

`run` 返回 `Promise<number | undefined>`：成功拿到单据 id，失败或用户点「取消提单」拿到 `undefined`。
**提单成功后要做后续动作（跳转、关弹窗、刷列表）的，判 `if (!ticketId) return;`，不要 try/catch**——`run`
内部已吃掉异常，不会 reject。

## useBatchCreateTicket

`src/hooks/useBatchCreateTicket.tsx`，用在「一批数据横跨多个业务，要拆成多张单」的场景。
`run({ bizIdExtractor, data, detailsExtractor, ticketPayload })` 按 `bizIdExtractor` 分组，同组内合并各行
`detailsExtractor` 的结果（**数组字段拼接，非数组字段取首次出现的值**），每组发一张单。两个约束：

- **依赖 `route.meta.ticketType`**，成功后按 DB 前缀跳 `DbaManage{Db}ToolboxResult`。只有 mysql / tendbcluster /
  redis / sqlserver / mongodb 有这个路由，**oracle 和非工具箱页面用不了**
- 没有 `onSuccess` / `successMessage` / `isToolbox` 选项，失败一律 `messageError`

## useApplyBase

`src/hooks/useApplyBase.ts`，只有服务申请页用。内部已封好 `useCreateTicket(undefined, { isToolbox: false,
successMessage: false })`，申请页直接调 `handleCreateTicket(formdata)`，**不要自己再建一个 `useCreateTicket`**。
它额外处理 `db_app_abbr` 缺失时的创建确认、成功后新窗口打开单据列表，并剔除 `sub_zone_ids` /
`sub_zone_names` / `city_name` 三个纯前端字段。

## 提交体字段映射

- 前端驼峰转下划线；`cluster.id` → `cluster_id`；`ip` + `port` → `instance_address`
- 资源池场景 `ip_source` 固定 `'resource_pool'`
- **页级单选的 radio 直接绑后端枚举值**，不要自造前端枚举再写双向映射——详情组件本来就直读后端字段
- **资源标签是双字段**：`labels` 传 id 字符串列表（`String(label.id)`），`label_names` 传标签名（`label.value`），按序对应
- 后端仍是 `{ db, table }[]` 协议的单据在边界做转换，不要改公共列组件的类型

## useTicketDetail

`src/hooks/useTicketDetail.ts`，182 处调用。克隆单、失败重提、「再次提单」全靠它反解 `details`。

签名是 `useTicketDetail<Mysql.Xxx>(TicketTypes.XXX, { onSuccess(ticketDetail) {} })`。四条行为要点，知道了才不会
写多余的兜底：

- **只在 `route.query.ticketId` 存在时发请求**，正常进页面零额外请求，可以无条件挂
- `ticket_type` 与传入枚举不一致时**静默 return**，同一路由挂多个不同类型是安全的
- 请求带 **1 秒缓存**。多模式页面里页面本体与各模式子组件**各自调一次**是推荐写法，**不要用 props 把
  `ticketDetails` 往下传**
- 成功后置 `window.changeConfirm = true`

链路：详情页「再次提单」→ `TicketClone.vue` 查路由映射 → 新窗口带 `?ticketId=` 打开 → 目标页反解。
映射的登记规则见 [registry.md](registry.md)。

### 回填完整度是最高频的缺陷

**提单页有的每一列 / 每一个表单项，回填都要有对应赋值。** 漏一项不报错、不白屏，只有用户点「再次提单」时才发现
「缺数据」。写完必须**手工逐项对照**提交体和 `onSuccess`，没有能替代这一步的命令。

两个高频漏点：

- **资源标签**：`labels` 回来是 id 列表，要配合 `label_names` 组装成 `{ id, value }[]`，`ResourceTagColumn`
  才能命中它的 `tagMap`

  ```ts
  labels: (item.resource_spec?.master?.labels || []).map((labelId, index) => ({
    id: Number(labelId),
    value: item.resource_spec?.master?.label_names?.[index] || '',
  })) as IDataRow['labels'],
  ```

- **规格 `spec_id`**：从 `item.resource_spec?.master?.spec_id` 取，展示名另从顶层 `details.specs` 取

### `clusters` / `specs` 必须可选链

```ts
cluster: { id: item.cluster_id, master_domain: details.clusters?.[item.cluster_id]?.immute_domain || '' },
```

后端未 `patch_cluster_details` 的单据不注入 `clusters`，直接索引会 `TypeError` 白屏。

工具箱提单页整体替换 `tableData` 后要刷 `tableKey`，以及域名解析时机、联动清空防误清这些 `EditableTable` 特有的
坑，见 `dbm-toolbox-developer` 的 `references/editable-table.md`。
