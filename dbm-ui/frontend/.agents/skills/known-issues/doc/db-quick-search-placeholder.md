# `<DbQuickSearch>` 不要再传 placeholder，走组件默认拼接

**已下沉到 ESLint**，不在 `checks.md` 索引里。`eslint.config.mjs` 的 `vue/no-restricted-v-bind`
和 `vue/no-restricted-static-attribute` 会在 `<DbQuickSearch>` 上的 `:placeholder` / `placeholder`
上报 error，提示信息指回本篇。

- **命中**：ESLint 报错；或人工排查时
  `rg -n '<DbQuickSearch' -A 12 src --glob '*.vue' | rg 'placeholder'`
- **为什么**：调用方各自手写一份「请输入或选择条件搜索 / 搜索单号、单据类型…」，和 `data` 里的搜索项不同步；漏配、配错、中英文各写一套。组件已按全量 `data.name` 用顿号拼默认文案 `请输入或选择 {n}`
- **改成**：模板里删掉 `placeholder` / `:placeholder`。需要覆盖时再显式传，默认不要传
- **不要**：不要在调用方再写一份「搜索」+ `data.map(item => item.name).join('、')` 当 placeholder，那就是默认值的重复实现
- **存量**：活跃调用已清完。`src/components/shard-selector/Index.vue` 里有一段注释掉的
  `<DbQuickSearch :placeholder="t('请输入或选择条件搜索')" />`，注释不进 ESLint，解开注释时会被拦下
- **核实**：2026-09-16
