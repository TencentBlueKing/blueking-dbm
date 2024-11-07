<template>
  <div class="bk-vxe-table">
    <VxeTable
      ref="table"
      v-bind="realProps"
      @filter-change="handleFilterChange"
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
      <VxeColumn
        fixed="right"
        :min-width="60"
        :resizable="false"
        :width="60">
        <template #header>
          <SettingColumn :get-table="getTable" />
        </template>
      </VxeColumn>
      <!-- @vue-ignore -->
      <template
        v-if="slots.prepend"
        #prepend>
        <slot name="prepend" />
      </template>
      <!-- @vue-ignore -->
      <template
        v-if="false"
        #settingColumn>
        <SettingColumn :get-table="getTable" />
      </template>
      <template
        v-if="slots.empty"
        #empty>
        <slot name="empty" />
      </template>
    </VxeTable>
    <div class="bk-vxe-table-pagination-wrapper">
      <Pagination
        v-bind="paginationConfig"
        @change="handlePaginationChange"
        @limit-change="handlePaginationLimitChange" />
    </div>
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
  import SettingColumn from './components/setting-column/Index.vue';

  import '@blueking/vxe-table/lib/style.css';
  import 'vxe-pc-ui/lib/style.css';
  /* eslint-disable vue/no-unused-properties */
  interface Props {
    isRowSelectEnable?: boolean;
    data: T[];
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
  }

  interface Emits {
    (e: 'column-sort', params: { column: VxeGridPropTypes.Column; field: string; type: string | null }): void;
    (e: 'sort-change', params: VxeTableDefines.SortChangeEventParams): void;
    (e: 'column-filter', params: { column: VxeGridPropTypes.Column; field: string; checked: string[] }): void;
    (e: 'filter-change', params: VxeTableDefines.FilterChangeEventParams): void;
    (e: 'page-limit-change', params: number): void;
    (e: 'page-value-change', params: number): void;
  }

  interface Slots {
    default?: () => VNode | VNode[];
    prepend?: () => VNode;
    empty?: () => VNode;
  }

  const props = withDefaults(defineProps<Props & VxeGridProps<T>>(), {
    pagination: undefined,
    isRowSelectEnable: false,
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
    minHeight: undefined,
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
    }),
    stripe: false,
  });
  const emits = defineEmits<Emits>();
  const slots = defineSlots<Slots>();

  defineOptions({
    name: 'BkVxeTable',
  });

  const attrs = useAttrs();

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

  const handlePaginationChange = (value: number) => {
    emits('page-value-change', value);
  };

  const handlePaginationLimitChange = (value: number) => {
    emits('page-limit-change', value);
  };
</script>
<style lang="less">
  @import './style/vxe-table-path.less';

  .bk-vxe-table-pagination-wrapper {
    padding: 14px 16px;
    background: #fff;
    border: 1px solid #e8eaec;
    border-top: none;

    .bk-pagination-limit {
      margin-right: auto;
    }
  }
</style>
