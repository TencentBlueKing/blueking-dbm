# 新增一个工具箱单据

需求拉取、评论解读、提案生成走 `tapd-todo` skill；**确认要建几套 `ticket_type`、对齐协议、写 details 类型这三步走
`dbm-ticket-developer` 的 `references/workflow-new.md`，先做完那边再回来**。本篇只补工具箱特有的部分。

## 原型图

TAPD 需求大概率带 HTML 原型图附件，`tapd-todo` 不覆盖这部分：

1. `get_attachment_info`（`type=story`）拿附件列表
2. 对 `.html` 附件调 `get_attachment_download_url`
3. `curl -L -o prototype.html '<url>'`
4. 用 `cursor-ide-browser` 的 `browser_navigate` 打开 `file:///<绝对路径>/prototype.html` 看渲染效果，再读 HTML 源码
   分析模式选择控件类型、表格列序与列内控件、批量录入弹窗格式、侧滑结构、详情页展示列序

**以下文案必须从原型图 HTML 提取原文，禁止自行编造**：`BkAlert` 的 `title`、`CardCheckbox` 的 `title` / `desc`、
`BkRadioGroup` 选项文本、批量录入弹窗的示例文本与字段标签、表格列头。

## 先确认是哪类入口

- **DBA 工具箱 / Webconsole / 记录页 / 分析页** → [dba-and-non-ticket.md](dba-and-non-ticket.md)，不要按五件套补枚举
- **服务申请** → 看 `service-apply/routes.ts` 是否 `createApplyRoute`，是则走 `dbm-db-developer`。不要只看目录名带 `_APPLY`（`TENDBCLUSTER_SPIDER_MNT_APPLY` 仍是工具箱）
- 其余才是业务工具箱单据，继续下面

## 单据类型数量决定页面怎么拆

`dbm-ticket-developer` 那边确认出的 `ticket_type` 个数，直接决定工具箱这边的页面形态：

- **多个独立 `ticket_type`** → 各自独立 `Index.vue`，页面间切换用模式 F
- **同一 `ticket_type` 内的子类型** → 单页内放模式选择控件，但列的组织仍按 [page-patterns.md](page-patterns.md)
  的规则拆动态组件

判断错了返工成本很高，动手前务必确认。

---

之后按 [page-patterns.md](page-patterns.md) 选模式抄模板，**写完从头到尾过一遍
[checklist.md](checklist.md)**，再过一遍 `dbm-ticket-developer` 的 `references/checklist.md`。
