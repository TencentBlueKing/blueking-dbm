<template>
  <EditableColumn
    :label="t('内存大小')"
    :loading="isLoading"
    :min-width="150"
    readonly>
    <EditableBlock :placeholder="t('自动生成')">
      {{ statData ? bytePretty(modelValue.memory_total) : '' }}
    </EditableBlock>
  </EditableColumn>
  <EditableColumn
    :label="t('Key 数量')"
    :loading="isLoading"
    :min-width="150"
    readonly>
    <EditableBlock :placeholder="t('自动生成')">
      {{ statData ? modelValue.key_num : '' }}
    </EditableBlock>
  </EditableColumn>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { getKeystatInfoByInstance } from '@services/source/redisKeystat';

  import { bytePretty } from '@utils';

  interface Props {
    instance: string;
  }

  const props = defineProps<Props>();
  const modelValue = defineModel<{
    key_num: number;
    memory_total: number;
  }>({
    required: true,
  });

  const { t } = useI18n();

  const {
    data: statData,
    loading: isLoading,
    run: runGetKeystatInfoByInstance,
  } = useRequest(getKeystatInfoByInstance, {
    manual: true,
    onSuccess(statResult) {
      const { key_num: keyNum, memory_total: memoryTotal } = statResult[props.instance];
      modelValue.value = {
        key_num: keyNum,
        memory_total: memoryTotal,
      };
    },
  });

  watch(
    () => props.instance,
    () => {
      if (props.instance) {
        runGetKeystatInfoByInstance({
          instances: props.instance,
        });
      }
    },
    {
      immediate: true,
    },
  );
</script>
