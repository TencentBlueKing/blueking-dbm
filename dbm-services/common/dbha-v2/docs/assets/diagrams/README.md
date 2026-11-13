# 配图资产（assets/diagrams）

本目录集中存放 dbha-v2 文档的全部配图（SVG）。**SVG 是唯一的图源**：文档正文只保留图片引用，不再保留任何图源码；后续修改配图请直接编辑本目录下的 SVG 文件。

## 图清单

| 文件 | 引用文档 | 图题 |
| --- | --- | --- |
| `architecture-system-overview.svg` | [architecture/overview.md](../../architecture/overview.md) | DBHA v2 系统架构图 |
| `migrator-single-run.svg` | [architecture/migrator-design.md](../../architecture/migrator-design.md) | migrate 单次执行流程 |
| `probe-generic-harvest.svg` | [detection/detection-doc-index.md](../../detection/detection-doc-index.md) | Probe 通用采集流程 |
| `analysis-generic-decision.svg` | [detection/detection-doc-index.md](../../detection/detection-doc-index.md) | Analysis 四路检查与入窗 |
| `mysql-storage-detection.svg` | [detection/mysql-detection-design.md](../../detection/mysql-detection-design.md) | MySQL 普通存储探测主流程 |
| `mysql-heartbeat-repl-loops.svg` | [detection/mysql-detection-design.md](../../detection/mysql-detection-design.md) | 心跳组与复制延迟组双定时循环 |
| `mysql-event-layers.svg` | [detection/mysql-detection-design.md](../../detection/mysql-detection-design.md) | 异常事件分层与入窗 |
| `mysql-switch-trigger-sequence.svg` | [detection/mysql-detection-design.md](../../detection/mysql-detection-design.md) | 切换触发时序 |
| `mysql-actionscope-dispatch.svg` | [detection/mysql-detection-design.md](../../detection/mysql-detection-design.md) | ActionScope 分发 |
| `mysql-switch-state-machine.svg` | [detection/mysql-detection-design.md](../../detection/mysql-detection-design.md) | 单实例切换状态机 |
| `mysql-switch-side-effects.svg` | [detection/mysql-detection-design.md](../../detection/mysql-detection-design.md) | 两家族切换副作用 |
| `flow-scan-pop-sequence.svg` | [flows/failure-detection-and-failover.md](../../flows/failure-detection-and-failover.md) | Scan 与 Pop 双循环时序 |
| `flow-sliding-window.svg` | [flows/failure-detection-and-failover.md](../../flows/failure-detection-and-failover.md) | 滑动窗口 |
| `flow-strategy-matching.svg` | [flows/failure-detection-and-failover.md](../../flows/failure-detection-and-failover.md) | 策略匹配 |
| `flow-config-sync-sequence.svg` | [flows/config-sync.md](../../flows/config-sync.md) | 配置下发时序 |
| `flow-harvest-report-sequence.svg` | [flows/probe-harvest-and-report.md](../../flows/probe-harvest-and-report.md) | 采集与上报时序 |
| `flow-gen-config.svg` | [flows/gen-config-design.md](../../flows/gen-config-design.md) | gen-config 执行流程 |

## SVG 结构契约

- 根元素：标准 `xmlns`、`viewBox`、固有 `width`/`height`（像素）、`preserveAspectRatio="xMidYMid meet"`、`style="max-width:100%;height:auto;background-color:#ffffff;"`。
- 无障碍：`<title>` 为中文图名，`<desc>` 为一句内容概述。
- 背景：根内第一个图形元素是铺满 `viewBox` 的 `fill="#ffffff"` 矩形，保证明暗主题下均可读。
- 文本：全部为原生 `<text>`/`<tspan>`；**禁止** `foreignObject`、`<script>`、`<image>`、外部 `href`、外部字体、`@import` 与 `url(...)` 外链——SVG 以 Markdown 图片的「安全静态模式」加载，以上元素都不会渲染。
- 结构：按语义分组（节点组 / 连线组 / 图例组），元素带 id，已格式化缩进，可直接文本编辑。
- 字体栈：`Noto Sans CJK SC, PingFang SC, Microsoft YaHei, sans-serif`（查看端按系统回退）。
- 防遮挡：连线标签、子图标题（`g.cluster-titles`）、时序图消息/分段文字下方各有一块不透明白底矩形（`rect.background` / `rect.text-bg`），连线不得穿过节点或其他文字；修改文字或移动元素后需同步调整对应白底矩形的位置与尺寸。

## 逐图配色对照

颜色语义**逐图绑定**，同一色值在不同图中含义不同，不得跨图套用或全局统一：

| 图 | 色值 → 语义 |
| --- | --- |
| architecture-system-overview | `#2563eb` 蓝实线=主路径；`#ea580c` 橙虚线=GSE 旁路；`#16a34a` 绿虚线=etcd Register/Watch；`#7c3aed` 紫实线=SSH 二次探测；`#64748b` 灰虚线=keepalive/配置回退 |
| probe-generic-harvest | `#2563eb` 主路径；`#64748b` 建连失败分支 |
| analysis-generic-decision | `#2563eb` 主路径；`#16a34a` 入窗；`#64748b` stub/仅告警；`#ea580c` 橙虚线=异步 Pop |
| mysql-storage-detection | `#2563eb` 主路径；`#64748b` 建连失败 |
| mysql-heartbeat-repl-loops | `#2563eb` 心跳组主路径；`#dc2626` 红=心跳写失败产出事件；`#0891b2` 青=复制延迟组 |
| mysql-event-layers | `#2563eb` 主路径；`#7c3aed` SSH 二次探测；`#16a34a` 入窗；`#64748b` 仅告警/stub；`#ea580c` 橙虚线=异步 Pop |
| mysql-actionscope-dispatch | `#2563eb` 分发与编排主路径 |
| mysql-switch-side-effects | `#2563eb` tendbha 分支（含共用入口）；`#0891b2` tendbcluster 分支 |
| flow-sliding-window | `#2563eb` Push/成熟主路径；`#64748b` 灰虚线=丢弃/inflight 超时清理 |
| flow-strategy-matching | `#2563eb` 主路径；`#16a34a` 绿实线=命中与 action=switch 两条判定分支；`#64748b` 灰实线=未命中/仅告警/跳过 |

## 手工编辑与本地预览

- 编辑：任意文本编辑器打开 SVG，按 id/分组定位节点或连线；改文字直接编辑 `<tspan>` 内容；改配色编辑 `stroke`/`fill` 并同步更新对应文档中的「色例」说明。
- 预览：浏览器直接打开 SVG 文件，或写入临时 HTML 用 `<img src="...">` 加载（与 Markdown 渲染行为一致，能暴露安全静态模式下的文字缺失问题）。
- 校验：XML 必须可解析；不得重新引入结构契约禁止的元素。

## 已知限制

- 图源码未入库（一次性转换产物），改图需直接编辑 SVG。
- 文字不可选中/搜索；不随明暗主题变化（固定白底深字）。
- 宽图（如 `mysql-switch-trigger-sequence.svg`）在窄容器中会等比缩小，建议点击查看原图。
- 查看端字体与生成端不同可能造成个别长标签与节点边框的间距变化。
