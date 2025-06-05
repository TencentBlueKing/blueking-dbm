<template>
  <BkSelect
    v-model="modelValue"
    v-bind="attrs"
    :clearable="false"
    filterable>
  </BkSelect>
</template>

<script setup lang="ts" generic="T extends string[] | number[] | string | number">
  const modelValue = defineModel<T>();

  const attrs = useAttrs();
</script>
