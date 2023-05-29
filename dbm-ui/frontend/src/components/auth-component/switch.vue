<template>
  <BkSwitcher
    v-if="isShowRaw"
    v-bind="attrs" />
  <span
    v-else
    disabled>
    <BkSwitcher
      v-cursor
      class="auth-switch-disable"
      v-bind="inheritAttrs"
      :disabled="false"
      :loading="loading"
      @click.stop="handleRequestPermission" />
  </span>
</template>
<script setup lang="ts">
  import { useAttrs } from 'vue';

  import { attrsWithoutListener } from '@utils';

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

  const inheritAttrs = attrsWithoutListener(attrs);

  const { loading, isShowRaw, handleRequestPermission } = useBase(props);
</script>
<style lang="less" scoped>
  .auth-switch-disable {
    color: #fff !important;
    background-color: #dcdee5 !important;
    border-color: #dcdee5 !important;
    user-select: none !important;

    &.is-text {
      color: #c4c6cc !important;
      background-color: transparent !important;
      border-color: transparent !important;
    }
  }
</style>
