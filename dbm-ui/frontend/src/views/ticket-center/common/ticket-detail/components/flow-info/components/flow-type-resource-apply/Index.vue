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

  import StatusSuccess from './StatusSuccess.vue';

  interface Props {
    data: FlowMode;
    ticketDetail: TicketModel;
  }

  defineOptions({
    name: FlowMode.TYPE_RESOURCE_APPLY,
    inheritAttrs: false,
  });

  const props = defineProps<Props>();

  const statusModule = Object.assign({}, FlowTypeCommon, {
    [FlowMode.STATUS_SUCCEEDED]: StatusSuccess,
  });

  const renderCom = statusModule[props.data.status] || '';
</script>
