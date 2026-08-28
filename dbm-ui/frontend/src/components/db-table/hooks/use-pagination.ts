import { reactive } from 'vue';

export interface Pagination {
  align: string;
  count: number;
  current: number;
  layout: Array<'total' | 'list' | 'limit'>;
  limit: number;
  limitList: Array<number>;
}

export const usePagination = (options?: { callback: () => void; defaultLimit?: number }) => {
  const defaultLimit = options?.defaultLimit ?? 20;
  const pagination = reactive<Pagination>({
    align: 'right',
    count: 0,
    current: 1,
    layout: ['total', 'limit', 'list'],
    limit: defaultLimit,
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
