---
name: mysql-toolbox
description: >-
  MySQL 工具箱提单页的完整实现指南，涵盖 TAPD 需求拉取、原型图预览、目录结构、路由注册、
  页面组件、列组件清单（含目标集群列模式）、单据详情页、工具箱菜单、提交流程与编辑回填的编码模式与约定。
  新建或修改 MySQL 工具箱提单页（MYSQL_xxx 类单据）、添加工具箱菜单项、
  注册单据详情页时使用，或当用户询问工具箱提单流程、可编辑表格列组件用法、
  createToolboxRoute / useCreateTicket / useTicketDetail 的使用方式时使用。
---

# MySQL 工具箱提单实现指南

本 skill 沉淀 MySQL 工具箱提单页的完整编码模式，基于 `src/views/db-manage/mysql/` 下已有工具箱的真实代码提炼。

**动手前先通读本文件**，实现时按「实现检查清单」逐条核对，专题细节按下方导航按需读取。

## 参考文件导航

专题细节拆分到 `references/` 目录，按场景按需读取，不必全部加载：

- [tapd-prototype.md](references/tapd-prototype.md)：第 0 步全流程——TAPD 需求拉取、原型图下载与预览、单据类型数量确认、项目 UI 组件对照、cypress fixtures 协议样例。**新建单据时必读**
- [page-template.md](references/page-template.md)：模式 A 的 `Index.vue` 完整模板——template 七元素结构、script setup 核心骨架（含回填、提交、批量录入方法签名）。**创建页面组件（第 2 步）时必读**
- [pattern-f.md](references/pattern-f.md)：模式 F（跨页 Wrapper 导航型）完整实现——Wrapper 组件模板、Index.vue 模板、common.ts 共享模块、关键点。**新工具箱归入模式 F 时必读**
- [column-components.md](references/column-components.md)：列组件与表单项完整清单——MySQL 专属列、跨库通用列、TargetClusterColumn 详解（Props 与复用决策）、模式选择组件。**选列组件时读**
- [row-editing-pitfalls.md](references/row-editing-pitfalls.md)：行编辑与回填三类易错点（集群域名解析时机、联动防误清、对象数组边界转换）、批量录入六条约定、ResourceTagColumn 回填与已知竞态坑。**表格含联动列 / 批量录入 / 资源标签列时必读**
- [ticket-detail.md](references/ticket-detail.md)：单据详情页实现——取值兜底三类、资源标签列、长列表折叠展开、联动列显示形态、行键与编辑入口位置。**实现详情页（第 2.5 步）时必读**
- [ticket-inventory.md](references/ticket-inventory.md)：现有 41 个 MySQL 工具箱的模式归属与特殊组件对照表。**找同类单据做参考实现时查；新单据完成后同步更新该表**

---

## 页面模式

MySQL 工具箱有 6 种已验证的页面模式，新工具箱必须归入其中一种（对照 [ticket-inventory.md](references/ticket-inventory.md) 找同类参考）。

### 模式 A：标准可编辑表格型（最常见）

`MYSQL_ADD_SLAVE`、`MYSQL_CHECKSUM`、`MYSQL_PROXY_ADD` 等 80% 的工具箱使用此模式。

结构：`SmartAction` > `BkAlert` + `BatchInput` + `BkForm` > `EditableTable` + `TicketPayload`，底部 `#action` 提交 + 重置。完整模板见 [page-template.md](references/page-template.md)。

**当 `BatchInput` 存在时，其下方的 `BkForm` 或 `EditableTable` 必须加 `class="mt-16"`**。参考：`MYSQL_ADD_SLAVE/Index.vue`、`MYSQL_DATA_MIGRATE/Index.vue`。

### 模式 B：多步骤向导型

`MYSQL_IMPORT_SQLFILE` 使用此模式。入口 `Index.vue` 根据 `route.params.step` 动态渲染 `steps/step1`、`step2`、`step3`，路由需带 `{ params: '/:step?' }`。

### 模式 C：子类型选择型

