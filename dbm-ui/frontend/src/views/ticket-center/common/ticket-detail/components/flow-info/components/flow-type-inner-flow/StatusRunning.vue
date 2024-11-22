<template>
  <StatusRunning :data="data">
    <template #content>
      <span>
        <I18nT keypath="m_耗时_t">
          <span style="color: #3a84ff">{{ t('执行中') }}</span>
          <CostTimer
            is-timing
            :start-time="utcTimeToSeconds(data.start_time)"
            :value="data.cost_time" />
        </I18nT>
        <template v-if="data.url">
          <span> ，</span>
          <a
            :href="data.url"
            target="_blank">
            {{ ticketDetail.status === TicketModel.STATUS_INNER_TODO ? t('去处理') : t('查看详情') }}
          </a>
        </template>
      </span>
    </template>
  </StatusRunning>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import FlowMode from '@services/model/ticket/flow';
  import TicketModel from '@services/model/ticket/ticket';

  import CostTimer from '@components/cost-timer/CostTimer.vue';

  import { utcTimeToSeconds } from '@utils';

  import StatusRunning from '../flow-type-common/StatusRunning.vue';

  interface Props {
    data: FlowMode;
    ticketDetail: TicketModel;
  }

  defineProps<Props>();

  defineOptions({
    name: FlowMode.STATUS_RUNNING,
  });

  const { t } = useI18n();
</script>
