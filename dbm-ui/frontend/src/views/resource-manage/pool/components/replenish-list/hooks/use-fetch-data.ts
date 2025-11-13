import { reactive, ref } from 'vue';

import { useUrlSearch } from '@hooks';

import { useStorage } from '@vueuse/core';
import { calcResourceWaterLevel } from '@services/source/dbresourceResource';
import { useRequest } from 'vue-request';

type ResourceWaterLevel = ServiceReturnType<typeof calcResourceWaterLevel>;

export default () => {
  const { getSearchParams } = useUrlSearch();
  const paginationLimitCache = useStorage('resource_pool_replenish_list_pagination', 20);

  const searchParams = getSearchParams();

  const flushTime = ref<string>('');
  const updateTime = ref<string>('');
  const dataList = ref<ResourceWaterLevel['water_level']>([]);
  const tableData = ref<ResourceWaterLevel['water_level']>([]);
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

  const { loading, run } = useRequest(calcResourceWaterLevel, {
    manual: true,
    onSuccess: (data: ResourceWaterLevel) => {
      flushTime.value = data.flush_time;
      updateTime.value = data.update_time;
      dataList.value = data.water_level;
      pagination.count = data.water_level.length;

      // 分页
      const offset = (pagination.current - 1) * pagination.limit;
      tableData.value = data.water_level.slice(offset, offset + pagination.limit);
    },
  });
  // 切换每页条数
  const handlePageLimitChange = (pageLimit: number) => {
    pagination.limit = pageLimit;
    paginationLimitCache.value = pageLimit;

    // 更新分页后的数据
    const offset = (pagination.current - 1) * pagination.limit;
    tableData.value = dataList.value.slice(offset, offset + pagination.limit);
  };

  // 切换页码
  const handlePageValueChange = (pageValue: number) => {
    pagination.current = pageValue;

    // 更新分页后的数据
    const offset = (pagination.current - 1) * pagination.limit;
    tableData.value = dataList.value.slice(offset, offset + pagination.limit);
  };

  return {
    tableData,
    run,
    loading,
    pagination,
    handlePageLimitChange,
    handlePageValueChange,
    updateTime,
    flushTime,
    dataList,
  };
};
