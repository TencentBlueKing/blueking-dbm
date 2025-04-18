<template>
  <div class="mt-12">
    <div v-if="data.context.action !== 'CHANGE'">
      <I18nT
        keypath="定时时间_m_倒计时_t"
        scope="global">
        <span>{{ utcDisplayTime(flowData.details.trigger_time) }}</span>
        <RunCountdown :model-value="flowData.details.trigger_time" />
      </I18nT>
    </div>
    <template v-if="data.context.action === 'CHANGE'">
      <I18nT
        keypath="U_已处理_A"
        scope="global">
        <span>{{ data.done_by }}</span>
        <span style="color: #f59500">{{ t('修改定时') }}</span>
      </I18nT>
      <span>，</span>
      <I18nT
        keypath="定时时间_m_倒计时_t"
        scope="global">
        <span>{{ utcDisplayTime(flowData.details.trigger_time) }}</span>
        <RunCountdown :model-value="flowData.details.trigger_time" />
      </I18nT>
    </template>
    <I18nT
      v-if="data.context.action === 'SKIP'"
      keypath="U_已处理_A"
      scope="global">
      <span>{{ data.done_by }}</span>
      <span style="color: #f59500">{{ t('立即执行') }}</span>
    </I18nT>
  </div>
  <div
    v-if="data.context.action && data.context.remark"
    class="mt-12"
    style="line-height: 16px; color: #63656e">
    <I18nT
      keypath="备注：c"
      scope="global">
      <span>{{ data.context.remark }}</span>
    </I18nT>
  </div>
  <div class="mt-12">
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
  </div>
  <div
    v-if="data.operators.includes(username) || ticketData.todo_helpers.includes(username)"
    class="mt-12">
    <DbPopconfirm
      :confirm-handler="handleExec"
      :content="t('将会立即进入下一节点，请谨慎操作！')"
      :title="t('确认跳过定时步骤，立即执行？')">
      <BkButton theme="primary">{{ t('立即执行') }}</BkButton>
    </DbPopconfirm>
    <ModifyTimer
      :flow-data="flowData"
      :todo-data="data">
      <BkButton class="ml-8">{{ t('修改定时') }}</BkButton>
    </ModifyTimer>
    <ProcessTerminate :todo-data="data">
      <BkButton
        class="ml-8"
        theme="danger">
        {{ t('终止单据') }}
      </BkButton>
    </ProcessTerminate>
  </div>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import FlowMode from '@services/model/ticket/flow';
  import TicketModel from '@services/model/ticket/ticket';
  import { batchProcessTodo } from '@services/source/ticketFlow';

  import { useUserProfile } from '@stores';

  import CostTimer from '@components/cost-timer/CostTimer.vue';

  import { utcDisplayTime, utcTimeToSeconds } from '@utils';

  import ModifyTimer from './components/ModifyTimer.vue';
  import ProcessTerminate from './components/ProcessTerminate.vue';
  import RunCountdown from './components/RunCountdown.vue';

  interface Props {
    data: FlowMode<
      unknown,
      unknown,
      { action: 'CHANGE' | 'TERMINATE' | 'SKIP'; flow_id: number; remark: string; ticket_id: number }
    >['todos'][number];
    flowData: FlowMode<{ run_time: string; trigger_time: string }>;
    ticketData: TicketModel;
  }

  const props = defineProps<Props>();

  const { t } = useI18n();
  const { username } = useUserProfile();

  const handleExec = () => {
    return batchProcessTodo({
      action: 'SKIP',
      operations: [
        {
          params: {},
          todo_id: props.data.id,
        },
      ],
    });
  };
</script>
