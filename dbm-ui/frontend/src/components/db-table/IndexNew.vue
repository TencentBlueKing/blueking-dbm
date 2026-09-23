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
          defaultSort: urlDefaultSort ?? inhertProps.defaultSort,
          maxHeight: tableMaxHeight,
          showHeader: true,
          resizable: true,
          titleEllipsis: true,
          ellipsis: true,
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
        <DbPagination
          v-bind="pagination"
          :layout="['total', 'limit', 'list']"
          :model-value="pagination.current"
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
        </DbPagination>
      </div>
    </BkLoading>
  </div>
</template>
<script setup lang="tsx">
  import _ from 'lodash';
  import {
    type FilterValue,
    type SortOptions,
    type TableProps,
    type TableRowData,
    type TableSort,
  } from 'tdesign-vue-next';
  import type { Ref, VNode } from 'vue';
  import type { ComponentProps } from 'vue-component-type-helpers';

  import type { IRequestPayload } from '@services/http';
  import type { ListBase } from '@services/types';

  import { useUrlSearch } from '@hooks';

  import EmptyStatus from '@components/empty-status/EmptyStatus.vue';
  import { type BkUiSettingsChangePayload, PrimaryTable } from '@components/tdesign-ui/table';

  import { getOffset } from '@utils';

  import { useTimeoutFn } from '@vueuse/core';

  import { usePagination } from './hooks/use-pagination.ts';
  import { useSelect } from './hooks/use-select.tsx';

  export interface Props {
    bkUiSettings?: ComponentProps<typeof PrimaryTable>['bkUiSettings'];
    // 没提供默认使用浏览器窗口的高度 window.innerHeight
    containerHeight?: number;
    // 自定义排序方法
    customSortMethod?: (sort: TableSort) => unknown;
    dataSource: (params: any, payload?: IRequestPayload) => Promise<any>;
    defaultLimit?: number;
    disableSelectMethod?: (data: any) => boolean | string;
    filterValue?: Record<string, string | string[]>;
    // 固定分页，不通过容器高度自动计算
    fixedPagination?: boolean;
    // 开启 10s 自动轮询，列表需要实时刷新状态时用，支持动态切换
    polling?: boolean;
    // 是否解析 URL query 参数
    releateUrlQuery?: boolean;
    // 是否允许行点击选中
    rowClickSelectable?: boolean;
    rowKey: string;
    // 是否开启远程分页
    selectable?: boolean;
    // 默认选中
    selected?: unknown[];
    // 是否单选
    // eslint-disable-next-line vue/no-unused-properties
    selectSingle?: boolean;
    // 是否显示跨页全选（透传给 useSelect）
    // eslint-disable-next-line vue/no-unused-properties
    showSelectAllPage?: boolean;
  }

  export interface Emits {
    (e: 'requestSuccess', value: any): void;
    (e: 'clearSearch'): void;
    (e: 'selection', key: string[], list: any[]): void;
    (e: 'sortChange', sort: TableSort, options: SortOptions<TableRowData>): void;
    (e: 'filterChange', filterValue: FilterValue): void;
    (e: 'bkUiSettingsChange', payload: BkUiSettingsChangePayload): void;
  }

  export interface Slots {
    bkUiAppearanceSettings: () => VNode;
    default: () => VNode;
    empty: () => VNode;
  }

  export interface Exposes {
    fetchAllData: <T>() => Promise<Array<T>>;
    fetchData: (params?: Record<string, any>, loading?: boolean) => void;
    getData: <T>() => Array<T>;
    loading: Ref<boolean>;
    removeSelectByKey: (key: string) => void;
    updateTableHeight: (containerHeight?: number) => void;
    updateTableKey: () => void;
  }

  const props = withDefaults(defineProps<Props & TableProps>(), {
    bkUiSettings: undefined,
    containerHeight: undefined,
    customSortMethod: undefined,
    defaultLimit: undefined,
    disableSelectMethod: () => false,
    filterValue: undefined,
    fixedPagination: false,
    polling: false,
    releateUrlQuery: false,
    rowClickSelectable: false,
    selectable: false,
    selected: () => [],
    selectSingle: false,
    showSelectAllPage: true,
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
    delete baseProps['polling'];
    // @ts-expect-error 删除不存在的 props
    delete baseProps['releateUrlQuery'];
    // @ts-expect-error 删除不存在的 props
    delete baseProps['rowClickSelectable'];
    // @ts-expect-error 删除不存在的 props
    delete baseProps['selectable'];
    // @ts-expect-error 删除不存在的 props
    delete baseProps['selectSingle'];
    // @ts-expect-error 删除不存在的 props
    delete baseProps['showSelectAllPage'];
    delete baseProps['onChange'];
    delete baseProps['onFilterChange'];
    // @ts-expect-error 删除不存在的 props
    delete baseProps['dataSource'];
    // @ts-expect-error 删除 TableProps 废弃 props
    delete baseProps['allowResizeColumnWidth'];
    return baseProps;
  });

  const router = useRouter();
  const { getSearchParams, replaceSearchParams } = useUrlSearch();

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

  const {
    onChange: handlePageValueChange,
    onLimitChange: handlePageLimitChange,
    pagination,
  } = usePagination({
    callback: () => {
      isPaginationChangeFetch = true;
      fetchListData();
    },
    defaultLimit: props.defaultLimit,
  });

  const { handleClearWholeSelect, handleSelect, selectColumn, selectedRowMap } = useSelect(
    props,
    tableData,
    pagination,
    {
      callback: () => {
        triggerSelection();
      },
    },
  );

  const isSearching = ref(false);
  const isRequestFailed = ref(false);
  const selectedCount = computed(() => Object.keys(selectedRowMap.value).length);

  let paramsMemo = {};
  let sortParams = {};

  let isReady = false;
  // URL 联动时首次请求沿用 URL 上的页码，不重置到第一页
  let isKeepUrlPage = false;
  let isSortChangeFetch = false;
  let isPaginationChangeFetch = false;
  // 请求序号，只接受最后一次请求的结果，避免快速切换筛选或分页时旧响应覆盖新数据
  let fetchSeq = 0;
  // 首屏那次请求不是用户改条件触发的，清空选中会把 selected 传进来的默认选中项冲掉
  let isFirstFetch = true;

  /**
   * 判断是否处于搜索状态
   */
  const getSearchingStatus = () => {
    const searchKeys: string[] = [];
    for (const [key, value] of Object.entries(paramsMemo)) {
      if (value === '' || value === undefined) continue;

      searchKeys.push(key);
    }

    return searchKeys.length > 0;
  };

  const triggerSelection = () => {
    emits('selection', Object.keys(selectedRowMap.value), Object.values(selectedRowMap.value));
  };

  const fetchListData = (loading = true, isPolling = false) => {
    // 用户触发的请求先停掉待执行的轮询，避免轮询请求顶掉本次请求
    if (!isPolling) {
      handleStopPolling();
    }
    // 触发来源在发起时就定下来，不能等响应回来再读，否则会被后续请求改写或因请求失败而残留
    const isKeepSelection = isPaginationChangeFetch || isSortChangeFetch || isPolling;
    isSortChangeFetch = false;
    isPaginationChangeFetch = false;
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
      const currentFetchSeq = ++fetchSeq;
      props
        .dataSource(params, payload)
        .then((data) => {
          if (currentFetchSeq !== fetchSeq) {
            return;
          }
          tableData.value = data;
          pagination.count = data.count;
          isSearching.value = getSearchingStatus();
          isRequestFailed.value = false;

          if (!props.fixedPagination && props.releateUrlQuery) {
            router.replace({
              query: replaceSearchParams(params, false),
            });
          }

          if (!isKeepSelection && !isFirstFetch) {
            handleClearWholeSelect();
          }
          isFirstFetch = false;

          if (props.polling && data.results.length > 0) {
            handleStartPolling();
          }

          emits('requestSuccess', data);
        })
        .catch((error) => {
          if (currentFetchSeq !== fetchSeq) {
            return;
          }
          console.log('from dbtable error = ', error);
          tableData.value.results = [];
          pagination.count = 0;
          isRequestFailed.value = true;
        })
        .finally(() => {
          if (currentFetchSeq === fetchSeq) {
            isLoading.value = false;
          }
        });
    });
  };

  const { start: handleStartPolling, stop: handleStopPolling } = useTimeoutFn(
    () => {
      fetchListData(false, true);
    },
    10 * 1000,
    // 首次计时由请求成功后发起，创建时不计时
    { immediate: false },
  );

  watch(
    () => props.polling,
    () => {
      if (props.polling) {
        handleStartPolling();
      } else {
        handleStopPolling();
      }
    },
  );

  // 拉取全量数据
  const fetchAllData = async () => {
    const { results } = await props.dataSource({
      limit: -1,
      // 跨页全选要的是当前条件下的全集，offset 必须归零，否则从第 2 页触发会漏掉前面几页
      offset: 0,
      ...paramsMemo,
    });
    return results;
  };

  watch(
    () => props.selected,
    () => {
      selectedRowMap.value = props.selected.reduce<typeof selectedRowMap.value>((acc, item) => {
        return Object.assign(acc, {
          [_.get(item, props.rowKey)]: item,
        });
      }, {});
    },
    {
      immediate: true,
    },
  );

  // 解析 URL 上的分页与排序信息，字段与 fetchListData 写回 URL 的 limit / offset / ordering 对应
  const parseURL = () => {
    if (!props.releateUrlQuery || props.fixedPagination) {
      return;
    }
    const { limit, offset, ordering } = getSearchParams();
    const urlLimit = ~~limit;
    if (urlLimit > 0) {
      pagination.limit = urlLimit;
      pagination.current = Math.floor(~~offset / urlLimit) + 1;
      pagination.limitList = [...new Set([...pagination.limitList, urlLimit])].sort((a, b) => a - b);
    }
    if (ordering) {
      sortParams = { ordering };
    }
    isReady = true;
    isKeepUrlPage = true;
    return ordering
      ? {
          descending: ordering.startsWith('-'),
          sortBy: ordering.replace(/^-/, ''),
        }
      : undefined;
  };

  // 表头排序图标只在首次渲染时读取 defaultSort，URL 需在 setup 阶段解析
  const urlDefaultSort: TableSort | undefined = parseURL();

  // 选中单行
  const handleRowClick = (payload: Parameters<NonNullable<TableProps['onRowClick']>>[number]) => {
    if (!props.rowClickSelectable || !props.selectable) {
      return;
    }
    const targetElement = payload.e.target as HTMLElement;
    // 点击行内按钮、链接、输入框、图标等交互元素时不切换选中
    if (
      targetElement.closest('button, a, input, .bk-button, .t-button, .bk-link, .t-link, .bk-dbm-icon, .db-svg-icon')
    ) {
      return;
    }

    if (props.disableSelectMethod(payload.row)) {
      return;
    }
    // 复用勾选框的处理，单选模式下同样是替换而非累加
    handleSelect(payload.row);
  };

  const handleSortChange = (payload: TableSort) => {
    if (props.customSortMethod) {
      return props.customSortMethod(payload);
    }
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

    isSortChangeFetch = true;
    fetchListData();
  };

  const handleDisplayColumnsChange = (payload: BkUiSettingsChangePayload) => {
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

  const updateTableHeight = (containerHeight = window.innerHeight) => {
    const paginationHeight = 60;
    tableMaxHeight.value = containerHeight - paginationHeight;
    nextTick(() => {
      bkTableRef.value?.refreshTable();
    });
  };

  onMounted(() => {
    calcTableHeight();
  });

  defineExpose<Exposes>({
    // 获取全量数据
    fetchAllData: fetchAllData,
    // 获取远程数据
    fetchData(params = {} as Record<string, any>, loading = true) {
      // URL 联动时首次请求沿用 URL 页码，之后每次都回到第一页
      // 未开启 URL 联动时查询条件变化才回到第一页，条件不变视为原地刷新
      const isParamsChanged = !_.isEqual(paramsMemo, params);
      paramsMemo = {
        ...params,
      };
      if (isKeepUrlPage) {
        isKeepUrlPage = false;
      } else if (isReady || isParamsChanged) {
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
      // selectedRowMap 是 shallowRef，必须整体替换才能触发更新
      const selectedMap = { ...selectedRowMap.value };
      delete selectedMap[key];
      selectedRowMap.value = selectedMap;
    },
    updateTableHeight,
    updateTableKey() {
      tableKey.value = Date.now().toString();
    },
  });
</script>
<style lang="less">
  .db-table {
    .t-table__th-cell-inner {
      display: flex !important;
    }

    .t-checkbox {
      display: flex !important;
    }

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

      // 占满一行，让总条数、每页条数靠左，页码靠右
      .dbm-pagination {
        width: 100%;
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
        top: 1px;
        left: 4px;
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
