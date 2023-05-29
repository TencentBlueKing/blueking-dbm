<template>
  <BkInput
    v-model="moduleValue"
    type="number">
    <template #prefix>
      <span>-</span>
    </template>
    <template #suffix>
      <span>+</span>
    </template>
  </BkInput>
</template>
<script setup lang="ts">
  const moduleValue = defineModel<string>();
</script>
