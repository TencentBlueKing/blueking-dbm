<template>
  <Column
    :description="t('通过列与列值确定记录')"
    :disabled-method="disabledMethod"
    field="rows_filter"
    :label="t('待闪回的记录')"
    :min-width="200">
    <EditTextarea v-model="modelValue" />
  </Column>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import { Column, Textarea as EditTextarea } from '@components/editable-table/Index.vue';

  interface Props {
    clusterId?: number;
  }

  const props = defineProps<Props>();

  const { t } = useI18n();

  const disabledMethod = () => (props.clusterId ? false : t('请先选择集群'));

  const modelValue = defineModel<string>();
</script>
