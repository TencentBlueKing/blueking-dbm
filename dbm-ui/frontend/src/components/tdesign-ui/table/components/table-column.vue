<template>
  <div
    :[TABLE_COLUMN_ID_ATTRIBUTE]="id"
    :cok-key="colKey"
    hidden
    style="display: none" />
</template>
<script lang="ts" setup>
  import type { PrimaryTableCellParams, PrimaryTableCol, TableCol, TableRowData, TNode } from 'tdesign-vue-next';
  import { computed, onBeforeUnmount, onMounted, useId } from 'vue';

  import { useTableInject } from '../hooks/use-table-inject';
  import type { BkUiTableCol } from '../types/table';
  import { TABLE_COLUMN_ID_ATTRIBUTE } from '../utils/constant';

  // eslint-disable-next-line vue/no-unused-properties
  const props = withDefaults(defineProps<BkUiTableCol>(), {
    resizable: true,
  });

  const slots = defineSlots<{
    default(props: PrimaryTableCellParams<any>): TNode<PrimaryTableCellParams<TableRowData>>;
    title(props: { col: PrimaryTableCol; colIndex: number }): TNode;
  }>();
  const tableInject = useTableInject();
  const id = useId();

  const state = computed(() => ({
    ...props,
    cell: (typeof slots.default === 'function' ? (_, data) => slots.default(data) : props.cell) as TableCol['cell'],
    title: (typeof slots.title === 'function' ? (_, data) => slots.title(data) : props.title) as TableCol['title'],
    // fix: 修复使用 title slots 时在 column-settings 中无法显示列名的问题
    titleText: typeof props.title === 'string' ? props.title : props.colKey!,
  }));

  onMounted(() => {
    tableInject.value?.addColumnProps(id, state);
  });
  onBeforeUnmount(() => {
    tableInject.value?.deleteColumn(id);
  });
</script>
