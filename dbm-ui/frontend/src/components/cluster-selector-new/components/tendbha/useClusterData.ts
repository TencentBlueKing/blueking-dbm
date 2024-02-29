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
import { type ComponentInternalInstance, getCurrentInstance, reactive, ref, shallowRef } from 'vue';

import { useGlobalBizs } from '@stores';

import { getSearchSelectorParams } from '@utils';

/**
 * 处理集群列表数据
 */
export function useClusterData<T>() {
  const globalBizsStore = useGlobalBizs();
  const currentInstance = getCurrentInstance() as ComponentInternalInstance & {
    proxy: {
      getResourceList: (params: any) => Promise<any>;
    };
  };

  const isLoading = ref(false);
  const tableData = shallowRef<T[]>([]);
  const isAnomalies = ref(false);
  const pagination = reactive({
    current: 1,
    count: 0,
    limit: 10,
    small: true,
  });
  const searchSelectValue = ref<ISearchValue[]>([]);

  watch(
    searchSelectValue,
    () => {
      setTimeout(() => {
        handleChangePage(1);
      });
    },
    {
      immediate: true,
      deep: true,
    },
  );

  /**
   * 获取列表
   */
  const fetchResources = async () => {
    isLoading.value = true;
    return currentInstance.proxy
      .getResourceList({
        bk_biz_id: globalBizsStore.currentBizId,
        limit: pagination.limit,
        offset: pagination.limit * (pagination.current - 1),
        ...getSearchSelectorParams(searchSelectValue.value),
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
    isAnomalies,
    searchSelectValue,
    fetchResources,
    handleChangePage,
    handeChangeLimit,
  };
}
