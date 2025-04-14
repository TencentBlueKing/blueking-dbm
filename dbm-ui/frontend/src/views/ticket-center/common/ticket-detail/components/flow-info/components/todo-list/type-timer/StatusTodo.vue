<template>
  <div
    v-if="isSuperuser || data.operators.includes(username) || ticketData.todo_helpers.includes(username)"
    class="mt-8">
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

  import ModifyTimer from './components/ModifyTimer.vue';
  import ProcessTerminate from './components/ProcessTerminate.vue';

  interface Props {
    data: FlowMode<unknown>['todos'][number];
    flowData: FlowMode<{ run_time: string; trigger_time: string }>;
    ticketData: TicketModel;
  }

  const props = defineProps<Props>();

  const { t } = useI18n();
  const { isSuperuser, username } = useUserProfile();

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
