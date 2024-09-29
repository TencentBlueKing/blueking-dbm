<template>
  <Column v-bind="realProps">
    <template
      v-if="realProps.slots.header"
      #header>
      <RenderHead :column="realProps" />
    </template>
    <template
      v-else-if="slots.header"
      #header>
      <slot name="header" />
    </template>
    <template
      v-if="realProps.slots.default"
      #default="payload">
      <RenderCell
        :column="realProps"
        :params="payload" />
    </template>
    <template
      v-else-if="slots.default"
      #default="payload">
      <slot
        v-bind="{
          ...payload,
          index: payload.columnIndex,
          cell: payload.column.field ? payload.row[payload.column.field] : '',
          data: payload.row,
        }" />
    </template>
  </Column>
</template>
<script setup lang="ts">
  import { computed, useAttrs, type VNode } from 'vue';

  import { Column, type VxeGridPropTypes } from '@blueking/vxe-table';

  import { columnConfig } from './adapter';
  import RenderCell from './components/RenderCell';
  import RenderHead from './components/RenderHead';

  interface Slot {
    header?: () => VNode;
    default?: (params: { row: any }) => VNode;
  }

  const props = withDefaults(defineProps<VxeGridPropTypes.Column>(), {
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
