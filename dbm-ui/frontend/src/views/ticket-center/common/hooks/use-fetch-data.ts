import { reactive, ref, useTemplateRef } from 'vue';
import { useRequest } from 'vue-request';

import TicketModel from '@services/model/ticket/ticket';
import { getTickets, getTicketStatus } from '@services/source/ticket';

import { useUrlSearch } from '@hooks';

import { useStorage, useTimeoutFn } from '@vueuse/core';

export default (dataSource: typeof getTickets, options?: { onSuccess?: (data: TicketModel[]) => void }) => {
  const { getSearchParams, replaceSearchParams } = useUrlSearch();
  const paginationLimitCache = useStorage('table_pagination_limit', 20);

  const searchParams = getSearchParams();

  const tableRef = useTemplateRef<any>('table');
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

  let requestKey = 0;
  const fetchTicketList = (params: ServiceParameters<typeof getTickets>) => {
    isLoading.value = true;
    requestKey = Date.now();
    dataSource({
      limit: pagination.limit,
      offset: (pagination.current - 1) * pagination.limit,
      ordering: ordering.value,
      ...params,
    })
      .then((data) => {
        const latestRequestKey = requestKey;
        dataList.value = data.results;

        tableRef.value.getVxeTableInstance().loadData(data.results.slice(0, 20));
        if (data.results.length > 20) {
          setTimeout(() => {
            if (latestRequestKey !== requestKey) {
              return;
            }
            tableRef.value.getVxeTableInstance().loadData(data.results.slice(0, 50));
            if (data.results.length > 50) {
              setTimeout(() => {
                if (latestRequestKey !== requestKey) {
                  return;
                }
                tableRef.value.getVxeTableInstance().loadData(data.results);
              }, 3000);
            }
          }, 1500);
        }

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
    fetchTicketList,
    loading: isLoading,
    ordering,
    pagination,
    tableMaxHeight,
  };
};
