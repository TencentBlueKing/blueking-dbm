<template>
  <Column
    :disabled-method="disabledMethod"
    field="tables"
    :label="label"
    :min-width="180"
    required
    :rules="rules">
    <EditTagInput
      v-model="modelValue"
      :placeholder="t('请输入表名称，支持通配符“%”，含通配符的仅支持单个')" />
  </Column>
</template>
<script setup lang="ts">
  import _ from 'lodash';
  import { useI18n } from 'vue-i18n';

  import { Column, TagInput as EditTagInput } from '@components/editable-table/Index.vue';

  interface Props {
    label: string;
    clusterId?: number;
  }

  const props = defineProps<Props>();

  const { t } = useI18n();

  const disabledMethod = () => (props.clusterId ? false : t('请先选择集群'));

  const modelValue = defineModel<string[]>();

  const rules = [
    {
      validator: (value: string[]) => _.every(value, (item) => /^[-_a-zA-Z0-9*?%]{0,64}$/.test(item)),
      message: t('库表名支持数字、字母、中划线、下划线，最大64字符'),
      trigger: 'blur',
    },
    {
      validator: (value: string[]) => _.every(value, (item) => item !== '*'),
      message: t('不允许为 *'),
      trigger: 'blur',
    },
    {
      validator: (value: string[]) =>
        !_.some(value, (item) => (/\*/.test(item) && item.length > 1) || (value.length > 1 && item === '*')),
      message: t('* 只能独立使用'),
      trigger: 'blur',
    },
    {
      validator: (value: string[]) => _.every(value, (item) => !/^[%?]$/.test(item)),
      message: t('% 或 ? 不允许单独使用'),
      trigger: 'blur',
    },
  ];
</script>
