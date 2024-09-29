import { onBeforeUnmount } from 'vue';
import { useRequest } from 'vue-request';

import { getTicketCount } from '@services/source/ticketFlow';

import { useEventBus } from '@hooks';

export const useTicketCount = () => {
  const data = ref({
    MY_APPROVE: 0,
    APPROVE: 0,
    TODO: 0,
    RUNNING: 0,
    RESOURCE_REPLENISH: 0,
    FAILED: 0,
    DONE: 0,
    SELF_MANAGE: 0,
  });

  const { run } = useRequest(getTicketCount, {
    cacheKey: 'ticketCount',
    cacheTime: 1000,
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
    data,
  };
};
