<!--
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 *
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 *
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License athttps://opensource.org/licenses/MIT
 *
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed
 * on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for
 * the specific language governing permissions and limitations under the License.
-->

<template>
  <div
    ref="rootRef"
    class="db-table">
    <BkLoading
      :loading="isLoading"
      :z-index="2">
      <PrimaryTable
        :key="tableKey"
        ref="bkTableRef"
        v-bind="{
          ...inhertProps,
          bkUiSettings,
          filterValue,
          data: tableData.results,
          maxHeight: tableMaxHeight,
          showHeader: true,
          filterRow: null as any,
          resizable: true,
          titleEllipsis: true,
          ellipsis: true
        }"
        @bk-ui-settings-change="handleDisplayColumnsChange"
        @filter-change="handleFilterChanges"
        @row-click="handleRowClick"
        @sort-change="handleSortChange">
        <component
          :is="selectColumn"
          v-if="selectable" />
        <slot />
        <template #empty>
          <slot name="empty">
            <EmptyStatus
              :is-anomalies="isRequestFailed"
              :is-searching="isSearching"
              @clear-search="handleClearFilter"
              @refresh="fetchListData" />
          </slot>
        </template>
        <template #bkUiAppearanceSettings>
          <slot name="bkUiAppearanceSettings" />
        </template>
      </PrimaryTable>
      <div class="table-footer">
        <BkPagination
          v-bind="pagination"
          :layout="['total', 'limit', 'list']"
          @change="handlePageValueChange"
          @limit-change="handlePageLimitChange">
          <template
            v-if="selectedCount > 0"
            #limitAppend>
            <I18nT
              class="ml-8"
              keypath="已选择n条"
              scope="global"
              tag="span">
              <span class="number">{{ selectedCount }}</span>
            </I18nT>
          </template>
        </BkPagination>
      </div>
    </BkLoading>
  </div>
