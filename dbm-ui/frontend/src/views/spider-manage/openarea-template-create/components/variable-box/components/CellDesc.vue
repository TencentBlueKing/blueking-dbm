<template>
  <div style="padding: 0 16px">
    {{ modelValue }}
  </div>
</template>
<script setup lang="ts">
  const modelValue = defineModel({
    required: false,
    default: false,
    local: true,
  });
</script>

