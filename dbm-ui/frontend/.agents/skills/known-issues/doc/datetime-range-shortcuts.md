# 时间范围快捷选项同目录共用一份常量

- **命中**：`rg -n 'shortcuts: \[' src` —— 选项集就地写在 props 里；或同一目录下 `useQuickSearch` 与
  `useColumnFilter` 各抄一份
- **为什么**：同一句「近 7 天」在不同页面走两套 i18n key，渲染出 `近7天`（无空格）与 `近 7 天`（带空格）；实际区间也不同——告警屏蔽页是「此刻往前推
  7×24 小时」，资源池 / 单据 / 任务历史页是「7 天前 00:00:00 到今天 23:59:59」。用户在两个页面选同名选项会拿到不同的数据范围
- **改成**：选项集提成模块常量，快捷搜索与表头筛选引用同一份。样板：
  `src/views/monitor-alarm/alarm-shield/useSearch.ts` 的 `shieldTimeShortcuts`，注释里写明了「快捷搜索与表头筛选共用」。
  **跨页面统一取值与 i18n key 的方案未定**，不要照着任一页面去改另一页面
- **不要**把所有页面压成同一份选项：`db-manage/todo/disabled` 的「今天 / 近 3 天 / 近 7 天 / 超过 7
  天」是「按积压时长分档」的业务语义，不是通用时间范围，抹平会丢产品意图。也**不要**反过来统一到 alarm-shield
  那套「此刻往前推」的语义：带天边界的版本占多数且更符合「今天 / 近 7 天」的日常读法，需要产品先定语义
- **存量**：`rg 'shortcuts: \[' src | wc -l` 当前 26 处，逐行核实过其中 4 组
- **核实**：2026-09-10

## 补充

已核实的四组取值：

| 位置（相对 `src/views/`） | 选项数 | 天级边界 | 文案 key |
| --- | --- | --- | --- |
| `monitor-alarm/alarm-shield/useSearch.ts` | 8 | 无，一律 `dayjs().subtract(n, unit)` → `dayjs()` | `近n天` |
| `resource-manage/todo/useQuickSearch.ts` + 同目录 `useColumnFilter.ts` | 7 | `startOf('day')` / `endOf('day')` | `近 7 天` |
| `db-manage/todo/disabled/useQuickSearch.ts` + 同目录 `useColumnFilter.ts` | 4 | 同上，「超过 7 天」用 `dayjs(0)` 兜底起点 | `近 7 天` |
| `db-manage/redis/memory-analysis-list/useSearchSelect.ts` | 7 | 同上 | 同上 |

成对定义是纯拷贝而非漂移——同目录下两个文件的选项逐行相同。

alarm-shield 那份虽然是「共用常量」的正确形状，但它自己的 8 项取值与文案 key 又和其余页面的 7
项版本不一致，所以「照着 alarm-shield 抄」反而会把第二套取值扩散出去（`monitor-alarm/alarm-events/useQuickSearch.ts`
就是这么来的）。
