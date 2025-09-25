import { reactive, ref } from 'vue';

import { useUrlSearch } from '@hooks';

import type useClusterMachineList from '@views/db-manage/hooks/useClusterMachineList';

import { useStorage } from '@vueuse/core';

type IData = ServiceReturnType<ReturnType<typeof useClusterMachineList>>['results'][number];

export const useFetchData = (
  dataSource: ReturnType<typeof useClusterMachineList>,
  options?: { onSuccess?: (data: IData[]) => void },
) => {
  const { getSearchParams, replaceSearchParams } = useUrlSearch();
  const paginationLimitCache = useStorage('table_pagination_limit', 20);

  const searchParams = getSearchParams();

  const isLoading = ref(false);
  const dataList = ref<IData[]>([]);
  const pagination = reactive({
    count: 0,
    current: 1,
    limit: paginationLimitCache.value,
    limitList: [10, 20, 50, 100, 200, 500],
    remote: true,
  });
  const ordering = ref('');
  const tableMaxHeight = ref<number | 'auto'>('auto');

  if (searchParams.limit && searchParams.current) {
    pagination.limit = Number(searchParams.limit);
    pagination.current = Number(searchParams.current);
  }

  const fetchHostList = (params: ServiceParameters<ReturnType<typeof useClusterMachineList>>) => {
    isLoading.value = true;
    dataSource({
      limit: pagination.limit,
      offset: (pagination.current - 1) * pagination.limit,
      ...params,
    })
      .then((data) => {
        dataList.value = data.results;

        pagination.count = data.count;

        const urlSearchParams = {
          current: pagination.current,
          limit: pagination.limit,
          ordering: ordering.value,
          ...params,
        };

        replaceSearchParams(urlSearchParams);
        if (options?.onSuccess) {
          options.onSuccess(data.results);
        }
      })
      .finally(() => {
        isLoading.value = false;
      });
  };

  return {
    dataList,
    fetchHostList,
    loading: isLoading,
    ordering,
    pagination,
    tableMaxHeight,
  };
};
