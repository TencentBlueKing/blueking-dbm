<template>
  <BkOption
    v-if="isShowRaw"
    v-bind="attrs">
    <template v-if="slots.default">
      <slot />
    </template>
    <template v-else>
      {{ attrs.label || attrs.name }}
    </template>
  </BkOption>
  <BkOption
    v-else
    v-cursor
    class="auth-option-disabled"
    v-bind="attrs">
    <div
      class="auth-option-label"
      @click.stop="handleRequestPermission">
      <template v-if="slots.default">
        <slot />
      </template>
      <template v-else>
        {{ attrs.label || attrs.name }}
      </template>
    </div>
  </BkOption>
</template>
<script setup lang="ts">
  import { useAttrs, useSlots } from 'vue';

  import useBase from './use-base';

  /* eslint-disable vue/no-unused-properties */
  interface Props {
    permission?: boolean | string;
    actionId: string;
    resource?: string | number;
    bizId?: string | number;
  }

  const props = withDefaults(defineProps<Props>(), {
    permission: 'normal',
    resource: '',
    bizId: undefined,
  });
  defineOptions({
    inheritAttrs: false,
  });

  const attrs = useAttrs();
  const slots = useSlots();

  const { isShowRaw, handleRequestPermission } = useBase(props);
</script>
<style lang="less" scoped>
  .auth-option-disabled {
    position: relative;
    color: #c4c6cc !important;

    & > * {
      pointer-events: none;
    }

    .auth-option-label {
      pointer-events: all !important;
      flex: 1;

      &::after {
        position: absolute;
        inset: 0;
        content: '';
      }
    }
  }
</style>
