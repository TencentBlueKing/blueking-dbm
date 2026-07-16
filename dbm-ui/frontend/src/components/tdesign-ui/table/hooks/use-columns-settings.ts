import type { TableCol, TableProps } from 'tdesign-vue-next';
import { computed, type ComputedRef, type ExtractPropTypes, type h, type Ref, shallowRef, useSlots, watch } from 'vue';

import ColumnSettings from '../components/column-settings.vue';
import FilterMultiple from '../components/filter-multiple.vue';
import FilterSingle from '../components/filter-single.vue';
import type { BkUiSettings, commonTableProps, FontSizeEnum, IRegisteredColumnProps, RowSizeEnum } from '../types/table';
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
  const tableColumnsMap = shallowRef<Record<string, ComputedRef<IRegisteredColumnProps>>>({});
  const tableColumns = computed<TableCol[]>(() => {
    if (props.columns?.length) {
      return props.columns;
    }
    if (!slots.default || Object.keys(tableColumnsMap.value).length === 0) {
      return [];
    }

    const list: TableCol[] = [];
    Array.from(tableColumnRef.value?.querySelectorAll(`[${TABLE_COLUMN_ID_ATTRIBUTE}]`) || [])
      .map((node) => node.getAttribute(TABLE_COLUMN_ID_ATTRIBUTE) as string)
      .forEach((columnId) => {
        if (columnId && tableColumnsMap.value[columnId]) {
          list.push(tableColumnsMap.value[columnId]?.value as TableCol);
        }
      });
    return camelCaseArray(list);
  });
  useTableProvide({
    addColumnProps: (id: string, columnProps: ComputedRef<IRegisteredColumnProps>) => {
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

  const customProps = computed<
    {
      bkUiSettings?: BkUiSettings;
    } & TableProps
  >(() => {
    const columns = [...tableColumns.value];

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
              columns: settingsColumns.value,
              displayColumns: localSettingsColumnesValue.value,
              fontSize: fontSize.value,
              hasCheckAll: props.bkUiSettings?.hasCheckAll,
              onChange: () => {
                props.onBkUiSettingsChange?.({
                  columns: localSettingsColumnesValue.value as string[],
                  fontSize: fontSize.value,
                  rowSize: rowSize.value,
                });
              },
              onColumnControllerVisibleChange: (v: boolean, trigger: 'cancel' | 'confirm' | 'open') => {
                props.onColumnControllerVisibleChange?.(v, { trigger });
              },
              onDisplayColumnsChange: (cols) => {
                localSettingsColumnesValue.value = cols;
                props.onDisplayColumnsChange?.(cols);
              },

              'onUpdate:fontSize'(size) {
                fontSize.value = size;
              },
              'onUpdate:rowSize'(size) {
                rowSize.value = size || 'medium';
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

  const settingsColumns = computed(() => {
    const { disabled, fields } = props.bkUiSettings || {};
    if (fields?.length) {
      return fields.map((item) => {
        return {
          disabled: item.disabled ?? !!disabled?.includes?.(item.field),
          field: item.field,
          label: item.label,
        };
      });
    }
    return customProps.value
      .columns!.map((item) => {
        if (!item.colKey || BUILT_IN_COLUMN_KEYS.includes(item.colKey)) {
          return undefined;
        }
        return {
          disabled: !!disabled?.includes?.(item.colKey),
          field: item.colKey,
          // @ts-expect-error titleText 是解决部分场景问题的自定义属性，通过 TableColumn 组件注入
          label: item.titleText ?? (typeof item.title === 'string' ? item.title! : item.colKey),
        };
      })
      .filter((v) => v !== undefined);
  });

  const localSettingsColumnesValue = shallowRef<NonNullable<TableProps['displayColumns']>>([]);
  watch(
    () => [props.displayColumns, props.bkUiSettings, tableColumns.value],
    () => {
      if (props.displayColumns?.length) {
        localSettingsColumnesValue.value = props.displayColumns;
      } else if (props.bkUiSettings?.checked?.length) {
        localSettingsColumnesValue.value = props.bkUiSettings.checked.concat(props.bkUiSettings.disabled ?? []);
      } else {
        localSettingsColumnesValue.value = tableColumns.value
          .map((item) => item.colKey)
          .filter((item) => item !== undefined) as string[];
      }
    },
    {
      immediate: true,
    },
  );

  const displayColumns = computed(() => {
    if (localSettingsColumnesValue.value.length) {
      return localSettingsColumnesValue.value.concat(BUILT_IN_COLUMN_KEYS);
    }

    return undefined;
  });

  const columnController = computed<TableProps['columnController']>(() =>
    isBkuiSettingsControl.value ? undefined : props.columnController,
  );
  const fontSize = shallowRef<FontSizeEnum>(props.bkUiSettings?.fontSize || 'medium');
  const rowSize = shallowRef<RowSizeEnum>(props.bkUiSettings?.rowSize || customProps.value.size || 'medium');
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
    localSettingsColumnesValue.value = columns;
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
