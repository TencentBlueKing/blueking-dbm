<template>
  <Component
    :is="renderCom"
    :data="data"
    :modify-records="modifyRecords"
    :ticket-detail="ticketDetail" />
</template>
<script setup lang="ts">
  import FlowMode from '@services/model/ticket/flow';
  import type TicketModifyRecordModel from '@services/model/ticket/modify-record';
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
    modifyRecords: TicketModifyRecordModel[];
    ticketDetail: TicketModel;
  }

  defineOptions({
    name: FlowMode.TYPE_HOST_RECYCLE,
    inheritAttrs: false,
  });

  const props = defineProps<Props>();

  const statusModule = Object.assign({}, FlowTypeCommon, {
    [FlowMode.STATUS_SUCCEEDED]: StatusSucceeded,
  });

  const renderCom = statusModule[props.data.status] || '';
</script>
