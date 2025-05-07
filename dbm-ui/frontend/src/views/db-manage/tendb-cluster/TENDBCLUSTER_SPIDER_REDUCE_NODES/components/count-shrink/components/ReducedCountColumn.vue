<template>
  <EditableColumn
    :append-rules="reducedCountRules"
    field="reduced_count"
    :label="t('缩容数量（台）')"
    :min-width="200"
    required>
    <template #headAppend>
      <BatchEditColumn
        v-model="showBatchEdit"
        :title="t('缩容数量（台）')"
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
      :max="cluster.role === 'spider_master' ? cluster.master_count : cluster.slave_count"
      :min="0"
      type="number"
      @change="handleChange" />
  </EditableColumn>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import BatchEditColumn from '@views/db-manage/common/batch-edit-column/Index.vue';

  interface Props {
    cluster: {
      master_count: number;
      role: string;
      slave_count: number;
    };
  }

  interface Emits {
    (e: 'batch-edit', value: string[]): void;
    (e: 'change'): void;
  }

  defineProps<Props>();

  const emits = defineEmits<Emits>();

  const modelValue = defineModel<string>();

  const { t } = useI18n();

  const reducedCountRules = [
    {
      message: t('缩容数量必须大于0'),
      trigger: 'change',
      validator: (value: string) => Number(value) > 0,
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
