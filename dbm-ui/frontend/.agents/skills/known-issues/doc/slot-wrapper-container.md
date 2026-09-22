# 有样式的容器不能由 `$slots.x` 决定渲染，插槽要裸渲染

- **命中**：`rg -n 'v-if="\$slots\.' src/components/bkui-vue -A 2`，其中 `v-if` 所在标签带 class（容器有背景 /
  边框 / 内边距）。自研 bkui-vue 替代组件新增插槽出口时同样命中
- **为什么**：`$slots.x` 只判断「插槽有没有传」，不判断它渲染出什么。调用方写
  `suffix: () => cond && <span />` 这种短路插槽时，`cond` 为假返回 `''`，插槽函数依然存在，容器照样渲染成一个可见的
  空盒子。`db-input` 的 `.dbm-input-suffix-area` 带左边框 + 左右 8px 内边距 + 灰底，空盒子在输入框右侧很显眼
- **改成**：照 `node_modules/bkui-vue/lib/<comp>/index.js` 的渲染结构对齐——bk-input 是
  `slots.suffix?.() ?? (props.suffix && <div class="bk-input--suffix-area">…)`，即**插槽内容裸渲染，带样式的容器只服务于同名
  prop**。模板写法：

  ```html
    10|  <slot name="suffix">
    <div
      v-if="suffix"
      class="dbm-input-suffix-area">
      {{ suffix }}
    </div>
  </slot>
  ```

  插槽有内容就用插槽、没传才回落到 prop 的盒子，语义与 bk-input 一致，也不用去判断插槽渲染结果是否为空
- **不要**在组件里遍历插槽返回的 VNode 判空（过滤 Comment / 空 Text / Fragment）：能解决空盒子，但保留了 bk-input
    20|  没有的那层盒子，`%`、图标按钮这类插槽内容仍然被灰块包着，调用方还得写 CSS 反向抵消
- **不要**只在调用方按条件不传 slot key：4 个域名表各改一遍，下一个用插槽的人照样踩
- **存量**：`rg -n 'v-if="\$slots\.' src/components/bkui-vue -A 2` 当前 6 处，其中带样式容器 2
  处，均未逐个对照 bkui-vue 源码，命中时先比对再动：
  - `src/components/bkui-vue/tag/Index.vue` 的 `.dbm-tag-icon`
  - `src/components/bkui-vue/select/Index.vue` 的 `.dbm-select-extension`
- **核实**：2026-09-22

## 补充

`db-input` 的 prefix / suffix 已按上面改法修掉。受影响的调用方（改动前被灰块包着，改动后恢复 bk-input 的裸渲染）：
    30|4 个域名表的 `.domain-address-placeholder`（sqlserver / mysql / mongodb 副本集 / redis 单实例申请页）、redis
单实例申请页的「选择主机」图标按钮、mongodb 分片集群与副本集申请页的 `%`。

`CycleRotate.vue` 还在用 `BkInput`，它的「人 / 天」是自己写 `.suffix-slot`（`width: 30px`、`background: #fafbfd`、
`border-left`）手工补出灰块的——反过来印证 bk-input 的插槽本来就没有容器。
