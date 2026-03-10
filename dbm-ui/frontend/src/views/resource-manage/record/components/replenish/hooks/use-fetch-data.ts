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
import { reactive, ref } from 'vue';

import { useUrlSearch } from '@hooks';
import { transfromDataToQuery } from '@utils';
import { useStorage } from '@vueuse/core';
import { fetchReplenish } from '@services/source/dbresourceReplenish';
import { useRequest } from 'vue-request';

const URL_REPLENISH_MEMO_KEY = '__replenish_operation_view_payload__';

export default () => {
  const route = useRoute();
  const paginationLimitCache = useStorage('replenish_operation_view_pagination', 20);
  const { getSearchParams, replaceSearchParams } = useUrlSearch();
  const searchParams = getSearchParams();

  const tableData = ref<ServiceReturnType<typeof fetchReplenish>['results']>([]);
  const pagination = reactive({
    count: 0,
    current: 1,
    limit: paginationLimitCache.value,
    limitList: [10, 20, 50, 100],
    remote: true,
  });

  if (searchParams.limit && searchParams.current) {
    pagination.limit = Number(searchParams.limit);
    pagination.current = Number(searchParams.current);
  }

  const { loading, run: dataSource } = useRequest(fetchReplenish, {
    manual: true,
    onSuccess: (data: ServiceReturnType<typeof fetchReplenish>) => {
      tableData.value = data.results;
      pagination.count = data.count;
      replaceSearchParams({
        ...searchParams,
        current: pagination.current,
        limit: pagination.limit,
      });
    },
  });

  const fetchData = () => {
    dataSource({
      limit: pagination.limit,
      offset: (pagination.current - 1) * pagination.limit,
      ...transfromDataToQuery(JSON.parse(decodeURIComponent(String(route.query[URL_REPLENISH_MEMO_KEY] || '{}')))),
    });
  };

  // 切换每页条数
  const handlePageLimitChange = (pageLimit: number) => {
    pagination.limit = pageLimit;
    paginationLimitCache.value = pageLimit;
    fetchData();
  };

  // 切换页码
  const handlePageValueChange = (pageValue: number) => {
    pagination.current = pageValue;
    fetchData();
  };

  return {
    tableData,
    fetchData,
    loading,
    pagination,
    handlePageLimitChange,
    handlePageValueChange,
  };
};
