import { reactive } from 'vue';

export const usePagination = (options: { callback: () => void }) => {
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

  const onChange = (pageValue: number) => {
    if (pagination.current === pageValue) {
      return;
    }
    pagination.current = pageValue;
    options?.callback();
  };

  const onLimitChange = (pageLimit: number) => {
    if (pagination.limit === pageLimit) {
      return;
    }
    pagination.limit = pageLimit;
    pagination.current = 1;
    options?.callback();
  };

  return {
    onChange,
    onLimitChange,
    pagination,
  };
};