`MYSQL_FLASHBACK` 使用 `BkRadioGroup`；`MYSQL_ROLLBACK` 使用 `CardCheckbox` 选择回档方式。仅适用于**同一 ticket_type 内**的子类型选择，通过 `<Component :is="comMap[type]" />` 或 `v-if` 条件渲染不同列。

**注意**：如果不同模式对应不同的 ticket_type，必须使用模式 F（跨页 Wrapper 导航型），不能用模式 C。

### 模式 D：Wrapper + 子组件型

`MYSQL_HA_TRUNCATE_DATA` 使用此模式。入口 `Index.vue` 只做 `useTicketDetail` 回填代理，实际表单在子目录组件中。

### 模式 E：公共组件复用型

`MYSQL_HA_APPLY`、`MYSQL_SINGLE_APPLY` 使用此模式。入口直接渲染 `<Apply />`（来自 `common/apply/`）。

### 模式 F：跨页 Wrapper 导航型

适用于多个独立 ticket_type 共享同一概念（如"迁移方式"），但每种方式是独立 ticket_type、各自有独立 `Index.vue` 的场景。**参考实现**：`MYSQL_FIXPOINT_EXIST_CLUSTER`、`MYSQL_DTS_DATA_MIGRATE` / `MYSQL_DTS_DATA_MIGRATE_RENAME`。

核心思路：创建一个 Wrapper 组件（BkAlert + 模式选择 CardCheckbox + slot），各 `Index.vue` 用 `<Wrapper>` 包裹 `<SmartAction>`。完整模板与关键点见 [pattern-f.md](references/pattern-f.md)。

---

## 实现步骤

### 第 0 步：TAPD 需求与原型图获取（新单据必做）

必须先从 TAPD 拉取需求详情与原型图附件，确认单据类型数量（每个独立 ticket_type 独立页面，严禁合并），并与 cypress fixtures 协议样例对齐。完整流程见 [tapd-prototype.md](references/tapd-prototype.md)。

**原型图是产品意图的最权威参考**，BkAlert / CardCheckbox / BkRadioGroup 的文案必须从原型图 HTML 提取原文，禁止自行编造。

### 第 1 步：注册 TicketType 常量

文件：`src/common/const/ticketTypes.ts`

```typescript
export enum TicketTypes {
  MYSQL_YOUR_NEW_TYPE = 'MYSQL_YOUR_NEW_TYPE',
}
```

命名规则：`MYSQL_` 前缀 + 全大写下划线分隔，枚举值必须与后端 `ticket_type` 完全一致。**每个独立的 ticket_type 都必须注册**。

### 第 2 步：创建页面组件

**每个独立的 ticket_type 创建独立的 `Index.vue`**，文件：`src/views/db-manage/mysql/MYSQL_YOUR_NEW_TYPE/Index.vue`，含 MIT 版权头。

template 七元素顺序固定：BkAlert → BatchInput（可选）→ BkForm（`mt-16`）→ EditableTable → 页级表单项（可选）→ TicketPayload → `#action` 提交重置。script setup 骨架（行数据工厂、`defaultData()`、`useTicketDetail` 回填、`useCreateTicket` 提交、批量录入、`defineExpose({ routerBack })`）完整代码见 [page-template.md](references/page-template.md)。

列组件路径与 props 见 [column-components.md](references/column-components.md)；表格含联动列 / 批量录入 / 资源标签列时，回填与解析的坑见 [row-editing-pitfalls.md](references/row-editing-pitfalls.md)。

### 第 2.5 步：实现单据详情页（与原型对齐）

文件：`src/views/ticket-center/common/ticket-detail/components/task-info/com-factory/mysql/YourNewType.vue`

结构：`InfoList`/`InfoItem`（页级信息）+ `TicketInfoTable`/`TicketInfoTableColumn`（行级表格）。取值兜底、资源标签列、折叠展开、行键与编辑入口等完整约定见 [ticket-detail.md](references/ticket-detail.md)。

### 第 3 步：注册路由

文件：`src/views/db-manage/mysql/routes.ts`

```typescript
const { createRouteItem } = createToolboxRoute(DBTypes.MYSQL);

createRouteItem(TicketTypes.MYSQL_YOUR_NEW_TYPE, t('功能名称'), { dbConsole: 'mysql.toolbox.yourFeature' });
```

