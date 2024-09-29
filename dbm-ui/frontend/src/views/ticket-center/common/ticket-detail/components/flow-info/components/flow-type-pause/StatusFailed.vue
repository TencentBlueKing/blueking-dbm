<template>
  <StatusFailed
    :data="data"
    :ticket-detail="ticketDetail">
    <template #title>
      <I18nT
        keypath="确认是否执行 n"
        scope="global">
        {{ data.flow_type_display }}
      </I18nT>
    </template>
    <template #content>
      <I18nT
        keypath="n 已处理_c_耗时 t"
        scope="global">
        <span>{{ data.summary.operator }}</span>
        <span style="color: #ea3636">{{ t('已撤销') }}</span>
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
    ticketDetail: TicketModel<unknown>;
  }

  defineProps<Props>();

  defineOptions({
    name: FlowMode.STATUS_FAILED,
  });

  const { t } = useI18n();
</script>
