# 页面模式与模板

## 最重要的一条：模式差异必须拆动态组件

**页面存在 `reduce_mode`、`target_select_mode` 这类模式字段，且可编辑列或提交协议随模式不同时，每种模式必须拆成
独立的表格子组件，页面用 `<Component :is>` 动态挂载。禁止把所有模式的列堆在一张 `EditableTable` 里用 `v-if` 切换。**

理由不是风格：模式分支散落在模板和数据层会造成行模型冗余（同一行同时携带多种模式的字段）、校验规则互相纠缠、
新增模式时要在十几处加分支。

参考实现 `MONGODB_INSTANCE_RELOAD`（按集群 / 主机 / 实例三种模式）：

```ts
const modeComponentMap = { cluster: ClusterModeTable, instance: InstanceModeTable, machine: MachineModeTable };
const modeComponent = computed(() => modeComponentMap[formData.targetSelectMode]);
```

子组件对外只有三个固定接口，页面不感知模式内部细节：各自维护本模式的 `tableData` 与 `EditableTable`；
`defineExpose({ validate, getValue })`，`getValue()` 返回本模式的 `details.infos`；页面提交时
`currentTableRef.value!.validate().then(() => createTicketRun({ details: { ...公共字段, infos: currentTableRef.value!.getValue() }, ...formData.payload }))`。

页面层只留模式选择控件、模式无关的公共字段、`TicketPayload`、提交与重置。

**回显不通过 props 传 `ticketDetails`**：页面与各子组件各自调 `useTicketDetail`（内部有秒级缓存，不会重复请求），
页面回调只还原模式字段与 payload，子组件在自己的回调里 `filter` 出本模式的 `infos`。ref 类型用联合标注
`useTemplateRef<ComponentExposed<typeof A | typeof B>>('currentTableRef')`。

**详情页不受这条约束**，那里用 `v-if` 切多张 `TicketInfoTable` 是既有范式——只读展示没有行模型和校验纠缠。

## 六种模式

| 模式 | 什么时候用 | 参考 |
| --- | --- | --- |
| A 标准可编辑表格 | 八成的工具箱 | `MYSQL_ADD_SLAVE`、`MONGODB_BACKUP` |
| B 多步骤向导 | 路由带 `{ params: '/:step?' }`，按 `route.params.step` 渲染 `steps/` | `MYSQL_IMPORT_SQLFILE` |
| C 子类型选择 | **同一个 `ticket_type` 内部**的子类型 | `MYSQL_ROLLBACK`、`MYSQL_FLASHBACK` |
| D Wrapper + 子组件 | 入口只做回填代理，表单在子目录 | `MYSQL_HA_TRUNCATE_DATA` |
| E 公共组件复用 | **服务申请页，不是工具箱**。目录碰巧也叫 `{TICKET_TYPE}`，路由在 `service-apply/routes.ts` 用 `createApplyRoute` | `MYSQL_HA_APPLY`（`mysql/common/apply/Index.vue`） |
| F 跨页 Wrapper 导航 | 多个**独立 `ticket_type`** 共享同一概念 | `MYSQL_FIXPOINT_EXIST_CLUSTER`、`MYSQL_DTS_DATA_MIGRATE` |

模式 C 定义的是**模式选择控件长什么样**，不是列怎么组织——列随子类型变化时照样拆动态组件。
**不同模式对应不同 `ticket_type` 时用 F，不能用 C。**

### 模式 F 的做法

建一个 Wrapper 装两个页面共享的 `BkAlert` + 模式选择 + `<slot />`，各 `Index.vue` 用 `<Wrapper>` 包住自己的
`<SmartAction>`：

```vue
<BkForm class="mb-24 toolbox-form" form-type="vertical" :model="formData">
  <BkFormItem :label="t('迁移方式')" required>
    <CardCheckbox v-model="formData.migrateMethod" :title="t('同名迁移')" :desc="t('...')"
      icon="bk-dbm-icon db-icon-copy" true-value="MYSQL_DTS_DATA_MIGRATE" />
    <CardCheckbox v-model="formData.migrateMethod" class="ml-8" ... true-value="MYSQL_DTS_DATA_MIGRATE_RENAME" />
  </BkFormItem>
</BkForm>
<slot />
```

- `CardCheckbox` 来自 `@views/db-manage/common/db-card-checkbox/CardCheckbox.vue`，`true-value` 直接就是对应的
  `ticket_type`，多个卡片共享一个 `v-model`
- 当前页靠 `route.meta.ticketType` 判断，`watch` 到变化时 `router.push` 到对方路由
- Wrapper 已提供 `BkForm`，各 `Index.vue` 内不再包一层
- 两个页面的提交类型完全相同时抽到 `{TICKET_TYPE}/common.ts` 由另一侧导入，不要把十几行泛型内联两遍

## 模式 A 的 template

节点顺序固定，写之前先确认每一项在不在。间距类名取自存量主流写法（`mb-20` 64 处、`toolbox-form` 65 处、
`w-88` / `ml-8` 各 100+ 处）：

