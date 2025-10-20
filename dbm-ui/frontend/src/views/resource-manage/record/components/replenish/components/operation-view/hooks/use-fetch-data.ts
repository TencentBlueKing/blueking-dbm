import { reactive, ref } from 'vue';

import { useUrlSearch } from '@hooks';
import { useStorage } from '@vueuse/core';
import { fetchReplenish } from '@services/source/dbresourceReplenish';
import { useRequest } from 'vue-request';

export default () => {
  const { getSearchParams, replaceSearchParams } = useUrlSearch();
  const paginationLimitCache = useStorage('resource_pool_replenish_operation_view_pagination', 20);
  const searchParams = getSearchParams();

  const tableData = ref<ServiceReturnType<typeof fetchReplenish>['results']>([]);
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

  const { loading, run: dataSource } = useRequest(fetchReplenish, {
    manual: true,
    onSuccess: (data: ServiceReturnType<typeof fetchReplenish>) => {
      tableData.value = data.results;
      pagination.count = data.count;
      replaceSearchParams({
        current: pagination.current,
        limit: pagination.limit,
        ...searchParams,
      });
    },
  });

  const fetchData = (params?: ServiceParameters<typeof fetchReplenish>) => {
    dataSource({
      limit: pagination.limit,
      offset: (pagination.current - 1) * pagination.limit,
      ...params,
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
