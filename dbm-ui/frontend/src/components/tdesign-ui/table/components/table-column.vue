<template>
  <div
    :[TABLE_COLUMN_ID_ATTRIBUTE]="id"
    :cok-key="colKey"
    hidden
    style="display: none" />
</template>
<script lang="ts" setup>
  import _ from 'lodash';
  import type { PrimaryTableCellParams, PrimaryTableCol, TableCol, TableRowData, TNode } from 'tdesign-vue-next';
  import { onBeforeUnmount, onMounted, shallowRef, useId, watch } from 'vue';

  import { useTableInject } from '../hooks/use-table-inject';
  import type { BkUiTableCol, IRegisteredColumnProps } from '../types/table';
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

  // 保持引用稳定，避免每次取值都生成新函数导致列配置被判定为变化
  const renderCell = ((h, data) => slots.default(data)) as TableCol['cell'];
  const renderTitle = ((h, data) => slots.title(data)) as TableCol['title'];

  const getColumnState = (): IRegisteredColumnProps => ({
    ...props,
    cell: typeof slots.default === 'function' ? renderCell : props.cell,
    title: typeof slots.title === 'function' ? renderTitle : props.title,
    // fix: 修复使用 title slots 时在 column-settings 中无法显示列名的问题
    titleText: typeof props.title === 'string' ? props.title : props.colKey!,
  });

  const state = shallowRef(getColumnState());

  // 模板上以字面量形式传入的对象（如 filter）每次渲染都是新引用，
  // 深比较后再更新，避免反向使表格的列配置失效造成递归更新
  watch(getColumnState, (latest) => {
    if (!_.isEqual(latest, state.value)) {
      state.value = latest;
    }
  });

  onMounted(() => {
    tableInject.value?.addColumnProps(id, state);
  });
  onBeforeUnmount(() => {
    tableInject.value?.deleteColumn(id);
  });
</script>
