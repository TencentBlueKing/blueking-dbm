<template>
  <BkOption
    v-if="isShowRaw"
    v-bind="attrs">
    <template v-if="slots.default">
      <slot />
    </template>
    <template v-else>
      {{ attrs.label }}
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
        {{ attrs.label }}
      </template>
    </div>
  </BkOption>
</template>
<script setup lang="ts">
  // import type { Option } from 'bkui-vue';
  import {
    useAttrs,
    useSlots,
  } from 'vue';

  import useBase from './use-base';

  // type OptionProps = InstanceType<typeof Option>['$props']
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
  const slots = useSlots();

  const {
    isShowRaw,
    handleRequestPermission,
  } = useBase(props);

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
