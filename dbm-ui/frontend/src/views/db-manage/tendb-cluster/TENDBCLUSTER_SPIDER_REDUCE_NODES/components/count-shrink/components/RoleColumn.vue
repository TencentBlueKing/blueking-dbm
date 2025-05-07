<template>
  <EditableColumn
    field="cluster.role"
    :label="t('缩容节点类型')"
    :min-width="200"
    required>
    <template #headAppend>
      <BatchEditColumn
        v-model="showBatchEdit"
        :data-list="nodeTypeOptions"
        :title="t('缩容节点类型')"
        type="select"
        @change="handleBatchEditChange">
        <span
          v-bk-tooltips="t('统一设置：将该列统一设置为相同的值')"
          class="batch-edit-btn"
          @click="handleBatchEditShow">
          <DbIcon type="bulk-edit" />
        </span>
      </BatchEditColumn>
    </template>
    <EditableSelect
      v-model="modelValue"
      :input-search="false"
      :list="nodeTypeOptions"
      @change="handleChange" />
  </EditableColumn>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import BatchEditColumn from '@views/db-manage/common/batch-edit-column/Index.vue';

  interface Emits {
    (e: 'batch-edit', value: string[]): void;
    (e: 'change'): void;
  }

  const emits = defineEmits<Emits>();

  const modelValue = defineModel<string>();

  const { t } = useI18n();

  const nodeTypeOptions = [
    {
      label: 'Spider Master',
      value: 'spider_master',
    },
    {
      label: 'Spider Slave',
      value: 'spider_slave',
    },
  ];

  const showBatchEdit = ref(false);

  const handleBatchEditShow = () => {
    showBatchEdit.value = true;
  };

  const handleBatchEditChange = (value: string[] | string) => {
    emits('batch-edit', value as string[]);
  };

  const handleChange = () => {
    emits('change');
  };
</script>

<style lang="less">
  .batch-edit-btn {
    font-size: 14px;
    color: #3a84ff;
    cursor: pointer;
  }
</style>
