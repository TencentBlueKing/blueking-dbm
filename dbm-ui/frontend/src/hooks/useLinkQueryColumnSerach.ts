/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 *
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 *
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 *
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed
 * on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for
 * the specific language governing permissions and limitations under the License.
 */
import type { ISearchValue } from 'bkui-vue/lib/search-select/utils';

import { queryBizClusterAttrs } from '@services/source/dbbase';

import { useGlobalBizs } from '@stores';

import type { ClusterTypes } from '@common/const';

type QueryBizClusterAttrsReturnType = ServiceReturnType<typeof queryBizClusterAttrs>;

export type SearchAttrs = Record<string, {
  id: string,
  name: string,
}[]>;

export const useLinkQueryColumnSerach = (
  clusterType: ClusterTypes,
  attrs: string[],
  fetchDataFn?: () => void,
  isCluster = true,
) => {
  const queryTableDataFn = fetchDataFn ? fetchDataFn : () => {};

  const { currentBizId } = useGlobalBizs();

  const searchValue = ref<ISearchValue[]>([]);
  const columnAttrs = ref<QueryBizClusterAttrsReturnType>({});
  const searchAttrs = ref<SearchAttrs>({});

  const sortValue: {
    ordering?: string,
  } = {};

  const attrsObj = isCluster ? {
    cluster_attrs: attrs.join(','),
  } : {
    instances_attrs: attrs.join(','),
  };

  watch(
    searchValue,
    () => {
      searchValueChange();
    },
    {
      deep: true,
    },
  );

  // 查询表头筛选列表
  queryBizClusterAttrs({
    bk_biz_id: currentBizId,
    cluster_type: clusterType,
    ...attrsObj,
  }).then((resultObj) => {
    columnAttrs.value = resultObj;
    searchAttrs.value = Object.entries(resultObj).reduce((results, item) => {
      Object.assign(results, {
        [item[0]]: item[1].map(item => ({
          id: item.value,
          name: item.text,
        })),
      });
      return results;
    }, {} as SearchAttrs);
  });

  onMounted(() => {
    queryTableDataFn();
  });

  // 表头筛选事件
  const columnFilterChange = (data: {
    checked: string[];
    column: {
      field: string;
      label: string;
      filter: {
        checked: string[],
        list: {
          value: string,
          text: string,
        }[]
      }
    };
    index: number;
  }) => {
    if (data.checked.length === 0) {
      searchValue.value = searchValue.value.filter(item => item.id !== data.column.field);
      return;
    }

    searchValue.value = [
      {
        id: data.column.field,
        name: data.column.label,
        values: data.checked.map(item => ({
          id: item,
          name: data.column.filter.list.find(row => row.value === item)?.text ?? '',
        })),
      },
    ];
  };

  const columnSortChange = (data: {
    column: {
      field: string;
      label: string;
    };
    index: number;
    type: 'asc' | 'desc' | 'null'
  }) => {
    if (data.type === 'asc') {
      sortValue.ordering = data.column.field;
    } else if (data.type === 'desc') {
      sortValue.ordering = `-${data.column.field}`;
    } else {
      delete sortValue.ordering;
    }
    queryTableDataFn();
  };

  /**
   * 搜索
   */
  const searchValueChange = () => {
    queryTableDataFn();
  };

  /**
   * 清空搜索
   */
  const clearSearchValue = () => {
    searchValue.value = [];
    queryTableDataFn();
  };

  return {
    columnAttrs,
    searchAttrs,
    searchValue,
    sortValue,
    columnFilterChange,
    columnSortChange,
    clearSearchValue,
    searchValueChange,
  };
};
