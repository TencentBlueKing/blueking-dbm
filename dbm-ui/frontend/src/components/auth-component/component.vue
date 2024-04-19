<template>
  <span
    v-if="isShowRaw"
    v-bind="attrs">
    <slot v-bind="{ permission: true }" />
  </span>
  <div
    v-else
    v-bind="attrsWithoutListener(attrs)"
    class="permission-disable-component">
    <slot v-bind="{ permission: false }" />
    <div
      v-cursor
      class="permission-disable-mask"
      @click="handleRequestPermission" />
  </div>
</template>
<script setup lang="ts">
  import { useAttrs } from 'vue';

  import { attrsWithoutListener } from '@utils';

  import useBase from './use-base';

  /* eslint-disable vue/no-unused-properties */
  interface Props {
    actionId: string;
    permission: string | boolean;
    resource?: string | number;
    bizId?: string | number;
  }

  const props = withDefaults(defineProps<Props>(), {
    permission: 'default',
    resource: '',
    bizId: undefined,
  });

  const attrs = useAttrs();

  const { isShowRaw, handleRequestPermission } = useBase(props);
</script>
<style lang="less">
  .permission-disable-component {
    position: relative;
    display: inline-block;
    user-select: none !important;

    * {
      color: #c4c6cc !important;
      pointer-events: none;
    }

    .permission-disable-mask {
      position: absolute;
      inset: 0;
      pointer-events: all;
    }
  }
</style>
