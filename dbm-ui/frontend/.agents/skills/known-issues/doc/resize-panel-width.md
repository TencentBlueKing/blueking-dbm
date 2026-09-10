# 可拖拽改宽度不要用 `table-detail-dialog/hooks/use-resize.ts`

- **命中**：`rg -n 'use-resize' src` 命中 import；或又写一份 `mousedown` + `clientX` 的拖拽逻辑
- **为什么**：它看着像可复用 hook，实际通过 `getCurrentInstance()?.props` 读宿主组件的 `minWidth` /
  `defaultOffsetLeft`，还硬查 `.navigation-container` 算默认宽。这四处依赖都不在 `(rootRef, resizeHandleRef)`
  这个签名里，换个组件调用会静默拿到 `undefined`
- **改成**：照抄 `src/views/task-history/detail/components/task-flow/Index.vue` 里 `handleResizeStart`
  那段，依赖全显式。拖拽期防选中沿用项目既有写法 `onselectstart` + `ondragstart` 置 false，不用 `preventDefault`。
  **抽公共原语的方案未定**，出现第 4 处再说
- **不要**改 `table-detail-dialog` 那份去兼容第二个调用方：它的 `'90%'` 与 `900`
  是弹窗专属语义，泛化后会把弹窗策略带进面板。也**不要**引入拖拽库，三处都只是一维位移
- **存量**：3 处独立实现，其中两处文件名都叫 `hooks/use-resize.ts` 但语义完全不同——
  - `src/components/editable-table/hooks/use-resize.ts` 调表格列宽
  - `src/components/table-detail-dialog/hooks/use-resize.ts` 调浮层面板宽度
  - `src/views/task-history/detail/components/task-flow/Index.vue` 就地实现，面板展开宽度
- **核实**：2026-09-10

## 补充

三处的限宽策略各不相同：`editable-table` 是 `Math.max(delta, 80)` 后夹 `minWidth || 60` / `maxWidth ||
1000000`；`table-detail-dialog` 是 `Math.max(resizeWidth, 900)`，超父宽 90% 就切成 `'90%'`；`task-flow` 是
`_.clamp(..., 240, 500)`。节流也只有 `table-detail-dialog` 有（60ms）。

视觉层反倒是一致的：16×64 的折叠把手、8px 的 `col-resize` 条、拖拽期 `inset: 0` 的 mask 在
`table-detail-dialog/Index.vue` 与 `task-flow/Index.vue` 对齐。漂移只在 JS 行为层。

真要抽，边界应该是「mousedown 起一次拖拽、返回位移」这一层，参数全部显式传入（起始值、min、max、方向），不要把宽度写回
DOM、不要碰 `getCurrentInstance`。
