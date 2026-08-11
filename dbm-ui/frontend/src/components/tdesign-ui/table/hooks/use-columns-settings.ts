import type { TableProps } from 'tdesign-vue-next';
import { computed, type ExtractPropTypes, type h, type Ref, shallowRef, useSlots, watch } from 'vue';

import ColumnSettings from '../components/column-settings.vue';
import FilterMultiple from '../components/filter-multiple.vue';
import FilterSingle from '../components/filter-single.vue';
import type {
  BkUiSettings,
  BkUiTableCol,
  commonTableProps,
  FontSizeEnum,
  IRegisteredColumnProps,
  RowSizeEnum,
} from '../types/table';
import { getSettingsFields, reorderTableColumns, resolveColumnSettings } from '../utils/column-settings';
import { BKUI_SETTINGS_COLUMN_NAME, BUILT_IN_COLUMN_KEYS, TABLE_COLUMN_ID_ATTRIBUTE } from '../utils/constant';
import { camelCaseArray, deleteUndefinedProps, makeMap } from '../utils/utils';

import { useTableProvide } from './use-table-inject';

const customFilterComponent = (columnList: TableProps['columns']) => {
  return columnList?.map((columnItem) => {
    const filter = columnItem.filter;
    if (!filter) {
      return columnItem;
    }
    const latestColumn = Object.assign({}, columnItem);

    if (['multiple', 'single'].includes(filter.type as string)) {
      Object.assign(latestColumn, {
        filter: {
          ...filter,
          component: filter.type === 'single' ? FilterSingle : FilterMultiple,
          confirmEvents: filter.showConfirmAndReset ? undefined : filter.type === 'single' ? ['onChange'] : undefined,
          props: {
            list: filter.list || [],
            ...(filter.props || { not: 'empty' }),
          },
          type: undefined,
        },
      });
    }

    Object.assign(latestColumn, {
      filter: {
        ...latestColumn.filter,
        popupProps: Object.assign({}, filter.popupProps || {}, {
          attach: 'body',
          placement: 'bottom',
        }),
      },
    });

    return latestColumn;
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
    return camelCaseArray(list);
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
  const localColumnSettings = shallowRef(resolveColumnSettings([]));
  const fontSize = shallowRef<FontSizeEnum>(props.bkUiSettings?.fontSize || 'medium');
  const rowSize = shallowRef<RowSizeEnum>(props.bkUiSettings?.rowSize || props.size || 'medium');

  watch(
    () => [props.displayColumns, props.bkUiSettings, settingsFields.value] as const,
    () => {
      localColumnSettings.value = resolveColumnSettings(settingsFields.value, {
        checked: props.displayColumns?.length ? (props.displayColumns as string[]) : props.bkUiSettings?.checked,
        order: props.bkUiSettings?.order,
      });
      fontSize.value = props.bkUiSettings?.fontSize || 'medium';
      rowSize.value = props.bkUiSettings?.rowSize || props.size || 'medium';
    },
    {
      immediate: true,
    },
  );

  const displayColumns = computed(() => {
    if (isBkuiSettingsControl.value || props.displayColumns) {
      return Array.from(new Set(localColumnSettings.value.checked.concat(BUILT_IN_COLUMN_KEYS)));
    }

    return undefined;
  });

  const customProps = computed<
    {
      bkUiSettings?: BkUiSettings;
    } & TableProps
  >(() => {
    const columns = reorderTableColumns(tableColumns.value, localColumnSettings.value.order);

    let lastDisplayColumnColKey = columns.at(-1)?.colKey;
    if (displayColumns.value) {
      const displayColumnsMap = makeMap(displayColumns.value as string[]);
      lastDisplayColumnColKey = columns.filter((item) => item.colKey && displayColumnsMap[item.colKey]).at(-1)?.colKey;
    }

    if (isBkuiSettingsControl.value) {
      columns.push({
        align: 'center',
        colKey: BKUI_SETTINGS_COLUMN_NAME,
        fixed: 'right',
        minWidth: '40px',
        resizable: false,
        thClassName: '__table-custom-setting-col__',
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
              onConfirm: (settings: {
                columns: string[];
                fontSize: FontSizeEnum;
                order: string[];
                rowSize: RowSizeEnum;
              }) => {
                localColumnSettings.value = resolveColumnSettings(settingsFields.value, {
                  checked: settings.columns,
                  order: settings.order,
                });
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
              order: localColumnSettings.value.order,
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

    return deleteUndefinedProps({
      ...props,
      columns: customFilterComponent(columns),
      rowspanAndColspan: ({ col, colIndex, row, rowIndex }) => {
        if (
          isBkuiSettingsControl.value &&
          lastDisplayColumnColKey &&
          col.colKey === lastDisplayColumnColKey &&
          col.fixed !== 'left'
        ) {
          return {
            colspan: col.fixed === 'right' ? 1 : 2,
            rowspan: 1,
          };
        }
        return props.rowspanAndColspan ? props.rowspanAndColspan({ col, colIndex, row, rowIndex }) : {};
      },
    });
  });

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
  const onDisplayColumnsChange = (columns: NonNullable<TableProps['displayColumns']>) => {
    localColumnSettings.value = resolveColumnSettings(settingsFields.value, {
      checked: columns as string[],
      order: localColumnSettings.value.order,
    });
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
