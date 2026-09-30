# 给 DbTable 传非数值 max-height 会让 tdesign 进入「固定表头」模式，表头克隆层飘在表体中间

- **命中**：给 `DbTable`（内部透传给 tdesign `PrimaryTable`）传 `max-height` / `:max-height`，而值不是具体数字，典型是
  `'auto'` 这种「表示不限制高度」的字符串。候选点用
  `rg -n "maxHeight\s*[:=]\s*['\"]" src -g '*.vue'` 找出来，再确认它是不是表格的 max-height（消息列表、筛选面板的
  `maxHeight: '220px'` 这类内联样式不算）。
- **为什么**：tdesign 只要收到 `maxHeight`——哪怕值是 `'auto'`——就进入「固定表头 + 表体滚动」模式，额外渲染一层表头克隆
  （`.t-table__affixed-header-elm`）。高度是 `auto` 时这层克隆没有落点，会飘在表体中间压住数据行，整张表看起来排版错乱，
  且很难从现象反推回 maxHeight。
- **改成**：不限制高度就干脆不给值。`src/components/db-table/IndexNew.vue` 里 `tableMaxHeight` 已收窄为 `ref<number>()`，
  走 `fixed-pagination`（整页滚动、表格不内滚）时不赋值即可，`undefined` 会被 tdesign 当成「没设高度」。
- **不要**：不要用 `'auto'` / `'unset'` / `'100%'` 表达「不限制高度」，tdesign 不认这种语义，见上。
- **存量**：`rg -n "maxHeight\s*[:=]\s*['\"]" src -g '*.vue'` 只有 3 处内联样式
  （`src/views/db-manage/common/sql-execute/mysql-execute-objects/components/components/render-sql/components/editor/MessageList.vue`、
  `src/views/ticket-center/common/ticket-detail/components/common/MessageList.vue`、
  `src/views/monitor-alarm/my-alarm-subscription/Index.vue`），没有表格 max-height 的字符串传值。
- **核实**：2026-10-12
