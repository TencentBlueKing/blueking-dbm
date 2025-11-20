<template>
  <StatusFailed
    :data="data"
    :ticket-detail="ticketDetail">
    <template #content>
      <template v-if="isNeedOperation">
        <I18nT
          keypath="m_处理人_p"
          scope="global">
          <span style="color: #ea3636">{{ t('执行失败') }}</span>
          {{ ticketDetail.todo_operators.join(',') }}
        </I18nT>
        <I18nT
          v-if="ticketDetail.todo_helpers.length > 0"
          keypath="_协助人_p"
          scope="global">
          {{ ticketDetail.todo_helpers.join(',') }}
        </I18nT>
        <I18nT
          keypath="_耗时_t"
          scope="global">
          <CostTimer
            :is-timing="false"
            :start-time="utcTimeToSeconds(data.start_time)"
            :value="data.cost_time" />
        </I18nT>
      </template>
      <I18nT
        v-else
        keypath="m_耗时_t"
        scope="global">
        <span style="color: #ea3636">{{ t('执行失败') }}</span>
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
          {{ t('去处理') }}
        </a>
      </template>
    </template>
  </StatusFailed>
</template>
<script setup lang="ts">
  import type { ComponentProps } from 'vue-component-type-helpers';
  import { useI18n } from 'vue-i18n';

  import FlowMode from '@services/model/ticket/flow';
  import TicketModel from '@services/model/ticket/ticket';

  import { TicketTypes } from '@common/const';

  import CostTimer from '@components/cost-timer/CostTimer.vue';

  import { utcTimeToSeconds } from '@utils';

  import StatusFailed from '../flow-type-common/StatusFailed.vue';

  import MongodbExecScriptDownloadFile from './components/MongodbExecScriptDownloadFile.vue';

  interface Props {
    data: FlowMode;
    ticketDetail: TicketModel<unknown>;
  }

  defineOptions({
    name: FlowMode.STATUS_FAILED,
  });

  const props = defineProps<Props>();

  const { t } = useI18n();

  const isNeedOperation = computed(() => props.data.err_msg || [0, 2].includes(props.data.err_code));
</script>
