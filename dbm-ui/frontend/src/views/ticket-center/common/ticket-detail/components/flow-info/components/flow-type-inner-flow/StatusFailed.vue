<template>
  <StatusFailed
    :data="data"
    :ticket-detail="ticketDetail">
    <template #content>
      <I18nT keypath="m_耗时_t">
        <span style="color: #ea3636">{{ t('执行失败') }}</span>
        <CostTimer
          :is-timing="false"
          :start-time="utcTimeToSeconds(data.start_time)"
          :value="data.cost_time" />
      </I18nT>
      <template v-if="data.url">
        <span> ，</span>
        <a
          :href="data.url"
          target="_blank">
          {{ t('查看详情') }}
        </a>
      </template>
      <div
        v-if="data.err_msg || [0, 2].includes(data.err_code)"
        class="mt-12">
        <DbPopconfirm
          :confirm-handler="handleRetry"
          :content="t('重新执行后无法撤回，请谨慎操作！')"
          :title="t('是否确认重试此步骤')">
          <BkButton
            class="w-88"
            theme="primary">
            {{ t('重试') }}
          </BkButton>
        </DbPopconfirm>
        <DbPopconfirm
          :confirm-handler="handleTerminate"
          :content="t('终止执行后无法撤回，请谨慎操作！')"
          :title="t('是否确认终止执行单据')">
          <BkButton
            class="ml-8 w-88"
            theme="danger">
            {{ t('终止') }}
          </BkButton>
        </DbPopconfirm>
      </div>
    </template>
  </StatusFailed>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import FlowMode from '@services/model/ticket/flow';
  import TicketModel from '@services/model/ticket/ticket';
  import { batchProcessTodo, retryFlow } from '@services/source/ticketFlow';

  import { useEventBus } from '@hooks';

  import CostTimer from '@components/cost-timer/CostTimer.vue';

  import { utcTimeToSeconds } from '@utils';

  import StatusFailed from '../flow-type-common/StatusFailed.vue';

  interface Props {
    data: FlowMode;
    ticketDetail: TicketModel<unknown>;
  }

  const props = defineProps<Props>();

  defineOptions({
    name: FlowMode.STATUS_FAILED,
  });

  const eventBus = useEventBus();
  const { t } = useI18n();

  const handleRetry = () =>
    retryFlow({
      id: props.ticketDetail.id,
      flow_id: props.data.id,
    }).then(() => eventBus.emit('refreshTicketStatus'));

  const handleTerminate = () =>
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