</template>
<script setup lang="tsx">
  import _ from 'lodash';
  import {
    type FilterValue,
    type SortOptions,
    type TableChangeContext,
    type TableChangeData,
    type TableProps,
    type TableRowData,
    type TableSort,
  } from 'tdesign-vue-next';
  import { nextTick, onMounted, type Ref, ref, type VNode } from 'vue';
  import type { ComponentProps } from 'vue-component-type-helpers';
  import { useRouter } from 'vue-router';

  import { PrimaryTable } from '@blueking/tdesign-ui';

  import type { IRequestPayload } from '@services/http';
  import type { ListBase } from '@services/types';

  import { useUrlSearch } from '@hooks';

  import EmptyStatus from '@components/empty-status/EmptyStatus.vue';

  import { getOffset } from '@utils';

  import { usePagination } from './hooks/use-pagination.ts';
  import { useSelect } from './hooks/use-select.tsx';

  export interface Props {
    bkUiSettings?: ComponentProps<typeof PrimaryTable>['bkUiSettings'];
    // 没提供默认使用浏览器窗口的高度 window.innerHeight
    containerHeight?: number;
    dataSource: (params: any, payload?: IRequestPayload) => Promise<any>;
    disableSelectMethod?: (data: any) => boolean | string;
    filterValue?: Record<string, string>;
    // 固定分页，不通过容器高度自动计算
    fixedPagination?: boolean;
    // 是否解析 URL query 参数
    releateUrlQuery?: boolean;
    // 是否允许行点击选中
    rowClickSelectable?: boolean;
    rowKey: string;
    // 是否开启远程分页
    selectable?: boolean;
    // 默认选中
    selected?: any[];
    // 是否单选
    // eslint-disable-next-line vue/no-unused-properties
    selectSingle?: boolean;
  }

  export interface Emits {
    (e: 'requestSuccess', value: any): void;
    (e: 'requestFinished', value: any[]): void;
    (e: 'clearSearch'): void;
    (e: 'selection', key: string[], list: any[]): void;
    (e: 'change', data: TableChangeData, context: TableChangeContext<TableRowData>): void;
    (e: 'sortChange', sort: TableSort, options: SortOptions<TableRowData>): void;
    (e: 'filterChange', filterValue: FilterValue): void;
    (e: 'bkUiSettingsChange', payload: Props['bkUiSettings']): void;
  }

  export interface Slots {
    bkUiAppearanceSettings: () => VNode;
    default: () => VNode;
    empty: () => VNode;
    expandRow: () => VNode;
    setting: () => VNode;
  }

  export interface Exposes {
    clearSelected: () => void;
    fetchAllData: <T>() => Promise<Array<T>>;
    fetchData: (params?: Record<string, any>, loading?: boolean) => void;
    getData: <T>() => Array<T>;
    loading: Ref<boolean>;
    removeSelectByKey: (key: string) => void;
    updateTableKey: () => void;
  }

  const props = withDefaults(defineProps<Props & TableProps>(), {
    bkUiSettings: undefined,
    containerHeight: undefined,
    disableSelectMethod: () => false,
    filterValue: undefined,
    fixedPagination: false,
    releateUrlQuery: false,
    rowClickSelectable: false,
    selectable: false,
    selected: () => [],
    selectSingle: false,
  });

  const emits = defineEmits<Emits>();

  defineSlots<Slots>();

  const inhertProps = computed(() => {
    const baseProps = { ...props };
    delete baseProps['containerHeight'];
    // @ts-expect-error 删除不存在的 props
    delete baseProps['disableSelectMethod'];
    // @ts-expect-error 删除不存在的 props
    delete baseProps['fixedPagination'];
    // @ts-expect-error 删除不存在的 props
    delete baseProps['releateUrlQuery'];
    // @ts-expect-error 删除不存在的 props
    delete baseProps['rowClickSelectable'];
    // @ts-expect-error 删除不存在的 props
    delete baseProps['selectable'];
    // @ts-expect-error 删除不存在的 props
    delete baseProps['selectSingle'];
    delete baseProps['onChange'];
    delete baseProps['onFilterChange'];
    // @ts-expect-error 删除不存在的 props
    delete baseProps['dataSource'];
    // @ts-expect-error 删除 TableProps 废弃 props
    delete baseProps['allowResizeColumnWidth'];
    return baseProps;
  });

  const router = useRouter();

  const rootRef = ref();
  const bkTableRef = ref();
  const tableKey = ref(Date.now().toString());
  const isLoading = ref(false);
  const tableMaxHeight = ref<number | 'auto'>('auto');
  const tableData = ref<ListBase<any>>({
    count: 0,
    next: '',
    permission: {},
    previous: '',
    results: [],
  });

  const { handleClearWholeSelect, selectColumn, selectedRowMap } = useSelect(props, tableData, {
    callback: () => {
      triggerSelection();
    },
  });

  const {
    onChange: handlePageValueChange,
    onLimitChange: handlePageLimitChange,
    pagination,
  } = usePagination({
    callback: () => {
      fetchListData();
    },
  });

  const isSearching = ref(false);
  const isRequestFailed = ref(false);
  const isWholeChecked = ref(false);
  const selectedCount = computed(() => Object.keys(selectedRowMap.value).length);

  let paramsMemo = {};
  let sortParams = {};

  let isReady = false;
  let isPaginationChangeFetch = false;

  /**
   * 判断是否处于搜索状态
   */
  const getSearchingStatus = () => {
    const searchKeys: string[] = [];
    for (const [key, value] of Object.entries(paramsMemo)) {
      if (['', undefined].includes(value as any)) continue;

      searchKeys.push(key);
    }

    return searchKeys.length > 0;
  };

  const { getSearchParams, replaceSearchParams } = useUrlSearch();

  const triggerSelection = () => {
    emits('selection', Object.keys(selectedRowMap.value), Object.values(selectedRowMap.value));
  };

  const fetchListData = (loading = true) => {
    Promise.resolve().then(() => {
      isLoading.value = loading;
      const params = {
        limit: pagination.limit,
        offset: (pagination.current - 1) * pagination.limit,
        ...paramsMemo,
        ...sortParams,
      };

      const payload = {};
      // API 参数需要和 URL 联动基本可以确认是页面级别的列表
      // 这个时候权限提示交互为页面嵌入的方式
      if (props.releateUrlQuery) {
        Object.assign(payload, {
          permission: 'page',
        });
      }
      isRequestFailed.value = false;
      props
        .dataSource(params, payload)
        .then((data) => {
          tableData.value = data;
          pagination.count = data.count;
          isSearching.value = getSearchingStatus();
          isRequestFailed.value = false;

          if (!props.fixedPagination && props.releateUrlQuery) {
            router.replace({
              query: replaceSearchParams(params, false),
            });
          }

          if (!isPaginationChangeFetch) {
            isWholeChecked.value = false;
            isPaginationChangeFetch = false;
            triggerSelection();
          }

          emits('requestSuccess', data);
        })
        .catch((error) => {
          console.log('from dbtable error = ', error);
          tableData.value.results = [];
          pagination.count = 0;
          isRequestFailed.value = true;
        })
        .finally(() => {
          isLoading.value = false;
        });
    });
  };

  // 拉取全量数据
  const fetchAllData = async () => {
    const { results } = await props.dataSource({
      limit: -1,
      offset: (pagination.current - 1) * pagination.limit,
      ...paramsMemo,
    });
    return results;
  };

  watch(
    () => props.selected,
    () => {
      selectedRowMap.value = props.selected.reduce<Record<string, any>>((acc, item) => {
        return Object.assign(acc, {
          [item[props.rowKey]]: item,
        });
      }, {});
    },
    {
      immediate: true,
    },
  );

  // 解析 URL 上面的分页信息
  const parseURL = () => {
    if (!props.releateUrlQuery || props.fixedPagination) {
      return;
    }
    const { offset, order_field: orderField, order_type: orderType, page_size: limit } = getSearchParams();
    if (offset && limit) {
      pagination.current = ~~offset;
      pagination.limit = ~~limit;
      pagination.limitList = [...new Set([...pagination.limitList, pagination.limit])].sort((a, b) => a - b);
    }
    if (orderField && orderType) {
      paramsMemo = {
        order_field: orderField,
        order_type: orderType,
      };
    }
    isReady = true;
  };

  // 选中单行
  const handleRowClick = (payload: Parameters<NonNullable<TableProps['onRowClick']>>[number]) => {
    if (!props.rowClickSelectable || !props.selectable) {
      return;
    }
    const targetElement = payload.e.target as HTMLElement;
    if (/bk-button/.test(targetElement.className)) {
      return;
    }

    if (props.disableSelectMethod(payload.row)) {
      return;
    }
    const selectedMap = { ...selectedRowMap.value };
    if (!selectedMap[_.get(payload.row, props.rowKey)]) {
      selectedMap[_.get(payload.row, props.rowKey)] = payload.row;
    } else {
      delete selectedMap[_.get(payload.row, props.rowKey)];
    }
    isWholeChecked.value = false;
    selectedRowMap.value = selectedMap;

    triggerSelection();
  };

  const handleSortChange = (payload: TableSort) => {
    if (Array.isArray(payload)) {
      return;
    }
    if (payload) {
      sortParams = {
        ordering: payload.descending ? `-${payload.sortBy}` : payload.sortBy,
      };
    } else {
      sortParams = {};
    }

    fetchListData();
  };

  const handleDisplayColumnsChange = (payload: Props['bkUiSettings']) => {
    emits('bkUiSettingsChange', payload);
  };

  const handleFilterChanges = (filterValue: FilterValue) => {
    emits('filterChange', filterValue);
  };

  // 情况搜索条件
  const handleClearFilter = () => {
    emits('filterChange', {});
    emits('clearSearch');
  };

  const calcTableHeight = () => {
    if (props.fixedPagination) {
      return;
    }
    nextTick(() => {
      const top = props.containerHeight ? 0 : getOffset(rootRef.value).top;
      const totalHeight = props.containerHeight ? props.containerHeight : window.innerHeight;
      const pageOffsetBottom = props.containerHeight ? 0 : 20;
      const paginationHeight = 60;

      const tableRowTotalHeight = totalHeight - top - pageOffsetBottom - paginationHeight;
      tableMaxHeight.value = tableRowTotalHeight;
    });
  };

  onMounted(() => {
    parseURL();
    calcTableHeight();
  });

  defineExpose<Exposes>({
    // 清空选择
    clearSelected() {
      handleClearWholeSelect();
    },
    // 获取全量数据
    fetchAllData: fetchAllData,
    // 获取远程数据
    fetchData(params = {} as Record<string, any>, loading = true) {
      paramsMemo = {
        ...params,
      };
      if (isReady) {
        pagination.current = 1;
      }
      fetchListData(loading);
    },
    // 获取表格渲染数据
    getData() {
      return tableData.value.results;
    },
    loading: isLoading,
    removeSelectByKey(key: string) {
      delete selectedRowMap.value[key];
    },
    updateTableKey() {
      tableKey.value = Date.now().toString();
    },
  });
