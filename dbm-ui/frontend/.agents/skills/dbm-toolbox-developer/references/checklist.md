# 工具箱单据自检清单

写完一个单据后从头到尾过一遍。**本篇是提单页检查项的唯一清单**，review 时也照它逐条核；
[workflow-review.md](workflow-review.md) 只补 diff 驱动的查法——命令、存量例外、定级。

本篇只查提单页这一侧。**单据纵线（枚举、details 类型、提交体、回填、详情组件）另过一遍 `dbm-ticket-developer` 的
`references/checklist.md`，两篇都要跑。**

按实现顺序排列，改已有单据时只过相关段落。通用项（国际化、`any`、版权头、eslint）见 `AGENTS.md`，不在此列。

## 需求与原型

- [ ] TAPD 需求已拉取，`description` 里的录入规范、页级表单项、校验规则、详情展示要求都读过
- [ ] 原型图已下载预览
- [ ] `BkAlert` 的 `title`、`CardCheckbox` 的 `title` / `desc`、`BkRadioGroup` 选项文本、表格列头、批量录入示例
      **全部取自原型图原文**，没有自行编造

## 工具箱这两件

- [ ] 提单页 `Index.vue` 已创建，**目录名等于 `TicketTypes` 枚举值**
- [ ] 路由已用 `createRouteItem` 注册，没手写 `name` / `path` / `component` / `fullscreen`
      （非单据入口和 DBA 工具箱除外，见 [dba-and-non-ticket.md](dba-and-non-ticket.md)）
- [ ] 工具箱菜单已添加，含 `dbConsoleValue`。`desc` 只要求 mysql / tendb-cluster；其余四个 DB 跟随同文件存量
- [ ] 需求里每种独立 `ticket_type` 都有自己的 `Index.vue`，没有合并成一个页面切换

## 页面骨架

- [ ] 根节点是 `SmartAction`，底部按钮在它的 `#action` 插槽内
- [ ] 新建页面表单容器用 `DbForm`
- [ ] 提单页**没有**写 `defineOptions({ name })`
- [ ] 行末有 `OperationColumn`
- [ ] 表单末尾有 `TicketPayload`
- [ ] 有 `defineExpose({ routerBack })`，且路由名在该 DB 真实存在（见 [db-profiles.md](db-profiles.md)）
- [ ] `BatchInput` 下方紧跟的元素加了 `mt-16`
- [ ] 全局注册组件（`SmartAction` / `DbForm` / `Editable*` / `OperationColumn` / `DbResetButton`）没被 import
- [ ] 页级单选的 radio **直接绑后端枚举值**，没造前端枚举再写双向映射函数

## 模式

- [ ] 模式选择方式正确：同一 `ticket_type` 内的子类型用页内控件；多个独立 `ticket_type` 用模式 F 跨页切换
- [ ] **协议或可编辑列随模式变化的，已拆成模式子组件**（`<Component :is>` + `defineExpose({ validate, getValue })`），
      页面零 `v-if` 分支

## 表格与列

- [ ] 行工厂覆盖**每一个**行模型字段，且都有默认值（缺默认值的列校验规则等于失效）
- [ ] 整体替换 `tableData` 的三处（重置、批量录入覆盖、回填）都刷了 `tableKey`
- [ ] `handleReset` 调 `createDefaultFormData()` 完整重置
- [ ] `EditableColumn` 内只有 `Editable` 系列组件，没有 `BkInput` / `DbSelect` 这类普通表单组件
- [ ] 非首列的集群选择用 `TargetClusterColumn`，不是 `ClusterColumn`
- [ ] 源 DB / 源表列传了 `check-not-exist`；忽略 DB / 忽略表列**没传**
- [ ] 未选源集群时，依赖源集群的列被禁用并提示「请先选择源集群」
- [ ] 数据加载回调里的 `validate()` 只在查询**未命中**时调用
- [ ] 跨列演算的校验写在演算结果列的 `append-rules` 里，不在提交函数里用 `Message` 拦截

## 批量操作

- [ ] `batchInputConfig` 覆盖了所有列（漏配的列录入后是空的）
- [ ] `key` 用**行数据字段名（前端驼峰）**，不是后端字段名
- [ ] 示例文本不含会被空白符误切的值（映射对用冒号，多条用逗号）
- [ ] 覆盖模式刷了 `tableKey` 并触发校验
- [ ] 随集群变化清空的列有 `xxx_domain` 归属标记，**回填 / 批量录入 / 侧滑确认三处都写入了**

## 提交时序

- [ ] 提交前先 `form.validate()` 再 `table.validate()`
- [ ] 用的是默认 `isToolbox: true`，没有显式传 `false`（传了失败错误条不会内联展示）
- [ ] 页面没有重复处理成功提示、重复单据确认、失败行级回填（hook 内部已做）
- [ ] 回填组装完表格数据后刷了 `tableKey`
- [ ] 备注走 `createTicketPayload(ticketDetail)` 回填

提交体字段、回填完整度、`clusters` / `specs` 兜底见 `dbm-ticket-developer` 的 `references/checklist.md`。

## 收尾

- [ ] mysql 单据已在 [inventory-mysql.md](inventory-mysql.md) 登记模式与特殊组件
- [ ] 改了公共列组件的，已 `rg -ln` 列全调用方并逐个读过
- [ ] 已过一遍 `dbm-ticket-developer` 的 `references/checklist.md`
