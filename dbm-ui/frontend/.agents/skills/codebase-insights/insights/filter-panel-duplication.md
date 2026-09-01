# 筛选下拉面板的多套并行实现

状态：未处理

## 现象

「带搜索框的筛选下拉面板」（单选 / 多选 / 级联 / 多级联 + 远程搜索）在项目里至少有两套完整的独立实现：
`db-quick-search` 的 `value-menu`，和 `db-table` 的列筛选面板。两套是同源拷贝（同名文件、同名 hook、连同一个拼写错误一起复制），
但此后各自改动，行为已经漂移：远程搜索时是否还叠加本地过滤、特殊选项（未知 / 通用）是否置底、关键字是否支持多值分割，四个下拉给出四种答案。

后果是同一个缺陷只会在被人打开的那一份里修好。本次修 `db-quick-search` 的 Select 面板「无关键字时已选项置顶」丢失
`return`、以及远程搜索无防抖无竞态保护，另一份拷贝里同样的写法仍然原样存在。

## 证据

同职责 hook 的两份拷贝：

| 文件 | 远程请求防抖 | 请求竞态保护 | 传给 remoteMethod 的 keyword |
| ------------------------------------------------------------------------------------------------------- | ------------ | ------------ | ---------------------------------------- |
| `src/components/db-quick-search/bk-quick-search/components/create-area/components/value-menu/hooks/useMenuList.ts` | 有（本次加） | 有（本次加） | `splitSearchKeyword(filterKey).join(',')` |
| `src/components/db-table/components/hooks/useMenuList.ts:26-53` | 无 | 无 | `filterKey` 原样 |

`renderList` 的四份实现：

| 文件 | remoteSearch 时跳过本地过滤 | 特殊选项置底 | 关键字匹配方式 |
| ------------------------------------------------------ | --------------------------- | ---------------------- | ------------------------------- |
| quick-search `Select.vue:83`（本次修） | 有 | `SpecialOptions.PUBLIC` | `isSearchKeywordMatch`（支持多关键字） |
| quick-search `MultSelect.vue:94` | 有 | `SpecialOptions.EMPTY` | `isSearchKeywordMatch` |
| db-table `SingleSelect.vue:94-101` | 无 | 无 | `label.toLowerCase().includes` |
| db-table `MultipleSelect.vue:99-110` | 有 | 无 | `label.toLowerCase().includes` |

同一个变量名拼写错误出现在两份 `MultCascader.vue`，是同源拷贝的直接证据：
`src/components/db-table/components/MultCascader.vue:43,52,55` 仍是 `expanedParent`，
`db-quick-search` 那份同名变量本次已改为 `expandedParent`。

第三处拷贝在多行输入区：`src/views/resource-manage/common/components/ip-search/Index.vue:118,129`
保留了与 `db-quick-search/bk-quick-search/components/create-area/Index.vue` 完全相同的
「手动输入模式支持 Shfit + Enter 换行」注释与分隔符解析流程。

## 项目里已有的正确做法

`SpecialOptions` / `specialOptionLabelMap`（`src/common/const/specialOptions.ts`）是做对的那一层：
「未知」「通用」两个特殊值的取值与文案集中在一处，两套面板都从这里取枚举。
它只统一了「值和文案」，没有统一「这些特殊值在列表里排在哪、什么时候画分隔线」，
于是 quick-search 的 Select 用 `PUBLIC` 置底、MultSelect 用 `EMPTY` 置底、db-table 两份完全不置底。

## 建议方向（未采纳）

方向：把「候选列表的排序与过滤」从组件里抽成一个纯函数（输入 list、已选值、keyword、remoteSearch、置底值，输出渲染列表），
两套面板都调它。纯函数不涉及模板与样式，是这两套实现里唯一真正重合且能安全共享的部分。

不推荐直接让 `db-table` 复用 `db-quick-search` 的面板组件：两者的宿主形态不同
（前者是表头 popover、宽度跟随列宽，后者是搜索框下的 tippy 面板、宽度自适应内容），
模板与样式几乎没有重合，强行合并会把两个宿主的布局约束缠在一起。

也不推荐只做「把 db-table 那份补齐到和 quick-search 一致」：这次能补齐，下次改动仍然是两处，漂移会重新长出来。

## 待查证

- 只核对了 `Select` / `MultSelect` / `SingleSelect` / `MultipleSelect` 四个下拉与两份 `useMenuList`、两份 `MultCascader`；
  `Cascader`、`DatetimeRange`、`MultipleInput` 三类是否也有同样的漂移没有逐行比对。
- `ip-search` 那处只核对了注释与多行输入解析，它是否也复制了面板逻辑未确认。
- 未确认两套实现的先后顺序与复制方向（谁抄谁），因此「哪一份是基准」这个判断尚无依据。
