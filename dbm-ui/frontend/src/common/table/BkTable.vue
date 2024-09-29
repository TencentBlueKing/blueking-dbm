<template>
  <div class="bk-vxe-table">
    <VxeTable
      ref="table"
      v-bind="realProps"
      @cell-click="handleCellClick"
      @cell-dblclick="handleCellDbclick"
      @cell-mouseenter="handleCellMouseenter"
      @cell-mouseleave="handleCellMouseleave"
      @filter-change="handleFilterChange"
      @scroll="handleScroll"
      @sort-change="handleSortChange">
      <template v-if="isRowSelectEnable">
        <VxeColumn
          fixed="left"
          :min-width="60"
          :resizable="false"
          :width="60">
          <BkCheckbox />
        </VxeColumn>
      </template>
      <slot />
      <template
        v-for="(columnItem, index) in columns"
        :key="index">
        <VxeColgroup
          v-if="columnItem.children"
          :title="columnItem.label">
          <template
            v-for="(columnChildrenItem, childrenIndex) in columnItem.children"
            :key="childrenIndex">
            <BkTableColumn v-bind="columnChildrenItem" />
          </template>
        </VxeColgroup>
        <BkTableColumn
          v-else
          v-bind="columnItem" />
      </template>
      <!-- @vue-ignore -->
      <template
        v-if="slots.prepend"
        #prepend>
        <slot name="prepend" />
      </template>
      <!-- @vue-ignore -->
      <template
        v-if="showSettings"
        #settingColumn>
        <SettingColumn
          :get-table="getTable"
          :is-show="showSettings"
          :settings="settings"
          @change="handleSettingChange">
          <slot name="setting" />
        </SettingColumn>
      </template>
      <template
        v-if="slots.empty"
        #empty>
        <slot name="empty" />
      </template>
      <!-- @vue-ignore -->
      <template
        v-if="pagination"
        #append>
        <div class="bk-vxe-table-pagination-wrapper">
          <Pagination
            v-bind="paginationConfig"
            @change="handlePaginationChange"
            @limit-change="handlePaginationLimitChange" />
        </div>
      </template>
    </VxeTable>
  </div>
