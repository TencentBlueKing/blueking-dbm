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
    class="audit-render-list">
    <BkLoading
      :loading="isLoading"
      :z-index="2">
      <BkTable
        ref="bkTableRef"
        :columns="columns"
        :data="tableData.results"
        :max-height="tableMaxHeight"
        :pagination="renderPagination"
        :pagination-heihgt="60"
        remote-pagination
        show-overflow-tooltip
        v-bind="$attrs"
        @column-sort="handleColumnSortChange"
        @page-limit-change="handlePageLimitChange"
        @page-value-change="handlePageValueChange">
        <slot />
        <template #expandRow="row">
          <slot
            name="expandRow"
            :row="row" />
        </template>
        <template #empty>
          <EmptyStatus
            :is-anomalies="isAnomalies"
            :is-searching="isSearching"
            @clear-search="handleClearSearch"
            @refresh="fetchListData" />
        </template>
      </BkTable>
    </BkLoading>
  </div>
</template>
<script lang="ts">
  export interface IPagination {
    count: number;
    current: number;
    limit: number;
    limitList: Array<number>;
    align: string,
    layout: Array<string>;
  }
  export interface IPaginationExtra {
    small?: boolean
  }
</script>
<script setup lang="ts">
  import type { Table } from 'bkui-vue';
  import {
    nextTick,
    onMounted,
    reactive,
    type Ref,
    ref,
  } from 'vue';

  import type { ListBase } from '@services/types/common';

  import { useUrlSearch } from '@hooks';

  import { useGlobalBizs } from '@stores';

  import EmptyStatus from '@components/empty-status/EmptyStatus.vue';

  import {
    getOffset,
  } from '@utils';

  interface Props {
    columns: InstanceType<typeof Table>['$props']['columns'],
    dataSource: (params: any)=> Promise<any>,
    fixedPagination?: boolean,
    clearSelection?: boolean,
    paginationExtra?: IPaginationExtra
  }

  interface Emits {
    (e: 'requestSuccess', value: any): void,
    (e: 'requestFinished', value: any[]): void,
    (e: 'clearSearch'): void,
  }

  interface Exposes {
    fetchData: (params: Record<string, any>, baseParams: Record<string, any>) => void,
    getData: <T>() => Array<T>,
    clearSelected: () => void,
    loading: Ref<boolean>,
    bkTableRef: Ref<InstanceType<typeof Table>>
  }

  const props = withDefaults(defineProps<Props>(), {
    fixedPagination: false,
    clearSelection: true,
    paginationExtra: () => ({}),
  });

  const emits = defineEmits<Emits>();

  const { currentBizId } = useGlobalBizs();
  const rootRef = ref();
  const bkTableRef = ref();

  const pagination = reactive<IPagination>({
    count: 0,
    current: 1,
    limit: 10,
    limitList: [10, 20, 50, 100],
    align: 'right',
    layout: ['total', 'limit', 'list'],
    ...props.paginationExtra,
  });
  const renderPagination = computed(() => Object.assign({}, pagination, props.paginationExtra));

  const isLoading = ref(false);
  const tableMaxHeight = ref(0);

  const tableData = ref<ListBase<any>>({
    count: 0,
    next: '',
    previous: '',
    results: [],
  });

  let paramsMemo = {};
  let baseParamsMemo = {};
  let sortParams = {};
  const isSearching = ref(false);
  const isAnomalies = ref(false);

  let isReady = false;

  /**
   * 判断是否处于搜索状态
   */
  const getSearchingStatus = () => {
    const searchKeys: string[] = [];
    const baseParamsKeys = Object.keys(baseParamsMemo);

    for (const [key, value] of Object.entries(paramsMemo)) {
      if (baseParamsKeys.includes(key) || [undefined, ''].includes(value as any)) continue;

      searchKeys.push(key);
    }

    return searchKeys.filter(key => !baseParamsKeys.includes(key)).length > 0;
  };

  const {
    getSearchParams,
    replaceSearchParams,
  } = useUrlSearch();

  const fetchListData = (loading = true) => {
    isReady = true;
    Promise.resolve()
      .then(() => {
        isLoading.value = loading;
        const params = {
          bk_biz_id: currentBizId,
          offset: (pagination.current - 1) * pagination.limit,
          limit: pagination.limit,
          ...paramsMemo,
          ...sortParams,
        };
        props.dataSource(params)
          .then((data) => {
            tableData.value = data;
            pagination.count = data.count;
            isSearching.value = getSearchingStatus();
            isAnomalies.value = false;

            // 默认清空选项
            if (props.clearSelection) {
              bkTableRef.value?.clearSelection?.();
            }

            if (!props.fixedPagination) {
              replaceSearchParams(params);
            }

            emits('requestSuccess', data);
          })
          .catch(() => {
            tableData.value.results = [];
            pagination.count = 0;
            isAnomalies.value = true;
          })
          .finally(() => {
            isLoading.value = false;
            emits('requestFinished', tableData.value.results);
          });
      });
  };

  // 解析 URL 上面的分页信息
  const parseURL = () => {
    if (props.fixedPagination) {
      return;
    }
    const {
      offset,
      page_size: limit,
      order_field: orderField,
      order_type: orderType,
    } = getSearchParams();
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
    isReady = false;
  };

  const handleColumnSortChange = (sortPayload: any) => {
    sortParams = {
      order_field: sortPayload.column.field,
      order_type: sortPayload.type,
    };
    fetchListData();
  };

  // 切换每页条数
  const handlePageLimitChange = (pageLimit: number) => {
    pagination.limit = pageLimit;
    fetchListData();
  };

  // 切换页码
  const handlePageValueChange = (pageValue:number) => {
    pagination.current = pageValue;
    fetchListData();
  };

  // 情况搜索条件
  const handleClearSearch  = () => {
    emits('clearSearch');
  };

  const calcTableHeight = () => {
    if (props.fixedPagination) {
      return;
    }
    nextTick(() => {
      const { top } = getOffset(rootRef.value);
      const windowInnerHeight = window.innerHeight;
      const tableHeaderHeight = 42;
      const paginationHeight = 40;
      const pageOffsetBottom = 48;
      const tableRowHeight = 42;

      const tableRowTotalHeight = windowInnerHeight - top - tableHeaderHeight - paginationHeight - pageOffsetBottom;

      const rowNum = Math.max(Math.floor(tableRowTotalHeight / tableRowHeight), 2);
      const pageLimit = new Set([
        ...pagination.limitList,
        rowNum,
      ]);
      pagination.limit = rowNum;
      pagination.limitList = [...pageLimit].sort((a, b) => a - b);


      tableMaxHeight.value = tableHeaderHeight + rowNum * tableRowHeight + paginationHeight + 3;
    });
  };

  onMounted(() => {
    parseURL();
    calcTableHeight();
  });

  defineExpose<Exposes>({
    fetchData(params = {} as Record<string, any>, baseParams = {} as Record<string, any>, loading = true) {
      paramsMemo = {
        ...params,
        ...baseParams,
      };
      baseParamsMemo = { ...baseParams };
      if (isReady) {
        pagination.current = 1;
      }
      fetchListData(loading);
    },
    getData() {
      return tableData.value.results;
    },
    clearSelected() {
      bkTableRef.value?.clearSelection();
    },
    loading: isLoading,
    bkTableRef,
  });
</script>
