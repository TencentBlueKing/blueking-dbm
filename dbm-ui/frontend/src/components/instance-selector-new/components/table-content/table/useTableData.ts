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

import {
  type ComponentInternalInstance,
  getCurrentInstance,
  reactive,
  type Ref,
  ref,
  shallowRef,
} from 'vue';

import { useGlobalBizs } from '@stores';

/**
 * 处理集群列表数据
 */
export function useTableData<T>(activePanel?: Ref<string>, role?: Ref<string>, clusterId?: Ref<number | undefined>) {
  const { currentBizId } = useGlobalBizs();
  const currentInstance = getCurrentInstance() as ComponentInternalInstance & {
    proxy: {
      getTableList: (params: any) => Promise<any>
    }
  };

  const isLoading = ref(false);
  const tableData = shallowRef<T[]>([]);
  const dbModuleList = shallowRef<{ id: number, name: string }[]>([]);
  const isAnomalies = ref(false);
  const pagination = reactive({
    count: 0,
    current: 1,
    limit: 10,
    limitList: [10, 20, 50, 100],
    align: 'right',
    layout: ['total', 'limit', 'list'],
  });
  const searchValue = ref('');

  /**
   * 获取列表
   */
  const fetchResources = () => {
    isLoading.value = true;
    const params = {
      db_type: 'mysql',
      bk_biz_id: currentBizId,
      instance_address: searchValue.value,
      limit: pagination.limit,
      offset: (pagination.current - 1) * pagination.limit,
      type: activePanel?.value === 'manualInput' ? undefined : 'spider',
      extra: 1,
    };

    if (role?.value) {
      Object.assign(params, {
        role: role.value,
      });
    }
    if (clusterId?.value && clusterId.value !== currentBizId) {
      Object.assign(params, {
        cluster_id: clusterId.value,
      });
    }
    return currentInstance.proxy.getTableList(params)
      .then((data) => {
        const ret = data;
        tableData.value = ret.results;
        pagination.count = ret.count;
        isAnomalies.value = false;
      })
      .catch(() => {
        tableData.value = [];
        pagination.count = 0;
        isAnomalies.value = true;
      })
      .finally(() => {
        isLoading.value = false;
      });
  };

  /**
   * change page
   */
  const handleChangePage = (value: number) => {
    pagination.current = value;
    return fetchResources();
  };

  /**
   * change limit
   */
  const handeChangeLimit = (value: number) => {
    pagination.limit = value;
    return handleChangePage(1);
  };

  // 清空搜索
  const handleClearSearch = () => {
    searchValue.value = '';
    handleChangePage(1);
  };

  return {
    isLoading,
    data: tableData,
    pagination,
    dbModuleList,
    isAnomalies,
    searchValue,
    fetchResources,
    handleChangePage,
    handeChangeLimit,
    handleClearSearch,
  };
}
