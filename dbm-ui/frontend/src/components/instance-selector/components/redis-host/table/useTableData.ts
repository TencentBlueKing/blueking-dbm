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
import type { ComponentInternalInstance, Ref } from 'vue';
import { useRequest } from 'vue-request';

import { useGlobalBizs } from '@stores';

import { getSearchSelectorParams } from '@utils';

/**
 * 处理集群列表数据
 */
export function useTableData<T>(
  searchSelectValue: Ref<ISearchValue[]>,
  role?: Ref<string | undefined>,
  clusterId?: Ref<number | undefined>,
) {
  const { currentBizId } = useGlobalBizs();
  const currentInstance = getCurrentInstance() as ComponentInternalInstance & {
    proxy: {
      getTableList: (params: any) => Promise<any>;
    };
  };

  const tableData = shallowRef<T[]>([]);
  const isAnomalies = ref(false);
  const pagination = reactive({
    count: 0,
    current: 1,
    limit: 10,
    limitList: [10, 20, 50, 100],
    align: 'right',
    layout: ['total', 'limit', 'list'],
    remote: true,
  });

  const { run: getTableListRun, loading: isLoading } = useRequest(currentInstance.proxy.getTableList, {
    manual: true,
    onSuccess(data) {
      tableData.value = data.results;
      pagination.count = data.count;
      isAnomalies.value = false;
    },
    onError() {
      tableData.value = [];
      pagination.count = 0;
      isAnomalies.value = true;
    },
  });

  watch(searchSelectValue, () => {
    setTimeout(() => {
      handleChangePage(1);
    });
  });

  const generateParams = () => {
    const params = {
      bk_biz_id: currentBizId,
      limit: pagination.limit,
      offset: (pagination.current - 1) * pagination.limit,
      ...getSearchSelectorParams(searchSelectValue.value),
    };
    if (role?.value) {
      Object.assign(params, {
        instance_role: role.value,
      });
    }
    if (clusterId?.value && clusterId.value !== currentBizId) {
      Object.assign(params, {
        cluster_ids: [clusterId.value],
      });
    }
    return params;
  };

  const fetchResources = async () => {
    const params = generateParams();
    return getTableListRun(params);
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
    generateParams,
    fetchResources,
    handleChangePage,
    handeChangeLimit,
  };
}
