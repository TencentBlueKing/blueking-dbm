<template>
  <BkButton
    v-if="isShowRaw"
    v-bind="attrs">
    <slot />
  </BkButton>
  <span
    v-else
    disabled>
    <BkButton
      v-cursor
      class="auth-button-disable"
      v-bind="inheritAttrs"
      :disabled="false"
      :loading="loading"
      @click.stop="handleRequestPermission">
      <slot />
    </BkButton>
  </span>
</template>
<script setup lang="ts">
  import {
    useAttrs,
  } from 'vue';

  import { attrsWithoutListener } from '@utils';

  import useBase from './use-base';

  /* eslint-disable vue/no-unused-properties */
  interface Props {
    permission?: boolean | string,
    actionId: string,
    resource?: string | number,
  }

  const props = withDefaults(defineProps<Props>(), {
    permission: 'normal',
    resource: '',
  });
  defineOptions({
    inheritAttrs: false,
  });

  const attrs = useAttrs();

  const inheritAttrs = attrsWithoutListener(attrs);

  const {
    loading,
    isShowRaw,
    handleRequestPermission,
  } = useBase(props);

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
