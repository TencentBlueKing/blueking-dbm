<template>
  <BkInput
    v-bind="attrs"
    ref="inputRef"
    v-model="modelValue"
    clearable />
</template>
<script setup lang="ts">
  const modelValue = defineModel<string>();

  const attrs = useAttrs();
</script>
