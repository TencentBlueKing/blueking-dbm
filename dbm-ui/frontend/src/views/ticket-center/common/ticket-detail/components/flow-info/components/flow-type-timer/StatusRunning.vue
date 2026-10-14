<template>
  <DbTimeLineItem>
    <template #icon>
      <DbIcon
        style="font-size: 14px; color: #3a84ff"
        svg
        type="timed-task" />
    </template>
    <template #title>
      <slot name="title">
        {{ data.flow_type_display }}
      </slot>
    </template>
    <template #content>
      <TodoList
        v-if="data.todos.length > 0"
        :data="data.todos"
        :flow-data="data"
        :modify-records="modifyRecords" />
    </template>
  </DbTimeLineItem>
</template>
<script setup lang="ts">
  import FlowMode from '@services/model/ticket/flow';
  import type TicketModifyRecordModel from '@services/model/ticket/modify-record';

  import DbTimeLineItem from '../time-line/TimeLineItem.vue';
  import TodoList from '../todo-list/Index.vue';

  interface Props {
    data: FlowMode<{
      run_time: string;
      trigger_time: string;
    }>;
    modifyRecords: TicketModifyRecordModel[];
  }

  defineOptions({
    name: FlowMode.STATUS_RUNNING,
  });

  defineProps<Props>();
</script>
