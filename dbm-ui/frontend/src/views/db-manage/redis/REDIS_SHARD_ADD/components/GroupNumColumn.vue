<template>
  <EditableColumn
    :disabled-method="() => !clusterId"
    field="group_num"
    :label="t('增加机器组数')"
    required
    :width="120">
    <template #headAppend>
      <BatchEditColumn
        :confirm-handler="handleBatchEditConfirm"
        :label="t('增加机器组数')">
        <BatchEditNumberInput v-model="batchEditValue" />
      </BatchEditColumn>
    </template>
    <EditableInput
      v-model="modelValue"
      :min="1"
      type="number" />
  </EditableColumn>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import BatchEditColumn, { BatchEditNumberInput } from '@views/db-manage/common/batch-edit-column-new/Index.vue';

  interface Props {
    clusterId: number;
  }

  interface Emits {
    (e: 'batch-edit', value: number, filed: string): void;
    (e: 'change'): void;
  }

  defineProps<Props>();
  const emits = defineEmits<Emits>();
  const modelValue = defineModel<number>();

  const { t } = useI18n();

  const batchEditValue = ref(1);

  const handleBatchEditConfirm = () => {
    emits('batch-edit', batchEditValue.value, 'group_num');
  };
</script>

<style lang="less">
  .batch-edit-btn {
    font-size: 14px;
    color: #3a84ff;
    cursor: pointer;
  }
</style>
