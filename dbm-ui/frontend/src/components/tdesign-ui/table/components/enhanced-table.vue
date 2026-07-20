<template>
  <component
    :is="
      h(
        EnhancedTable,
        {
          filterIcon: () => filterIcon,
          sortIcon: () => sortIcon,
          ...attrs,
          ...customProps,
          class: {
            [attrs.class?.toString() || '']: true,
            [tableFontSizeClass]: true,
            [tableSizeClass]: true,
          },
          columnController,
          displayColumns,
          onDisplayColumnsChange,
        },
        slots,
      )
    "
    ref="tableRef" />
  <div
    ref="tableColumnRef"
    hidden
    style="display: none">
    <slot />
  </div>
</template>

<script setup lang="ts">
  import { EnhancedTable } from 'tdesign-vue-next';
  import baseTableProps from 'tdesign-vue-next/es/table/base-table-props';
  import enhancedTableProps from 'tdesign-vue-next/es/table/enhanced-table-props';
  import primaryTableProps from 'tdesign-vue-next/es/table/primary-table-props';
  import { h, useAttrs, useTemplateRef } from 'vue';

  import { useColumnsSettings } from '../hooks/use-columns-settings';
  import { useTableExpose } from '../hooks/use-table-expose';
  import { type BkUiTableCol, commonTableProps, type EnhancedTableRefExpose } from '../types/table';

  import { filterIcon, sortIcon } from './icons';

  defineOptions({
    name: 'EnhancedTable',
    inheritAttrs: false,
  });
  const props = defineProps({
    ...baseTableProps,
    ...primaryTableProps,
    ...enhancedTableProps,
    ...commonTableProps,
  });
  const {
    bkUiAppearanceSettings,
    default: defaultSlots,
    ...slots
  } = defineSlots<{
    bkUiAppearanceSettings(): void;
    default(): { props: BkUiTableCol }[];
  }>();
  const attrs = useAttrs();
  const tableRef = useTemplateRef<EnhancedTableRefExpose>('tableRef');
  const tableColumnRef = useTemplateRef<HTMLDivElement>('tableColumnRef');

  const { columnController, customProps, displayColumns, onDisplayColumnsChange, tableFontSizeClass, tableSizeClass } =
    useColumnsSettings(props, tableColumnRef);
  useTableExpose<EnhancedTableRefExpose>(tableRef);
  defineExpose<EnhancedTableRefExpose>();
</script>
<style lang="less">
  @import './table';
</style>
