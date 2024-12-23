<template>
  <StatusFailed
    :data="data"
    :ticket-detail="ticketDetail">
    <template #content>
      <I18nT
        v-if="isNeedOperation"
        keypath="m_处理人_p_耗时_t"
        scope="global">
        <span style="color: #ea3636">{{ t('执行失败') }}</span>
        <span>{{ ticketDetail.todo_operators.join(',') }}</span>
        <CostTimer
          :is-timing="false"
          :start-time="utcTimeToSeconds(data.start_time)"
          :value="data.cost_time" />
      </I18nT>
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
      <div
        v-if="isCanOperation && isNeedOperation"
        class="mt-12">
        <ProcessRetry
          :data="ticketDetail"
          :flow-data="data">
          <BkButton
            class="w-88"
            theme="primary">
            {{ t('失败重试') }}
          </BkButton>
        </ProcessRetry>
        <ProcessFailedTerminate
          :data="ticketDetail"
          :flow-data="data">
          <BkButton
            class="ml-8 w-88"
            theme="danger">
            {{ t('终止') }}
          </BkButton>
        </ProcessFailedTerminate>
      </div>
    </template>
  </StatusFailed>
</template>
<script setup lang="ts">
  import type { ComponentProps } from 'vue-component-type-helpers';
  import { useI18n } from 'vue-i18n';

  import FlowMode from '@services/model/ticket/flow';
  import TicketModel from '@services/model/ticket/ticket';

  import { useUserProfile } from '@stores';

  import { TicketTypes } from '@common/const';

  import CostTimer from '@components/cost-timer/CostTimer.vue';

  import ProcessFailedTerminate from '@views/ticket-center/common/action-confirm/ProcessFailedTerminate.vue';
  import ProcessRetry from '@views/ticket-center/common/action-confirm/ProcessRetry.vue';

  import { utcTimeToSeconds } from '@utils';

  import StatusFailed from '../flow-type-common/StatusFailed.vue';

  import MongodbExecScriptDownloadFile from './components/MongodbExecScriptDownloadFile.vue';

  interface Props {
    data: FlowMode;
    ticketDetail: TicketModel<unknown>;
  }

  const props = defineProps<Props>();

  defineOptions({
    name: FlowMode.STATUS_FAILED,
  });

  const { t } = useI18n();
  const { username, isSuperuser } = useUserProfile();

  const isCanOperation = computed(() => isSuperuser || props.ticketDetail.todo_operators.includes(username));
  const isNeedOperation = computed(() => props.data.err_msg || [0, 2].includes(props.data.err_code));
</script>
