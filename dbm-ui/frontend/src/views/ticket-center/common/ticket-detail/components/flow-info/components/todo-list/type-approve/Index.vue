<template>
  <template v-if="data.type === FlowMode.TODO_TYPE_APPROVE">
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

  interface Props {
    data: FlowMode['todos'][number];
    flowData: FlowMode;
    ticketData: TicketModel;
  }

  const props = defineProps<Props>();

  const renderCom = StatusCommon[props.data.status];
</script>
