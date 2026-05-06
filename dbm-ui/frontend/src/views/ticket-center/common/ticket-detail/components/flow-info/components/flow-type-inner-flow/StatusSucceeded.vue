<template>
  <StatusSucceeded :data="data">
    <template #content>
      <I18nT
        keypath="m_耗时_t"
        scope="global">
        <span style="color: #2dcb56">{{ t('执行成功') }}</span>
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
      <template v-if="ticketDetail.ticket_type === TicketTypes.MONGODB_DATA_EXPORT">
        <span> ，</span>
        <!-- prettier-ignore -->
        <MongodbExportDataDownload :ticket-detail="(ticketDetail as ComponentProps<typeof MongodbExportDataDownload>['ticketDetail'])" />
      </template>
      <template v-if="ticketDetail.ticket_type === TicketTypes.REDIS_KEYS_EXTRACT">
        <span> ，</span>
        <RedisKeysExtractFile :id="data.flow_obj_id" />
      </template>
      <template v-if="ticketDetail.ticket_type === TicketTypes.SQLSERVER_DATA_EXPORT">
        <span> ，</span>
        <SqlserverExportDataDownload
          :details="data.details as ComponentProps<typeof SqlserverExportDataDownload>['details']" />
      </template>
      <template
        v-if="[TicketTypes.MYSQL_DUMP_DATA, TicketTypes.TENDBCLUSTER_DUMP_DATA].includes(ticketDetail.ticket_type)">
        <span> ，</span>
        <!-- prettier-ignore -->
        <MysqlDumpDataDownload :details="(data.details as ComponentProps<typeof MysqlDumpDataDownload>['details'])" />
      </template>
      <template v-if="data.url">
        <span> ，</span>
        <a
          :href="data.url"
          target="_blank">
          {{ t('查看详情') }}
        </a>
      </template>
      <template
        v-if="[TicketTypes.REDIS_HOT_KEY_ANALYSIS, TicketTypes.REDIS_KEYSTAT].includes(ticketDetail.ticket_type)">
        <span> ，</span>
        <RedisAnalysisToList
          :biz-id="ticketDetail.bk_biz_id"
          :ticket-type="ticketDetail.ticket_type" />
      </template>
    </template>
  </StatusSucceeded>
</template>
<script setup lang="ts">
  import type { ComponentProps } from 'vue-component-type-helpers';
  import { useI18n } from 'vue-i18n';

  import FlowMode from '@services/model/ticket/flow';
  import TicketModel from '@services/model/ticket/ticket';

  import { TicketTypes } from '@common/const';

  import CostTimer from '@components/cost-timer/CostTimer.vue';

  import { utcTimeToSeconds } from '@utils';

  import StatusSucceeded from '../flow-type-common/StatusSucceeded.vue';

  import MongodbExecScriptDownloadFile from './components/MongodbExecScriptDownloadFile.vue';
  import MongodbExportDataDownload from './components/MongodbExportDataDownload.vue';
  import MysqlDumpDataDownload from './components/MysqlDumpDataDownload.vue';
  import RedisAnalysisToList from './components/RedisAnalysisToList.vue';
  import RedisKeysExtractFile from './components/RedisKeysExtractFile.vue';
  import SqlserverExportDataDownload from './components/SqlserverExportDataDownload.vue';

  interface Props {
    data: FlowMode<unknown>;
    ticketDetail: TicketModel<unknown>;
  }

  defineOptions({
    name: FlowMode.STATUS_SUCCEEDED,
    inheritAttrs: false,
  });

  defineProps<Props>();

  const { t } = useI18n();
</script>
