<template>
  <EditableColumn
    :append-rules="rules"
    field="target_proxy_count"
    :label="t('扩容数量（台）')"
    required
    :width="200">
    <template #headAppend>
      <BatchEditColumn
        :confirm-handler="handleBatchEditConfirm"
        :label="t('扩容数量（台）')">
        <BatchEditNumberInput v-model="batchEditValue" />
      </BatchEditColumn>
    </template>
    <EditableInput
      v-model="modelValue"
      :min="1"
      :placeholder="t('不能少于n台', { n: 1 })"
      :rules="rules"
      type="number" />
  </EditableColumn>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import BatchEditColumn, { BatchEditNumberInput } from '@views/db-manage/common/batch-edit-column-new/Index.vue';

  interface Emits {
    (e: 'batch-edit', value: string, filed: string): void;
    (e: 'change'): void;
  }

  const emits = defineEmits<Emits>();
  const modelValue = defineModel<string>();

  const { t } = useI18n();

  const rules = [
    {
      message: t('不能少于n台', { n: 1 }),
      trigger: 'change',
      validator: (value: number) => value >= 1,
    },
  ];

  const batchEditValue = ref('');

  const handleBatchEditConfirm = () => {
    emits('batch-edit', batchEditValue.value, 'target_proxy_count');
  };
</script>

<style lang="less">
  .batch-edit-btn {
    font-size: 14px;
    color: #3a84ff;
    cursor: pointer;
  }
</style>
