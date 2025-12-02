import { reactive } from 'vue';
import DbResourceModel from '@services/model/db-resource/DbResource';
import { useStorage } from '@vueuse/core';
import { useRequest } from 'vue-request';
import { fetchList } from '@services/source/dbresourceResource';
import type { HostInfo, ListBase } from '@services/types';

export default (defaultParams?: {
  bk_cloud_ids?: string;
  for_biz?: number;
  for_bizs?: number[];
  hosts?: HostInfo[];
  os_names?: string[];
  os_type?: string;
  resource_type?: string;
  resource_types?: string[];
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

  const fetchData = (params?: ServiceParameters<typeof fetchList>) =>
    run({
      ...defaultParams,
      ...params,
      limit: pagination.limit,
      offset: pagination.current - 1,
      bk_biz_id: undefined, // 资源池参数用for_biz,把db-table内置的bk_biz_id去掉
    });

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
