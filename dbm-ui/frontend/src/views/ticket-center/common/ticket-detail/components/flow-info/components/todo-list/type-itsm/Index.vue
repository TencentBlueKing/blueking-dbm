<template>
  <template v-if="data.type === FlowMode.TODO_TYPE_ITSM">
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

  import StatusDoneFailed from './StatusDoneFailed.vue';
  import StatusSuccess from './StatusSuccess.vue';
  import StatusTodo from './StatusTodo.vue';

  interface Props {
    data: FlowMode['todos'][number];
    flowData: FlowMode;
    ticketData: TicketModel;
  }

  const props = defineProps<Props>();

  const renderCom = Object.assign({}, StatusCommon, {
    [FlowMode.TODO_STATUS_DONE_FAILED]: StatusDoneFailed,
    [FlowMode.TODO_STATUS_DONE_SUCCESS]: StatusSuccess,
    [FlowMode.TODO_STATUS_TODO]: StatusTodo,
  })[props.data.status];
</script>
