import { computed } from 'vue';
import { useI18n } from 'vue-i18n';

import TicketModel from '@services/model/ticket/ticket';

import { useTicketCount } from '@hooks';

export default () => {
  const { t } = useI18n();
  const { data: ticketCount } = useTicketCount();

  return computed(() => [
    {
      id: TicketModel.STATUS_APPROVE,
      name: `${t('待审批')}(${ticketCount.value.APPROVE})`,
    },
    {
      id: TicketModel.STATUS_TODO,
      name: `${t('待执行')}(${ticketCount.value.TODO})`,
    },
    {
      id: TicketModel.STATUS_RESOURCE_REPLENISH,
      name: `${t('待补货')}(${ticketCount.value.RESOURCE_REPLENISH})`,
    },
    {
      id: TicketModel.STATUS_FAILED,
      name: `${t('失败待处理')}(${ticketCount.value.FAILED})`,
    },
    {
      id: TicketModel.STATUS_RUNNING,
      name: `${t('待继续')}(${ticketCount.value.RUNNING})`,
    },
  ]);
};
