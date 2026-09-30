# 内容区里的 sticky 元素要抵消 .db-navigation-content-wrapper 的上内边距，否则会留出一条缝

- **命中**：在页面 / 组件样式里写 `position: sticky; top: 0`，而该元素位于 `.db-navigation-content-wrapper` 内（即页面内容区）。
  搜法：`rg -n "position: sticky" src -g '*.vue' -g '*.less'`，再确认命中的元素是不是内容区的后代。
- **为什么**：滚动容器按 **padding box** 裁剪内容，而 sticky 的 `top` 相对 **content box**。内容区有 `padding-top: 20px`
  （`src/layout/Index.vue` 的 `.db-navigation-content-wrapper`），`top: 0` 会让粘性元素停在内容区顶边下方 20px，
  这 20px 正好露出从下面滚上来的内容——表格行会从粘性条上方穿出来。
- **改成**：`top: calc(-1 * var(--db-content-padding-top, 0px));`
  该变量由 `src/layout/Index.vue` 的 `.db-navigation-content-wrapper` 提供（`20px`），全屏态 `.is-fullscreen` 下为 `0px`，
  两种状态都正确。
- **不要**：
  - 不要写死 `top: -20px`：全屏态内容区 padding 为 0，会把粘性元素顶部裁掉；
  - 不要给内容区或卡片加 `overflow: hidden` 去挡：那会让最近的滚动容器变成它自己，sticky 直接失效。
- **存量**：`rg -n "position: sticky" src -g '*.vue' -g '*.less'` 的其它命中都在组件内部的滚动容器里
  （bkui tag-input / select、BatchEditSideslider、editable-table 固定列、cluster-authorize 的 `.bk-modal-content`、review-data-dialog），
  这些容器没有上内边距，不受影响。内容区里的命中只有 create-module、clone-module 六个模块页的 Tab 头，已用上面的 `calc`。
- **核实**：2026-10-12
