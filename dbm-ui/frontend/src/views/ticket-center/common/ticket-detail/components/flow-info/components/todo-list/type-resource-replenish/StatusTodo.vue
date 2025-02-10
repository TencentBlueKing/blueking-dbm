<template>
  <div>
    <I18nT
      keypath="处理人_p"
      scope="global">
      {{ data.operators.join(',') }}
    </I18nT>
    <I18nT
      v-if="ticketData.todo_helpers.length > 0"
      keypath="_协助人_p"
      scope="global">
      {{ ticketData.todo_helpers.join(',') }}
    </I18nT>
    <I18nT
      keypath="_耗时_t"
      scope="global">
      <CostTimer
        is-timing
        :start-time="utcTimeToSeconds(flowData.start_time)"
        :value="flowData.cost_time" />
    </I18nT>
    <div style="margin-top: 10px; color: #979ba5">{{ utcDisplayTime(data.done_at) }}</div>
    <template v-if="isSuperuser || data.operators.includes(username) || ticketData.todo_helpers.includes(username)">
      <ProcessResourceReplenish :todo-data="data">
        <BkButton
          class="w-88"
          theme="primary">
          {{ t('重试') }}
        </BkButton>
      </ProcessResourceReplenish>
      <ProcessTerminate :todo-data="data">
        <BkButton
          class="w-88 ml-8"
          theme="danger">
          {{ t('终止单据') }}
        </BkButton>
      </ProcessTerminate>
    </template>
  </div>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import FlowMode from '@services/model/ticket/flow';
  import TicketModel from '@services/model/ticket/ticket';

  import { useUserProfile } from '@stores';

  import CostTimer from '@components/cost-timer/CostTimer.vue';

  import ProcessResourceReplenish from '@views/ticket-center/common/action-confirm/ProcessResourceReplenish.vue';
  import ProcessTerminate from '@views/ticket-center/common/action-confirm/ProcessTerminate.vue';

  import { utcDisplayTime, utcTimeToSeconds } from '@utils';

  interface Props {
    ticketData: TicketModel;
    data: FlowMode<unknown>['todos'][number];
    flowData: FlowMode<unknown>;
  }

  defineProps<Props>();

  const { t } = useI18n();
  const { username, isSuperuser } = useUserProfile();
</script>
