<template>
  <BkSelect
    v-model="modelValue"
    @change="handleChange">
    <BkOption
      key="default"
      :label="t('无限制')"
      :value="0" />
    <BkOption
      v-for="biz in data"
      :key="biz.bk_biz_id"
      :label="biz.display_name"
      :value="biz.bk_biz_id" />
  </BkSelect>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { getBizs } from '@services/source/cmdb';

  interface Emits {
    (e: 'change', value: number): void;
  }

  interface Exposes {
    getValue: () => {
      for_biz: number;
    };
  }

  const emits = defineEmits<Emits>();

  const modelValue = defineModel<number>({
    default: 0,
  });

  const { t } = useI18n();

  const { data } = useRequest(getBizs, {
    initialData: [],
  });

  const handleChange = (value: number) => {
    emits('change', value);
  };

  defineExpose<Exposes>({
    getValue: () => ({
      for_biz: modelValue.value,
    }),
  });
</script>
