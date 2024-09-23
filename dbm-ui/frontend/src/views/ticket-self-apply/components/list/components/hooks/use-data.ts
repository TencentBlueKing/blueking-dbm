import { reactive, ref } from 'vue';
import { useRequest } from 'vue-request';

import TicketModel from '@services/model/ticket/ticket';
import { getTickets, getTicketStatus } from '@services/source/ticket';

import { useUrlSearch } from '@hooks';

import { useTimeoutFn } from '@vueuse/core';

const isLoading = ref(false);
const dataList = ref<TicketModel<unknown>[]>([]);
const pagination = reactive({
  offset: 0,
  limit: 15,
  current: 1,
  count: 0,
});

export default (options?: { onSuccess?: (data: TicketModel<unknown>[]) => void }) => {
  const { replaceSearchParams, getSearchParams } = useUrlSearch();
  const searchParams = getSearchParams();

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
      debounceInterval: 100,
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
        limit: pagination.limit,
        offset: (pagination.current - 1) * pagination.limit,
        self_manage: 0,
        ...params,
      }),
    {
      manual: true,
      onBefore() {
        isLoading.value = true;
      },
      onAfter() {
        isLoading.value = false;
      },
      onSuccess(data, params) {
        dataList.value = data.results;
        pagination.count = data.count;

        const urlSearchParams = {
          limit: pagination.limit,
          current: pagination.current,
          ...params[0],
        };

        const searchParams = getSearchParams();
        if (Number(searchParams.viewId)) {
          Object.assign(urlSearchParams, {
            viewId: searchParams.viewId,
          });
        }
        replaceSearchParams(urlSearchParams);
        if (options && options.onSuccess) {
          options.onSuccess(data.results);
        }
      },
    },
  );

  return {
    loading: isLoading,
    dataList,
    pagination,
    fetchTicketList,
  };
};
