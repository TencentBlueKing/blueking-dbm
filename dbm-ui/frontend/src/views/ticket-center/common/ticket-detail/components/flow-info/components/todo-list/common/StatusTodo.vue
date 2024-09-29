<template>
  <div>
    <div>
      <I18nT keypath="处理人_p_耗时_t">
        <span>{{ data.operators.join(',') }}</span>
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
    </div>
    <div style="margin-top: 10px; color: #979ba5">{{ utcDisplayTime(data.done_at) }}</div>
    <template v-if="globalManage || data.operators.includes(username)">
      <DbPopconfirm
        :confirm-handler="handleConfirmExecution"
        :content="t('执行后不可撤回')"
        :title="t('确认执行？')">
        <BkButton theme="primary">
          {{ t('确认执行') }}
        </BkButton>
      </DbPopconfirm>
      <DbPopconfirm
        class="ml-8"
        :confirm-handler="handleTermination"
        :content="t('终止后不可撤回')"
        :title="t('终止单据？')">
        <BkButton theme="danger">
          {{ t('终止单据') }}
        </BkButton>
      </DbPopconfirm>
    </template>
  </div>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import FlowMode from '@services/model/ticket/flow';
  import { batchProcessTodo } from '@services/source/ticketFlow';

  import { useEventBus } from '@hooks';

  import { useUserProfile } from '@stores';

  import CostTimer from '@components/cost-timer/CostTimer.vue';

  import { utcDisplayTime, utcTimeToSeconds } from '@utils';

  interface Props {
    data: FlowMode<unknown>['todos'][number];
    flowData: FlowMode<unknown>;
  }

  const props = defineProps<Props>();

  defineOptions({
    name: FlowMode.TODO_STATUS_TODO,
  });

  const { t } = useI18n();
  const eventBus = useEventBus();
  const { username, globalManage } = useUserProfile();

  const handleConfirmExecution = () =>
    batchProcessTodo({
      action: 'APPROVE',
      operations: [
        {
          todo_id: props.data.id,
          params: {
            remark: t('确认执行'),
          },
        },
      ],
    }).then(() => eventBus.emit('refreshTicketStatus'));

  const handleTermination = () =>
    batchProcessTodo({
      action: 'TERMINATE',
      operations: [
        {
          todo_id: props.data.id,
          params: {
            remark: t('人工终止'),
          },
        },
      ],
    }).then(() => eventBus.emit('refreshTicketStatus'));
</script>
