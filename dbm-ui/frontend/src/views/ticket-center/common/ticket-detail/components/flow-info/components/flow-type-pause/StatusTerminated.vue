<template>
  <StatusTerminated
    :data="data"
    :ticket-detail="ticketDetail">
    <template #title>
      <I18nT
        keypath="确认是否执行 n"
        scope="global">
        {{ data.flow_type_display }}
      </I18nT>
    </template>
  </StatusTerminated>
</template>
<script setup lang="ts">
  import FlowMode from '@services/model/ticket/flow';
  import TicketModel from '@services/model/ticket/ticket';

  import StatusTerminated from '../flow-type-common/StatusTerminated.vue';

  interface Props {
    data: FlowMode;
    ticketDetail: TicketModel<unknown>;
  }

  defineOptions({
    name: FlowMode.STATUS_RUNNING,
  });

  defineProps<Props>();
</script>
