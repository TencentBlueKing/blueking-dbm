import { reactive, ref } from 'vue';
import { useRequest } from 'vue-request';

import TicketModel from '@services/model/ticket/ticket';
import { getTicketStatus, getTodoTickets } from '@services/source/ticket';

import { useUrlSearch } from '@hooks';

import { useTimeoutFn } from '@vueuse/core';

const dataList = ref<TicketModel<unknown>[]>([]);
const pagination = reactive({
  offset: 0,
  limit: 15,
  current: 1,
  count: 0,
});

export default (options?: { onSuccess?: (data: TicketModel<unknown>[]) => void }) => {
  const { replaceSearchParams } = useUrlSearch();

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
  }, 10000);

  const { run: fetchTicketList } = useRequest(
    (params: ServiceParameters<typeof getTodoTickets>) =>
      getTodoTickets({
        limit: pagination.limit,
        offset: (pagination.current - 1) * pagination.limit,
        ...params,
      }),
    {
      manual: true,
      onSuccess(data, params) {
        dataList.value = data.results;
        pagination.count = data.count;
        replaceSearchParams({
          limit: pagination.limit,
          current: pagination.current,
          ...params[0],
        });
        if (options && options.onSuccess) {
          options.onSuccess(data.results);
        }
      },
    },
  );

  return {
    dataList,
    pagination,
    fetchTicketList,
  };
};
