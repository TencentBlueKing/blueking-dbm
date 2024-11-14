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
import _ from 'lodash';
import { useRequest } from 'vue-request';

import { type ClusterInfo, queryAllTypeClusterList } from '@services/source/dbbase';

import { getSearchSelectorParams } from '@utils';

/**
 * 处理集群列表数据
 */
export function useTableData(
  searchSelectValue: Ref<ISearchValue[]>,
  params: ComputedRef<{
    cluster_types: string;
    bk_biz_id?: number;
    db_module_id?: number;
  }>,
) {
  const tableData = shallowRef<ClusterInfo[]>([]);
  const pagination = reactive({
    count: 0,
    current: 1,
    limit: 10,
    limitList: [10, 20, 50, 100],
    align: 'right',
    layout: ['total', 'limit', 'list'],
  });

  const searchParams = computed(() => {
    const comParams = getSearchSelectorParams(searchSelectValue.value);
    const cloneParams = _.cloneDeep(comParams);
    delete cloneParams.domain;
    return {
      limit: pagination.limit,
      offset: (pagination.current - 1) * pagination.limit,
      extra: 1,
      immute_domain: comParams.domain,
      ...cloneParams,
      ...params.value,
    };
  });

  const { run: fetchDataFn, loading: isLoading } = useRequest(queryAllTypeClusterList, {
    manual: true,
    onSuccess(data) {
      tableData.value = data.results;
      pagination.count = data.count;
    },
    onError() {
      tableData.value = [];
      pagination.count = 0;
    },
  });

  watch(params, () => {
    setTimeout(() => {
      handleChangePage(1);
    });
  });

  const fetchResources = () => {
    fetchDataFn(searchParams.value);
  };

  const handleChangePage = (value: number) => {
    pagination.current = value;
    return fetchResources();
  };

  const handeChangeLimit = (value: number) => {
    pagination.limit = value;
    return handleChangePage(1);
  };

  return {
    isLoading,
    data: tableData,
    pagination,
    fetchResources,
    handleChangePage,
    handeChangeLimit,
  };
}
