<template>
  <StatusRunning :data="data">
    <template #content>
      <TodoList
        v-if="data.todos.length > 0"
        :data="data.todos"
        :flow-data="data" />
    </template>
  </StatusRunning>
</template>
<script setup lang="ts">
  import FlowMode from '@services/model/ticket/flow';

  import StatusRunning from '../flow-type-common/StatusRunning.vue';
  import TodoList from '../todo-list/Index.vue';

  interface Props {
    data: FlowMode;
  }

  defineProps<Props>();

  defineOptions({
    name: FlowMode.STATUS_RUNNING,
  });
</script>
