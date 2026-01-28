import { reactive, ref } from 'vue';
import { useRequest } from 'vue-request';

import { getTickets } from '@services/source/ticket';

import { useUrlSearch } from '@hooks';

import { TicketTypes } from '@common/const';

import { transfromDataToQuery } from '@utils';

import { useStorage } from '@vueuse/core';

export default () => {
  const route = useRoute();
  const paginationLimitCache = useStorage('replenish_ticket_view_pagination', 20);
  const { getSearchParams, replaceSearchParams } = useUrlSearch();
  const searchParams = getSearchParams();

  const URL_REPLENISH_MEMO_KEY = '__replenish_ticket_view_payload__';

  const dataList = ref<ServiceReturnType<typeof getTickets>['results']>([]);
  const pagination = reactive({
    count: 0,
    current: 1,
    limit: paginationLimitCache.value,
    limitList: [10, 20, 50, 100, 200, 500],
    remote: true,
  });

  if (searchParams.limit && searchParams.current) {
    pagination.limit = Number(searchParams.limit);
    pagination.current = Number(searchParams.current);
  }

  const { loading, run: dataSource } = useRequest(getTickets, {
    manual: true,
    onSuccess: (data: ServiceReturnType<typeof getTickets>) => {
      dataList.value = data.results;
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
      ticket_type: TicketTypes.RESOURCE_HCM_REPLENISH,
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
    dataList,
    fetchData,
    handlePageLimitChange,
    handlePageValueChange,
    loading,
    pagination,
  };
};
