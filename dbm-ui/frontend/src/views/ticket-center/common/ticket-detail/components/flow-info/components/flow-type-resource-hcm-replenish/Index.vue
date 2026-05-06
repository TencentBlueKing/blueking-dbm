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
    name: FlowMode.TYPE_RESOURCE_HCM_REPLENISH,
    inheritAttrs: false,
  });

  const props = defineProps<Props>();

  const statusModule = Object.assign({}, FlowTypeCommon, {
    [FlowMode.STATUS_FAILED]: StatusFailed,
  });

  const renderCom = statusModule[props.data.status] || '';
</script>
