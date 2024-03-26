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
<style lang="less">
  .auth-button-disable {
    background-color: #dcdee5 !important;
    border-color: #dcdee5 !important;
    user-select: none !important;

    .bk-button-text {
      color: #fff !important;
    }

    &.is-text,
    * {
      background-color: transparent !important;
      border-color: transparent !important;

      .bk-button-text {
        color: #c4c6cc !important;
      }
    }
  }
</style>
