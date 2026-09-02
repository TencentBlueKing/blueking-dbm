# 时间范围快捷选项的重复定义与取值漂移

状态：未处理

## 现象

`datetime-range` 搜索项 / 表头筛选的「快捷选项」（近 1 小时、今天、近 7 天……）在项目里被大量就地定义在
`props.shortcuts` 里。同一份选项集通常在同一个功能目录下被抄两遍——一遍给快捷搜索、一遍给表头筛选，
而不同功能目录之间的选项集又互不相同：有 8 项的、7 项的、4 项的，天级选项有的取当天边界、有的从当前时刻往前推。

后果有两层，都是用户能看到的：

    10|1. 同一句「近 7 天」在不同页面走两套 i18n key，渲染出的文案不一样——`近7天`（无空格）与 `近 7 天`（带空格）并存。
2. 同一句「近 1 天 / 近 7 天」在不同页面的实际区间不一样：告警屏蔽页是「此刻往前推 7×24 小时」，
   资源池 / 单据 / 任务历史页是「7 天前的 00:00:00 到今天的 23:59:59」。用户在两个页面选同名选项会拿到不同的数据范围。

## 证据

逐行读过并核对取值的四处（同一目录下的成对定义按一条列）：

| 文件:行 | 选项集 | 天级边界 | 文案 key 家族 |
| --- | --- | --- | --- |
    20|| `src/views/monitor-alarm/alarm-shield/useSearch.ts:27-60` | 8 项：近30分钟 / 近1小时 / 近12小时 / 近1天 / 近7天 / 近1个月 / 近3个月 / 近6个月 | 无，一律 `dayjs().subtract(n, unit).toDate()` → `dayjs().toDate()` | `近n天`、`近1小时`、`近n个月` |
| `src/views/resource-manage/todo/useQuickSearch.ts:92-121` + `src/views/resource-manage/todo/useColumnFilter.ts:49-78` | 7 项：近 1 小时 / 近 12 小时 / 今天 / 近 7 天 / 近 1 个月 / 近 3 个月 / 近 6 个月 | 天及以上用 `startOf('day')` / `endOf('day')` | `近 7 天`、`近 1 小时`、`近 3 个月` |
| `src/views/db-manage/todo/disabled/useQuickSearch.ts:48-65` + `src/views/db-manage/todo/disabled/useColumnFilter.ts:60-77` | 4 项：今天 / 近 3 天 / 近 7 天 / 超过 7 天 | `startOf('day')` / `endOf('day')`，「超过 7 天」用 `dayjs(0)` 兜底起点 | `近 7 天` |
| `src/views/db-manage/redis/memory-analysis-list/useSearchSelect.ts:82-111` | 7 项，与 `resource-manage/todo` 同 | 同上 | 同上 |

两套 i18n key 家族在语言包里同时存在，且渲染结果确实不同：

- `src/locales/zh-cn.json`：`"近n天": "近{n}天"`、`"近1小时": "近1小时"`、`"近n个月": "近{n}个月"`
- `src/locales/zh-cn.json`：`"近 7 天": "近 7 天"`、`"近 1 小时": "近 1 小时"`、`"近 3 个月": "近 3 个月"`

    30|成对重复的具体形态（已读过的两对，逐行相同，不是漂移而是纯拷贝）：

- `resource-manage/todo`：`useQuickSearch.ts:92-121` 与 `useColumnFilter.ts:49-78` 的 7 项取值逐行一致
- `db-manage/todo/disabled`：`useQuickSearch.ts:48-65` 与 `useColumnFilter.ts:60-77` 的 4 项取值逐行一致

## 项目里已有的正确做法

`src/views/monitor-alarm/alarm-shield/useSearch.ts` 是做对的那一处：把选项集提成模块常量
`shieldTimeShortcuts`（:27-60），快捷搜索（:76）与表头筛选（:122）引用同一份，
并在注释里写明「屏蔽时间快捷选项，快捷搜索与表头筛选共用」。同文件的 `shieldCategoryList` 也是这么共用的。

    40|它没覆盖到的地方有两层：一是这份常量只服务 alarm-shield 自己，其他功能目录仍各自就地定义；
二是它自己那 8 项的取值与文案 key 又和其余页面的 7 项版本不一致，
所以「照着 alarm-shield 抄」反而会把第二套取值扩散出去——本次 `alarm-events` 就是照它抄的，
新增的 `src/views/monitor-alarm/alarm-events/useQuickSearch.ts:59-92` 又是一份 8 项拷贝。

## 建议方向（未采纳）

方向：把「通用的那一套」提成一个共享常量（例如 `@common/const` 或 `@utils` 下的 `datetimeRangeShortcuts`），
同时统一到一套 i18n key；页面若有业务专属项（如禁用时间的「超过 7 天」）在共享常量基础上拼接，而不是整份重写。
选项集是纯数据、`value` 是惰性函数，不涉及组件与样式，是这些重复里唯一能安全共享的部分。

    50|不推荐把所有页面强行压成同一份选项：`db-manage/todo/disabled` 的「今天 / 近 3 天 / 近 7 天 / 超过 7 天」
是「按积压时长分档」的业务语义，不是通用时间范围，抹平会丢掉产品意图。

不推荐只合并同目录下 `useQuickSearch` / `useColumnFilter` 那一对而不动取值与文案：
那样每个目录仍是一份独立取值，跨页面的「近 7 天 含义不同」和两套文案 key 都还在，漂移会重新长出来。

不推荐反过来统一到 alarm-shield 那套「此刻往前推」的语义再顺手改掉 `startOf('day')`：
带天边界的版本占多数且更符合「今天 / 近 7 天」的日常读法，改动面反而更大，需要产品先定语义。

## 待查证

    60|- grep 定位到 28 处就地写的 `shortcuts: [`（`src/hooks/useClusterQuickSearch.ts:214`、
  `src/hooks/useClusterColumnFilter.ts:34`、`src/hooks/useInstanceQuickSearch.ts:161`、
  `src/hooks/useInstanceColumnFilter.ts:26`、`src/views/ticket-center/**`、`src/views/db-configure/**`、
  `src/views/staff-manage/**`、`src/views/task-history/**`、`src/views/resource-manage/**` 等），
  本篇只逐行读过上表四处 + 两对成对定义，其余 20 余处的取值是否又有第四、第五套没有核对。
- `src/hooks/` 下的 `useClusterQuickSearch` / `useClusterColumnFilter` / `useInstanceQuickSearch` /
  `useInstanceColumnFilter` 是全局 hook，它们是否已经算「共享层」、以及和各页面自带的那份是什么关系，未确认。
- 未确认两套 i18n key 家族的出现先后，因此「哪一套是基准文案」没有依据。
- `date-range`（只到日）与 `datetime-range` 是否共用同一批快捷选项、有无各自的取值，未核对。
