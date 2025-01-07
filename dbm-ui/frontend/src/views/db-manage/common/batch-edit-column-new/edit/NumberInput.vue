<template>
  <BkInput
    v-bind="attrs"
    v-model="modelValue"
    type="number" />
</template>

<script setup lang="ts">
  import useColumn from '../useColumn';

  const modelValue = defineModel<string>();

  const attrs = useAttrs();

  useColumn('number-input');
</script>
