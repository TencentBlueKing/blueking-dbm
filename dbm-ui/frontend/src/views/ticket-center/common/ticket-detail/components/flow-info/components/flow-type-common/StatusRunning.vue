<template>
  <DbTimeLineItem>
    <template #icon>
      <DbIcon
        class="rotate-loading"
        style="font-size: 14px; color: #3a84ff"
        svg
        type="loading-tubiao" />
    </template>
    <template #title>
      <slot name="title">
        {{ data.flow_type_display }}
      </slot>
    </template>
    <template #content>
      <slot name="content">
        <TodoList
          v-if="data.todos.length > 0"
          :data="data.todos"
          :flow-data="data" />
      </slot>
      <div
        v-if="data.err_msg"
        style="padding: 12px; margin-top: 12px; background: #f5f7fa; border: 2px">
        {{ data.err_msg }}
      </div>
    </template>
  </DbTimeLineItem>
</template>
<script setup lang="ts">
  import type { VNode } from 'vue';

  import FlowMode from '@services/model/ticket/flow';

  import DbTimeLineItem from '../time-line/TimeLineItem.vue';
  import TodoList from '../todo-list/Index.vue';

  interface Props {
    data: FlowMode<unknown, any>;
  }

  defineProps<Props>();

  defineSlots<{
    title: () => VNode;
    content: () => VNode;
  }>();

  defineOptions({
    name: FlowMode.STATUS_RUNNING,
  });
</script>
