<template>
  <EditableColumn
    :disabled-method="() => !clusterId"
    field="add_shard_nodes_num"
    :label="t('扩容节点数')"
    required
    :width="150">
    <template #headAppend>
      <BatchEditColumn
        v-model="showBatchEdit"
        :title="t('扩容节点数')"
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
      type="number" />
  </EditableColumn>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import BatchEditColumn from '@views/db-manage/common/batch-edit-column/Index.vue';

  interface Props {
    clusterId: number;
  }

  interface Emits {
    (e: 'batch-edit', value: string, filed: string): void;
    (e: 'change'): void;
  }

  defineProps<Props>();
  const emits = defineEmits<Emits>();
  const modelValue = defineModel<number>();

  const { t } = useI18n();

  const showBatchEdit = ref(false);

  const handleBatchEditShow = () => {
    showBatchEdit.value = true;
  };

  const handleBatchEditChange = (value: string[] | string) => {
    emits('batch-edit', value as string, 'add_shard_nodes_num');
  };
</script>

<style lang="less">
  .batch-edit-btn {
    font-size: 14px;
    color: #3a84ff;
    cursor: pointer;
  }
</style>
