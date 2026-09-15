# 选择器右侧「结果预览」视觉是一套，改一处要看其余几处

- **命中**：改带 `t('结果预览')` 的右侧预览栏（标题条、`result-item` / `preview-item` 操作区、配套
  `CollapseMini`）。定位：`rg -ln "t\('结果预览'\)" src`
- **为什么**：几份选择器预览是同源拷贝。只改打开的那一份，用户在另一个选择器里会看到缺图标、缺行内复制、hover
  背景或折叠头间距对不上
- **改成**：改预览视觉时，对照下面「已对齐」清单其余几份同一项，缺的报告给用户，等用户决定是否同步。**抽公共预览组件的方案未定**
- **不要**把预览抽成单一公共组件：复制字段不同（`ip` / `instance_address` / `master_domain` /
  `shard_name`），分组也不同（按 tab / 按业务 / 平铺），`cluster-selector` 的标题条还写在
  `Index.vue` 而不是预览子组件里。强行合并会把数据形状和布局缠在一起
- **存量**：`rg -ln "t\('结果预览'\)" src` 当前 8 处。已对齐 5 组（标题 `legend` 图标、行内复制+删除、行 hover
  `#e1ecff`、`CollapseMini` 间距 8px / 头高 32px / 头 hover `#e1ecff`）：
  - `src/components/cluster-selector/Index.vue` + `src/components/cluster-selector/components/result-preview/`
  - `src/components/instance-selector-new/components/preview-result/`
  - `src/components/host-selector/components/preview-result/`
  - `src/components/machine-resource-selector/components/PreviewResult.vue` + 同目录 `CollapseMini.vue`
  - `src/components/cluster-resource-selector/components/PreviewResult.vue` + 同目录 `CollapseMini.vue`

  尚未对齐、命中只报告的 3 处：
  - `src/components/shard-selector/Index.vue`
  - `src/views/db-manage/mongodb/common/mongo-host-selector/components/preview-result/Index.vue`
  - `src/views/db-manage/redis/REDIS_CLUSTER_CUTOFF/components/resource-selector/components/PreviewResult.vue`
    + 同目录 `CollapseMini.vue`
- **核实**：2026-09-16

## 补充

已对齐组对照时看这几项，不要发明第三套：

- 标题前 `<DbIcon class="mr-4" type="legend" />`
- 每行删除前有复制；hover 行才显示；复制图标 `font-size: @font-size-mini`；两图标包在
  `display: flex; gap: 6px` 的操作区里，避免 `justify-content: space-between` 把复制顶到中间
- 行 hover 背景 `#e1ecff`

`src/views/db-manage/common/cluster-batch-edit-subscription/components/domain-list/components/CollapseMini.vue`
根节点也有 `collapse-mini-header`，但不是选择器预览，不纳入这组。
