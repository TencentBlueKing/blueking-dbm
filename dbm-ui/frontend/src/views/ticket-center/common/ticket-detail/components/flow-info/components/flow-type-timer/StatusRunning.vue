<template>
  <DbTimeLineItem>
    <template #icon>
      <DbIcon
        style="font-size: 14px; color: #3a84ff"
        svg
        type="timed-task" />
    </template>
    <template #title>
      <slot name="title">
        {{ data.flow_type_display }}
      </slot>
    </template>
    <template #content>
      <I18nT
        keypath="定时时间_m_倒计时_t"
        scope="global">
        <span>{{ utcDisplayTime(data.details.trigger_time) }}</span>
        <RunCountdown :model-value="data.details.trigger_time" />
      </I18nT>
      <div
        v-if="ticketDetail.creator === username"
        class="mt-12">
        <DbPopconfirm
          :confirm-handler="handleExec"
          :content="t('将会立即进入下一节点，请谨慎操作！')"
          :title="t('确认跳过定时步骤，立即执行？')">
          <BkButton theme="primary">{{ t('立即执行') }}</BkButton>
        </DbPopconfirm>
        <ModifyTimer :data="data">
          <BkButton class="ml-8">{{ t('修改定时') }}</BkButton>
        </ModifyTimer>
        <ProcessTerminate :data="data">
          <BkButton
            class="ml-8"
            theme="danger">
            {{ t('终止单据') }}
          </BkButton>
        </ProcessTerminate>
      </div>
    </template>
  </DbTimeLineItem>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import FlowMode from '@services/model/ticket/flow';
  import TicketModel from '@services/model/ticket/ticket';
  import { operateTimerFlow } from '@services/source/ticketFlow';

  import { useUserProfile } from '@stores';

  import { utcDisplayTime } from '@utils';

  import DbTimeLineItem from '../time-line/TimeLineItem.vue';

  import ModifyTimer from './components/ModifyTimer.vue';
  import ProcessTerminate from './components/ProcessTerminate.vue';
  import RunCountdown from './components/RunCountdown.vue';

  interface Props {
    data: FlowMode<{
      run_time: string;
      trigger_time: string;
    }>;
    ticketDetail: TicketModel;
  }

  defineOptions({
    name: FlowMode.STATUS_RUNNING,
  });

  const props = defineProps<Props>();

  const { t } = useI18n();
  const { username } = useUserProfile();

  const handleExec = () => {
    return operateTimerFlow({
      action: 'skip',
      flow_id: props.data.id,
    });
  };
</script>
