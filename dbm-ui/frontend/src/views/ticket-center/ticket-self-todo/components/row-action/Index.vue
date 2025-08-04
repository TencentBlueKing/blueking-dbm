<template>
  <component
    :is="renderCom"
    :data="data" />
</template>
<script setup lang="ts">
  import TicketModel from '@services/model/ticket/ticket';

  import StatusApprove from './StatusApprove.vue';
  import StatusFailed from './StatusFailed.vue';
  import StatusInnerTodo from './StatusInnerTodo.vue';
  import StatusResourceReplenish from './StatusResourceReplenish.vue';
  import StatusTimer from './StatusTimer.vue';
  import StatusTodo from './StatusTodo.vue';

  interface Props {
    data: TicketModel;
    ticketStatus: string;
  }

  const props = defineProps<Props>();

  const comMap = {
    [TicketModel.STATUS_APPROVE]: StatusApprove,
    [TicketModel.STATUS_FAILED]: StatusFailed,
    [TicketModel.STATUS_INNER_TODO]: StatusInnerTodo,
    [TicketModel.STATUS_RESOURCE_REPLENISH]: StatusResourceReplenish,
    [TicketModel.STATUS_TIMER]: StatusTimer,
    [TicketModel.STATUS_TODO]: StatusTodo,
  };

  const renderCom = comMap[props.ticketStatus];
</script>
