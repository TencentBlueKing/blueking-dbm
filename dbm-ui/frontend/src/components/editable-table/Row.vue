<template>
  <tr ref="rowRootRef">
    <slot />
  </tr>
</template>
<script lang="ts">
  import _ from 'lodash';
  import { inject, type InjectionKey, onBeforeUnmount, onMounted, provide } from 'vue';

  import type { IContext as IColumnContext } from './Column.vue';
  import { tableInjectKey } from './Index.vue';

  export const injectKey: InjectionKey<{
    registerColumn: (column: IColumnContext) => void;
    unregisterColumn: (columnKey: string) => void;
    getColumnIndex: () => number;
    getRowIndex: () => number;
  }> = Symbol.for('bk-editable-table-row');
</script>
<script setup lang="ts">
  const tableContext = inject(tableInjectKey);

  const rowRootRef = ref<HTMLElement>();

  const columnList: IColumnContext[] = [];

  const registerColumn = (column: IColumnContext) => {
    const index = _.indexOf(rowRootRef.value!.children, column.el);
    if (index > -1) {
      columnList.splice(index, 0, column);
    } else {
      columnList.push(column);
    }

    tableContext?.updateRow();
  };

  const unregisterColumn = (columnKey: string) => {
    _.remove(columnList, (item) => item.key === columnKey);
    tableContext?.updateRow();
  };

  const getColumnIndex = (() => {
    let columnIndex = 0;
    return () => {
      columnIndex = columnIndex + 1;
      return columnIndex;
    };
  })();

  const getRowIndex = () => tableContext?.getAllColumnList().findIndex((item) => item === columnList) as number;

  provide(injectKey, {
    registerColumn,
    unregisterColumn,
    getColumnIndex,
    getRowIndex,
  });

  onMounted(() => {
    tableContext?.registerRow(columnList);
  });

  onBeforeUnmount(() => {
    tableContext?.unregisterRow(columnList);
  });
</script>
