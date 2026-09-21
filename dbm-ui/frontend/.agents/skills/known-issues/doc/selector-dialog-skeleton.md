# 六个选择器弹窗共用一套骨架，基线是 host-selector

- **命中**：改下面六个目录里的 `Index.vue`、`PanelTab.vue`、表格组件（`Table.vue` / `RenderTable.vue` /
  `ClusterTable.vue`）或它们的 `<style>`，或新写一个「左表格 + 右结果预览」的选择器弹窗。定位：
  `rg -ln "BkResizeLayout" src/components`
  - `src/components/host-selector/`（基线）
  - `src/components/instance-selector-new/`（基线）
  - `src/components/cluster-selector/`
  - `src/components/cluster-resource-selector/`
  - `src/components/machine-resource-selector/`
  - `src/components/shard-selector/`
- **为什么**：六个组件在页面上是同一个交互物（弹窗 → 顶部类型 Tab → 搜索 + 可勾选表格 → 右侧结果预览 →
  确定/取消），用户按同一套肌肉记忆操作。2026-09-16 已按基线对齐过一轮，之前的偏差已经跑到过交互层
  （resource-selector 点行不选中、确定按钮禁用无提示、`cluster-resource-selector` 与 `shard-selector`
  点取消不回滚），再各改各的会重新裂开
- **改成**：改到下面「已对齐」里的任何一项，就按那一项的取值写，不要再发明第三套。**新写同形选择器直接照抄
  `host-selector/` 的骨架**。「仍有差异」那几项命中只报告
- **不要**：
  - 不要统一 Tab 互斥语义。`cluster-selector` 的 `onlyOneType`（切 tab 清空已选）、host / instance 的
    `uniquePanelSettings`（有选中就禁用其它 tab）、两个 resource-selector 的无限制，是三种业务需求，
    不是拷贝偏差
  - 不要为了对齐去合并成一个公共组件：取值形状不同（按 tab 分组的 `Record<string, T[]>` vs 平铺数组）、
    `cluster-selector` 的 13 个 tab 还带 `customColums`、`disabledRowConfig`、`submitTips` 插槽。
    合并只会把这些差异变成一堆开关
  - 不要顺手摘掉 `cluster-selector` / 两个 resource-selector 的 `parse-url`。它决定弹窗打开时是否用 URL
    query 回填搜索条件，可能被直达链接依赖（见 `dbm-frontend-developer` 的 `references/direct-link.md`）
  - Tab 条不要求抽成 `PanelTab.vue`。`cluster-selector` 的 tab 内联在 `Index.vue` 且包了 BkPopover
    说明气泡，样式一致即可（BkPopover 默认不加包裹元素，`flex: 1` 仍落在 `.tabs-item` 上）
- **存量**：固定六份，见上方命中清单。同形但不在这组的另外两处（mongo-host-selector、
  REDIS_CLUSTER_CUTOFF 的 resource-selector）见 [selector-preview-style.md](selector-preview-style.md)
- **核实**：2026-09-16

## 补充

右侧结果预览的内部视觉（行内复制、hover 背景、`CollapseMini` 间距）是另一条，记在
[selector-preview-style.md](selector-preview-style.md)，本篇不重复。

### 已对齐，六份一致（改到哪项就照这个写）

弹窗外壳：

- `<BkDialog>` 上 `width="80%"`，`:close-icon="false"` `:draggable="false"` `:esc-close="false"`
  `:quick-close="false"`
- 根样式 `display: block; width: 80%; max-width: 1600px; min-width: 1200px;`，并置空
  `.bk-modal-header { display: none }`、`.bk-dialog-content { padding: 0; margin: 0 }`
- 根节点不设 `font-size`，12px 只由结果预览自己声明
- `<BkResizeLayout>` 右侧预览：`:border="false"` `collapsible` `initial-divide="320px"` `:max="360"`
  `:min="320"` `placement="right"`

Tab 条（容器只负责 `display: flex`，背景和边框都挂在 item 上）：

```less
.xxx-panel-tab {
  display: flex;

  .tab-item {
    display: flex;
    height: 40px;
    cursor: pointer;
    background-color: #fafbfd;
    border-bottom: 1px solid #dcdee5;
    justify-content: center;
    align-items: center;
    flex: 1;

    &.active {
      background-color: #fff;
      border-bottom-color: transparent;
    }

    & ~ .tab-item {
      border-left: 1px solid #dcdee5;
    }
  }
}
```