</template>
<script setup lang="ts" generic="T extends Record<any, any>">
  import { Pagination } from 'bkui-vue';
  import { computed, reactive, useAttrs, useTemplateRef, type VNode } from 'vue';

  import {
    VxeColgroup,
    VxeColumn,
    type VxeGridProps,
    type VxeGridPropTypes,
    VxeTable,
    type VxeTableDefines,
  } from '@blueking/vxe-table';

  import { tableConfig } from './adapter';
  import BkTableColumn from './BkTableColumn.vue';
  import SettingColumn, { type ISettings } from './components/setting-column/Index.vue';

  import '@blueking/vxe-table/lib/style.css';
  import 'vxe-pc-ui/lib/style.css';
  /* eslint-disable vue/no-unused-properties */
  interface Props {
    data: T[];
    isRowSelectEnable?: boolean;
    pagination?: {
      current: number;
      count: number;
      limit?: number;
      limitList?: number[];
      showLimit?: boolean;
      type?: 'default' | 'compact';
      align?: 'left' | 'center' | 'right';
      small?: boolean;
    };
    showSettings?: boolean;
  }

  interface Emits {
    // vxe-table 支持的事件
    (e: 'sort-change', params: VxeTableDefines.SortChangeEventParams<T>): void;
    (e: 'filter-change', params: VxeTableDefines.FilterChangeEventParams<T>): void;
    (e: 'cell-click', params: VxeTableDefines.CellClickEventParams<T>): void;
    (e: 'cell-dbclick', params: VxeTableDefines.CellDblclickEventParams<T>): void;
    (e: 'scroll', params: VxeTableDefines.ScrollEventParams<T>): void;
    (e: 'cell-mouseenter', params: VxeTableDefines.CellMouseenterEventParams<T>): void;
    (e: 'cell-mouseleave', params: VxeTableDefines.CellMouseleaveEventParams<T>): void;
    // bk-table 自定义事件
    (e: 'setting-change', params: ISettings): void;
    (e: 'scroll-bottom'): void;
    (e: 'column-filter', params: { column: VxeGridPropTypes.Column; field: string; checked: string[] }): void;
    (e: 'column-sort', params: { column: VxeGridPropTypes.Column; field: string; type: string | null }): void;
    (e: 'row-mouse-enter' | 'row-mouse-leave', params: { event: Event; row: T; index: number }): void;
    (e: 'page-limit-change', params: number): void;
    (e: 'page-value-change', params: number): void;
  }

  interface Slots {
    default?: () => VNode | VNode[];
    prepend?: () => VNode;
    empty?: () => VNode;
    setting?: () => VNode;
  }

  const props = withDefaults(defineProps<Props & VxeGridProps<T>>(), {
    // 自定义功能
    pagination: undefined,
    isRowSelectEnable: false,
    showSettings: false,
    settings: undefined,
    // vxe table props 默认值
    align: 'left',
    animat: true,
    autoResize: true,
    border: false,
    columnKey: false,
    columnConfig: () => ({
      useKey: true,
      isHover: true,
      resizable: true,
      width: undefined,
      minWidth: 'auto',
    }),
    delayHover: 250,
    emptyText: undefined,
    filterConfig: () => ({
      remote: true,
      confirmButtonText: '确认',
      resetButtonText: '重置',
    }),
    fit: true,
    footerAlign: undefined,
    headerAlign: 'left',
    highlightCurrentColumn: undefined,
    highlightCurrentRow: undefined,
    highlightHoverColumn: undefined,
    highlightHoverRow: undefined,
    keepSource: undefined,
    minHeight: 40,
    padding: true,
    round: false,
    rowConfig: () => ({
      isHover: true,
    }),
    rowId: undefined,
    showFooterOverflow: true,
    showHeader: true,
    showHeaderOverflow: true,
    showOverflow: 'tooltip',
    size: 'small',
    sortConfig: () => ({
      remote: true,
      trigger: 'cell',
    }),
    stripe: false,
  });
  const emits = defineEmits<Emits>();
  const slots = defineSlots<Slots>();

  defineOptions({
    name: 'BkVxeTable',
  });

  const attrs = useAttrs();

  const settings = defineModel<ISettings>('settings', {
    default: undefined,
    required: false,
  });

  const tableRef = useTemplateRef('table');

  const paginationConfig = reactive({
    layout: ['total', 'limit', 'list'],
    location: 'left',
    count: 10,
    align: 'left',
    modelValue: 1,
  });

  const realProps = computed(() =>
    tableConfig({
      ...props,
      ...attrs,
    }),
  );

  const getTable = () => tableRef.value;

  watch(
    () => props.pagination,
    () => {
      if (!props.pagination) {
        return;
      }
      Object.assign(paginationConfig, {
        ...props.pagination,
        modelValue: props.pagination.current,
      });
    },
    {
      immediate: true,
      deep: true,
    },
  );

  const handleSettingChange = (payload: ISettings) => {
    settings.value = payload;
    emits('setting-change', {
      checked: payload.checked,
      fields: payload.fields,
      size: payload.size,
    });
  };

  const handleSortChange = (payload: VxeTableDefines.SortChangeEventParams) => {
    emits('column-sort', {
      column: payload.column,
      field: payload.field,
      type: payload.order,
    });
    emits('sort-change', payload);
  };

  const handleFilterChange = (payload: VxeTableDefines.FilterChangeEventParams) => {
    emits('column-filter', {
      column: Object.assign({}, payload.column, {
        filter: {
          list: payload.column.filters.map((item) => ({
            text: item.label,
            value: item.value,
          })),
        },
      }),
      field: payload.field,
      checked: payload.values,
    });
    emits('filter-change', payload);
  };

  const handleCellClick = (payload: VxeTableDefines.CellClickEventParams) => {
    emits('cell-click', payload);
  };

  const handleCellDbclick = (payload: VxeTableDefines.CellDblclickEventParams) => {
    emits('cell-dbclick', payload);
  };

  const handleScroll = (payload: VxeTableDefines.ScrollEventParams) => {
    emits('scroll', payload);
    if (payload.bodyHeight + payload.scrollTop + 10 > payload.scrollHeight) {
      emits('scroll-bottom');
    }
  };

  const handleCellMouseenter = (payload: VxeTableDefines.CellMouseenterEventParams<T>) => {
    emits('row-mouse-enter', {
      event: payload.$event,
      row: payload.row,
      index: payload.rowIndex,
    });
    emits('cell-mouseenter', payload);
  };

  const handleCellMouseleave = (payload: VxeTableDefines.CellMouseleaveEventParams<T>) => {
    emits('row-mouse-leave', {
      event: payload.$event,
      row: payload.row,
      index: payload.rowIndex,
    });
    emits('cell-mouseleave', payload);
  };

  const handlePaginationChange = (value: number) => {
    emits('page-value-change', value);
  };

  const handlePaginationLimitChange = (value: number) => {
    emits('page-limit-change', value);
  };
</script>
<style lang="less">
  @import './style/vxe-table-path.less';

  .bk-vxe-table {
    .vxe-table--body-wrapper,
    .vxe-table--fixed-left-body-wrapper,
    .vxe-table--fixed-right-body-wrapper {
      &::-webkit-scrollbar {
        width: 12px;
        height: 12px;
      }

      &::-webkit-scrollbar-thumb {
        border-radius: 6px;
      }
    }
  }

  .bk-vxe-table-pagination-wrapper {
    padding: 14px 16px;

    .bk-pagination-limit {
      margin-right: auto;
    }
  }
</style>
