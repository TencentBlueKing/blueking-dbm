<template>
  <StatusSucceeded
    :data="data"
    :modify-records="modifyRecords"
    :ticket-detail="ticketDetail">
    <template #title>
      <I18nT
        keypath="确认是否执行 n"
        scope="global">
        {{ data.flow_type_display }}
      </I18nT>
    </template>
    <template #content>
      <TodoList
        v-if="data.todos.length > 0"
        :data="data.todos"
        :flow-data="data"
        :modify-records="modifyRecords" />
    </template>
  </StatusSucceeded>
</template>
<script setup lang="ts">
  import FlowMode from '@services/model/ticket/flow';
  import type TicketModifyRecordModel from '@services/model/ticket/modify-record';
  import TicketModel from '@services/model/ticket/ticket';

  import StatusSucceeded from '../flow-type-common/StatusSucceeded.vue';
  import TodoList from '../todo-list/Index.vue';

  interface Props {
    data: FlowMode;
    modifyRecords: TicketModifyRecordModel[];
    ticketDetail: TicketModel<any>;
  }

  defineOptions({
    name: FlowMode.STATUS_SUCCEEDED,
  });

  defineProps<Props>();
</script>
