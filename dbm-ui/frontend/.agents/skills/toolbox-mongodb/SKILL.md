---
name: toolbox-mongodb
description: >-
  mongodb 工具箱提单页开发规范：新增或修改 src/views/db-manage/mongodb/{TICKET_TYPE}/ 下的提单页、
  对应单据详情页（ticket-center com-factory）、工具箱菜单与路由时使用。
  覆盖页面骨架、可编辑表格数据层、批量编辑/导入、模式差异的动态组件拆分（v-if 差异列 / 多模式子表格）、
  useCreateTicket 提单与 useTicketDetail 回显、列组件复用与编写、四件套注册检查清单与常见坑。
---

# mongodb 工具箱提单页 Coding Skill

一个工具箱功能 = 一个「提单页」+ 一条「路由」+ 一项「菜单」+ 一个「单据详情页」，缺一不可。
参考实现：`MONGODB_BACKUP`（库表备份，最典型）、`MONGODB_DATA_EXPORT`（带自定义校验）、
`MONGODB_SCALE_UPDOWN`（带规格/资源池列）、`MONGODB_EXEC_SCRIPT_APPLY`（非表格型）、
`MONGODB_INSTANCE_RELOAD`（多模式动态表格组件，模式拆分的标准范式）。

## 一、四件套注册（缺一不可）

| 步骤 | 文件 | 要点 |
| --- | --- | --- |
| 1. TicketTypes 枚举 | `src/common/const/ticketTypes.ts` | `MONGODB_XXX = 'MONGODB_XXX'`，值必须与后端 `ticket_type` 完全一致 |
| 2. 路由 | `src/views/db-manage/mongodb/routes.ts` | `createToolboxRoute(DBTypes.MONGODB).createRouteItem(TicketTypes.MONGODB_XXX, t('中文名'))`。name/path 自动取枚举值，meta 自动带 `fullscreen: true` + `ticketType`，**不要手写重复** |
| 3. 菜单 | `mongodb/toolbox/toolboxMenuList.ts` | `id` 用 TicketTypes；一个入口绑定多个单据类型时用 `bind: [A, B]` 数组（如整机替换、迁移、扩容 Shard 节点） |
| 4. 详情页 | `src/views/ticket-center/common/ticket-detail/components/task-info/com-factory/mongodb/{TicketType}.vue` | `defineOptions.name` 必须等于 TicketTypes 枚举值（com-factory 按名字动态匹配），加 `inheritAttrs: false` |

## 二、提单页骨架（可编辑表格型）

固定顺序：SmartAction → 根 div → BkAlert → BatchInput → DbForm → EditableTable → 表格外单项 → TicketPayload。

```html
<template>
  <SmartAction>
    <div class="mongo-data-export-page db-toolbox">
      <BkAlert class="mb-16" theme="info" :title="t('数据导出：……')" />
      <BatchInput :config="batchInputConfig" @change="handleBatchInput" />
      <DbForm ref="form" class="toolbox-form mt-16" form-type="vertical" :model="formData" style="margin-top: 16px">
        <EditableTable :key="tableKey" ref="editableTable" class="mt-16 mb-16" :model="formData.tableData">
          <EditableRow v-for="(item, index) in formData.tableData" :key="index">
            <ClusterColumn v-model="item.cluster" :selected="selected" @batch-edit="handleClusterBatchEdit" />
            <!-- 只读展示列：EditableColumn readonly + EditableBlock -->
            <!-- 业务列：复用/自建列组件，@batch-edit 上抛 -->
            <OperationColumn :create-row-method="createRowData" :table-data="formData.tableData" />
          </EditableRow>
        </EditableTable>
        <!-- 表格外单项：BkFormItem property + required -->
        <TicketPayload v-model="formData.payload" />
      </DbForm>
    </div>
    <template #action>
      <BkButton class="w-88" :loading="isSubmitting" theme="primary" @click="handleSubmit">{{ t('提交') }}</BkButton>
      <DbResetButton class="ml-8" :confirm-handler="handleReset" :disabled="isSubmitting" />
    </template>
  </SmartAction>
</template>
```

- `SmartAction`、`DbForm`、`EditableTable/Row/Column/Input/Textarea/Block…`、`OperationColumn`、`DbResetButton` 全局已注册（见 `src/common/importComps.ts`），**不要 import**
- `#action` 必须是 `SmartAction` 的具名插槽（提交 + DbResetButton 二件套）
- 根类名 `{页面语义}-page`，页面级 padding 用它承载；批量导入组件 `BatchInput` 的 `config`：`{ case: 示例文本, key: 字段名, label: t(表头) }[]`

