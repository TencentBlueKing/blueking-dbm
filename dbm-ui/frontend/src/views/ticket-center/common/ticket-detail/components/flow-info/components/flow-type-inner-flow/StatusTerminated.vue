<template>
  <StatusTerminated :data="data">
    <template #content>
      <I18nT
        keypath="m_耗时_t"
        scope="global">
        <span style="color: #ea3636">{{ t('任务终止') }}</span>
        <CostTimer
          :is-timing="false"
          :start-time="utcTimeToSeconds(data.start_time)"
          :value="data.cost_time" />
      </I18nT>
      <template v-if="ticketDetail.ticket_type === TicketTypes.MONGODB_EXEC_SCRIPT_APPLY">
        <span> ，</span>
        <!-- prettier-ignore -->
        <MongodbExecScriptDownloadFile :details="(data.details as ComponentProps<typeof MongodbExecScriptDownloadFile>['details'])" />
      </template>
      <template v-if="data.url">
        <span> ，</span>
        <a
          :href="data.url"
          target="_blank">
          {{ t('查看详情') }}
        </a>
      </template>
    </template>
  </StatusTerminated>
</template>
<script setup lang="ts">
  import type { ComponentProps } from 'vue-component-type-helpers';
  import { useI18n } from 'vue-i18n';

  import FlowMode from '@services/model/ticket/flow';
  import TicketModel from '@services/model/ticket/ticket';

  import { TicketTypes } from '@common/const';

  import CostTimer from '@components/cost-timer/CostTimer.vue';

  import { utcTimeToSeconds } from '@utils';

  import StatusTerminated from '../flow-type-common/StatusTerminated.vue';

  import MongodbExecScriptDownloadFile from './components/MongodbExecScriptDownloadFile.vue';

  interface Props {
    data: FlowMode;
    ticketDetail: TicketModel<unknown>;
  }

  defineProps<Props>();

  defineOptions({
    name: FlowMode.STATUS_RUNNING,
  });

  const { t } = useI18n();
</script>
