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
    data: FlowMode<
      unknown,
      {
        approve_result: boolean;
        message: string;
        operator: string;
        status: string;
      }
    >;
    ticketDetail: TicketModel<unknown>;
  }

  const props = defineProps<Props>();

  defineOptions({
    name: FlowMode.TYPE_BK_ITSM,
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
