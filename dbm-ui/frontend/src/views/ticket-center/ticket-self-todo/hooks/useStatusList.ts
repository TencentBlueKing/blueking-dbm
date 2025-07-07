import _ from 'lodash';
import { computed, type Ref, watch } from 'vue';
import { useI18n } from 'vue-i18n';
import { useRoute } from 'vue-router';

import TicketModel from '@services/model/ticket/ticket';

import { useTicketCount } from '@hooks';

export default (isAssist: Ref<number>) => {
  const { t } = useI18n();
  const { data: ticketCount } = useTicketCount();

  const route = useRoute();

  const defaultStatus = ref('');

  const list = computed(() => {
    const countData = isAssist.value ? ticketCount.value.to_help : ticketCount.value.pending;
    return [
      {
        count: countData.APPROVE,
        id: TicketModel.STATUS_APPROVE,
        name: `${t('待审批')}(${countData.APPROVE})`,
      },
      {
        count: countData.TODO,
        id: TicketModel.STATUS_TODO,
        name: `${t('待执行')}(${countData.TODO})`,
      },
      {
        count: countData.RESOURCE_REPLENISH,
        id: TicketModel.STATUS_RESOURCE_REPLENISH,
        name: `${t('待补货')}(${countData.RESOURCE_REPLENISH})`,
      },
      {
        count: countData.FAILED,
        id: TicketModel.STATUS_FAILED,
        name: `${t('失败待处理')}(${countData.FAILED})`,
      },
      {
        count: countData.INNER_TODO,
        id: TicketModel.STATUS_INNER_TODO,
        name: `${t('待继续')}(${countData.INNER_TODO})`,
      },
      {
        count: countData.TIMER,
        id: TicketModel.STATUS_TIMER,
        name: `${t('定时中')}(${countData.TIMER})`,
      },
    ];
  });

  const routeParamsStatus = String(route.params.status);
  if (routeParamsStatus && _.find(list.value, (item) => item.id === routeParamsStatus)) {
    defaultStatus.value = routeParamsStatus;
  } else {
    defaultStatus.value = _.find(list.value, (item) => item.count > 0)?.id ?? TicketModel.STATUS_APPROVE;
  }

  watch(list, () => {
    defaultStatus.value = _.find(list.value, (item) => item.count > 0)?.id ?? TicketModel.STATUS_APPROVE;
  });

  return {
    defaultStatus,
    list,
  };
};
