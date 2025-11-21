<template>
  <EditableColumn
    ref="editableColumnRef"
    :append-rules="rules"
    field="add_shards_num"
    :label="t('新增集群分片数')"
    required
    :width="150">
    <template #headAppend>
      <BatchEditColumn
        :confirm-handler="handleBatchEditConfirm"
        :label="t('新增集群分片数')">
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
    singleHostShardNum: number;
  }

  type Emits = (e: 'batch-edit', value: number, filed: string) => void;

  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();
  const modelValue = defineModel<number>();

  const { t } = useI18n();

  const rules = [
    {
      message: t('不能少于n', { n: 1 }),
      trigger: 'change',
      validator: (value: number) => value >= 1,
    },
    {
      message: t('新增 集群分片数 必须是 单机分片数 的倍数'),
      trigger: 'change',
      validator: (value: number) => value % props.singleHostShardNum === 0,
    },
  ];

  const editableColumnRef = useTemplateRef('editableColumnRef');

  const batchEditValue = ref(1);

  watch(
    () => props.singleHostShardNum,
    () => {
      if (props.singleHostShardNum > 0) {
        editableColumnRef.value!.validate();
      }
    },
  );

  const handleBatchEditConfirm = () => {
    emits('batch-edit', batchEditValue.value, 'add_shards_num');
  };
</script>

<style lang="less">
  .batch-edit-btn {
    font-size: 14px;
    color: #3a84ff;
    cursor: pointer;
  }
</style>
