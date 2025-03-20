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

  defineOptions({
    name: FlowMode.TYPE_BK_ITSM,
    inheritAttrs: false,
  });

  const props = defineProps<Props>();

  const statusModule = Object.assign({}, FlowTypeCommon, {
    [FlowMode.STATUS_FAILED]: StatusFailed,
    [FlowMode.STATUS_RUNNING]: StatusRunning,
    [FlowMode.STATUS_SUCCEEDED]: StatusSucceeded,
    [FlowMode.STATUS_TERMINATED]: StatusTerminated,
  });

  const renderCom = statusModule[props.data.status] || '';
</script>