## 三、数据层三件套（与表格校验强耦合）

```ts
interface IDataRow { cluster: {...}; db_patterns: string[]; /* ... */ }

const createRowData = (values = {} as Partial<IDataRow>) => ({
  cluster: Object.assign({ id: 0, master_domain: '' /* ... */ }, values.cluster),
  db_patterns: values.db_patterns || [],
  // ...
});

const createDefaultFormData = () => ({
  format: 'json' as 'json' | 'bson',
  payload: createTicketPayload(),
  tableData: [createRowData()],
});
```

- `formData = reactive(createDefaultFormData())`（reactive，不是 ref；重置用 `Object.assign(formData, createDefaultFormData())`）
- **每一行必须由 `createRowData()` 生成**，且每个字段都要有默认值——行内字段缺默认值会导致 EditableTable 校验路径取不到值
- 复杂嵌套行用 `values: DeepPartial<IDataRow>`（见 `MONGODB_SCALE_UPDOWN`）
- `createTicketPayload` 从 `@views/db-manage/common/toolbox-field/form-item/ticket-payload/Index.vue` 具名导入，回显时传 ticketDetail

## 四、选中态与批量逻辑（四段固定模式）

```ts
const selected = computed(() => formData.tableData.filter((item) => item.cluster.id).map((item) => item.cluster));
const selectedMap = computed(() => Object.fromEntries(selected.value.map((cur) => [cur.master_domain, true])));
```

1. **集群批量选择** `handleClusterBatchEdit(clusterList: MongodbModel[])`：跳过 `selectedMap` 已存在的域名 → 追加新行 → `formData.tableData = [...(selected.value.length ? formData.tableData : []), ...newList]`
2. **批量导入** `handleBatchInput(data, isClear)`：字符串字段 `split(',')` 转数组；`isClear` 时 `tableKey.value = random()` 强刷表格再整体替换，否则按 1 的规则追加
3. **列级批量编辑** `handleDbTableBatchEdit(value, field)`：遍历 `formData.tableData`，`Object.assign(item, { [field]: value })`（field 名由列组件 batch-edit 事件透传）
4. **重置** `handleReset`：`Object.assign(formData, createDefaultFormData())`；子组件有内部状态时用 `resetFormKey` 自增重挂载

`tableKey = ref(random())`：EditableTable 的强刷 key，**凡整体替换 tableData 必须同时刷 key**。

## 五、提单与回显（两个 hook，页面零请求）

```ts
useTicketDetail<Mongodb.DataExport>(TicketTypes.MONGODB_DATA_EXPORT, {
  onSuccess(ticketDetail) {
    const { details } = ticketDetail;
    Object.assign(formData, {
      payload: createTicketPayload(ticketDetail),
      tableData: infos.map((item) => createRowData({ /* 用 details.infos 逐行还原 */ })),
    });
  },
});
```

- `useTicketDetail<T>`：URL 带 `ticketId` 时拉详情回显（克隆单/失败重提）。`T` 用 `@services/model/ticket/ticket` 里 `Mongodb` namespace 的 details 类型；onSuccess 内用 `createRowData()` 组装回显行，保证字段完整
- `useCreateTicket<DetailsType>(TicketTypes.XXX)`：`run({ details: {...}, ...formData.payload })`；`loading` 即 `isSubmitting`。**重复单检测（code 8704005）hook 内已弹 InfoBox 处理，页面不要重复处理**
- 提交前双校验：`await formRef.value!.validate()` 然后 `editableTableRef.value!.validate().then(() => createTicketRun(...))`
- ref 获取一律 `useTemplateRef('form')`，模板 ref 名与组件 ref 属性一致
- **`details` 协议是三方契约**：字段名必须同时满足后端、回显逻辑、详情页展示。先看同 DB 类型最近提单页的 details 形状再定结构

## 六、列组件复用与编写

优先级：全局注册列（`OperationColumn`）→ DB 公共列（`@views/db-manage/common/toolbox-field/column/`：available-resource、resource-tag、spec…）→ mongodb 专属列（`@views/db-manage/mongodb/common/toolbox-field/`：cluster-column、db-name-column、table-name-column、host-column、instance-column、shard-column、cutoff、addShardNodes…）→ 页面私有列放 `{TICKET_TYPE}/components/`。

没有合适的再新建，参照 `mongodb/common/toolbox-field/cluster-column/Index.vue` 的模式：