`createToolboxRoute` 自动设置 `fullscreen: true`、`hideTitle: true`、`ticketType` meta，组件路径自动推导为 `@views/db-manage/mysql/${ticketType}/Index.vue`。**每个独立的 ticket_type 注册独立路由**。

### 第 4 步：注册单据详情页

组件通过 `import.meta.glob` 自动注册，`defineOptions` 的 `name` 必须与 `TicketTypes` 枚举值一致。**每个独立的 ticket_type 创建独立的详情页**。

### 第 5 步：添加工具箱菜单

文件：`src/views/db-manage/mysql/toolbox/toolboxMenuList.ts`

```typescript
{
  dbConsoleValue: 'mysql.toolbox.yourFeature',
  desc: t('功能描述'),
  id: TicketTypes.MYSQL_YOUR_NEW_TYPE,
  name: t('功能名称'),
},
```

**每个独立的 ticket_type 添加独立的菜单项**，完成后同步更新 [ticket-inventory.md](references/ticket-inventory.md)。

---

## 核心 Hook 与工具函数

### useCreateTicket

```typescript
const { loading: isSubmitting, run: createTicketRun } = useCreateTicket<SubmitDetailsType>(
  TicketTypes.MYSQL_YOUR_NEW_TYPE,
);
createTicketRun({ details: { /* ... */ }, ...formData.payload });
```

内置行为：成功后显示消息（含「查看详情」链接）、原地清空可继续提单、重复单据弹确认框、失败按行级错误回填。

**泛型规范**：

- 泛型用**内联的提交 payload 类型**（只描述实际提交的 `details` 结构：`infos[]` + `task` 等），**禁止**写 `useCreateTicket<Mysql.XxxXx>` 复用详情类型——详情类型继承 `DetailBase`，要求 `__ticket_detail__`、`clusters`、`specs` 等仅后端返回的字段，提单不传，类型不匹配报红
- 两个页面提交类型完全相同时，抽到共享模块（如 `MYSQL_DTS_DATA_MIGRATE/common.ts` 导出的 `DtsTicketResourceSpec`），避免 18 行泛型在两处内联重复
- 提交体字段与 `cypress/fixtures/mysql/<TICKET_TYPE>/createTicket.json` 样例对得上

### useTicketDetail

```typescript
useTicketDetail<Mysql.YourNewType>(TicketTypes.MYSQL_YOUR_NEW_TYPE, {
  onSuccess(ticketDetail) { /* 从 details 映射回 formData */ },
});
```

自动从 `route.query.ticketId` 获取单据 ID，仅当 `ticket_type` 匹配时触发回填。

**回填完整度自查**：提单页有的每一列，回填都必须有对应赋值——遗漏即「再次提单缺数据」。高频遗漏：资源标签（`labels` 配合 `label_names` 组装，见 [row-editing-pitfalls.md](references/row-editing-pitfalls.md)）、规格（`spec_id`）。`clusters` 用可选链兜底（`clusters?.[id]?.immute_domain || ''`），旧单据可能未注入。

### createToolboxRoute

```typescript
const { createRouteItem } = createToolboxRoute(DBTypes.MYSQL);
createRouteItem(ticketType, navName, { dbConsole?: string });
```

自动生成 `path`、`name`、`component`（懒加载）、`meta`（含 `ticketType`、`fullscreen: true`、`hideTitle: true`）。

### 类型检查环境说明

`yarn type-check`（`vue-tsc --build`）在当前环境**跑不了**：`tsconfig.json` 的 `ignoreDeprecations: "6.0"` 与本机 TS 5.9.3 不兼容报 TS5103，且默认堆内存不足会 OOM。替代方案：

```powershell
$env:NODE_OPTIONS="--max-old-space-size=8192"; npx vue-tsc -p tsconfig.check.json --noEmit
```

日志中可能存在与本次改动无关的存量报错，以「改动文件相关报错清零」为通过标准，必要时用 `git stash` 对比基线。

---

## 编码约定

### 导入规则

