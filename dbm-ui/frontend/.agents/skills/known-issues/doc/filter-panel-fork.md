# 筛选下拉面板有两套同源拷贝，改一处要看另一处

- **命中**：改 `src/components/db-quick-search/bk-quick-search/components/create-area/components/value-menu/**` 或
  `src/components/db-table/components/**` 下的筛选面板，尤其是两边同名的 `useMenuList` / `renderList` /
  `MultCascader`。定位：`rg -ln 'useMenuList' src`
- **为什么**：两套是同源拷贝（连 `expanedParent` 这个拼写错误都一起复制），此后各自改动已经漂移：远程搜索时是否还叠加本地过滤、特殊选项是否置底、关键字是否支持多值分割，四个下拉给出四种答案。只修被打开的那一份，另一份的同样缺陷会原样留着
- **改成**：改动一并在另一套里检查同样写法，有就报告
- **不要**直接让两边复用同一个面板组件：宿主形态不同（表头 popover 宽度跟随列宽，vs
  搜索框下的 tippy 面板宽度自适应内容），模板与样式几乎没有重合，强行合并会把两个宿主的布局约束缠在一起。也**不要**只做「把
  db-table 那份补齐到和 quick-search 一致」：这次能补齐，下次改动仍然是两处
- **存量**：`src/components/db-table/components/hooks/useMenuList.ts` 仍无防抖、无请求竞态保护（quick-search
  那份已加 `_.debounce`）；拼错的 `expanedParent` 现在只剩 `src/components/db-table/components/MultCascader.vue`
  一个文件（`rg -n expanedParent src`），quick-search 那份已改名，是漂移的又一个实例
- **核实**：2026-09-10

## 补充

四份 `renderList` 的差异：

| 文件 | remoteSearch 时跳过本地过滤 | 特殊选项置底 | 关键字匹配 |
| --- | --- | --- | --- |
| quick-search `Select.vue` | 有 | `SpecialOptions.PUBLIC` | `isSearchKeywordMatch`（支持多关键字） |
| quick-search `MultSelect.vue` | 有 | `SpecialOptions.EMPTY` | `isSearchKeywordMatch` |
| db-table `SingleSelect.vue` | 无 | 无 | `label.toLowerCase().includes` |
| db-table `MultipleSelect.vue` | 有 | 无 | `label.toLowerCase().includes` |

`SpecialOptions` / `specialOptionLabelMap`（`src/common/const/specialOptions.ts`）是做对的那一层，两套面板都从这里取「未知」「通用」的值与文案；它只统一了值和文案，没统一「这些特殊值排在哪、什么时候画分隔线」。

要抽的话，边界是「候选列表的排序与过滤」这个纯函数（输入 list、已选值、keyword、remoteSearch、置底值，输出渲染列表），不涉及模板与样式。

`src/views/resource-manage/common/components/ip-search/Index.vue` 是第三处拷贝痕迹（与 `bk-quick-search`
的 create-area 有逐字相同的注释与分隔符解析流程），是否也复制了面板逻辑未确认。
