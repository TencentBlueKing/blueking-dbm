# 单据详情里的改单数据（内容版本、改单记录）走 props，不用 provide / inject

- **命中**：
  - 你正要在 `src/views/ticket-center/common/action-confirm/**` 或 `src/views/ticket-center/common/ticket-detail/**`
    里给待办操作提交 `version`、使用改单记录，或新增流程类型入口、流程状态组件、待办类型
  - `rg -n '\b(provide|inject)\(' src/views/ticket-center/common/ticket-detail` 出现下面「存量」以外的行
  - `rg -nU 'if \(props\.data\) \{[\s\S]*?if \(props\.todoData\)' src/views/ticket-center/common/action-confirm` 有输出
- **为什么**：注入是隐式依赖，组件渲染在没有 provide 的位置时静默拿到空值，版本按 `null` 提交、改单记录整块不显示，都不报错；
  改走必填 props 后，漏传由类型检查拦下
- **改成**：
  - 内容版本：action-confirm 组件 `data: TicketModel` 必填、`todoData` 可选，先判 `todoData` 走 `batchProcessTodo`，
    `version: props.data.version`，否则走 `batchProcessTicket`；详情页调用处写 `:data="ticketData"` 加 `:todo-data="data"`。
    todo-list 下直接提交的组件用 `props.ticketData.version`
  - 改单记录：只在 `ticket-detail/Index.vue` 请求一次，以 `modifyRecords` prop 逐层下传：`FlowInfos` → `RenderFlow` →
    流程类型入口（`FlowTypeBase.vue` 与 `flow-type-*/Index.vue`）→ 流程状态组件 → `ModifyRecordList` / `TodoList` →
    `TypeConfirmModify` → 确认修改待办 / `ChangeDiffDrawer`。新增流程类型入口要转发给分发出去的状态组件；
    包装通用状态组件（根节点是 `flow-type-common/Status*.vue`）的状态组件要声明并显式写 `:modify-records="modifyRecords"`
- **不要**：
  - 不要在 action-confirm 里先判 `props.data`：详情页同时传 `data` 和 `todoData`，会误走 `batchProcessTicket`，
    按 `ticket_ids` 提交而不是当前这条 `todo_id`
  - 不要靠属性透传省掉包装组件里的声明：包装组件自己设了 `inheritAttrs: false` 时（如
    `flow-type-inner-flow/StatusSucceeded.vue`），透传到里层通用状态组件就断了；不用也不转发的组件
    （如 `flow-type-common/StausPending.vue`）不声明，否则 `vue/no-unused-properties` 报错
  - 不要给 `RelatedTicketFlow.vue` 里的 `RenderFlow` 传 `modifyRecords`：关联单据流程不展示改单记录，靠默认空数组
  - 不要去掉 `flow-info/Index.vue` 里 `RenderFlow` 的 `:key="data.version ?? 0"`：todo-list 的 `ticketData` 只在挂载时请求一次，
    流程又按 `flow_type#status` 复用，重新编辑后审批步骤仍是 `ITSM#RUNNING`；没有这个 key，点「刷新页面」后审批仍按旧版本提交
- **存量**：第二条命令只应剩 info-table 自己的表格 → 列上下文两行
  `src/views/ticket-center/common/ticket-detail/components/common/info-table/Index.vue` 与
  `src/views/ticket-center/common/ticket-detail/components/common/info-table/InfoTableColumn.vue`，和改单无关；第三条命令为空
- **核实**：2026-10-13

## 补充

todo-list 下的 `ticketData` 是 `todo-list/Index.vue` 按 `flowData.ticket` 自己请求的，不是详情页传下来的那份。
约定视为与详情页一致：内容版本变化时靠 `RenderFlow` 的 version key 重建流程树来保证，不要以「两份数据请求时机不同」为由改回注入。关联单据流程里 `flowData.ticket` 就是关联单据，
版本天然对得上。

待办类型分发器里只有 `todo-list/type-confirm-modify/Index.vue` 需要改单记录，其余 `todo-list/type-*/Index.vue` 不转发。
