<template>
  <EditableColumn
    :disabled-method="() => !clusterId"
    field="group_num"
    :label="t('减少机器组数')"
    required
    :rules="rules"
    :width="120">
    <template #headAppend>
      <BatchEditColumn
        :confirm-handler="handleBatchEditConfirm"
        :label="t('减少机器组数')">
        <BatchEditNumberInput v-model="batchEditValue" />
      </BatchEditColumn>
    </template>
    <EditableInput
      v-model="modelValue"
      :max="groupNum - 1"
      :min="1"
      type="number" />
  </EditableColumn>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import BatchEditColumn, { BatchEditNumberInput } from '@views/db-manage/common/batch-edit-column-new/Index.vue';

  interface Props {
    clusterId: number;
    groupNum: number;
  }

  interface Emits {
    (e: 'batch-edit', value: number, filed: string): void;
    (e: 'change'): void;
  }

  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();
  const modelValue = defineModel<number>();

  const { t } = useI18n();

  const rules = [
    {
      message: t('最终机器组数不能为 0'),
      trigger: 'change',
      validator: (value: number) => props.groupNum - value !== 0,
    },
  ];

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
