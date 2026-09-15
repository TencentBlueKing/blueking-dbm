/*
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
 */

import type {
  EnhancedTableProps as TdEnhancedTableProps,
  PrimaryTableProps as TdPrimaryTableProps,
  TableRowData,
} from 'tdesign-vue-next/es/table';

import './theme/_index.less';

import EnhancedTable from './components/enhanced-table.vue';
import PrimaryTable from './components/primary-table.vue';
import TableColumn from './components/table-column.vue';
import type { CommonTableProps } from './types/table';

export type * from './types/table';
export { BaseTable } from 'tdesign-vue-next';
export type * from 'tdesign-vue-next/es/table';
export { EnhancedTable, PrimaryTable, TableColumn };
export const Table = PrimaryTable;
export type EnhancedTableProps<T extends TableRowData = TableRowData> = CommonTableProps & TdEnhancedTableProps<T>;
export type PrimaryTableProps<T extends TableRowData = TableRowData> = CommonTableProps & TdPrimaryTableProps<T>;
export type TableProps<T extends TableRowData = TableRowData> = CommonTableProps & TdPrimaryTableProps<T>;
