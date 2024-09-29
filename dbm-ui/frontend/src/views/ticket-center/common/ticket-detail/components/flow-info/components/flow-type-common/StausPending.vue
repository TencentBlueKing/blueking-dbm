<template>
  <DbTimeLineItem>
    <template #title>
      <slot name="title">
        {{ data.flow_type_display }}
      </slot>
    </template>
  </DbTimeLineItem>
</template>
<script setup lang="ts">
  import FlowMode from '@services/model/ticket/flow';

  import DbTimeLineItem from '../time-line/TimeLineItem.vue';

  interface Props {
    data: FlowMode<unknown>;
  }

  defineProps<Props>();

  defineSlots<{
    title: () => VNode;
  }>();

  defineOptions({
    name: FlowMode.STATUS_PENDING,
  });
</script>