```html
<EditableColumn ref="editableColumnRef" :append-rules="rules" :field="field" fixed="left"
  :label="label || t('目标集群')" :loading="isLoading" :min-width="350" required>
  <template #headAppend>
    <span v-bk-tooltips="t('批量选择')" class="batch-select-button" @click="handleShowClusterSelector">
      <DbIcon type="batch-host-select" />
    </span>
  </template>
  <EditableInput v-model="modelValue.master_domain" :placeholder="t('请输入或选择集群')" @change="handleChange" />
  <ClusterSelector v-model:is-show="isShowClusterSelector" ... @change="handelClusterChange" />
</EditableColumn>
```

- 取值组件包在 `EditableColumn` 内，校验走 `append-rules`（validator 返回 `t()` 文案或 true）
- **`EditableColumn` 内只能使用 `Editable` 系列组件**（`EditableInput`/`EditableSelect`/`EditableTextarea`/`EditableBlock`/`EditableTagInput` 等），不能用普通表单组件（`DbSelect`/`BkInput` 等）——否则表格编辑态、校验联动与禁用态不生效；下拉多选用 `EditableSelect` 的 `:list` + `multiple`，选项依赖行数据、列整体禁用走 `EditableColumn` 的 `disabled-method`（范式参照 `MONGODB_REDUCE_MONGOS/components/IpColumn.vue`）
- 三条经典规则：域名格式（`@common/regex` 的 `domainRegex`）、重复（基于 `props.selected` 计数）、存在性（手动输入后 `useRequest(filterClusters)` 按 `exact_domain` 查询回填整行模型，查不到主动触发 `validate`）
- 数据流用 `defineModel`；列组件不感知页面业务，差异化通过 props（`field`/`label`/`setCurrentSpecIdMethod`）注入
- 批量入口在 `#headAppend`，选中结果通过 `emits('batch-edit', list)` 上抛

## 七、模式差异：协议与 UI 列随模式变化（动态组件）

当页面存在类似 `reduce_mode`、`target_select_mode` 的模式字段，导致**可编辑列与提交协议按模式各不相同**时，
**必须每种模式拆成独立的表格子组件，页面用 `<Component :is>` 动态挂载**，
禁止把所有模式的列堆在同一张 EditableTable 里用 `v-if/v-else` 分支切换——模式分支散落在模板和数据层会造成
行模型冗余（同一行同时携带多种模式的字段）、校验规则互相纠缠、新增模式时到处加分支。
参照 `MONGODB_INSTANCE_RELOAD`（按集群/按主机/按实例三种模式）的结构：

```ts
import ClusterModeTable from './components/cluster/Index.vue';
import MachineModeTable from './components/host/Index.vue';
import InstanceModeTable from './components/instance/Index.vue';

const modeComponentMap = {
  cluster: ClusterModeTable,
  instance: InstanceModeTable,
  machine: MachineModeTable,
};
const modeComponent = computed(() => modeComponentMap[formData.targetSelectMode]);
```

```html
<!-- 动态模式表格 -->
<Component :is="modeComponent" ref="currentTableRef" />
```

   子组件约定（三个固定对外接口，页面不感知模式内部细节）：
   - 各自维护本模式的 `tableData` 与 EditableTable
   - `defineExpose({ validate, getValue })`：`validate()` 走本模式表格校验，`getValue()` 返回本模式的 `details.infos`
   - 页面提交时 `currentTableRef.value!.validate().then(() => createTicketRun({ details: { ...公共字段, infos: currentTableRef.value!.getValue() }, ...formData.payload }))`

   页面层只保留：模式选择控件（CardCheckbox / BkRadioGroup type="card"）、模式无关的公共字段、TicketPayload、提交/重置。
   回显数据**不通过 props 传 `ticketDetails`**：页面与各模式子组件各自调用 `useTicketDetail`（内部秒级缓存，不会重复请求），
   页面回调只还原模式字段与 payload，子组件在回调里 `filter` 出本模式的 `infos` 组装行数据。
   ref 类型用联合标注：`useTemplateRef<ComponentExposed<typeof A | typeof B>>('currentTableRef')`。

判定口诀：**协议或可编辑列随模式不同 → 一律拆模式子组件，模式之间零交叉、页面零分支。**

## 八、单据详情页

参照 `com-factory/mongodb/DataExport.vue`：

