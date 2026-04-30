import _ from 'lodash';
import { reactive } from 'vue';

export const usePagination = <T>(dataList: Ref<T[]>, options?: { callback: () => void }) => {
  const pagination = reactive<{
    align: string;
    count: number;
    current: number;
    layout: Array<string>;
    limit: number;
    limitList: Array<number>;
  }>({
    align: 'right',
    count: 0,
    current: 1,
    layout: ['total', 'limit', 'list'],
    limit: 20,
    limitList: [10, 20, 50, 100, 200, 500],
  });

  const currentPageDataList = ref<T[]>([]);

  const setCurrentDataList = () => {
    if (!dataList.value.length) {
      currentPageDataList.value = [];
      return;
    }

    const start = (pagination.current - 1) * pagination.limit;
    const end = Math.min(start + pagination.limit, dataList.value.length);

    // 边界处理
    if (start >= dataList.value.length && pagination.current > 1) {
      // 这里不能直接修改 pagination.current，会导致无限循环
      currentPageDataList.value = [];
      return;
    }

    currentPageDataList.value = _.cloneDeep(dataList.value.slice(start, end));
  };

  watch(
    dataList,
    () => {
      pagination.count = dataList.value.length;
      pagination.current = 1;
      setCurrentDataList();
    },
    {
      immediate: true,
    },
  );

  const onChange = (pageValue: number) => {
    if (pagination.current === pageValue) {
      return;
    }
    pagination.current = pageValue;
    setCurrentDataList();
    options?.callback();
  };

  const onLimitChange = (pageLimit: number) => {
    if (pagination.limit === pageLimit) {
      return;
    }
    pagination.limit = pageLimit;
    pagination.current = 1;
    setCurrentDataList();
    options?.callback();
  };

  return {
    currentPageDataList,
    onChange,
    onLimitChange,
    pagination,
  };
};
