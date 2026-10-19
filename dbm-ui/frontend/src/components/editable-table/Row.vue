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
  import type { InjectionKey } from 'vue';

  import type { IContext as IColumnContext } from './Column.vue';
  import { tableInjectKey } from './Index.vue';

  export const injectKey: InjectionKey<{
    getRowIndex: () => number;
    registerColumn: (column: IColumnContext) => void;
    unregisterColumn: (uniqueKey: string) => void;
  }> = Symbol.for('bk-editable-table-row');
</script>
<script setup lang="ts">
  const tableContext = inject(tableInjectKey);

  const rowRootRef = useTemplateRef<HTMLElement>('rowRoot');

  const columnList: IColumnContext[] = [];

  // 列组件在 tr 中的 DOM 锚点：td 未渲染（被合并或尚未计算合并状态）时是 v-if 留下的注释节点
  const getColumnAnchor = (column: IColumnContext) => column.instance.subTree.el as Node | null;

  // 列 key 按列在行内的位置分配，保证同一列在各行一致；列宽、合并计数、表头 data-name 都依赖它
  const syncColumnKey = () => {
    columnList.forEach((column, index) => column.updateKey(index));
  };

  // 列的挂载顺序不一定与 DOM 顺序一致（如 v-if 后加入的列），按 DOM 位置插入保证列序正确
  const registerColumn = (column: IColumnContext) => {
    const anchor = getColumnAnchor(column);
    const index = anchor
      ? columnList.findIndex((item) => {
          const itemAnchor = getColumnAnchor(item);
          // 找到第一个排在新列之后的已注册列
          return Boolean(itemAnchor && anchor.compareDocumentPosition(itemAnchor) & Node.DOCUMENT_POSITION_FOLLOWING);
        })
      : -1;
    if (index > -1) {
      columnList.splice(index, 0, column);
    } else {
      columnList.push(column);
    }
    syncColumnKey();
    tableContext?.updateRow();
  };

  const unregisterColumn = (uniqueKey: string) => {
    _.remove(columnList, (item) => item.uniqueKey === uniqueKey);
    syncColumnKey();
    tableContext?.updateRow();
  };

  const getRowIndex = () => tableContext?.getAllColumnList().findIndex((item) => item === columnList) as number;

  provide(injectKey, {
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
