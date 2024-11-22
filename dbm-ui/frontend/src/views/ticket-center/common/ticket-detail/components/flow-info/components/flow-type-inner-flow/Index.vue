<template>
  <Component
    :is="renderCom"
    :data="data"
    :ticket-detail="ticketDetail" />
</template>
<script setup lang="ts">
  import FlowMode from '@services/model/ticket/flow';
  import TicketModel from '@services/model/ticket/ticket';

  import FlowTypeCommon from '../flow-type-common/index';

  import StatusFailed from './StatusFailed.vue';
  import StatusRunning from './StatusRunning.vue';
  import StatusSucceeded from './StatusSucceeded.vue';
  import StatusTerminated from './StatusTerminated.vue';

  interface Props {
    data: FlowMode;
    ticketDetail: TicketModel;
  }

  const props = defineProps<Props>();

  defineOptions({
    name: FlowMode.TYPE_INNER_FLOW,
    inheritAttrs: false,
  });

  const statusModule = Object.assign({}, FlowTypeCommon, {
    [FlowMode.STATUS_SUCCEEDED]: StatusSucceeded,
    [FlowMode.STATUS_RUNNING]: StatusRunning,
    [FlowMode.STATUS_TERMINATED]: StatusTerminated,
    [FlowMode.STATUS_FAILED]: StatusFailed,
  });

  const renderCom = statusModule[props.data.status] || '';
</script>
