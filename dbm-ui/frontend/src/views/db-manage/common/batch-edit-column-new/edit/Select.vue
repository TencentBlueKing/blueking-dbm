<template>
  <BkSelect
    v-model="modelValue"
    v-bind="attrs"
    :clearable="false"
    filterable>
  </BkSelect>
</template>

<script setup lang="ts" generic="T extends string[] | number[] | string | number">
  import useColumn from '../useColumn';

  const modelValue = defineModel<T>();

  const attrs = useAttrs();

  useColumn('select');
</script>
