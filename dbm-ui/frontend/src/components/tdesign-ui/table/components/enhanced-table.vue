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
  <component
    :is="
      h(
        EnhancedTable,
        {
          filterIcon: renderFilterIcon,
          sortIcon: renderSortIcon,
          ...attrs,
          ...customProps,
          class: normalizeClass([attrs.class, tableFontSizeClass, tableSizeClass]),
          columnController,
          displayColumns,
          onDisplayColumnsChange,
        },
        getTableSlots(),
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
  import { h, normalizeClass, useAttrs, useTemplateRef } from 'vue';

  import { useColumnsSettings } from '../hooks/use-columns-settings';
  import { useTableExpose } from '../hooks/use-table-expose';
  import { type BkUiTableCol, commonTableProps, type EnhancedTableRefExpose } from '../types/table';

  import { renderFilterIcon, renderSortIcon } from './icons';

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
  const slots = defineSlots<{
    bkUiAppearanceSettings(): void;
    default(): { props: BkUiTableCol }[];
  }>();
  const attrs = useAttrs();

  // 渲染时再取，动态插槽（如 v-if 控制的 #empty）增删后才能同步转发
  const getTableSlots = () => {
    const { bkUiAppearanceSettings, default: defaultSlots, ...tableSlots } = slots;
    return tableSlots;
  };
  const tableRef = useTemplateRef<EnhancedTableRefExpose>('tableRef');
  const tableColumnRef = useTemplateRef<HTMLDivElement>('tableColumnRef');

  const { columnController, customProps, displayColumns, onDisplayColumnsChange, tableFontSizeClass, tableSizeClass } =
    useColumnsSettings(props, tableColumnRef);
  useTableExpose<EnhancedTableRefExpose>(tableRef);
  defineExpose<EnhancedTableRefExpose>();
</script>
