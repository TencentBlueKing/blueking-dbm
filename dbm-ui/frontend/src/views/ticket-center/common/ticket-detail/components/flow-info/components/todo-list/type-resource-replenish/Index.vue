<template>
  <template v-if="data.type === FlowMode.TODO_TYPE_RESOURCE_REPLENISH">
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

  import StatusTodo from './StatusTodo.vue';

  interface Props {
    ticketData: TicketModel;
    data: FlowMode['todos'][number];
    flowData: FlowMode;
  }

  const props = defineProps<Props>();

  const renderCom = Object.assign({}, StatusCommon, {
    [FlowMode.TODO_STATUS_TODO]: StatusTodo,
  })[props.data.status];
</script>
