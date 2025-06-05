<template>
  <BkDatePicker
    v-model="modelValue"
    v-bind="attrs"
    :clearable="false"
    style="width: 100%"
    type="datetime" />
</template>

<script setup lang="ts" generic="T extends [string, string] | [Date, Date] | string | Date">
  const modelValue = defineModel<T>();

  const attrs = useAttrs();
</script>
