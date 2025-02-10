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
    <template v-if="flowData.url">
      <span> ，</span>
      <a
        :href="flowData.url"
        target="_blank">
        {{ t('查看详情') }}
      </a>
    </template>
    <div style="margin-top: 10px; color: #979ba5">{{ utcDisplayTime(data.done_at) }}</div>
    <template v-if="data.operators.includes(username) || ticketData.todo_helpers.includes(username)">
      <ProcessPass :todo-data="data">
        <BkButton
          class="w-88"
          theme="primary">
          {{ t('通过') }}
        </BkButton>
      </ProcessPass>
      <ProcessRefuse :todo-data="data">
        <BkButton
          class="w-88 ml-8"
          theme="danger">
          {{ t('拒绝') }}
        </BkButton>
      </ProcessRefuse>
    </template>
  </div>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import FlowMode from '@services/model/ticket/flow';
  import TicketModel from '@services/model/ticket/ticket';

  import { useUserProfile } from '@stores';

  import CostTimer from '@components/cost-timer/CostTimer.vue';

  import ProcessPass from '@views/ticket-center/common/action-confirm/ProcessPass.vue';
  import ProcessRefuse from '@views/ticket-center/common/action-confirm/ProcessRefuse.vue';

  import { utcDisplayTime, utcTimeToSeconds } from '@utils';

  interface Props {
    ticketData: TicketModel;
    data: FlowMode<unknown>['todos'][number];
    flowData: FlowMode<unknown>;
  }

  defineProps<Props>();

  const { t } = useI18n();
  const { username } = useUserProfile();
</script>
