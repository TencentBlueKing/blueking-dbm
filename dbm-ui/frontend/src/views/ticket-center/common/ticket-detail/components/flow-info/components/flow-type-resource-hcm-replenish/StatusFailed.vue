<template>
  <StatusFailed
    :data="data"
    :ticket-detail="ticketDetail">
    <template #content>
      <I18nT
        keypath="m_耗时_t"
        scope="global">
        <span style="color: #ea3636">{{ t('执行失败') }}</span>
        <CostTimer
          :is-timing="false"
          :start-time="utcTimeToSeconds(data.start_time)"
          :value="data.cost_time" />
      </I18nT>
      <template v-if="data.url">
        <span> ，</span>
        <a
          :href="data.url"
          target="_blank">
          {{ t('查看详情') }}
        </a>
      </template>
    </template>
  </StatusFailed>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import FlowMode from '@services/model/ticket/flow';
  import TicketModel from '@services/model/ticket/ticket';

  import CostTimer from '@components/cost-timer/CostTimer.vue';

  import { utcTimeToSeconds } from '@utils';

  import StatusFailed from '../flow-type-common/StatusFailed.vue';

  interface Props {
    data: FlowMode<unknown, any>;
    ticketDetail: TicketModel;
  }

  defineOptions({
    name: FlowMode.STATUS_FAILED,
  });

  defineProps<Props>();

  const { t } = useI18n({
    useScope: 'global',
  });
</script>
