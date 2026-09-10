# 分页组件不认 `current`，必须显式绑 `:model-value`

- **命中**：`<BkPagination>` / `<DbPagination>` 只写了 `v-bind="pagination"`、没有 `:model-value`，而代码里又会从外部改写
  `pagination.current`（筛选变化时重置为 1、从 URL 恢复页码）。全量扫描见下方「存量」的命令
- **为什么**：两个组件都只认 `modelValue`。`current` 经 `v-bind` 会落到根 div 上变成无意义的 DOM
  属性，组件自己维护的当前页不被覆盖。表现两种：筛选变化后请求回到第一页但页码条仍高亮旧页；从 URL
  恢复页码时请求取的是 URL 里的页、页码条却显示第 1 页
- **改成**：补 `:model-value="pagination.current"`。纯加性改动，不影响其它绑定
- **不要**在分页组件里新增 `current` prop 当 `modelValue` 的别名：两个入口写同一份状态，谁优先无法自解释，之后每个调用点都要先判断自己走的是哪条路
- **存量**：14 个文件未绑定，含 `src/components/db-table/IndexNew.vue`。`cluster-selector` /
  `instance-selector` 两批调用点都写了，是绑定这一侧的样板。取当前列表：

  ```bash
  cd dbm-ui/frontend
  rg -U --pcre2 -l '<(Bk|Db)Pagination(?:(?!/?>)[\s\S])*?v-bind="pagination"(?:(?!/?>)[\s\S])*?/?>' src | sort > /tmp/p_all
  rg -U --pcre2 -l '<(Bk|Db)Pagination(?:(?!/?>)[\s\S])*?:model-value(?:(?!/?>)[\s\S])*?/?>' src | sort > /tmp/p_ok
  comm -23 /tmp/p_all /tmp/p_ok
  ```

- **核实**：2026-09-10

## 补充

分页状态对象本身也是各写一份，字段与取值已经漂移（有的带 `align` / `layout`，有的不带；`limitList` 有三套取值）。
`src/components/db-table/hooks/use-pagination.ts` 是唯一被抽出来的分页状态 hook，设计是对的（`onChange`
带去重判断、`onLimitChange` 重置 `current`），但只有 `db-table` 自己在用，且它自己的模板恰好也漏了 `:model-value`。

把状态字段名对齐组件契约（`current` → `modelValue`）让 `v-bind` 直接生效是更彻底的做法，但要连带改所有定义和所有读
`pagination.current` 的地方，未做。
