<!--
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 *
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 *
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 *
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed
 * on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for
 * the specific language governing permissions and limitations under the License.
-->

<template>
  <tr ref="rowRoot">
    <slot />
  </tr>
</template>
<script lang="ts">
  import _ from 'lodash';
  import { inject, type InjectionKey, onBeforeUnmount, onMounted, provide } from 'vue';

  import type { IContext as IColumnContext } from './Column.vue';
  import { tableInjectKey } from './Index.vue';

  export const injectKey: InjectionKey<{
    getColumnIndex: () => number;
    getRowIndex: () => number;
    registerColumn: (column: IColumnContext) => void;
    unregisterColumn: (columnKey: string) => void;
  }> = Symbol.for('bk-editable-table-row');
</script>
<script setup lang="ts">
  const tableContext = inject(tableInjectKey);

  const rowRootRef = useTemplateRef<HTMLElement>('rowRoot');

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
    getColumnIndex,
    getRowIndex,
    registerColumn,
    unregisterColumn,
  });

  onMounted(() => {
    tableContext?.registerRow(columnList, rowRootRef.value!);
  });

  onBeforeUnmount(() => {
    tableContext?.unregisterRow(columnList);
  });
</script>
