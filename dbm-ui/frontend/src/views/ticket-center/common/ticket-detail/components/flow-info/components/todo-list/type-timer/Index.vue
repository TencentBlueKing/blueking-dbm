<template>
  <template v-if="data.type === FlowMode.TODO_TYPE_TIMER">
    <Component
      :is="renderCom"
      :data="data"
      :flow-data="flowData"
      :ticket-data="ticketData" />
  </template>
</template>
<script setup lang="ts">
  import FlowMode from '@services/model/ticket/flow';
  import TicketModel from '@services/model/ticket/ticket';

  import StatusCommon from '../common';

  import StatusDoneSuccess from './StatusDoneSuccess.vue';
  import StatusTodo from './StatusTodo.vue';

  interface Props {
    data: FlowMode<
      unknown,
      unknown,
      {
        action: 'CHANGE' | 'TERMINATE' | 'SKIP';
        flow_id: number;
        remark: string;
        ticket_id: number;
      }
    >['todos'][number];
    flowData: FlowMode<{
      run_time: string;
      trigger_time: string;
    }>;
    ticketData: TicketModel;
  }

  const props = defineProps<Props>();

  const renderCom = Object.assign({}, StatusCommon, {
    [FlowMode.TODO_STATUS_DONE_SUCCESS]: StatusDoneSuccess,
    [FlowMode.TODO_STATUS_TODO]: StatusTodo,
  })[props.data.status];
</script>
