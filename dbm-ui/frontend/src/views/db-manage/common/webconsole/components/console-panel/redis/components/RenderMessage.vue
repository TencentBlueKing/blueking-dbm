<template>
  <p
    v-for="(row, index) in rows"
    :key="index"
    class="preserve-whitespace">
    {{ row }}
  </p>
</template>

<script setup lang="ts">
  interface Props {
    data: string;
  }

  const props = defineProps<Props>();

  const rows = computed(() => props.data.split('\n') || []);
</script>

<style lang="less" scoped>
  .preserve-whitespace {
    font-family: 'Courier New', Courier, monospace; /* 等宽字体 */
    white-space: pre;
  }
</style>
