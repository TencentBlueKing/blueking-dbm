<template>
  <EditableColumn
    :append-rules="rules"
    field="target_num"
    :label="t('缩容至（节点数）')"
    required
    :width="200">
    <template #headAppend>
      <BatchEditColumn
        v-model="showBatchEdit"
        :title="t('缩容至（节点数）')"
        type="number-input"
        @change="handleBatchEditChange">
        <span
          v-bk-tooltips="t('统一设置：将该列统一设置为相同的值')"
          class="batch-edit-btn"
          @click="handleBatchEditShow">
          <DbIcon type="bulk-edit" />
        </span>
      </BatchEditColumn>
    </template>
    <EditableInput
      v-model="modelValue"
      :disabled="disabled"
      :max="max"
      :min="3"
      type="number" />
  </EditableColumn>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import BatchEditColumn from '@views/db-manage/common/batch-edit-column/Index.vue';

  interface Props {
    disabled: boolean;
    max: number;
  }

  interface Emits {
    (e: 'batch-edit', value: string, filed: string): void;
    (e: 'change'): void;
  }

  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();
  const modelValue = defineModel<string>();

  const { t } = useI18n();

  const rules = [
    {
      message: t('不能少于n台', { n: 3 }),
      trigger: 'change',
      validator: (value: number) => value >= 3,
    },
    {
      message: t('必须小于当前节点数'),
      trigger: 'change',
      validator: (value: number) => value < props.max,
    },
  ];
  const showBatchEdit = ref(false);

  const handleBatchEditShow = () => {
    showBatchEdit.value = true;
  };

  const handleBatchEditChange = (value: string[] | string) => {
    emits('batch-edit', value as string, 'target_num');
  };
</script>

<style lang="less">
  .batch-edit-btn {
    font-size: 14px;
    color: #3a84ff;
    cursor: pointer;
  }
</style>
