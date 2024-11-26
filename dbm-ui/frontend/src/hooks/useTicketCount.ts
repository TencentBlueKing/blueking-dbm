import { onBeforeUnmount } from 'vue';
import { useRequest } from 'vue-request';

import { getTicketCount } from '@services/source/ticketFlow';

import { useEventBus } from '@hooks';

const run = () => {
  const data = ref<ServiceReturnType<typeof getTicketCount>>({
    MY_APPROVE: 0,
    APPROVE: 0,
    TODO: 0,
    RUNNING: 0,
    RESOURCE_REPLENISH: 0,
    FAILED: 0,
    DONE: 0,
    SELF_MANAGE: 0,
  });

  const { loading, run } = useRequest(getTicketCount, {
    cacheKey: 'ticketCount',
    cacheTime: 10000,
    onSuccess(result) {
      data.value = result;
    },
  });

  const eventBus = useEventBus();

  eventBus.on('refreshTicketStatus', run);

  onBeforeUnmount(() => {
    eventBus.off('refreshTicketStatus', run);
  });

  return {
    loading,
    data,
  };
};

let context: ReturnType<typeof run>;

export const useTicketCount = () => {
  if (!context) {
    context = run();
  }
  return context;
};
