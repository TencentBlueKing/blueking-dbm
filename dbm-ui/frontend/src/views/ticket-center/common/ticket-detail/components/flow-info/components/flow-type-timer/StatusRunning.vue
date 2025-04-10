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
        :flow-data="data" />
    </template>
  </DbTimeLineItem>
</template>
<script setup lang="ts">
  import FlowMode from '@services/model/ticket/flow';

  // import { utcDisplayTime } from '@utils';
  import DbTimeLineItem from '../time-line/TimeLineItem.vue';
  import TodoList from '../todo-list/Index.vue';

  // import RunCountdown from './components/RunCountdown.vue';

  interface Props {
    data: FlowMode<{
      run_time: string;
      trigger_time: string;
    }>;
  }

  defineOptions({
    name: FlowMode.STATUS_RUNNING,
  });

  defineProps<Props>();
</script>
