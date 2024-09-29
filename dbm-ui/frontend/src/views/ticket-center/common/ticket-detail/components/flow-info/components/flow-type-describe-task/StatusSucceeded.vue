<template>
  <StatusSucceeded :data="data">
    <template #content>
      <I18nT
        keypath="m_耗时_t"
        scope="global">
        <span style="color: #2dcb56">
          {{ t('执行成功') }}
          <span v-if="data.summary.status === 'FAILED'">({{ data.summary.message }})</span>
        </span>
        <CostTimer
          :is-timing="false"
          :start-time="utcTimeToSeconds(data.start_time)"
          :value="data.cost_time" />
      </I18nT>
      <template v-if="data.url">
        <span> ，</span>
        <RouterLink
          target="_blank"
          :to="{
            name: ticketDetail.ticket_type === TicketTypes.MYSQL_IMPORT_SQLFILE ? 'MySQLExecute' : 'spiderSqlExecute',
            params: {
              step: 'result',
            },
            query: {
              rootId: (ticketDetail as TicketModel<Mysql.ImportSqlFile>).details.root_id,
            },
          }">
          {{ t('查看详情') }}
        </RouterLink>
      </template>
    </template>
  </StatusSucceeded>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import FlowMode from '@services/model/ticket/flow';
  import TicketModel, { type Mysql } from '@services/model/ticket/ticket';

  import { TicketTypes } from '@common/const';

  import CostTimer from '@components/cost-timer/CostTimer.vue';

  import { utcTimeToSeconds } from '@utils';

  import StatusSucceeded from '../flow-type-common/StatusSucceeded.vue';

  interface Props {
    ticketDetail: TicketModel;
    data: FlowMode<
      unknown,
      {
        message: string;
        status: string;
      }
    >;
  }

  defineProps<Props>();

  defineOptions({
    name: FlowMode.STATUS_SUCCEEDED,
  });

  const { t } = useI18n();
</script>
