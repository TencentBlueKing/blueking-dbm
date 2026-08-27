# 第 0 步：TAPD 需求与原型图获取（新单据必做）

实现任何新工具箱前，**必须先从 TAPD 获取需求详情和附件**，确保实现与产品意图一致。

## 拉取 TAPD 需求详情

使用 TAPD MCP 的 `stories_get` 工具，传入 `workspace_id`（从 `agent-flow.config.json` 的 `projectId` 获取）和需求 ID。

重点关注 `description` 字段中的：单据标识（ticket_type 值、单据名称）、工具页录入规范（列序、必填、通配、批量录入字段对齐）、页级表单项、提交校验规则、单据详情展示要求、验收标准。

## 获取并预览原型图

TAPD 需求大概率包含 HTML 原型图附件。流程：

1. 调用 `get_attachment_info`（`type=story`）获取附件列表
2. 对 `.html` 附件调用 `get_attachment_download_url` 获取下载链接
3. 用 `Invoke-WebRequest -Uri <url> -OutFile <workspace>/prototype.html` 下载到工作区
4. 用 `web_preview`（`previewMode=static`）预览原型页面
5. 读取 HTML 源码，分析 UI 结构：模式选择组件类型、表格列序与列内控件、批量录入弹窗格式、侧滑结构、单据详情展示列序

**原型图是产品意图的最权威参考**。以下文案必须从原型图 HTML 中提取原文，禁止自行编造：

- BkAlert 的 `title`（顶部提示文案）
- CardCheckbox 的 `title`、`desc`（模式选择卡片文案）
- BkRadioGroup 各选项的 label 和显示文本
- 批量录入弹窗的示例文本和字段标签
- 表格列头文本

## 确认单据类型数量

仔细阅读 TAPD 需求，确认需求涉及的是**一个单据类型还是多个独立单据类型**。

- 如果需求描述了多种模式/方式，且每种模式对应**独立的 ticket_type**，则应为每种模式创建**独立的工具箱页面**（各自 `Index.vue`）
- 判断依据：后端是否为每种模式分配了不同的 `ticket_type` 枚举值
- **严禁将多个独立 ticket_type 合并到一个共用页面中用 CardCheckbox/BkTab 切换**——每个 ticket_type 必须有自己的 `Index.vue`

## 对照项目 UI 规范

原型图展示了产品意图，落地时需对照项目已有组件：

- **模式选择（迁移方式等）**：项目标准用 `CardCheckbox`（`@components/db-card-checkbox/CardCheckbox.vue`），参见 `MYSQL_ROLLBACK/Index.vue`
- **单选表单项**：用 `BkRadioGroup` + `BkRadio`（非 `BkRadioButton`，除非原型明确要求按钮组样式）
- **表格**：`EditableTable` + `EditableRow` + 列组件
- **侧滑**：`BkSideslider`
- **批量录入**：`BatchInput`

## 对接后端协议样例（cypress fixtures）

后端提单/详情协议最权威的参考是 `cypress/fixtures/mysql/<TICKET_TYPE>/` 下的两个样例：

- `createTicket.json`：提交 payload 结构（重点看 `details` 字段），可带注释说明字段语义
- `ticketDetail.json`：单据详情接口的实际返回结构

若 TAPD 需求或后端提供了协议 JSON，先落到这两个文件再写代码。提单页 `useCreateTicket` 的提交体、模型类型（`services/model/ticket/details/mysql/xxx.ts`）、详情页取值都要与样例对得上；后端协议变更时同步更新 fixtures。

参考：`cypress/fixtures/mysql/MYSQL_DTS_DATA_MIGRATE/createTicket.json`、`cypress/fixtures/mysql/MYSQL_DTS_DATA_MIGRATE_RENAME/ticketDetail.json`。
