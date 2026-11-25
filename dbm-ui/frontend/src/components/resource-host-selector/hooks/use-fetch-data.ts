import { reactive } from 'vue';
import { useRequest } from 'vue-request';

import DbResourceModel from '@services/model/db-resource/DbResource';
import { fetchList } from '@services/source/dbresourceResource';
import type { HostInfo, ListBase } from '@services/types';

import { useStorage } from '@vueuse/core';

export default (defaultParams?: {
  params: {
    bk_cloud_ids?: string;
    for_biz?: number;
    for_bizs?: number[];
    hosts?: HostInfo[];
    os_names?: string[];
    os_type?: string;
    resource_type?: string;
    resource_types?: string[];
  };
}) => {
  const paginationLimitCache = useStorage('resource_host_selector_pagination', 20);

  const pagination = reactive({
    count: 0,
    current: 1,
    limit: paginationLimitCache.value,
    limitList: [10, 20, 50, 100, 200, 500],
    remote: true,
  });
  const tableData = shallowRef<DbResourceModel[]>([]);

  const { loading, run } = useRequest(fetchList, {
    manual: true,
    onSuccess: (data: ListBase<DbResourceModel[]>) => {
      pagination.count = data.count;
      tableData.value = data.results;
    },
  });

  // 最近一次搜索条件，翻页时复用，否则只剩 defaultParams
  type ListParams = ServiceParameters<typeof fetchList>;
  const lastParams = shallowRef<ListParams>({});

  const fetchData = (params: ListParams = {}) => {
    lastParams.value = params;
    // 资源池参数用 for_biz，把 db-table 内置的 bk_biz_id 去掉
    const { ...restParams } = params as { bk_biz_id?: number } & Omit<ListParams, 'bk_biz_id'>;
    return run({
      ...(defaultParams ? defaultParams.params : {}),
      ...restParams,
      limit: pagination.limit,
      offset: pagination.current - 1,
    } as ListParams);
  };

  // 切换每页条数
  const handlePageLimitChange = (pageLimit: number) => {
    pagination.limit = pageLimit;
    paginationLimitCache.value = pageLimit;
    fetchData(lastParams.value);
  };

  // 切换页码
  const handlePageValueChange = (pageValue: number) => {
    pagination.current = pageValue;
    fetchData(lastParams.value);
  };

  return {
    fetchData,
    handlePageLimitChange,
    handlePageValueChange,
    loading,
    pagination,
    tableData,
  };
};