- `defineOptions({ name: TicketTypes.MONGODB_DATA_EXPORT, inheritAttrs: false })`，name 匹配是硬约束
- `Props: { ticketDetails: TicketModel<Mongodb.DataExport> }`，数据只从 `ticketDetails.details` 读
- 多行用 `TicketInfoTable` + `TicketInfoTableColumn`（全局注册）：数组字段用 `TagBlock` 渲染，需要复制整列的列加 `get-copy-value`
- **按详情结构选形态，不硬套**（详情页是只读展示，以下均为存量范式）：
  - 纯表格型（无表单项）：`TicketInfoTable` 直接作模板根，多数 mongodb 组件如此（`DataExport`/`ReduceMongos`/`ReduceShardNodes`）
  - 带表单项（模式、开关、布尔等）：`InfoList`（`import InfoList, { Item as InfoItem } from '../components/info-list/Index.vue'`）在前逐项展示，表格在后，顺序与提单页一致（`InstanceReload`/`ReduceShard`/`redis/ProxyScaleDown`）
  - 模式型：`InfoList` 展示模式字段后，用 `v-if` 按模式切换多张 `TicketInfoTable`（`InstanceReload` 按集群/主机/实例三张表）——详情允许 v-if，不受提单页动态组件规则约束
  - 补充说明项用 `InfoList`/`InfoItem`；存量 `ticket-details-list` div 写法是旧范式，新代码不要用
- **列数据必须来自 details 协议字段，不得臆造字段名或自造合并叫法**：允许聚合展示（如 `ReduceMongos` 把 nodes 拼成 IP 列表）与只读演算（如 `ReduceShardNodes` 的「缩容至」= 当前 − 缩容数、`ReduceShard` 的最终分片数），但每列都能说清来自哪个协议字段或由哪些字段演算；建议先 map 成展示行再绑定 `col-key`（`ReduceShardNodes`/`ReduceMongos` 范式）；`clusters`/`instances` 映射读取用 `?.` 防御；**详情展示字段与提单页可编辑字段一一对应，新增提单字段时两处同改**
- **跨列演算校验写在「演算结果列」（如最终分片数等只读列）的 `append-rules` 里**：`field` 取演算字段名（行模型可不声明该字段），validator 签名 `(_value, { rowData }: { rowData: IDataRow })`，判定基于 `rowData` 的其他字段演算（`rowData` 即当前行模型，与 `MONGODB_SHARD_CUTOFF`、`TENDBCLUSTER_SPIDER_MNT_APPLY` 等既有列一致），不要写在触发输入的列上、更不要放到提交函数或子组件 `validate()` 里用 `Message` 拦截

## 九、硬性约定与常见坑

- `ref`/`computed`/`watch`/`useTemplateRef`/`useRoute` 均 auto-import，不要 `import { ref } from 'vue'`
- 所有文案 `t()`；路由名、列 label、校验 message、placeholder 全部走语言包
- `<script setup>` 与 `<style>` 内容整体缩进一级；新建文件带 MIT 版权头（照抄同目录文件）
- less 写完整嵌套类名（禁 `&-name`）；个别需深层覆盖 bkui 内部样式的页面用非 scoped `<style lang="less">`（如 `MONGODB_EXEC_SCRIPT_APPLY` 覆盖 `.bk-form-label`）
- 类型上不用 `any`（`handleBatchInput` 的 `Record<string, any>` 是存量，新代码可用 `Record<string, string>` 收紧）
- 列组件内**不要在数据加载回调（`onSuccess` 等）里手动触发 `validate()`**——刚选完集群/还没录入时会把必填列立即标红；校验统一交给 `EditableTable.validate()` 的提交时机
- **`Editable` 系列组件内部会 watch 自身 modelValue 触发所在列的 `validate('change')`**。注意 `EditableSelect` 泛型为 `string[] | number[] | string | number`：单选时是原始值（同值赋值不触发 watch），**多选时是数组引用——即使内容相同，新引用赋值也会触发校验**。框架层已在 `editable-table/edit/Select.vue`、`TagInput.vue` 加守卫：`// 对于引用类型，实际值变化才校验`（`_.isEqual(newValue, oldValue)` 通过才触发）。因此业务侧联动清空、回显过滤直接 `v-model` 直绑 + 正常赋值即可，不要绕开 v-model 改用 `:model-value` + `@change` 手动同步，也不用在业务侧加赋值守卫
- 自检清单：枚举 → 路由 → 菜单 → 详情页；回显能逐行还原；重置能清干净（含 tableKey）；`details` 三方一致；`yarn type-check` + `npx eslint <改动文件> --fix`
