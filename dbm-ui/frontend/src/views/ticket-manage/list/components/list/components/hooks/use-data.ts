import { reactive, ref } from 'vue';
import { useRequest } from 'vue-request';
import { useRoute } from 'vue-router';

import TicketModel from '@services/model/ticket/ticket';
import { getTickets, getTicketStatus } from '@services/source/ticket';

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
  const route = useRoute();
  const { replaceSearchParams } = useUrlSearch();

  if (route.query.limit && route.query.current) {
    pagination.limit = Number(route.query.limit);
    pagination.current = Number(route.query.current);
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
  }, 10000);

  const { run: fetchTicketList } = useRequest(
    (params: ServiceParameters<typeof getTickets>) =>
      getTickets({
        bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
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
