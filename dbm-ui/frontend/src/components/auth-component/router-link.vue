<template>
  <RouterLink
    v-bind="(attrs as unknown as any)">
    <slot />
  </RouterLink>
</template>
<script setup lang="ts">
  import {
    useAttrs,
  } from 'vue';

  /* eslint-disable vue/no-unused-properties */
  interface Props {
    permission?: boolean | string,
    actionId: string,
    resource?: string | number,
  }

  withDefaults(defineProps<Props>(), {
    permission: 'normal',
    resource: '',
  });

  defineOptions({
    inheritAttrs: false,
  });

  const attrs = useAttrs();
</script>
<style lang="less" scoped>
  .auth-router-link-disabled {
    color: #c4c6cc !important;
    user-select: none !important;
  }
</style>