</script>
<style lang="less">
  .db-table {
    .table-footer {
      position: relative;
      z-index: 1;
      display: flex;
      height: 60px;
      padding: 0 16px;
      margin-top: -1px;
      background: #fff;
      border-top: 1px solid var(--td-component-border);
      align-items: center;

      .bk-pagination {
        width: 100%;

        & > .is-last {
          margin-left: auto;
        }
      }
    }
  }

  .db-table-select-cell {
    position: relative;
    display: flex;
    align-items: center;

    .db-table-whole-check {
      position: relative;
      display: inline-block;
      width: 16px;
      height: 16px;
      vertical-align: middle;
      cursor: pointer;
      background-color: #fff;
      border: 1px solid #3a84ff;
      border-radius: 2px;

      &::after {
        position: absolute;
        top: 2px;
        left: 5px;
        width: 4px;
        height: 8px;
        border: 2px solid #3a84ff;
        border-top: 0;
        border-left: 0;
        content: '';
        transform: rotate(45deg);
      }
    }

    .select-menu-flag {
      margin-left: 4px;
      font-size: 18px;
      color: #63656e;
    }
  }

  [data-theme~='db-table-select-menu'] {
    padding: 0 !important;

    .db-table-select-plan {
      padding: 5px 0;

      .plan-item {
        padding: 0 10px;
        font-size: 12px;
        line-height: 26px;
        cursor: pointer;

        &:hover {
          color: #3a84ff;
          background-color: #eaf3ff;
        }

        &.is-selected {
          color: #3a84ff;
          background-color: #f4f6fa;
        }
      }
    }
  }
</style>
