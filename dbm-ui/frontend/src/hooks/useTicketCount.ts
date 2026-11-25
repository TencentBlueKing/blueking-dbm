import { onBeforeUnmount } from 'vue';
import { useRequest } from 'vue-request';
import { useRoute } from 'vue-router';

import { getTicketCount } from '@services/source/ticketFlow';

import { useEventBus } from '@hooks';

const run = () => {
  const isLoading = ref(true);
  const data = ref<ServiceReturnType<typeof getTicketCount>>({
    DONE: 0,
    MY_APPROVE: 0,
    pending: {
      APPROVE: 0,
      CONFIRM_PENDING: 0,
      FAILED: 0,
      INNER_HELP: 0,
      INNER_TODO: 0,
      RESOURCE_REPLENISH: 0,
      TIMER: 0,
      TODO: 0,
    },
    SELF_MANAGE: 0,
    TIMER: 0,
    to_help: {
      APPROVE: 0,
      CONFIRM_PENDING: 0,
      FAILED: 0,
      INNER_HELP: 0,
      INNER_TODO: 0,
      RESOURCE_REPLENISH: 0,
      TIMER: 0,
      TODO: 0,
    },
  });

  const { run } = useRequest(getTicketCount, {
    onSuccess(result) {
      data.value = result;
      isLoading.value = false;
    },
  });

  return {
    // 共用这份数据的调用方，按挂载顺序排列
    callers: [] as symbol[],
    data,
    loading: isLoading,
    refresh: run,
  };
};

let context: ReturnType<typeof run> | undefined;

export const useTicketCount = () => {
  const route = useRoute();
  const eventBus = useEventBus();

  if (!context) {
    context = run();
  }
  // context 可能被其他调用方重置，这里固定引用当前使用的那一份
  const currentContext = context;
  const caller = Symbol('ticketCountCaller');
  currentContext.callers.push(caller);

  // 每个调用方都监听，只由排在最前的一个发请求：避免重复请求，且它卸载后由下一个接替
  eventBus.on('refreshTicketStatus', () => {
    if (currentContext.callers[0] === caller) {
      currentContext.refresh();
    }
  });

  onBeforeUnmount(() => {
    currentContext.callers = currentContext.callers.filter((item) => item !== caller);
    setTimeout(() => {
      if (route.name !== 'MyTodos') {
        context = undefined;
      }
    });
  });

  return {
    data: currentContext.data,
    loading: currentContext.loading,
  };
};