```vue
<template>
  <SmartAction>
    <div class="your-feature-page db-toolbox">
      <!-- 1. 顶部提示，文案从原型图提取 -->
      <BkAlert class="mb-20" closable theme="info" :title="t('业务说明文案')" />
      <!-- 2. 批量录入（可选） -->
      <BatchInput :config="batchInputConfig" @change="handleBatchInput" />
      <!-- 3. 表单容器：DbForm + toolbox-form；紧跟 BatchInput 时加 mt-16 -->
      <DbForm ref="form" class="toolbox-form mt-16" form-type="vertical" :model="formData">
        <!-- 4. 可编辑表格 -->
        <EditableTable :key="tableKey" ref="editableTable" class="mb-20" :model="formData.tableData">
          <EditableRow v-for="(item, index) in formData.tableData" :key="index">
            <ClusterColumn v-model="item.cluster" :selected="selected" @batch-edit="handleClusterBatchEdit" />
            <!-- 非首列的目标集群用 TargetClusterColumn，不要复用 ClusterColumn -->
            <TargetClusterColumn v-model="item.targetCluster" :cluster="item.cluster" :selected="selectedTargets" />
            <!-- 行操作列：必须，固定右侧 -->
            <OperationColumn v-model:table-data="formData.tableData" :create-row-method="createRowData" />
          </EditableRow>
        </EditableTable>
        <!-- 5. 表格外的页级表单项（可选） -->
        <BkFormItem :label="t('数据冲突处理')" required>
          <BkRadioGroup v-model="formData.onDuplicate">
            <BkRadio label="replace">{{ t('覆盖') }}</BkRadio>
          </BkRadioGroup>
        </BkFormItem>
        <!-- 6. 单据备注：必须 -->
        <TicketPayload v-model="formData.payload" />
      </DbForm>
    </div>
    <!-- 7. 固定底栏，必须在 SmartAction 的 #action 插槽内 -->
    <template #action>
      <BkButton class="w-88" :loading="isSubmitting" theme="primary" @click="handleSubmit">
        {{ t('提交') }}
      </BkButton>
      <DbResetButton class="ml-8" :confirm-handler="handleReset" :disabled="isSubmitting" />
    </template>
  </SmartAction>
</template>
```

- 根 div 类名 `{页面语义}-page db-toolbox`，页面级 padding 由它承载
- **标准提单页没有「取消」按钮**，只有提交 + 重置。重置用 `DbResetButton`，它自带二次确认气泡；提交中提交按钮
  `loading`、重置按钮 `disabled`
- `BatchInput` 下方紧跟的元素**必须加 `mt-16`**，否则贴在一起
- 页级单选用 `BkRadioGroup` + `BkRadio`（不是 `BkRadioButton`，除非原型明确要求按钮组）
- 必填校验文案由列组件按 `{label}不能为空` 自动生成，不要每列手写
- 间距细节跟随同 DB 存量（mysql 多 `mb-20`，mongodb 多 `mb-16`），不跨 DB 强行统一

## 模式 A 的 script setup

```typescript
interface IDataRow {
  cluster: { id: number; master_domain: string };
  sourceDbList: string[];
}

const { t } = useI18n();
const router = useRouter();
const formRef = useTemplateRef('form');
const tableRef = useTemplateRef('editableTable');
const tableKey = ref(random());

// 行工厂：每个字段都要有默认值
const createRowData = (values = {} as Partial<IDataRow>) => ({
  cluster: Object.assign({ id: 0, master_domain: '' }, values.cluster),
  sourceDbList: values.sourceDbList || [],
});

// 表单默认值工厂，重置复用
const createDefaultFormData = () => ({
  onDuplicate: 'replace',
  payload: createTicketPayload(),
  tableData: [createRowData()],
});

const formData = reactive(createDefaultFormData());
const selected = computed(() => formData.tableData.filter((item) => item.cluster.id).map((item) => item.cluster));

useTicketDetail<Mysql.YourNewType>(TicketTypes.MYSQL_YOUR_NEW_TYPE, {
  onSuccess(ticketDetail) {
    const { details } = ticketDetail;
    const tableData = details.infos.map((item) =>
      createRowData({
        // clusters 可能未注入，必须可选链兜底
        cluster: { id: item.cluster_id, master_domain: details.clusters?.[item.cluster_id]?.immute_domain || '' },
        sourceDbList: item.source_db_list,
      }),
    );
    Object.assign(formData, {
      onDuplicate: details.on_duplicate,
      payload: createTicketPayload(ticketDetail),
      tableData: tableData.length ? tableData : [createRowData()],
    });
    tableKey.value = random();
  },
});

// 泛型是内联的提交类型，不是 Mysql.YourNewType
const { loading: isSubmitting, run: createTicketRun } = useCreateTicket<{
  infos: { cluster_id: number; source_db_list: string[] }[];
  on_duplicate: string;
}>(TicketTypes.MYSQL_YOUR_NEW_TYPE);

const handleSubmit = async () => {
  await formRef.value!.validate();
  await tableRef.value!.validate();
  createTicketRun({
    details: {
      infos: formData.tableData.map((item) => ({
        cluster_id: item.cluster.id,
        source_db_list: item.sourceDbList,
      })),
      on_duplicate: formData.onDuplicate,
    },
    ...formData.payload,
  });
};

const handleReset = () => {
  Object.assign(formData, createDefaultFormData());
  tableKey.value = random();
};

defineExpose({
  routerBack() {
    router.push({ name: 'MysqlToolboxIndex' }); // 路由名各 DB 不同，见 db-profiles.md
  },
});
```

`createTicketPayload` 从 `@views/db-manage/common/toolbox-field/form-item/ticket-payload/Index.vue` 具名导入。
工厂函数命名跟随同 DB 存量（mysql 多为 `createTableRow` / `defaultData`），不跨 DB 强行统一。

## 提交数据映射

字段映射规则（驼峰转下划线、`ip_source`、radio 直绑后端枚举、资源标签双字段）见 `dbm-ticket-developer` 的
`references/submit-and-backfill.md`「提交体字段映射」。后端是 `{ db, table }[]` 对象数组协议时在边界做转换，
见 [editable-table.md](editable-table.md)。
