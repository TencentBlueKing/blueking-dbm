<template>
  <EditableColumn
    :append-rules="rules"
    field="add_proxy_num"
    :label="t('扩容数量（台）')"
    required
    :width="150">
    <template #headAppend>
      <BatchEditColumn
        v-model="showBatchEdit"
        :title="t('扩容数量（台）')"
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
      :min="1"
      :placeholder="t('不能少于n台', { n: 1 })"
      type="number" />
  </EditableColumn>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import BatchEditColumn from '@views/db-manage/common/batch-edit-column/Index.vue';

  interface Emits {
    (e: 'batch-edit', value: string, filed: string): void;
    (e: 'change'): void;
  }

  const emits = defineEmits<Emits>();
  const modelValue = defineModel<number>();

  const { t } = useI18n();

  const rules = [
    {
      message: t('不能少于n台', { n: 1 }),
      trigger: 'change',
      validator: (value: string) => Number(value) >= 1,
    },
  ];
  const showBatchEdit = ref(false);

  const handleBatchEditShow = () => {
    showBatchEdit.value = true;
  };

  const handleBatchEditChange = (value: string[] | string) => {
    emits('batch-edit', value as string, 'add_proxy_num');
  };
</script>

<style lang="less">
  .batch-edit-btn {
    font-size: 14px;
    color: #3a84ff;
    cursor: pointer;
  }
</style>
