<template>
  <div>
    <I18nT
      keypath="处理人_p"
      scope="global">
      <bk-user-display-name :user-id="data.operators.join(',')" />
    </I18nT>
    <I18nT
      v-if="ticketData.todo_helpers.length > 0"
      keypath="_协助人_p"
      scope="global">
      <bk-user-display-name :user-id="ticketData.todo_helpers.join(',')" />
    </I18nT>
    <I18nT
      keypath="_耗时_t"
      scope="global">
      <CostTimer
        is-timing
        :start-time="utcTimeToSeconds(flowData.start_time)"
        :value="flowData.cost_time" />
    </I18nT>
    <div
      class="mt-12"
      style="color: #979ba5">
      {{ utcDisplayTime(data.done_at) }}
    </div>
    <div
      v-if="isSuperuser || data.operators.includes(username) || ticketData.todo_helpers.includes(username)"
      class="mt-12">
      <ProcessResourceReplenish
        :data="ticketData"
        :todo-data="data">
        <BkButton
          class="w-88"
          theme="primary">
          {{ t('重试') }}
        </BkButton>
      </ProcessResourceReplenish>
      <BkButton
        v-if="isTicketModifiable(ticketData.ticket_type)"
        class="w-88 ml-8"
        @click="handleAdjustApply">
        {{ t('调整申请') }}
      </BkButton>
    </div>
  </div>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import FlowMode from '@services/model/ticket/flow';
  import TicketModifyRecordModel from '@services/model/ticket/modify-record';
  import TicketModel from '@services/model/ticket/ticket';

  import { useUserProfile } from '@stores';

  import CostTimer from '@components/cost-timer/CostTimer.vue';

  import ProcessResourceReplenish from '@views/ticket-center/common/action-confirm/ProcessResourceReplenish.vue';
  import { isTicketModifiable } from '@views/ticket-center/common/ticket-modify/registry';
  import useOpenTicketModify from '@views/ticket-center/common/ticket-modify/useOpenTicketModify';

  import { utcDisplayTime, utcTimeToSeconds } from '@utils';

  interface Props {
    data: FlowMode<unknown>['todos'][number];
    flowData: FlowMode<unknown>;
    ticketData: TicketModel;
  }

  const props = defineProps<Props>();

  const { t } = useI18n();
  const { isSuperuser, username } = useUserProfile();
  const openTicketModify = useOpenTicketModify();

  // 调整申请与「重试」同权，入口放在同一个可见块里
  const handleAdjustApply = () => {
    openTicketModify(props.ticketData, TicketModifyRecordModel.MODE_ADJUST_APPLY);
  };
</script>
