<template>
  <div style="padding: 0 16px">
    {{ modelValue }}
  </div>
</template>
<script setup lang="ts">
  const modelValue = defineModel<string>({
    required: false,
    default: '',
  });
</script>
