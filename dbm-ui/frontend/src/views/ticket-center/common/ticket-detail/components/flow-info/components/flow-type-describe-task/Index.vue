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

  import StatusSucceeded from './StatusSucceeded.vue';

  interface Props {
    data: FlowMode<
      unknown,
      {
        message: string;
        status: string;
      }
    >;
    ticketDetail: TicketModel;
  }

  const props = defineProps<Props>();

  defineOptions({
    name: FlowMode.TYPE_DESCRIBE_TASK,
    inheritAttrs: false,
  });

  const statusModule = Object.assign({}, FlowTypeCommon, {
    [FlowMode.STATUS_SUCCEEDED]: StatusSucceeded,
  });

  const renderCom = statusModule[props.data.status] || '';
</script>
