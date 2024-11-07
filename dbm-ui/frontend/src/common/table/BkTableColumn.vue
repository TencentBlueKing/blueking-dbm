<template>
  <Column v-bind="realProps">
    <template
      v-if="slots.header"
      #header>
      <slot name="header" />
    </template>
    <template
      v-if="slots.default"
      #default="{ row }">
      <slot v-bind="{ row }" />
    </template>
  </Column>
</template>
<script setup lang="ts">
  import { computed, useAttrs, type VNode } from 'vue';

  import { Column, type VxeGridPropTypes } from '@blueking/vxe-table';

  import { columnConfig } from './adapter';

  /* eslint-disable vue/no-unused-properties */
  interface Props {
    // label?: string | (() => any);
    // sort?: boolean;
    // filter?: any;
    // textAlign?: string;
    // align?: string;
  }

  interface Slot {
    header?: () => VNode;
    default?: (params: { row: any }) => VNode;
  }

  const props = withDefaults(defineProps<Props & VxeGridPropTypes.Column>(), {
    // 兼容 BkTableColumn prop
    sort: false,
    filter: false,
    textAlign: undefined,
    label: undefined,
    align: undefined,
    // VxeColumn prop
    visible: true,
    resizable: true,
    minWidth: 'auto',
    showHeaderOverflow: 'tooltip',
    showOverflow: 'tooltip',
    width: undefined,
    fit: true,
  });

  const slots = defineSlots<Slot>();

  const attrs = useAttrs();

  const realProps = computed(() =>
    columnConfig({
      ...attrs,
      ...props,
    }),
  );
</script>
