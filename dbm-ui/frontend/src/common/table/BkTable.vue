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
        <!-- @vue-ignore -->
        <BkTableColumn v-bind="columnItem">
          <!-- @vue-ignore -->
          <template
            v-if="columnItem.renderHead || _.isFunction(columnItem.label)"
            #header>
            <RenderHead
              :column="columnItem"
              :index="index" />
          </template>
          <!-- @vue-ignore -->
          <template
            v-if="columnItem.render"
            #default="params">
            <RenderCell
              :column="columnItem"
              :params="params" />
          </template>
        </BkTableColumn>
      </template>
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
  </div>
</template>
<script setup lang="ts" generic="T extends Record<any, any>">
  import _ from 'lodash';
  import { computed, useTemplateRef, type VNode } from 'vue';

  import {
    VxeColumn,
    type VxeGridProps,
    type VxeGridPropTypes,
    VxeTable,
    type VxeTableDefines,
  } from '@blueking/vxe-table';

  import { tableConfig } from './adapter';
  import BkTableColumn from './BkTableColumn.vue';
  import RenderCell from './components/RenderCell';
  import RenderHead from './components/RenderHead';
  import SettingColumn from './components/setting-column/Index.vue';

  import '@blueking/vxe-table/lib/style.css';
  import 'vxe-pc-ui/lib/style.css';
  /* eslint-disable vue/no-unused-properties */
  interface Props {
    rowClass?: (params: any) => string;
    isRowSelectEnable?: boolean;
    data: T[];
  }

  interface Emits {
    (e: 'column-sort', params: { column: VxeGridPropTypes.Column; field: string; type: string | null }): void;
    (e: 'sort-change', params: VxeTableDefines.SortChangeEventParams): void;
    (e: 'column-filter', params: { column: VxeGridPropTypes.Column; field: string; checked: string[] }): void;
    (e: 'filter-change', params: VxeTableDefines.FilterChangeEventParams): void;
  }

  interface Slots {
    default?: () => VNode | VNode[];
    prepend?: () => VNode;
    empty?: () => VNode;
  }

  const props = withDefaults(defineProps<Props & VxeGridProps<T>>(), {
    rowClass: undefined,
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

  const tableRef = useTemplateRef('table');

  const realProps = computed(() => tableConfig(props));

  const getTable = () => tableRef.value;

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
</script>
<style lang="less">
  @import './style/vxe-table-path.less';
</style>
