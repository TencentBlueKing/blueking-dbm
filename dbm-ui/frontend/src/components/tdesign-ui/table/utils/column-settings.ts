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

import type { BkUiSettings, BkUiSettingsField, BkUiTableCol } from '../types/table';

import { BKUI_COLUMN_ROW_OPERATION_KEY, BUILT_IN_COLUMN_KEYS } from './constant';

export interface ResolvedColumnSettings {
  checked: string[];
  fields: BkUiSettingsField[];
  order: string[];
}

const unique = (values: string[]) => {
  return Array.from(new Set(values));
};

export const getSettingsFields = (columns: BkUiTableCol[], settings?: BkUiSettings) => {
  const columnMap = new Map(columns.map((column) => [column.colKey, column]));
  const disabledSet = new Set(settings?.disabled);
  const columnFields = columns
    .filter((column) => column.colKey && !BUILT_IN_COLUMN_KEYS.includes(column.colKey))
    .map((column) => ({
      field: column.colKey!,
      label:
        // @ts-expect-error titleText 是 TableColumn 组件为设置面板注入的扩展属性
        column.titleText ?? (typeof column.title === 'string' ? column.title : column.colKey!),
    }));
  // 外部配置的字段在前，其余列按定义顺序补在后面；同名字段由下方 fieldsMap 以先出现的为准
  const sourceFields = (settings?.fields ?? []).filter((field) => columnMap.has(field.field)).concat(columnFields);

  const fieldsMap = new Map<string, BkUiSettingsField>();
  sourceFields.forEach((field) => {
    if (!field.field || BUILT_IN_COLUMN_KEYS.includes(field.field) || fieldsMap.has(field.field)) {
      return;
    }
    fieldsMap.set(field.field, {
      disabled: field.disabled ?? disabledSet.has(field.field),
      field: field.field,
      label: field.label,
    });
  });

  return Array.from(fieldsMap.values());
};

export const resolveColumnSettings = (
  fields: BkUiSettingsField[],
  settings?: Pick<BkUiSettings, 'checked' | 'order'>,
): ResolvedColumnSettings => {
  const fieldKeys = fields.map((field) => field.field);
  const validSet = new Set(fieldKeys);
  const disabledKeys = fields.filter((field) => field.disabled).map((field) => field.field);
  // 禁用列固定在最前，其后按已保存的顺序，未保存过的列按定义顺序补在最后
  const order = unique(
    disabledKeys.concat(
      (settings?.order ?? []).filter((field) => validSet.has(field)),
      fieldKeys,
    ),
  );
  // 未配置选中列时默认全选，禁用列始终选中
  const checkedSet = new Set((settings?.checked ?? fieldKeys).concat(disabledKeys));

  const fieldMap = new Map(fields.map((field) => [field.field, field]));

  return {
    checked: order.filter((field) => checkedSet.has(field)),
    fields: order.map((field) => fieldMap.get(field)!),
    order,
  };
};

export const reorderTableColumns = (columns: BkUiTableCol[], order: string[]) => {
  const leftBuiltInColumns: BkUiTableCol[] = [];
  const normalColumns: BkUiTableCol[] = [];

  columns.forEach((column) => {
    if (column.colKey === BKUI_COLUMN_ROW_OPERATION_KEY) {
      return;
    }
    if (column.colKey && BUILT_IN_COLUMN_KEYS.includes(column.colKey)) {
      leftBuiltInColumns.push(column);
      return;
    }
    normalColumns.push(column);
  });

  const normalColumnMap = new Map(
    normalColumns.filter((column) => column.colKey).map((column) => [column.colKey!, column]),
  );
  const orderedColumns = order.map((field) => normalColumnMap.get(field)).filter((column) => column !== undefined);
  const orderedSet = new Set(orderedColumns);

  const reorderedColumns = leftBuiltInColumns
    .concat(orderedColumns)
    .concat(normalColumns.filter((column) => !orderedSet.has(column)));
  let reorderedIndex = 0;

  return columns.map((column) => {
    if (column.colKey === BKUI_COLUMN_ROW_OPERATION_KEY) {
      return column;
    }
    return reorderedColumns[reorderedIndex++];
  });
};
