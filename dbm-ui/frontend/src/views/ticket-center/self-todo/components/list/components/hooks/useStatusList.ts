import _ from 'lodash';
import { computed } from 'vue';
import { useI18n } from 'vue-i18n';
import { useRoute } from 'vue-router';

import TicketModel from '@services/model/ticket/ticket';

import { useTicketCount } from '@hooks';

const create = () => {
  const { t } = useI18n();
  const { data: ticketCount } = useTicketCount();

  const route = useRoute();

  const defaultStatus = ref('');

  const list = computed(() => {
    const countData = Number(route.params.assist) ? ticketCount.value.to_help : ticketCount.value.pending;
    return [
      {
        id: TicketModel.STATUS_APPROVE,
        name: `${t('待审批')}(${countData.APPROVE})`,
        count: countData.APPROVE,
      },
      {
        id: TicketModel.STATUS_TODO,
        name: `${t('待执行')}(${countData.TODO})`,
        count: countData.TODO,
      },
      {
        id: TicketModel.STATUS_RESOURCE_REPLENISH,
        name: `${t('待补货')}(${countData.RESOURCE_REPLENISH})`,
        count: countData.RESOURCE_REPLENISH,
      },
      {
        id: TicketModel.STATUS_FAILED,
        name: `${t('失败待处理')}(${countData.FAILED})`,
        count: countData.FAILED,
      },
      {
        id: TicketModel.STATUS_INNER_TODO,
        name: `${t('待继续')}(${countData.INNER_TODO})`,
        count: countData.INNER_TODO,
      },
    ];
  });

  const routeParamsStatus = String(route.params.status);
  if (routeParamsStatus && _.find(list.value, (item) => item.id === routeParamsStatus)) {
    defaultStatus.value = routeParamsStatus;
  } else {
    defaultStatus.value = _.find(list.value, (item) => item.count > 0)?.id ?? TicketModel.STATUS_APPROVE;
  }

  return {
    list,
    defaultStatus,
  };
};

let context: ReturnType<typeof create> | undefined;
export default () => {
  if (!context) {
    context = create();
  }

  return context;
};
