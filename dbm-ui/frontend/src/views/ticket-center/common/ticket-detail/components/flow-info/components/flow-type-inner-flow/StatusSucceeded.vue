<template>
  <DbTimeLineItem>
    <template #icon>
      <div style="width: 10px; height: 10px; background: #2dcb56; border-radius: 50%" />
    </template>
    <template #title> {{ data.flow_type_display }} </template>
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
      <template v-if="ticketDetail.ticket_type === TicketTypes.REDIS_KEYS_EXTRACT">
        <span> ，</span>
        <FlowRedisKeyExtract :id="data.flow_obj_id" />
      </template>
      <template v-if="ticketDetail.ticket_type === TicketTypes.MYSQL_DUMP_DATA">
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
    </template>
    <template #desc>
      {{ data.updateAtDisplay }}
    </template>
  </DbTimeLineItem>
</template>
<script setup lang="ts">
  import type { ComponentProps } from 'vue-component-type-helpers';
  import { useI18n } from 'vue-i18n';

  import FlowMode from '@services/model/ticket/flow';
  import TicketModel from '@services/model/ticket/ticket';

  import { TicketTypes } from '@common/const';

  import CostTimer from '@components/cost-timer/CostTimer.vue';

  import FlowRedisKeyExtract from '@views/db-manage/common/FlowRedisKeyExtract.vue';

  import { utcTimeToSeconds } from '@utils';

  import DbTimeLineItem from '../time-line/TimeLineItem.vue';

  import MysqlDumpDataDownload from './components/MysqlDumpDataDownload.vue';

  interface Props {
    data: FlowMode<unknown>;
    ticketDetail: TicketModel<unknown>;
  }

  defineProps<Props>();

  defineOptions({
    name: FlowMode.STATUS_SUCCEEDED,
    inheritAttrs: false,
  });

  const { t } = useI18n();
</script>
