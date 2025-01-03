import { onBeforeUnmount } from 'vue';
import { useRequest } from 'vue-request';

import { getTicketCount } from '@services/source/ticketFlow';

import { useEventBus } from '@hooks';

const run = () => {
  const isLoading = ref(true);
  const data = ref<ServiceReturnType<typeof getTicketCount>>({
    DONE: 0,
    MY_APPROVE: 0,
    pending: {
      APPROVE: 0,
      TODO: 0,
      INNER_TODO: 0,
      INNER_HELP: 0,
      RESOURCE_REPLENISH: 0,
      FAILED: 0,
    },
    SELF_MANAGE: 0,
    to_help: {
      APPROVE: 0,
      TODO: 0,
      INNER_TODO: 0,
      INNER_HELP: 0,
      RESOURCE_REPLENISH: 0,
      FAILED: 0,
    },
  });

  const { run } = useRequest(getTicketCount, {
    onSuccess(result) {
      data.value = result;
      isLoading.value = false;
    },
  });

  const eventBus = useEventBus();

  eventBus.on('refreshTicketStatus', run);

  onBeforeUnmount(() => {
    eventBus.off('refreshTicketStatus', run);
  });

  return {
    loading: isLoading,
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
