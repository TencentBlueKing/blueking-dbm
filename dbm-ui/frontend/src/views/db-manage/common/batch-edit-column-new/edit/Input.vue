<template>
  <BkInput
    v-bind="attrs"
    ref="inputRef"
    v-model="modelValue"
    clearable />
</template>
<script setup lang="ts">
  import useColumn from '../useColumn';

  const modelValue = defineModel<string>();

  const attrs = useAttrs();

  useColumn('input');
</script>
