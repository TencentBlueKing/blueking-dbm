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
        :remote-pagination="remotePagination"
        show-overflow-tooltip
        v-bind="$attrs"
        @column-sort="handleColumnSortChange"
        @page-limit-change="handlePageLimitChange"
        @page-value-change="handlePageValueChange"
        @row-click="handleRowClick">
        <template
          v-if="releateUrlQuery && Object.keys(rowSelectMemo).length > 0"
          #prepend>
          <div class="head-prepend-row">
            <I18nT keypath="已选n条，">
              <span class="number">{{ Object.keys(rowSelectMemo).length }}</span>
            </I18nT>
            <BkButton
              text
              theme="primary"
              @click="handleClearWholeSelect">
              {{ t('清除所有勾选') }}
            </BkButton>
          </div>
        </template>
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
<script setup lang="tsx">
  import type { Table } from 'bkui-vue';
  import _ from 'lodash';
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

  import type { IRequestPayload } from '@services/http';
  import type { ListBase } from '@services/types';

  import { useUrlSearch } from '@hooks';

  import EmptyStatus from '@components/empty-status/EmptyStatus.vue';

  import { getOffset } from '@utils';

  interface Props {
    columns?: InstanceType<typeof Table>['$props']['columns'],
    dataSource: (params: any, payload?: IRequestPayload)=> Promise<any>,
    fixedPagination?: boolean,
    clearSelection?: boolean,
    paginationExtra?: {
    small?: boolean;
  },
    selectable?: boolean,
    disableSelectMethod?: (data: any) => boolean|string,
    // data 数据的主键
    primaryKey?: string,
    // 是否解析 URL query 参数
    releateUrlQuery?: boolean,
    // 没提供默认使用浏览器窗口的高度 window.innerHeight
    containerHeight?: number,
    // 是否开启远程分页
    remotePagination?: boolean,
    // 是否允许行点击选中
    allowRowClickSelect?: boolean,
    remoteSort?: boolean,
  }

  interface Emits {
    (e: 'requestSuccess', value: any): void,
    (e: 'requestFinished', value: any[]): void,
    (e: 'clearSearch'): void,
    (e: 'selection', key: string[], list: Record<any, any>[]): void,
    (e: 'selection', key: number[], list: Record<any, any>[]): void,
  }

  interface Exposes {
    fetchData: (params?: Record<string, any>, baseParams?: Record<string, any>, loading?: boolean) => void,
    getData: <T>() => Array<T>,
    getAllData: <T>() => Promise<Array<T>>,
    clearSelected: () => void,
    loading: Ref<boolean>,
    bkTableRef: Ref<InstanceType<typeof Table>>,
    updateTableKey: () => void,
    removeSelectByKey: (key: string) => void,
  }

  const props = withDefaults(defineProps<Props>(), {
    columns: () => [],
    fixedPagination: false,
    clearSelection: true,
    paginationExtra: () => ({}),
    selectable: false,
    disableSelectMethod: () => false,
    primaryKey: 'id',
    releateUrlQuery: false,
    containerHeight: undefined,
    remotePagination: true,
    allowRowClickSelect: false,
    remoteSort: false,
  });

  const emits = defineEmits<Emits>();

  defineOptions({
    inheritAttrs: false,
  });

  // 生成可选中列配置
  const genSelectionColumn = () => ({
    width: 80,
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
              default: () => <db-icon class="select-menu-flag" type="down-big" />,
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
    render: ({ data }: {data: any}) => {
      const selectDisabled = props.disableSelectMethod(data);
      const tips = {
        disabled: !selectDisabled,
        content: _.isString(selectDisabled) ? selectDisabled : t('禁止选择'),
      };
      return (
        <span v-bk-tooltips={tips}>
          <bk-checkbox
            label={true}
            disabled={Boolean(selectDisabled)}
            onChange={() => handleSelecteRow(data)}
            modelValue={Boolean(rowSelectMemo.value[_.get(data, props.primaryKey)])} />
        </span>
      );
    },
  });

  const { t } = useI18n();

  const rootRef = ref();
  const bkTableRef = ref();
  const tableKey = ref(Date.now().toString());
  const isLoading = ref(false);
  const tableMaxHeight = ref<number | 'auto'>('auto');
  const tableData = ref<ListBase<any>>({
    count: 0,
    next: '',
    previous: '',
    results: [],
    permission: {},
  });
  const isSearching = ref(false);
  const isAnomalies = ref(false);
  const rowSelectMemo = shallowRef<Record<string|number, Record<any, any>>>({});
  const isWholeChecked = ref(false);
  const pagination = reactive<{
    count: number;
    current: number;
    limit: number;
    limitList: Array<number>;
    align: string;
    layout: Array<string>;
  }>({
    count: 0,
    current: 1,
    limit: 10,
    limitList: [10, 20, 50, 100, 500],
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
      if (!selectMap[_.get(list[i], props.primaryKey)]) {
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
    isReady = true;
    Promise.resolve()
      .then(() => {
        isLoading.value = loading;
        const params = {
          offset: (pagination.current - 1) * pagination.limit,
          limit: pagination.limit,
          bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
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

        isAnomalies.value = false;

        props.dataSource(params, payload)
          .then((data) => {
            tableData.value = data;
            console.log('tabledata = ', data);
            pagination.count = data.count;
            isSearching.value = getSearchingStatus();
            isAnomalies.value = false;

            // 默认清空选项
            if (props.clearSelection) {
              bkTableRef.value?.clearSelection?.();
            }

            if (!props.fixedPagination && props.releateUrlQuery) {
              replaceSearchParams(params);
            }

            emits('requestSuccess', data);
          })
          .catch((error) => {
            console.log('from dbtable error = ', error);
            tableData.value.results = [];
            pagination.count = 0;
            isAnomalies.value = true;
          })
          .finally(() => {
            isReady = false;
            isLoading.value = false;
            emits('requestFinished', tableData.value.results);
          });
      });
  };

  // 拉取全量数据
  const fetchAllData = async () => {
    const { results } = await props.dataSource({
      bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
      offset: (pagination.current - 1) * pagination.limit,
      limit: -1,
      ...paramsMemo,
      ...sortParams,
    })
    return results;
  };

  watch(() => props.columns, () => {
    tableKey.value = Date.now().toString();
  });

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
      if (props.disableSelectMethod(dataItem)) {
        return;
      }
      selectMap[_.get(dataItem, props.primaryKey)] = dataItem;
    });
    rowSelectMemo.value = selectMap;
    isWholeChecked.value = false;
    triggerSelection();
  };

  // 切换当前页全选
  const handleTogglePageSelect = (checked: boolean) => {
    const selectMap = { ...rowSelectMemo.value };
    tableData.value.results.forEach((dataItem: any) => {
      if (checked) {
        if (!props.disableSelectMethod(dataItem)) {
          selectMap[_.get(dataItem, props.primaryKey)] = dataItem;
        }
      } else {
        delete selectMap[_.get(dataItem, props.primaryKey)];
      }
    });
    if (!checked) {
      isWholeChecked.value = false;
    }
    rowSelectMemo.value = selectMap;
    triggerSelection();
  };

  // 清空选择
  const handleClearWholeSelect = () => {
    rowSelectMemo.value = {};
    isWholeChecked.value = false;
    triggerSelection();
  };

  // 跨页全选
  const handleWholeSelect = () => {
    props.dataSource({
      bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
      offset: (pagination.current - 1) * pagination.limit,
      limit: -1,
      ...paramsMemo,
      ...sortParams,
    }).then((data) => {
      const selectMap = { ...rowSelectMemo.value };
      data.results.forEach((dataItem: any) => {
        if (props.disableSelectMethod(dataItem)) {
          return;
        }
        selectMap[_.get(dataItem, props.primaryKey)] = dataItem;
      });
      rowSelectMemo.value = selectMap;
      isWholeChecked.value = true;
      triggerSelection();
    });
  };

  // 选中单行
  const handleRowClick = (event: MouseEvent, data: any) => {
    if (!props.allowRowClickSelect) {
      return;
    }
    const targetElement = event.target as HTMLElement;
    if (/bk-button/.test(targetElement.className)) {
      return;
    }
    if (!props.selectable) {
      return;
    }
    if (props.disableSelectMethod(data)) {
      return;
    }
    const selectMap = { ...rowSelectMemo.value };
    if (!selectMap[_.get(data, props.primaryKey)]) {
      selectMap[_.get(data, props.primaryKey)] = data;
    } else {
      delete selectMap[_.get(data, props.primaryKey)];
      isWholeChecked.value = false;
    }
    rowSelectMemo.value = selectMap;

    triggerSelection();
  };

  // 勾选单行
  const handleSelecteRow = (data: any) => {
    if (!props.selectable) {
      return;
    }
    if (props.disableSelectMethod(data)) {
      return;
    }
    const selectMap = { ...rowSelectMemo.value };
    if (!selectMap[_.get(data, props.primaryKey)]) {
      selectMap[_.get(data, props.primaryKey)] = data;
    } else {
      delete selectMap[_.get(data, props.primaryKey)];
      isWholeChecked.value = false;
    }
    rowSelectMemo.value = selectMap;

    triggerSelection();
  };

  // 排序
  const handleColumnSortChange = (sortPayload: any) => {
    if (!props.remoteSort) {
      return;
    }
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
    pagination.current = 1;
    fetchListData();
  };

  // 切换页码
  const handlePageValueChange = (pageValue:number) => {
    pagination.current = pageValue;
    fetchListData();
    bkTableRef.value.scrollTo(0, 0);
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
      const pageOffsetBottom = props.containerHeight ? 0 : 20;
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
    // 获取远程数据
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
    // 获取表格渲染数据
    getData() {
      return tableData.value.results;
    },
    // 获取全量数据
    getAllData: fetchAllData,
    // 清空选择
    clearSelected() {
      bkTableRef.value?.clearSelection();
    },
    updateTableKey() {
      tableKey.value = Date.now().toString();
    },
    removeSelectByKey(key: string) {
      delete rowSelectMemo.value[key];
    },
    loading: isLoading,
    bkTableRef,
  });
</script>
<style lang="less">
  .db-table {
    .head-prepend-row {
      display: flex;
      height: 30px;
      background: #ebecf0;
      align-items: center;
      justify-content: center;
    }

    table tbody tr td .cell {
      line-height: unset !important;
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
