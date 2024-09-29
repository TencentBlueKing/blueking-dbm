import _ from 'lodash';
import { reactive, ref } from 'vue';
import { useRequest } from 'vue-request';
import { onBeforeRouteLeave, useRoute } from 'vue-router';

import TicketModel from '@services/model/ticket/ticket';
import { getTicketStatus, getTodoTickets } from '@services/source/ticket';

import { useEventBus, useUrlSearch } from '@hooks';

import { getOffset } from '@utils';

import { useTimeoutFn } from '@vueuse/core';

const isLoading = ref(false);
const dataList = ref<TicketModel<unknown>[]>([]);
const pagination = reactive({
  offset: 0,
  limit: 15,
  current: 1,
  count: 0,
  limitList: [10, 20, 50, 100, 500],
});
const tableMaxHeight = ref<number | 'auto'>('auto');

let isMounted = false;

export default (
  dataSource: typeof getTodoTickets,
  options?: { onSuccess?: (data: TicketModel<unknown>[]) => void },
) => {
  const route = useRoute();
  const eventBus = useEventBus();
  const { replaceSearchParams, getSearchParams } = useUrlSearch();
  const searchParams = getSearchParams();

  if (searchParams.limit && searchParams.current) {
    pagination.limit = Number(searchParams.limit);
    pagination.current = Number(searchParams.current);
  }

  const tableRef = useTemplateRef<HTMLElement>('table');

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
  }, 1000000);

  const fetchTicketList = (params: ServiceParameters<typeof getTodoTickets>) => {
    isLoading.value = true;
    dataSource({
      limit: pagination.limit,
      offset: (pagination.current - 1) * pagination.limit,
      ...params,
    })
      .then((data) => {
        dataList.value = data.results;

        pagination.count = data.count;

        const urlSearchParams = {
          limit: pagination.limit,
          current: pagination.current,
          ...params,
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
      })
      .finally(() => {
        isLoading.value = false;
      });
  };

  const calcTableMaxHeight = () => {
    const { top } = getOffset(tableRef.value as HTMLElement);
    const totalHeight = window.innerHeight;
    const tableHeaderHeight = 42;
    const paginationHeight = 60;
    const pageOffsetBottom = 20;
    const tableRowHeight = 42;

    const tableRowTotalHeight = totalHeight - top - tableHeaderHeight - paginationHeight - pageOffsetBottom;

    const rowNum = Math.max(Math.floor(tableRowTotalHeight / tableRowHeight), 5);

    tableMaxHeight.value = tableHeaderHeight + rowNum * tableRowHeight + paginationHeight + 3;

    pagination.limit = Math.floor(tableMaxHeight.value / 42);

    pagination.limit = rowNum;
    pagination.limitList = _.uniq([...pagination.limitList, rowNum]).sort((a, b) => a - b);
  };

  eventBus.on('refreshTicketStatus', fetchTicketStatus);

  onMounted(() => {
    if (isMounted) {
      return;
    }
    isMounted = true;
    calcTableMaxHeight();
  });

  onBeforeUnmount(() => {
    eventBus.off('refreshTicketStatus', fetchTicketStatus);
  });

  onBeforeRouteLeave((currentRoute) => {
    setTimeout(() => {
      if (currentRoute.name === route.name) {
        return;
      }
      isMounted = false;
    });
  });

  return {
    loading: isLoading,
    tableMaxHeight,
    dataList,
    pagination,
    fetchTicketList,
  };
};
