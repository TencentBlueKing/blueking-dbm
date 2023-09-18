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

import { getModules } from '@services/common';

import { useGlobalBizs } from '@stores';

/**
 * 处理集群列表数据
 */
export function useClusterData<T>(activeTab: Ref<string>, searchParams: Record<string, any>) {
  const globalBizsStore = useGlobalBizs();
  const currentInstance = getCurrentInstance() as ComponentInternalInstance & {
    proxy: {
      getResourceList: (params: any) => Promise<any>
    }
  };

  const isLoading = ref(false);
  const tableData = shallowRef<T[]>([]);
  const dbModuleList = shallowRef<{id: number, name: string}[]>([]);
  const isAnomalies = ref(false);
  const pagination = reactive({
    current: 1,
    count: 0,
    limit: 10,
    small: true,
  });

  /**
   * 获取列表
   */
  const fetchResources = () => {
    isLoading.value = true;
    return currentInstance.proxy.getResourceList({
      type: activeTab.value,
      bk_biz_id: globalBizsStore.currentBizId,
      limit: pagination.limit,
      offset: pagination.limit * (pagination.current - 1),
      ...searchParams,
    })
      .then((res) => {
        pagination.count = res.count;
        tableData.value = res.results;
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

  /**
   * 获取模块列表
   */
  const fetchModules = () => {
    getModules({
      bk_biz_id: globalBizsStore.currentBizId,
      cluster_type: activeTab.value,
    }).then((res) => {
      dbModuleList.value = res.map(item => ({
        id: item.db_module_id,
        name: item.name,
      }));
      return dbModuleList.value;
    });
  };

  return {
    isLoading,
    data: tableData,
    pagination,
    dbModuleList,
    isAnomalies,
    fetchResources,
    fetchModules,
    handleChangePage,
    handeChangeLimit,
  };
}
