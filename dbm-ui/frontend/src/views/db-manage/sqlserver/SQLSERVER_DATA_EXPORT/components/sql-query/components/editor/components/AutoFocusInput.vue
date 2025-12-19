<template>
  <BkInput
    ref="inputRef"
    v-model="modelValue" />
</template>
<script setup lang="ts">
  const modelValue = defineModel<string>({
    default: '',
  });

  const inputRef = ref();

  onMounted(() => {
    inputRef.value?.focus();
  });
</script>
