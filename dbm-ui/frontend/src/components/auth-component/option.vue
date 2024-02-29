<template>
  <BkOption v-bind="attrs">
    <template v-if="slots.default">
      <slot />
    </template>
    <template v-else>
      {{ attrs.label }}
    </template>
  </BkOption>
</template>
<script setup lang="ts">
  import { useAttrs, useSlots } from 'vue';

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
  const slots = useSlots();
</script>
<style lang="less" scoped>
  .auth-option-disabled {
    color: #c4c6cc !important;

    & > * {
      pointer-events: none;
    }

    .auth-option-label {
      pointer-events: all !important;
    }
  }
</style>
