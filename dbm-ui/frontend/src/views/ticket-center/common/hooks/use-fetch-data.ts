import { onBeforeUnmount, reactive, ref } from 'vue';
import { useRequest } from 'vue-request';

import TicketModel from '@services/model/ticket/ticket';
import { getTickets, getTicketStatus } from '@services/source/ticket';

import { useEventBus, useUrlSearch } from '@hooks';

import { useStorage, useTimeoutFn } from '@vueuse/core';

const create = (dataSource: typeof getTickets, options?: { onSuccess?: (data: TicketModel[]) => void }) => {
  const eventBus = useEventBus();
  const { getSearchParams, replaceSearchParams } = useUrlSearch();
  const paginationLimitCache = useStorage('table_pagination_limit', 20);

  const searchParams = getSearchParams();

  const isLoading = ref(false);
  const dataList = ref<TicketModel[]>([]);
  const pagination = reactive({
    count: 0,
    current: 1,
    limit: paginationLimitCache.value,
    limitList: [10, 20, 50, 100],
    remote: true,
  });
  const ordering = ref('');
  const tableMaxHeight = ref<number | 'auto'>('auto');

  if (searchParams.limit && searchParams.current) {
    pagination.limit = Number(searchParams.limit);
    pagination.current = Number(searchParams.current);
  }

  const { run: fetchTicketStatus } = useRequest(
    () => {
      if (dataList.value.length < 1) {
        return Promise.reject();
      }
      return getTicketStatus({
        ticket_ids: dataList.value.map((item) => item.id).join(','),
      });
    },
    {
      manual: true,
      onSuccess(data) {
        dataList.value.forEach((ticketData) => {
          if (data[ticketData.id]) {
            Object.assign(ticketData, {
              status: data[ticketData.id],
            });
          }
        });
        loopFetchTicketStatus();
      },
    },
  );

  const { start: loopFetchTicketStatus } = useTimeoutFn(() => {
    fetchTicketStatus();
  }, 3000);

  const fetchTicketList = (params: ServiceParameters<typeof getTickets>) => {
    isLoading.value = true;
    dataSource({
      limit: pagination.limit,
      offset: (pagination.current - 1) * pagination.limit,
      ordering: ordering.value,
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

  eventBus.on('refreshTicketStatus', fetchTicketStatus);

  onBeforeUnmount(() => {
    eventBus.off('refreshTicketStatus', fetchTicketStatus);
  });

  return {
    dataList,
    fetchTicketList,
    loading: isLoading,
    ordering,
    pagination,
    tableMaxHeight,
  };
};

let context: ReturnType<typeof create> | undefined;

export default (...args: Parameters<typeof create>) => {
  if (!context) {
    context = create(...args);
  }

  onBeforeUnmount(() => {
    context = undefined;
  });

  return context;
};
