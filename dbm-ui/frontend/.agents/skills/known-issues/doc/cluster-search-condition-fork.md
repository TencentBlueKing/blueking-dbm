# 集群搜索条件列表有两套 hook，标签选项转换有三份

- **命中**：改集群搜索条件列表，或改标签筛选选项的编码格式。定位：`rg -ln "tag_keys#" src`

- **为什么**：集群搜索条件有两套独立实现——列表页走 `src/hooks/useClusterQuickSearch.ts`（15 个条件），集群选择器走 `src/components/cluster-selector/components/useSelectorSearch.ts`（8 个条件），各自维护、已经漂移（同一个「集群名称」条件，列表页叫「集群标识（集群名称 / 别名）」）。

  更硬的问题是把 `listTag` 结果转成两级级联选项的那段逻辑（父节点 `tag_keys#<key>`、子节点 `tag_ids#<id>`）在 **3 个文件**里逐字重复。tag 的编码前缀是和后端约定的，改一次要同时改 3 处，漏一处就是那个入口的标签筛选静默失效。

- **改成**：改 tag 选项转换时，先 `rg -ln "tag_keys#" src` 把 3 个文件逐个核对一遍，都改到。改搜索条件时，在另一个 hook 里查一下同名条件（同 `id`）是否也该跟着改，有就报告。

  `listTag` → 级联选项 那段抽成公用函数是安全的（3 份逐字相同，输入输出一致），但那是独立改动，不要夹在别的需求里做。

- **不要**：把两个 hook 合并。条件集和文案都不同（选择器 8 个条件 vs 列表页 15 个），合并会改掉选择器弹窗的搜索交互；而且选择器的 `queryBizClusterAttrs` 结果还要经 `columnAttrs` 供表格列筛选用，列表页那边走的是独立的 `useClusterColumnFilter`，两者的数据出口也不一样。

- **存量**：`rg -ln "tag_keys#" src`，2026-09-15 跑出 3 处：
  - `src/hooks/useClusterQuickSearch.ts`
  - `src/hooks/useClusterColumnFilter.ts`
  - `src/components/cluster-selector/components/useSelectorSearch.ts`

- **核实**：2026-09-15
