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
  const configuredFieldSet = new Set(settings?.fields?.map((field) => field.field));
  const sourceFields = (settings?.fields ?? [])
    .filter((field) => columnMap.has(field.field))
    .concat(columnFields.filter((field) => !configuredFieldSet.has(field.field)));

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
  const definitionOrder = fields.map((field) => field.field);
  const validFields = new Set(definitionOrder);
  const disabledOrder = fields.filter((field) => field.disabled).map((field) => field.field);
  const disabledSet = new Set(disabledOrder);
  const savedOrder = unique(settings?.order ?? []).filter((field) => validFields.has(field));
  const savedOrderSet = new Set(savedOrder);
  const normalOrder =
    savedOrder.length > 0
      ? savedOrder
          .filter((field) => !disabledSet.has(field))
          .concat(definitionOrder.filter((field) => !disabledSet.has(field) && !savedOrderSet.has(field)))
      : definitionOrder.filter((field) => !disabledSet.has(field));
  const order = disabledOrder.concat(normalOrder);
  const checkedSet = new Set((settings?.checked ?? definitionOrder).filter((field) => validFields.has(field)));

  fields.forEach((field) => {
    if (field.disabled) {
      checkedSet.add(field.field);
    }
  });

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