- `vue` / `vue-router` API 已 auto-import，不要显式 import `ref`、`computed`、`watch`、`useRouter`、`useRoute`
- `useI18n`、`useTemplateRef`、`reactive` 必须显式 import
- 路径别名优先：`@services/*`、`@common/const`、`@views/*`、`@hooks`、`@utils`、`@components/*`
- `CardCheckbox` 从 `@components/db-card-checkbox/CardCheckbox.vue` 导入

### 组件命名

- 页面 `defineOptions({ name })` 设为 `TicketTypes.MYSQL_XXX`
- 详情页 `defineOptions({ name: TicketTypes.MYSQL_XXX, inheritAttrs: false })`
- 目录名 kebab-case，入口固定 `Index.vue`，仅本组件使用的子文件放同级 `components/`

### 间距约定

- `BkAlert` 加 `class="mb-20"`
- `BatchInput` 下方紧跟的 `BkForm` 或 `EditableTable` 必须加 `class="mt-16"`
- `EditableTable` 加 `class="mb-20"`
- `CardCheckbox` 多个卡片之间用 `class="ml-8"` 间隔
- 模式 F 的 Wrapper `BkForm` 加 `class="mb-24 toolbox-form"`

### 列禁用约定

- **未选择源集群时，其他所有依赖源集群的列应被禁用**，提示「请先选择源集群」
- `DbNameColumn` / `TableNameColumn`：设置 `check-not-exist` 时，组件内置 `disabledMethod` 在 `clusterId` 为空时自动禁用
- `TargetClusterColumn`：通过 `disabledMethod` 在源集群 `id` 为空时禁用
- 自定义列组件通过 `EditableColumn` 的 `:disabled-method` prop 实现条件禁用

### 库表存在校验约定

- **源 DB / 源表列应校验在源集群中是否存在**：传 `check-not-exist` prop，DB/表在集群中不存在时校验失败
- **忽略 DB / 忽略表列不需要校验存在性**
- 通配符 `*` `%` `?` 不参与存在校验

### 数据模式

- `formData` 用 `reactive`，不用 `ref`
- `tableRef` 用 `useTemplateRef('tableRef')`
- `tableKey` 用 `ref(random())`，批量录入清空时 `tableKey.value = random()` 强制重渲染
- 行数据通过 `createTableRow(data?)` 工厂创建
- 表单默认值通过 `defaultData()` 工厂创建

### 提交数据映射

- 表格行字段名用驼峰（前端），提交时转为下划线（后端）
- `cluster.id` → `cluster_id`
- `ip` + `port` → `instance_address: '${ip}:${port}'`
- `ip_source` 固定为 `'resource_pool'`（资源池场景）
- 对象数组字段（`do_tables`/`ignore_tables` 等）：UI 层保持字符串列表编辑，提交时 `flatMap` 组装（`db 列表 × table 列表` 笛卡尔积），回填时 `.map((x) => x.table)` 还原
- 单选枚举（冲突处理等）：radio 直接绑后端枚举值，不造前端枚举、不写双向映射函数
- `resource_spec` 双字段：`labels` 传标签 id 字符串列表（`String(label.id)`），`label_names` 传标签名列表（`label.value`），后端回显时按序对应

### 国际化

所有文案走 `t()`，语言包在 `src/locales/`。`routes.ts` 和 `toolboxMenuList.ts` 中的 `t()` 从 `@locales/index` 导入。

### 版权头

新建 `.vue` / `.ts` 文件带 MIT 版权头，照抄同目录已有文件的头部。

---

## 实现检查清单

