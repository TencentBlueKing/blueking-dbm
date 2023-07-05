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
      <BkTable
        :key="tableKey"
        ref="bkTableRef"
        :columns="localColumns"
        :data="tableData.results"
        :max-height="tableMaxHeight"
        :pagination="pagination"
        :pagination-heihgt="60"
        remote-pagination
        show-overflow-tooltip
        v-bind="$attrs"
        @column-sort="handleColumnSortChange"
        @page-limit-change="handlePageLimitChange"
        @page-value-change="handlePageValueChange"
        @row-click="handleRowClick">
        <slot />
        <template #expandRow="row">
          <slot
            name="expandRow"
            :row="row" />
        </template>
        <template #empty>
          <slot name="empty">
            <EmptyStatus
              :is-anomalies="isAnomalies"
              :is-searching="isSearching"
              @clear-search="handleClearSearch"
              @refresh="fetchListData" />
          </slot>
        </template>
      </BkTable>
    </BkLoading>
  </div>
</template>
<script lang="tsx">
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
<script setup lang="tsx">
  import type { Table } from 'bkui-vue';
  import {
    computed,
    nextTick,
    onMounted,
    reactive,
    type Ref,
    ref,
    shallowRef,
  } from 'vue';
  import { useI18n } from 'vue-i18n';

  import type { ListBase } from '@services/types/common';

  import { useUrlSearch } from '@hooks';

  import { useGlobalBizs } from '@stores';

  import EmptyStatus from '@components/empty-status/EmptyStatus.vue';

  import {
    getOffset,
    random,
  } from '@utils';

  import DbIcon from '../db-icon';

  interface Props {
    columns: InstanceType<typeof Table>['$props']['columns'],
    dataSource: (params: any)=> Promise<any>,
    fixedPagination?: boolean,
    clearSelection?: boolean,
    paginationExtra?: IPaginationExtra,
    selectable?: boolean
    // data 数据的主键
    primaryKey?: string,
    // 是否解析 URL query 参数
    releateUrlQuery?: boolean,
    // 没提供默认使用浏览器窗口的高度 window.innerHeight
    containerHeight?: number,
  }

  interface Emits {
    (e: 'requestSuccess', value: any): void,
    (e: 'requestFinished', value: any[]): void,
    (e: 'clearSearch'): void,
    (e: 'selection', key: string[], list: Record<any, any>[]): void,
    (e: 'selection', key: number[], list: Record<any, any>[]): void,
  }

  interface Exposes {
    fetchData: (params: Record<string, any>, baseParams: Record<string, any>) => void,
    getData: <T>() => Array<T>,
    clearSelected: () => void,
    loading: Ref<boolean>,
    bkTableRef: Ref<InstanceType<typeof Table>>,
    updateTableKey: () => void,
  }

  const props = withDefaults(defineProps<Props>(), {
    fixedPagination: false,
    clearSelection: true,
    paginationExtra: () => ({}),
    selectable: false,
    primaryKey: 'id',
    releateUrlQuery: false,
    containerHeight: undefined,
  });

  const emits = defineEmits<Emits>();

  // 生成可选中列配置
  const genSelectionColumn = () => ({
    width: 60,
    fixed: 'left',
    label: () => {
      const renderCheckbox = () => {
        if (isWholeChecked.value) {
          return (
            <div class="db-table-whole-check" onClick={handleClearWholeSelect} />
          );
        }
        return (
          <bk-checkbox
            label={true}
            modelValue={isCurrentPageAllSelected.value}
            onChange={handleTogglePageSelect} />
        );
      };
      return (
        <div class="db-table-select-cell">
          {renderCheckbox()}
          <bk-popover
            placement="bottom-start"
            theme="light db-table-select-menu"
            arrow={ false }
            trigger='hover'
            v-slots={{
              default: () => <DbIcon class="select-menu-flag" type="down-big" />,
              content: () => (
                <div class="db-table-select-plan">
                  <div class="item" onClick={handlePageSelect}>{t('本页全选')}</div>
                  <div class="item" onClick={handleWholeSelect}>{t('跨页全选')}</div>
                </div>
              ),
            }}>
          </bk-popover>
      </div>
      );
    },
    render: ({ data }: {data: any}) => (
      <bk-checkbox
        style="pointer-events: none;"
        label={true}
        modelValue={Boolean(rowSelectMemo.value[data[props.primaryKey]])} />
    ),
  });

  const { t } = useI18n();
  const { currentBizId } = useGlobalBizs();

  const rootRef = ref();
  const bkTableRef = ref();
  const tableKey = ref(random());
  const isLoading = ref(false);
  const tableMaxHeight = ref(0);
  const tableData = ref<ListBase<any>>({
    count: 0,
    next: '',
    previous: '',
    results: [],
  });
  const isSearching = ref(false);
  const isAnomalies = ref(false);
  const rowSelectMemo = shallowRef<Record<string|number, Record<any, any>>>({});
  const isWholeChecked = ref(false);
  const pagination = reactive<IPagination>({
    count: 0,
    current: 1,
    limit: 10,
    limitList: [10, 20, 50, 100],
    align: 'right',
    layout: ['total', 'limit', 'list'],
    ...props.paginationExtra,
  });
  // 是否本页全选
  const isCurrentPageAllSelected = computed(() => {
    const list = tableData.value.results;
    if (list.length < 1) {
      return false;
    }
    const selectMap = { ...rowSelectMemo.value };
    for (let i = 0; i < list.length; i++) {
      if (!selectMap[list[i][props.primaryKey]]) {
        return false;
      }
    }
    return true;
  });

  const localColumns = computed(() => {
    if (!props.selectable || !props.columns) {
      return props.columns;
    }

    return [
      genSelectionColumn(),
      ...props.columns,
    ];
  });

  let paramsMemo = {};
  let baseParamsMemo = {};
  let sortParams = {};

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
    console.log('pagination = ', pagination);
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

  const triggerSelection = () => {
    emits('selection', Object.keys(rowSelectMemo.value), Object.values(rowSelectMemo.value));
  };

  // 解析 URL 上面的分页信息
  const parseURL = () => {
    if (!props.releateUrlQuery || props.fixedPagination) {
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

  // 全选当前页
  const handlePageSelect = () => {
    const selectMap = { ...rowSelectMemo.value };
    tableData.value.results.forEach((dataItem: any) => {
      selectMap[dataItem[props.primaryKey]] = dataItem;
    });
    rowSelectMemo.value = selectMap;
    triggerSelection();
  };

  // 切换当前页全选
  const handleTogglePageSelect = (checked: boolean) => {
    const selectMap = { ...rowSelectMemo.value };
    tableData.value.results.forEach((dataItem: any) => {
      if (checked) {
        selectMap[dataItem[props.primaryKey]] = dataItem;
      } else {
        delete selectMap[dataItem[props.primaryKey]];
      }
    });
    rowSelectMemo.value = selectMap;
    triggerSelection();
  };

  // 清空选择
  const handleClearWholeSelect = () => {
    rowSelectMemo.value = {};
    triggerSelection();
  };

  // 跨页全选
  const handleWholeSelect = () => {
    props.dataSource({
      bk_biz_id: currentBizId,
      offset: (pagination.current - 1) * pagination.limit,
      limit: -1,
      ...paramsMemo,
      ...sortParams,
    }).then((data) => {
      const selectMap = { ...rowSelectMemo.value };
      data.results.forEach((dataItem: any) => {
        selectMap[dataItem[props.primaryKey]] = dataItem;
      });
      rowSelectMemo.value = selectMap;
      isWholeChecked.value = true;
      triggerSelection();
    });
  };

  // 选中单行
  const handleRowClick = (event: Event, data: any) => {
    if (!props.selectable) {
      return;
    }
    const selectMap = { ...rowSelectMemo.value };
    if (!selectMap[data[props.primaryKey]]) {
      selectMap[data[props.primaryKey]] = data;
    } else {
      delete selectMap[data[props.primaryKey]];
    }
    rowSelectMemo.value = selectMap;
    triggerSelection();
  };

  // 排序
  const handleColumnSortChange = (sortPayload: any) => {
    const valueMap = {
      null: undefined,
      desc: 0,
      asc: 1,
    };
    sortParams = {
      [sortPayload.column.field]: valueMap[sortPayload.type as keyof typeof valueMap],
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
      const top = props.containerHeight ? 0 : getOffset(rootRef.value).top;
      const totalHeight = props.containerHeight ? props.containerHeight : window.innerHeight;
      const tableHeaderHeight = 42;
      const paginationHeight = 60;
      const pageOffsetBottom = 48;
      const tableRowHeight = 42;

      const tableRowTotalHeight = totalHeight - top - tableHeaderHeight - paginationHeight - pageOffsetBottom;


      const rowNum = Math.max(Math.floor(tableRowTotalHeight / tableRowHeight), 5);
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
      setTimeout(() => {
        fetchListData(loading);
      });
    },
    getData() {
      return tableData.value.results;
    },
    clearSelected() {
      bkTableRef.value?.clearSelection();
    },
    updateTableKey() {
      tableKey.value = random();
    },
    loading: isLoading,
    bkTableRef,
  });
</script>
<style lang="less">
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
      content: "";
      transform: rotate(45deg);
    }
  }

  .select-menu-flag {
    margin-left: 4px;
    font-size: 18px;
    color: #63656E;
  }
}

[data-theme~='db-table-select-menu'] {
  padding: 0 !important;

  .db-table-select-plan {
    padding: 5px 0;

    .item {
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
