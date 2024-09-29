<template>
  <Component
    :is="renderCom"
    :data="data"
    :ticket-detail="ticketDetail" />
</template>
<script setup lang="ts">
  import FlowMode from '@services/model/ticket/flow';
  import TicketModel from '@services/model/ticket/ticket';

  import FlowTypeCommon from './flow-type-common/index';

  interface Props {
    data: FlowMode<unknown>;
    ticketDetail: TicketModel<unknown>;
  }

  const props = defineProps<Props>();

  const renderCom = FlowTypeCommon[props.data.status] || '';
</script>