- [ ] **TAPD 需求已拉取**：`stories_get` 获取需求详情，`description` 字段已分析
- [ ] **原型图已预览**：下载 HTML 并 `web_preview` 预览，UI 结构已分析
- [ ] **单据类型数量已确认**：需求涉及的每个独立 `ticket_type` 都注册了独立枚举值和独立页面
- [ ] **每个 ticket_type 有独立 `Index.vue`**：不共用页面
- [ ] **TicketType 常量已注册**：在 `ticketTypes.ts` 中添加，与后端一致
- [ ] **页面组件已创建**：含 MIT 版权头，`defineOptions` name 设为 `TicketTypes` 枚举值
- [ ] **BkAlert title 文案从原型图获取**：放在 `SmartAction` 内第一个元素位置（模式 F 放在 Wrapper 内第一个元素）
- [ ] **模式选择正确**：同一 ticket_type 内子类型用 `CardCheckbox`（模式 C）；多 ticket_type 跨页切换用 Wrapper + `CardCheckbox` + `router.push`（模式 F），参考 `MYSQL_FIXPOINT_EXIST_CLUSTER`
- [ ] **CardCheckbox title/desc 文案从原型图获取**：禁止自行编造
- [ ] **页级单选表单项**：用 `BkRadioGroup` + `BkRadio`，radio 值直接绑后端枚举（不写双向映射函数）
- [ ] **协议样例已核对**：提交体与 `cypress/fixtures/mysql/<TICKET_TYPE>/createTicket.json` 结构一致，模型类型与 `ticketDetail.json` 一致
- [ ] **`useCreateTicket` 泛型是内联提交类型**：禁止复用 `Mysql.XxxXx` 详情类型（`__ticket_detail__`/`clusters` 报红）
- [ ] **回填完整度**：提单页每一列在 `useTicketDetail` 回填里都有对应赋值（重点自查资源标签 `labels`+`label_names` 组装、规格 `spec_id`）
- [ ] **`clusters`/`specs` 可选链兜底**：`details.clusters?.[id]?.immute_domain || '--'`、`details.specs?.[spec_id]?.name || ''`，禁止直接索引
- [ ] **批量录入示例无空白符歧义**：示例文本不含空格分隔的多词值（映射对用冒号、多条用逗号）
- [ ] **批量录入解析齐全**：`batchInputConfig` 覆盖所有列（含规格 `spec_name`、标签 `labels`），解析后字段类型与 RowData 匹配（`{value}` 数组补断言）
- [ ] **详情页空值统一 `--`**：空列表、缺失域名均显示 `--`；资源标签空时显示绿色「通用无标签」
- [ ] **详情页规格名取顶层 `specs`**：`details.specs?.[spec_id]?.name`，不在 `resource_spec.master.spec_name` 取（实际不返回该字段）
- [ ] **联动清空有归属标记**：随集群变化的列（如库映射）用 `xxx_domain` 标记防误清，回填/批量录入/侧滑确认三处同步写入
- [ ] **`BatchInput` 下方加 `mt-16`**：紧跟的 `BkForm` 或 `EditableTable` 必须加
- [ ] **非首列集群选择用 `TargetClusterColumn`**：参考 `MYSQL_FIXPOINT_EXIST_CLUSTER/components/target-cluster-column/Index.vue`
- [ ] **库表存在校验**：源 DB / 源表列传 `check-not-exist`
- [ ] **列禁用**：未选源集群时，依赖源集群的列被禁用提示「请先选择源集群」
- [ ] **路由已注册**：`routes.ts` 中 `createRouteItem`，每个 ticket_type 独立路由
- [ ] **单据详情页已创建**：`com-factory/mysql/YourType.vue`，`name` 与 `TicketTypes` 一致
- [ ] **`OperationColumn` 已包含**：行操作列必须存在
- [ ] **`TicketPayload` 已包含**：备注表单项必须存在
- [ ] **`useCreateTicket` 提交**：`details` 与后端 API 协议一致
- [ ] **`useTicketDetail` 回填**：编辑/克隆场景的表单回填已实现
- [ ] **`defineExpose({ routerBack })`**：返回 `MysqlToolboxIndex`
- [ ] **工具箱菜单已添加**：`toolboxMenuList.ts` 中注册，含 `desc` 描述
- [ ] **`ticket-inventory.md` 已更新**：新单据的模式与特殊组件已登记
- [ ] **批量录入配置**：`batchInputConfig` 的 `key` 与后端字段名一致
- [ ] **重置功能**：`handleReset` 调用 `defaultData()` 重置表单
- [ ] **国际化**：所有文案走 `t()`，无硬编码中文
- [ ] **类型安全**：`useCreateTicket<T>` 和 `useTicketDetail<T>` 泛型已正确指定
- [ ] **eslint 通过**：`npx eslint <改动文件> --fix` 通过
