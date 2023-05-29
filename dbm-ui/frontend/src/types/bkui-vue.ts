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

import type { DatePicker, Table } from 'bkui-vue';
import type { ISearchItem, ISearchValue } from 'bkui-vue/lib/search-select/utils';
export type { FormItemProps } from 'bkui-vue/lib/form/form-item';

export type DatePickerValues = Array<InstanceType<typeof DatePicker>['$props']['modelValue']>;
export type TableProps = InstanceType<typeof Table>['$props'];

// search-select 组件 types
export type SearchSelectValues = Array<ISearchValue>;
export type SearchSelectValue = ISearchValue;
export type SearchSelectData = Array<ISearchItem>;
export type SearchSelectItem = ISearchItem;

export interface TableColumnRender {
  cell: string,
  data: any,
  row: any,
  column: any,
  index: number,
  rows: any[]
}

export interface TableSelectionData<T> {
  checked: boolean,
  data: T[],
  index: number,
  isAll: boolean,
  row: T
}
