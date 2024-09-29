<template>
  <div>
    <I18nT keypath="处理人_p_耗时_t">
      <span>{{ data.operators.join(',') }}</span>
      <CostTimer
        :is-timing="false"
        :start-time="utcTimeToSeconds(flowData.start_time)"
        :value="data.cost_time" />
    </I18nT>
    <div style="margin-top: 10px; color: #979ba5">{{ utcDisplayTime(data.done_at) }}</div>
    <template v-if="globalManage || data.operators.includes(username)">
      <DbPopconfirm
        :confirm-handler="handleConfirmExecution"
        :content="t('通过后不可撤回')"
        :title="t('确认通过？')">
        <BkButton theme="primary">
          {{ t('通过') }}
        </BkButton>
      </DbPopconfirm>
      <DbPopconfirm
        class="ml-8"
        :confirm-handler="handleTermination"
        :content="t('拒绝后不可撤回')"
        :title="t('拒绝单据？')">
        <BkButton theme="danger">
          {{ t('拒绝') }}
        </BkButton>
      </DbPopconfirm>
    </template>
  </div>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import FlowMode from '@services/model/ticket/flow';
  import { batchProcessTodo } from '@services/source/ticketFlow';

  import { useUserProfile } from '@stores';

  import CostTimer from '@components/cost-timer/CostTimer.vue';

  import { utcDisplayTime, utcTimeToSeconds } from '@utils';

  interface Props {
    data: FlowMode<unknown>['todos'][number];
    flowData: FlowMode<unknown>;
  }

  const props = defineProps<Props>();

  const { t } = useI18n();
  const { username, globalManage } = useUserProfile();

  const handleConfirmExecution = () =>
    batchProcessTodo({
      action: 'APPROVE',
      operations: [
        {
          todo_id: props.data.id,
          params: {
            remark: t('已确认'),
          },
        },
      ],
    });

  const handleTermination = () =>
    batchProcessTodo({
      action: 'TERMINATE',
      operations: [
        {
          todo_id: props.data.id,
          params: {
            remark: t('已拒绝'),
          },
        },
      ],
    });
</script>
