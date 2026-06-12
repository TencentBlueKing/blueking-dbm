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
import { onUnmounted, reactive, ref } from 'vue';
import { useRequest } from 'vue-request';

import { fetchReplenish } from '@services/source/dbresourceReplenish';
import { getTicketStatus } from '@services/source/ticket';

import { useUrlSearch } from '@hooks';

import { transfromDataToQuery } from '@utils';

import { useStorage, useTimeoutFn } from '@vueuse/core';

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
  const shouldPoll = ref(false);

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

      // 收集所有关联单据 ID
      const allTicketIds = getAllTicketIds();

      // 如果有单据 ID，则启动轮询
      if (allTicketIds.length > 0) {
        shouldPoll.value = true;
        fetchTicketStatus();
      }
    },
  });

  const fetchData = () => {
    dataSource({
      limit: pagination.limit,
      offset: (pagination.current - 1) * pagination.limit,
      ...transfromDataToQuery(JSON.parse(decodeURIComponent(String(route.query[URL_REPLENISH_MEMO_KEY] || '{}')))),
    });
  };

  // 获取所有关联单据 ID（去重）
  const getAllTicketIds = () => {
    const ticketIds = tableData.value.flatMap((item) => item.ticket_ids || []);
    return [...new Set(ticketIds)];
  };

  // 更新记录的 status 数组
  const updateRecordsStatus = (statusMap: Record<string, string>) => {
    tableData.value = tableData.value.map((record) => {
      if (!record.ticket_ids?.length) {
        return record;
      }

      // 根据 ticket_ids 和 statusMap 更新 status 数组
      const newStatus = record.ticket_ids.map((ticketId, index) => statusMap[ticketId] ?? record.status[index]);

      // 如果 status 没有变化，返回原记录（避免不必要的响应式更新）
      if (newStatus.every((s, i) => s === record.status[i])) {
        return record;
      }

      return { ...record, status: newStatus };
    });
  };

  // 轮询获取单据状态
  const { refresh: fetchTicketStatus } = useRequest(
    () => {
      if (!shouldPoll.value) {
        return Promise.reject();
      }
      const allTicketIds = getAllTicketIds();
      if (allTicketIds.length === 0) {
        return Promise.reject();
      }
      return getTicketStatus({
        ticket_ids: allTicketIds.join(','),
      });
    },
    {
      manual: true,
      onSuccess(data: Record<string, string>) {
        updateRecordsStatus(data);

        // 继续轮询
        if (shouldPoll.value) {
          loopFetchTicketStatus();
        }
      },
    },
  );

  const { start: loopFetchTicketStatus, stop: stopPolling } = useTimeoutFn(() => {
    fetchTicketStatus();
  }, 3000);

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

  // 组件卸载时停止轮询
  onUnmounted(() => {
    stopPolling();
  });

  return {
    fetchData,
    handlePageLimitChange,
    handlePageValueChange,
    loading,
    pagination,
    tableData,
  };
};
