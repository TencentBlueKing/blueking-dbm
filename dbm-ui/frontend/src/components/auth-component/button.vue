<template>
  <BkButton v-bind="attrs">
    <slot />
  </BkButton>
</template>
<script setup lang="ts">
  import { useAttrs } from 'vue';

  /* eslint-disable vue/no-unused-properties */
  interface Props {
    permission?: boolean | string;
    actionId: string;
    resource?: string | number;
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
<style lang="less">
  .auth-button-disable {
    color: #fff !important;
    background-color: #dcdee5 !important;
    border-color: #dcdee5 !important;
    user-select: none !important;

    &.is-text,
    * {
      color: #c4c6cc !important;
      background-color: transparent !important;
      border-color: transparent !important;
    }
  }
</style>
