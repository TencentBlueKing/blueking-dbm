<template>
  <RenderTableName
    ref="editRef"
    :cluster-id="clusterId"
    :ignore-dbs="ignoreDbs"
    :model-value="modelValue"
    :required="false"
    :rules="rules" />
</template>
<script setup lang="ts">
  import _ from 'lodash';
  import { computed, ref } from 'vue';
  import { useI18n } from 'vue-i18n';

  import RenderTableName from '@views/db-manage/mysql/common/edit-field/TableName.vue';

  interface Props {
    clusterId: number;
    ignoreDbs?: string[];
    modelValue?: string[];
  }

  interface Exposes {
    getValue: () => Promise<Record<string, string[]>>;
  }

  const props = defineProps<Props>();

  const { t } = useI18n();

  const editRef = ref<InstanceType<typeof RenderTableName>>();

  const rules = computed(() => [
    {
      message: t('忽略 DB 和忽略表名需同时为空或者同时有值'),
      validator: (value: string[]) =>
        (props.ignoreDbs && props.ignoreDbs.length > 0 && value.length > 0) ||
        ((!props.ignoreDbs || props.ignoreDbs.length === 0) && value.length === 0),
    },
    {
      message: t('一格仅支持单个 % 对象'),
      validator: (value: string[]) => {
        const hasAllMatch = _.find(value, (item) => item.endsWith('%'));
        return !(value.length > 1 && hasAllMatch);
      },
    },
  ]);

  defineExpose<Exposes>({
    getValue() {
      return (editRef.value as InstanceType<typeof RenderTableName>).getValue('ignore_tables');
    },
  });
</script>