`shard-selector` 只有一个固定 tab、不可切换，所以直接取 `.active` 那组取值（白底 + `border-bottom: 1px
solid transparent`），并去掉 `cursor: pointer`——点不动的东西不给手型。

搜索 + 表格：

- 容器 `height: 570px; padding: 0 24px;`
- `<DbQuickSearch>` 上 `class="mt-16 mb-16"`
- `<DbTable>` 上 `:container-height="containerHeight"`，脚本里
  `const containerHeight = 570 - 32 - 16; // 去除搜索框的高度和margin bottom`。
  不要改用 `fixed-pagination` + `:height`，那套不跟着容器算高度
- `<DbTable>` 上 `row-click-selectable`，点行即勾选

取值与提交：

- 入参只读，不在弹窗内写回；勾选走内部副本 `localSelected`，`watch isShow` 打开时重置
- 点「确定」`emit('change', localSelected.value)` 后关闭，点「取消」直接关闭丢弃副本
- **不要在 `watch isShow` 里重新 `fetchData`**。`DbTable` 非首次取数会 `handleClearWholeSelect()` 并回吐一个空
  selection，把刚种下的 `localSelected` 冲掉，回填直接消失（`shard-selector` 2026-09-16 踩过，它的
  `openSelection` + `handleRequestSuccess` 是没接上的修复尝试，已删）。列表数据由 `DbQuickSearch` 挂载时的
  回显 emit 拉一次就够（wrapper 上的 `watch(modelValue, { immediate: true })` 会 emit 一次 change）
- 调用方的 `disableSelectMethod` 要依赖「弹窗内当前选中」时（跨集群禁选这类），把选中态作为第二个参数传给它：
  `disableSelectMethod?: (data: IRowData, selected: IRowData[]) => boolean | string`，组件内用
  `const handleDisableSelect = (data) => props.disableSelectMethod?.(data, localSelected.value) ?? false` 包一层
  再给 `DbTable`。**不要让调用方去读绑给弹窗的 `v-model`**——入参只读之后那里拿到的是上次提交的值，禁选会静默失效
- 确定按钮外层包一层 `span` 挂 `v-bk-tooltips`，禁用时给出原因：

```html
<span
  v-bk-tooltips="{
    disabled: !isEmpty,
    content: t('请选择主机'),
  }">
  <BkButton
    class="w-88"
    :disabled="isEmpty"
    theme="primary"
    @click="handleSubmit">
    {{ t('确定') }}
  </BkButton>
</span>
<BkButton
  class="ml-8 w-88"
  @click="handleClose">
  {{ t('取消') }}
</BkButton>
```

### 仍有差异，命中只报告

| 项 | 现状 | 没对齐的原因 |
| --- | --- | --- |
| 预览栏实现位置 | `cluster-selector` 与 `shard-selector` 整块写在各自 `Index.vue` 里（类名 `result-title` / `result-content`），另外四份在预览子组件内（类名 `header` / `result-wrapper`）。尺寸取值已对齐，见 [selector-preview-style.md](selector-preview-style.md) | 搬家要连带迁移「清空所有 / 复制所有」下拉的逻辑，纯结构改动 |
| 入参写法 | `cluster-selector` 是 `selected` prop，另外五份是 `v-model` / `v-model:selected` | `cluster-selector` 有 61 个调用方 |
| 取消事件 | host / instance / `shard-selector` 额外 `emit('cancel')`，另外三份没有 | 调用方没有这个需求 |
| 选中结果形状 | `cluster-selector` / host / instance 是 `Record<tabId, T[]>`，两个 resource-selector 与 `shard-selector` 是平铺数组 | 业务差异，前者要按 tab 分组回填 |
| 单选 | `cluster-selector` 用 `:select-single="!multiple"`，host / instance 用 `:select-single="single"`，两个 resource-selector 与 `shard-selector` 不支持 | 没有单选场景，加了也没人用 |
| `parse-url` | `cluster-selector` 与两个 resource-selector 带，host / instance / `shard-selector` 不带 | 可能被直达链接依赖，见「不要」 |
| Tab 互斥语义 / 搜索项 | 三套 / 各配各的 | 业务差异，见「不要」 |
