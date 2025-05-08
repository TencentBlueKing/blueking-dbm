<template>
  <EditableColumn
    field="rollback_time"
    :label="t('指定时间')"
    required>
    <template #headAppend>
      <BatchEditColumn
        v-model="showBatchEdit"
        :disable-fn="disableDate"
        :title="t('指定时间')"
        type="datetime"
        @change="handleBatchEditChange">
        <span
          v-bk-tooltips="t('统一设置：将该列统一设置为相同的值')"
          class="batch-edit-btn"
          @click="handleBatchEditShow">
          <DbIcon type="bulk-edit" />
        </span>
      </BatchEditColumn>
    </template>
    <EditableDatePicker
      v-model="modelValue"
      :disabled-date="disableDate"
      type="datetime" />
  </EditableColumn>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import BatchEditColumn from '@views/db-manage/common/batch-edit-column/Index.vue';

  type Emits = (e: 'batch-edit', value: string, field: string) => void;

  const emits = defineEmits<Emits>();

  const modelValue = defineModel<string | Date>();

  const { t } = useI18n();

  const showBatchEdit = ref(false);

  const disableDate = (date?: number | Date) => Boolean(date && date.valueOf() > Date.now());

  const handleBatchEditShow = () => {
    showBatchEdit.value = true;
  };

  const handleBatchEditChange = (value: string[] | string) => {
    emits('batch-edit', value as string, 'rollback_time');
  };
</script>

<style lang="less">
  .batch-edit-btn {
    font-size: 14px;
    color: #3a84ff;
    cursor: pointer;
  }
</style>
