# 写不存在的 `Db*` 组件会被当成原生元素，静默失效

- **命中**：`rg -n '<Db(Radio|RadioGroup|Checkbox|Switch|Alert|Dialog|Tree)\b' src`
  （这些 bkui 组件族没有 `Db*` 包装）；更一般地——正要写 `<Db某组件>` 时，
  它既不在 `src/common/importComps.ts` 的注册表里，本文件也没有 import
- **为什么**：Vue 对未注册标签不报错，按未知元素渲染。表现是"样式不对"（radio 没有圆圈、button 没有边框），
  但**功能同样是坏的**：`v-model`、`@change`、props 全部接不上，用户点了没有任何反应，且控制台无警告，
  只有 vue-tsc 恰好报模板类型错时才会暴露
- **改成**：bkui 组件一律用 `Bk*`（`main.ts` 已 `app.use(bkuiVue)` 全局注册）；
  单选写法固定为 `<BkRadioGroup v-model="x"><BkRadio label="值">文案</BkRadio></BkRadioGroup>`
  —— Radio 的值 prop 是 `label`，不是 `value`
- **不要**：不要为了这一处再包一层同名的 `Db*` 壳；先在 `importComps.ts` 里搜一遍是否已有
- **存量**：已清零（`src/views/db-configure/components/VersionOsEditor.vue`、
  `src/views/db-configure/list/.../ModuleVersionPanel.vue` 各有一处 `DbRadioGroup` / `DbRadio`，2026-10-09 修）
- **核实**：2026-10-12

## 补充：`Bk*` 也不一定全局注册（同一种静默失效）

- **命中**：写 `<BkXxx>` 时，先用 `rg -n "search-select" node_modules/bkui-vue/lib/index.js` 之类的方式确认 **bkui 的 barrel 是否导出该组件**。
  反例：`bkui-vue` 的 barrel（`lib/index.js`）里**没有** `search-select`，组件只存在于 `lib/search-select/`，
  于是 `app.use(bkuiVue)` 不会注册它——在模板里写 `<BkSearchSelect>` 会被当成未知元素，**页面完全没变化**、控制台无警告。
- **为什么**：与 `Db*` 那条同因：Vue 对未注册标签不报错。区别是 `Bk*` 前缀看起来"应该已全局注册"，更容易误判。
- **改成**：显式深引入（项目既有先例：`import InfoBox from 'bkui-vue/lib/info-box'`）：
  `import BkSearchSelect from 'bkui-vue/lib/search-select';`，类型定义在同目录 `utils.d.ts` / `input.d.ts`。
  或者先 `rg -n "<BkXxx" src` 看项目里有没有现成用法，没有就按此方式显式引入。
- **不要**：不要因为"页面没变化"就反复改 props/样式——先确认组件到底有没有渲染出来。
- **核实**：2026-10-12
