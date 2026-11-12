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

import _ from 'lodash';
import type { TableProps } from 'tdesign-vue-next';
import { computed, type ExtractPropTypes, type h, type Ref, shallowRef, useSlots, watch } from 'vue';

import ColumnSettings from '../components/column-settings.vue';
import FilterMultiple from '../components/filter-multiple.vue';
import FilterSingle from '../components/filter-single.vue';
import type {
  BkUiSettings,
  BkUiSettingsChangePayload,
  BkUiTableCol,
  commonTableProps,
  FontSizeEnum,
  IRegisteredColumnProps,
  RowSizeEnum,
} from '../types/table';
import {
  getSettingsFields,
  reorderTableColumns,
  resolveColumnSettings,
  type ResolvedColumnSettings,
} from '../utils/column-settings';
import { BKUI_SETTINGS_COLUMN_NAME, BUILT_IN_COLUMN_KEYS, TABLE_COLUMN_ID_ATTRIBUTE } from '../utils/constant';
import { deleteUndefinedProps } from '../utils/utils';

import { useTableProvide } from './use-table-inject';

const customFilterComponent = (columnList: TableProps['columns']) => {
  return columnList?.map((columnItem): BkUiTableCol => {
    const filter = columnItem.filter;
    if (!filter) {
      return columnItem;
    }
    const isSingle = filter.type === 'single';

    return {
      ...columnItem,
      filter: {
        ...filter,
        // 单选 / 多选换成带搜索的自定义面板，type 置空后 tdesign 才会改用 component
        ...((isSingle || filter.type === 'multiple') && {
          component: isSingle ? FilterSingle : FilterMultiple,
          // 单选且不带确认按钮时，选中即确认并收起弹层
          confirmEvents: isSingle && !filter.showConfirmAndReset ? ['onChange'] : undefined,
          props: {
            list: filter.list || [],
            ...filter.props,
          },
          type: undefined,
        }),
        popupProps: {
          ...filter.popupProps,
          attach: 'body',
          placement: 'bottom',
        },
      },
    };
  });
};

