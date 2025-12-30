import { reactive, ref } from 'vue';
import { useRequest } from 'vue-request';

import { getRunningReplenishRecord } from '@services/source/dbresourceReplenish';
import { calcResourceWaterLevel } from '@services/source/dbresourceResource';

import { useUrlSearch } from '@hooks';

import { useStorage } from '@vueuse/core';

export type ResourceWaterLevel = ServiceReturnType<typeof calcResourceWaterLevel>;

export default () => {
  const { getSearchParams } = useUrlSearch();
  const paginationLimitCache = useStorage('resource_pool_replenish_list_pagination', 20);

  const searchParams = getSearchParams();

  const waterLevelData = ref<ResourceWaterLevel>();
  const runningReplenishRecord = ref(0); // 补货中的记录ID
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

  const { run: fetchRunningReplenishRecord } = useRequest(getRunningReplenishRecord, {
    manual: true,
    onSuccess: (data: number) => {
      runningReplenishRecord.value = data;
    },
  });

  const { loading, run } = useRequest(calcResourceWaterLevel, {
    manual: true,
    onSuccess: (data: ResourceWaterLevel) => {
      waterLevelData.value = data;
      dataList.value = data.water_level;
      pagination.count = data.water_level.length;

      // 分页
      const offset = (pagination.current - 1) * pagination.limit;
      tableData.value = data.water_level.slice(offset, offset + pagination.limit);

      fetchRunningReplenishRecord();
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
    dataList,
    handlePageLimitChange,
    handlePageValueChange,
    loading,
    pagination,
    run,
    runningReplenishRecord,
    tableData,
    waterLevelData,
  };
};
