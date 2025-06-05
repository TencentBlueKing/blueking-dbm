<template>
  <BkInput
    v-bind="attrs"
    v-model="modelValue"
    type="number" />
</template>

<script setup lang="ts">
  const modelValue = defineModel<string>();

  const attrs = useAttrs();
</script>
