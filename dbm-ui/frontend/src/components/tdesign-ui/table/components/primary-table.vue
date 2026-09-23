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
  <div>
    <component
      :is="
        h(
          PrimaryTable,
          {
            filterIcon: renderFilterIcon,
            sortIcon: renderSortIcon,
            // tdesign 仅在 filterRow === null 时关闭过滤行，过滤条件统一由外部搜索栏承载
            filterRow: null as any,
            ...attrs,
            ...customProps,
            class: normalizeClass([
              attrs.class,
              tableFontSizeClass,
              tableSizeClass,
              { 't-table__custom-scroll': needCustomScroll },
            ]),
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
    <CustomScroll v-if="needCustomScroll" />
  </div>
</template>

<script setup lang="ts">
  import { PrimaryTable } from 'tdesign-vue-next';
  import baseTableProps from 'tdesign-vue-next/es/table/base-table-props';
  import primaryTableProps from 'tdesign-vue-next/es/table/primary-table-props';
  import { h, normalizeClass, useAttrs, useTemplateRef } from 'vue';

  import { useColumnsSettings } from '../hooks/use-columns-settings';
  import { useTableExpose } from '../hooks/use-table-expose';
  import { type BkUiTableCol, commonTableProps, type PrimaryTableRefExpose } from '../types/table';

  import CustomScroll from './custom-scroll.vue';
  import { renderFilterIcon, renderSortIcon } from './icons';

  defineOptions({
    name: 'PrimaryTable',
    inheritAttrs: false,
  });
  const props = defineProps({
    ...baseTableProps,
    ...primaryTableProps,
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

  const tableRef = useTemplateRef<PrimaryTableRefExpose>('tableRef');
  const tableColumnRef = useTemplateRef<HTMLDivElement>('tableColumnRef');

  const { columnController, customProps, displayColumns, onDisplayColumnsChange, tableFontSizeClass, tableSizeClass } =
    useColumnsSettings(props, tableColumnRef);

  useTableExpose<PrimaryTableRefExpose>(tableRef);

  defineExpose<PrimaryTableRefExpose>();
</script>
