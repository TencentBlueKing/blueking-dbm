<template>
  <component
    :is="renderCom"
    :data="data" />
</template>
<script setup lang="ts">
  import TicketModel from '@services/model/ticket/ticket';

  import StatusApprove from './StatusApprove.vue';
  import StatusFailed from './StatusFailed.vue';
  import StatusResourceReplenish from './StatusResourceReplenish.vue';
  import StatusRunning from './StatusRunning.vue';
  import StatusTodo from './StatusTodo.vue';

  interface Props {
    ticketStatus: string;
    data: TicketModel<unknown>;
  }

  const props = defineProps<Props>();

  const comMap = {
    [TicketModel.STATUS_TODO]: StatusTodo,
    [TicketModel.STATUS_APPROVE]: StatusApprove,
    [TicketModel.STATUS_RESOURCE_REPLENISH]: StatusResourceReplenish,
    [TicketModel.STATUS_FAILED]: StatusFailed,
    [TicketModel.STATUS_RUNNING]: StatusRunning,
  };

  const renderCom = comMap[props.ticketStatus];
</script>
