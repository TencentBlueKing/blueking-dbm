<template>
  <tr ref="rowRootRef">
    <slot />
  </tr>
</template>
<script lang="ts">
  import _ from 'lodash';
  import { inject, type InjectionKey, onBeforeMount, onMounted, provide } from 'vue';

  import type { IContext as IColumnContext } from './Column.vue';
  import { tableInjectKey } from './Index.vue';

  export const injectKey: InjectionKey<{
    registerColumn: (column: IColumnContext) => void;
    unregisterColumn: (columnKey: string) => void;
    getColumnIndex: () => number;
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

  provide(injectKey, {
    registerColumn,
    unregisterColumn,
    getColumnIndex,
  });

  onMounted(() => {
    tableContext?.registerRow(columnList);
  });

  onBeforeMount(() => {
    tableContext?.unregisterRow(columnList);
  });
</script>
