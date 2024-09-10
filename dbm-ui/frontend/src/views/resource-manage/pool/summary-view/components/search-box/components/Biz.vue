<template>
  <BkSelect
    v-model="modelValue"
    @change="handleChange">
    <BkOption
      v-for="biz in data"
      :key="biz.bk_biz_id"
      :label="biz.display_name"
      :value="biz.bk_biz_id" />
  </BkSelect>
</template>

<script setup lang="ts">
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