export const useColumnsSettings = (
  props: {
    bkUiSettings?: BkUiSettings;
  } & ExtractPropTypes<typeof commonTableProps> &
    TableProps,
  tableColumnRef: Ref<HTMLDivElement | null>,
) => {
  const slots = useSlots();
  const tableColumnsMap = shallowRef<Record<string, Ref<IRegisteredColumnProps>>>({});
  const tableColumns = computed<BkUiTableCol[]>(() => {
    if (props.columns?.length) {
      return props.columns;
    }
    if (!slots.default || Object.keys(tableColumnsMap.value).length === 0) {
      return [];
    }

    const list: BkUiTableCol[] = [];
    Array.from(tableColumnRef.value?.querySelectorAll(`[${TABLE_COLUMN_ID_ATTRIBUTE}]`) || [])
      .map((node) => node.getAttribute(TABLE_COLUMN_ID_ATTRIBUTE) as string)
      .forEach((columnId) => {
        if (columnId && tableColumnsMap.value[columnId]) {
          list.push(tableColumnsMap.value[columnId]?.value as BkUiTableCol);
        }
      });
    return list;
  });
  useTableProvide({
    addColumnProps: (id: string, columnProps: Ref<IRegisteredColumnProps>) => {
      const newMap = {
        ...tableColumnsMap.value,
        [id]: columnProps,
      };
      tableColumnsMap.value = newMap;
    },
    deleteColumn: (id: string) => {
      const newMap = {
        ...tableColumnsMap.value,
      };
      delete newMap[id];
      tableColumnsMap.value = newMap;
    },
  });
  const isBkuiSettingsControl = computed(() => {
    return Boolean(props.bkUiSettings);
  });

  const settingsFields = computed(() => getSettingsFields(tableColumns.value, props.bkUiSettings));
  const fontSize = shallowRef<FontSizeEnum>(props.bkUiSettings?.fontSize || 'medium');
  const rowSize = shallowRef<RowSizeEnum>(props.bkUiSettings?.rowSize || props.size || 'medium');
  // 当前生效的列配置来源：外部传入的配置，或组件内确认过、外部尚未回写的配置；外部配置变化后以外部为准
  const rawSettings = shallowRef<Pick<BkUiSettings, 'checked' | 'order'>>();

  // 只监听外部配置本身：列定义变化（列 props 更新、列增删）不会重置 rawSettings，沿用组件内已确认的配置
  watch(
    () => props.bkUiSettings,
    (bkUiSettings) => {
      rawSettings.value = bkUiSettings;
      fontSize.value = bkUiSettings?.fontSize || 'medium';
      rowSize.value = bkUiSettings?.rowSize || props.size || 'medium';
    },
    {
      immediate: true,
    },
  );

  // 内容不变时保持引用，避免列配置重建导致 tdesign 重置列宽
  const localColumnSettings = computed<ResolvedColumnSettings>((oldValue) => {
    const latest = resolveColumnSettings(settingsFields.value, rawSettings.value);
    return oldValue && _.isEqual(latest, oldValue) ? oldValue : latest;
  });

  // 启用 bkUiSettings 时由设置面板决定显示哪些列；未启用时 displayColumns 原样交给 tdesign
  const displayColumns = computed(() =>
    isBkuiSettingsControl.value
      ? Array.from(new Set(localColumnSettings.value.checked.concat(BUILT_IN_COLUMN_KEYS)))
      : props.displayColumns,
  );

  const orderedColumns = computed(() => reorderTableColumns(tableColumns.value, localColumnSettings.value.order));

  const lastDisplayColumnColKey = computed(() => {
    if (!displayColumns.value) {
      return orderedColumns.value.at(-1)?.colKey;
    }
    const displayColumnSet = new Set(displayColumns.value);
    return orderedColumns.value.filter((item) => item.colKey && displayColumnSet.has(item.colKey)).at(-1)?.colKey;
  });

  // 列配置单独成 computed，只依赖列相关状态。
  // 若跟着 customProps 一起在 data 等无关 props 变化时重算，
  // tdesign 会因为 columns 引用变化重置列宽，丢失用户拖拽的宽度
  const finalColumns = computed(() => {
    const columns = [...orderedColumns.value];

    if (isBkuiSettingsControl.value) {
      columns.push({
        align: 'center',
        colKey: BKUI_SETTINGS_COLUMN_NAME,
        fixed: 'right',
        minWidth: '40px',
        resizable: false,
        thClassName: 'bkui-table-custom-setting-col',
        title: (createElement: typeof h) => {
          return createElement(
            ColumnSettings,
            {
              columns: localColumnSettings.value.fields,
              displayColumns: localColumnSettings.value.checked,
              fontSize: fontSize.value,
              hasCheckAll: props.bkUiSettings?.hasCheckAll,
              onColumnControllerVisibleChange: (v: boolean, trigger: 'cancel' | 'confirm' | 'open') => {
                props.onColumnControllerVisibleChange?.(v, { trigger });
              },
              onConfirm: (settings: BkUiSettingsChangePayload) => {
                rawSettings.value = {
                  checked: settings.columns,
                  order: settings.order,
                };
                fontSize.value = settings.fontSize;
                rowSize.value = settings.rowSize;
                props.onDisplayColumnsChange?.(localColumnSettings.value.checked);
                props.onBkUiSettingsChange?.({
                  columns: localColumnSettings.value.checked,
                  fontSize: fontSize.value,
                  order: localColumnSettings.value.order,
                  rowSize: rowSize.value,
                });
              },
              rowSize: rowSize.value,
            },
            {
              appearanceSettings: () => slots.bkUiAppearanceSettings?.(),
            },
          );
        },
        width: '40px',
      });
    }

    return customFilterComponent(columns);
  });

  const rowspanAndColspan: NonNullable<TableProps['rowspanAndColspan']> = ({ col, colIndex, row, rowIndex }) => {
    if (
      isBkuiSettingsControl.value &&
      lastDisplayColumnColKey.value &&
      col.colKey === lastDisplayColumnColKey.value &&
      col.fixed !== 'left'
    ) {
      return {
        colspan: col.fixed === 'right' ? 1 : 2,
        rowspan: 1,
      };
    }
    return props.rowspanAndColspan ? props.rowspanAndColspan({ col, colIndex, row, rowIndex }) : {};
  };

  const customProps = computed<
    {
      bkUiSettings?: BkUiSettings;
    } & TableProps
  >(() =>
    deleteUndefinedProps({
      ...props,
      columns: finalColumns.value,
      // tdesign 只要收到该函数就会在每次 data / columns 变化时逐单元格计算合并，无需合并时不传
      rowspanAndColspan: isBkuiSettingsControl.value || props.rowspanAndColspan ? rowspanAndColspan : undefined,
    }),
  );

  const columnController = computed<TableProps['columnController']>(() =>
    isBkuiSettingsControl.value ? undefined : props.columnController,
  );
  const tableSizeClass = computed(() => {
    if (rowSize.value === 'mini') {
      return 't-size-xs';
    }
    return `t-size-${rowSize.value.charAt(0).toLowerCase()}`;
  });
  const tableFontSizeClass = computed(() => {
    return `t-font-size-${fontSize.value.charAt(0).toLowerCase()}`;
  });
  // 未启用 bkUiSettings 时走 tdesign 原生列控制，变更原样转给调用方
  const onDisplayColumnsChange = (columns: NonNullable<TableProps['displayColumns']>) => {
    props.onDisplayColumnsChange?.(columns);
  };
  return {
    columnController,
    customProps,
    displayColumns,
    onDisplayColumnsChange,
    tableFontSizeClass,
    tableSizeClass,
  };
};
