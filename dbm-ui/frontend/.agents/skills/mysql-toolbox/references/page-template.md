# 模式 A 页面模板（Index.vue 完整骨架）

文件：`src/views/db-manage/mysql/MYSQL_YOUR_NEW_TYPE/Index.vue`，含 MIT 版权头。**每个独立的 ticket_type 创建独立的 `Index.vue`**。

## template 结构（七元素顺序固定）

```vue
<!-- MIT 版权头 -->
<template>
  <SmartAction>
    <!-- 1. 顶部提示条（SmartAction 内第一个元素，文案从原型图获取） -->
    <BkAlert class="mb-20" closable :title="t('业务说明文案')" />
    <!-- 2. 批量录入（可选） -->
    <BatchInput :config="batchInputConfig" @change="handleBatchInput" />
    <!-- 3. 表单（BatchInput 下方必须加 mt-16） -->
    <BkForm class="mt-16 mb-20" form-type="vertical" :model="formData">
      <!-- 4. 可编辑表格 -->
      <EditableTable :key="tableKey" ref="tableRef" class="mb-20" :model="formData.tableData">
        <EditableRow v-for="(item, index) in formData.tableData" :key="index">
          <!-- 首列：源集群 -->
          <ClusterColumn v-model="item.cluster" :selected="selected" @batch-edit="handleBatchEdit" />
          <!-- 非首列目标集群：用 TargetClusterColumn -->
          <TargetClusterColumn v-model="item.targetCluster" :cluster="item.cluster" :selected="selectedTargetClusters" />
          <!-- 操作列（必须） -->
          <OperationColumn v-model:table-data="formData.tableData" :create-row-method="createTableRow" />
        </EditableRow>
      </EditableTable>
      <!-- 5. 页级表单项（可选） -->
      <BkFormItem :label="t('数据冲突处理')" required>
        <BkRadioGroup v-model="formData.conflictHandle">...</BkRadioGroup>
      </BkFormItem>
      <!-- 6. 单据负载（必须） -->
      <TicketPayload v-model="formData.payload" />
    </BkForm>
    <!-- 7. 底部操作栏 -->
    <template #action>
      <BkButton class="mr-8 w-88" :loading="isSubmitting" theme="primary" @click="handleSubmit">{{ t('提交') }}</BkButton>
      <DbResetButton class="ml-8" :confirm-handler="handleReset" :disabled="isSubmitting" />
    </template>
  </SmartAction>
</template>
```

## script setup 核心结构

```typescript
defineOptions({ name: TicketTypes.MYSQL_YOUR_NEW_TYPE });

// --- 导入 ---
import { reactive, useTemplateRef } from 'vue';
import { useI18n } from 'vue-i18n';
import TendbhaModel from '@services/model/mysql/tendbha';
import type { Mysql } from '@services/model/ticket/ticket';
import { useCreateTicket, useTicketDetail } from '@hooks';
import { TicketTypes } from '@common/const';
import BatchInput from '@views/db-manage/common/batch-input/Index.vue';
import OperationColumn from '@views/db-manage/common/toolbox-field/column/operation-column/Index.vue';
import TicketPayload, { createTicketPayload } from '@views/db-manage/common/toolbox-field/form-item/ticket-payload/Index.vue';
import ClusterColumn from '@views/db-manage/mysql/common/toolbox-field/cluster-column/Index.vue';
import { random } from '@utils';

// --- 类型定义 ---
interface RowData { cluster: TendbhaModel; /* ... */ }

// --- 基础设置 ---
const { t } = useI18n();
const router = useRouter();
const tableRef = useTemplateRef('tableRef');
const tableKey = ref(random());

// --- 行数据工厂 ---
const createTableRow = (data: DeepPartial<RowData> = {}) => ({ /* ... */ });

// --- 表单默认值工厂 ---
const defaultData = () => ({ payload: createTicketPayload(), tableData: [createTableRow()] });
const formData = reactive(defaultData());

// --- 计算属性 ---
const selected = computed(() => formData.tableData.filter(i => i.cluster.id).map(i => i.cluster));

// --- 编辑/克隆回填 ---
useTicketDetail<Mysql.YourNewType>(TicketTypes.MYSQL_YOUR_NEW_TYPE, {
  onSuccess(ticketDetail) {
    const { details } = ticketDetail;
    const { clusters, infos } = details;
    const tableData = infos.map((item) =>
      createTableRow({
        cluster: { master_domain: clusters?.[item.cluster_id]?.immute_domain || '' } as TendbhaModel,
        // labels 是 id 列表，配合 label_names 补名称回显（有资源标签列时必写，缺了再次提单标签列为空）
        labels: (item.resource_spec?.master?.labels || []).map((labelId, index) => ({
          id: Number(labelId),
          value: item.resource_spec?.master?.label_names?.[index] || '',
        })) as RowData['labels'],
      }),
    );
    Object.assign(formData, {
      payload: createTicketPayload(ticketDetail),
      tableData: tableData.length ? tableData : [createTableRow()],
    });
  },
});

// --- 提交 ---
// 泛型用内联的提交 payload 类型（只描述实际提交的 details 结构），禁止用 Mysql.XxxXx 详情类型
// ——详情类型继承 DetailBase，要求 __ticket_detail__ / clusters 等后端返回字段，提单不传会类型不匹配报红
const { loading: isSubmitting, run: createTicketRun } = useCreateTicket<SubmitDetailsType>(TicketTypes.MYSQL_YOUR_NEW_TYPE);
const handleSubmit = async () => {
  const result = await tableRef.value!.validate();
  if (!result) return;
  createTicketRun({ details: { /* ... */ }, ...formData.payload });
};

// --- 重置 ---
const handleReset = () => { Object.assign(formData, defaultData()); };

// --- 批量编辑 ---
const handleBatchEdit = (list: TendbhaModel[]) => { /* ... */ };

// --- 批量录入 ---
// 六条约定与解析细节见 row-editing-pitfalls.md
const handleBatchInput = (data: Record<string, any>[], isClear: boolean) => { /* ... */ };

// --- 返回工具箱 ---
defineExpose({ routerBack() { router.push({ name: 'MysqlToolboxIndex' }); } });
```

## 模板要点

- 模式 F 的 Index.vue 结构（`<Wrapper>` 包裹 `<SmartAction>`，BkAlert 和模式选择在 Wrapper 中）见 [pattern-f.md](pattern-f.md)
- `handleBatchInput` 批量录入的六条约定与解析细节见 [row-editing-pitfalls.md](row-editing-pitfalls.md)
- 回填块中资源标签 `labels` + `label_names` 组装是高频遗漏点，见 [row-editing-pitfalls.md](row-editing-pitfalls.md)
- 列组件的路径与 props 见 [column-components.md](column-components.md)
