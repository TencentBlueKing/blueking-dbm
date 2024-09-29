<template>
  <StatusRunning :data="data">
    <template #content>
      <slot name="content">
        <TodoList
          v-if="data.todos.length > 0"
          :data="data.todos"
          :flow-data="data" />
      </slot>
    </template>
  </StatusRunning>
</template>
<script setup lang="ts">
  import FlowMode from '@services/model/ticket/flow';

  import StatusRunning from '../flow-type-common/StatusRunning.vue';
  import TodoList from '../todo-list/Index.vue';

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
  }

  defineProps<Props>();

  defineOptions({
    name: FlowMode.STATUS_RUNNING,
  });
</script>
