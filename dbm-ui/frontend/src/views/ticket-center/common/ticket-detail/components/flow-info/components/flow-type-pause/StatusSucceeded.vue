<template>
  <StatusSucceeded :data="data">
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
        :flow-data="data" />
    </template>
  </StatusSucceeded>
</template>
<script setup lang="ts">
  import FlowMode from '@services/model/ticket/flow';

  import StatusSucceeded from '../flow-type-common/StatusSucceeded.vue';
  import TodoList from '../todo-list/Index.vue';

  interface Props {
    data: FlowMode;
  }

  defineProps<Props>();

  defineOptions({
    name: FlowMode.STATUS_SUCCEEDED,
  });
</script>
