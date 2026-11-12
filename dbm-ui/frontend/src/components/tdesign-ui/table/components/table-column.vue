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
  <div
    :[TABLE_COLUMN_ID_ATTRIBUTE]="id"
    :cok-key="colKey"
    hidden
    style="display: none" />
</template>
<script lang="ts" setup>
  import _ from 'lodash';
  import type { PrimaryTableCellParams, PrimaryTableCol, TableCol } from 'tdesign-vue-next';
  import { computed, onBeforeUnmount, onMounted, useId, type VNode } from 'vue';

  import { useTableInject } from '../hooks/use-table-inject';
  import type { BkUiTableCol, IRegisteredColumnProps } from '../types/table';
  import { TABLE_COLUMN_ID_ATTRIBUTE } from '../utils/constant';

  // eslint-disable-next-line vue/no-unused-properties
  const props = withDefaults(defineProps<BkUiTableCol>(), {
    // 显式 undefined 跳过布尔转换，否则缺省会变成 false，tdesign 表头不再跟随 ellipsis 省略
    ellipsisTitle: undefined,
    resizable: true,
  });

  // 插槽函数返回的是渲染结果（VNode 数组），不是 tdesign 的渲染函数 TNode
  const slots = defineSlots<{
    default(props: PrimaryTableCellParams<any>): VNode[];
    title(props: { col: PrimaryTableCol; colIndex: number }): VNode[];
  }>();
  const tableInject = useTableInject();
  const id = useId();

  // 保持引用稳定，避免每次取值都生成新函数导致列配置被判定为变化
  const renderCell: TableCol['cell'] = (h, data) => slots.default(data);
  const renderTitle: TableCol['title'] = (h, data) => slots.title(data);

  const getColumnState = (): IRegisteredColumnProps => ({
    ...props,
    cell: typeof slots.default === 'function' ? renderCell : props.cell,
    title: typeof slots.title === 'function' ? renderTitle : props.title,
    // fix: 修复使用 title slots 时在 column-settings 中无法显示列名的问题
    titleText: typeof props.title === 'string' ? props.title : props.colKey!,
  });

  // 模板上以字面量形式传入的对象（如 filter）每次渲染都是新引用，
  // 深比较后内容不变则沿用旧引用，避免反向使表格的列配置失效造成递归更新
  const state = computed<IRegisteredColumnProps>((oldValue) => {
    const latest = getColumnState();
    return oldValue && _.isEqual(latest, oldValue) ? oldValue : latest;
  });

  onMounted(() => {
    tableInject?.addColumnProps(id, state);
  });
  onBeforeUnmount(() => {
    tableInject?.deleteColumn(id);
  });
</script>
