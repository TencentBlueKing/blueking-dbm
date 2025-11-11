<template>
  <EditableColumn
    :disabled-method="() => !clusterId"
    field="online_switch_type"
    :label="t('切换模式')"
    :min-width="150">
    <template #headAppend>
      <BatchEditColumn
        :confirm-handler="handleBatchEditConfirm"
        :label="t('切换模式')">
        <BatchEditSelect
          v-model="batchEditValue"
          :input-search="false"
          :list="switchModeOptions" />
      </BatchEditColumn>
    </template>
    <EditableSelect
      v-model="modelValue"
      :input-search="false"
      :list="switchModeOptions" />
  </EditableColumn>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import BatchEditColumn, { BatchEditSelect } from '@views/db-manage/common/batch-edit-column-new/Index.vue';

  interface Props {
    clusterId: number;
  }

  type Emits = (e: 'batch-edit', value: string, filed: string) => void;

  defineProps<Props>();
  const emits = defineEmits<Emits>();
  const modelValue = defineModel<string>({
    required: true,
  });

  const { t } = useI18n();

  const switchModeOptions = [
    {
      label: t('需人工确认'),
      value: 'user_confirm',
    },
    {
      label: t('无需确认'),
      value: 'no_confirm',
    },
  ];

  const batchEditValue = ref('');

  const handleBatchEditConfirm = () => {
    emits('batch-edit', batchEditValue.value, 'online_switch_type');
  };
</script>
