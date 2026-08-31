<template>
  <div>
    <component
      :is="
        h(
          PrimaryTable,
          {
            filterIcon: () => filterIcon,
            sortIcon: () => sortIcon,
            // tdesign 仅在 filterRow === null 时关闭过滤行，过滤条件统一由外部搜索栏承载
            filterRow: null as any,
            ...attrs,
            ...customProps,
            class: {
              [attrs.class?.toString() || '']: true,
              [tableFontSizeClass]: true,
              [tableSizeClass]: true,
              't-table__custom-scroll': needCustomScroll,
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
    <CustomScroll v-if="needCustomScroll" />
  </div>
</template>

<script setup lang="ts">
  import { PrimaryTable } from 'tdesign-vue-next';
  import baseTableProps from 'tdesign-vue-next/es/table/base-table-props';
  import primaryTableProps from 'tdesign-vue-next/es/table/primary-table-props';
  import { h, useAttrs, useTemplateRef } from 'vue';

  import { useColumnsSettings } from '../hooks/use-columns-settings';
  import { useTableExpose } from '../hooks/use-table-expose';
  import { type BkUiTableCol, commonTableProps, type PrimaryTableRefExpose } from '../types/table';

  import CustomScroll from './custom-scroll.vue';
  import { filterIcon, sortIcon } from './icons';

  defineOptions({
    name: 'PrimaryTable',
    inheritAttrs: false,
  });
  const props = defineProps({
    ...baseTableProps,
    ...primaryTableProps,
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

  const tableRef = useTemplateRef<PrimaryTableRefExpose>('tableRef');
  const tableColumnRef = useTemplateRef<HTMLDivElement>('tableColumnRef');

  const { columnController, customProps, displayColumns, onDisplayColumnsChange, tableFontSizeClass, tableSizeClass } =
    useColumnsSettings(props, tableColumnRef);

  useTableExpose<PrimaryTableRefExpose>(tableRef);

  defineExpose<PrimaryTableRefExpose>();
</script>
<style lang="less">
  @import './table.less';
</style>
