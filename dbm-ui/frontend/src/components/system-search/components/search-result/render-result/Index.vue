<template>
  <Component
    :is="renderCom"
    v-bind="attrs" />
</template>
<script setup lang="ts">
  import { computed, useAttrs } from 'vue';

  import RenderEntry from './entry.vue';
  import RenderInstance from './Instance.vue';
  import ResourcePool from './ResourcePool.vue';
  import RenderTask from './Task.vue';
  import RenderTicket from './Ticket.vue';

  interface Props {
    name: string;
  }

  const props = defineProps<Props>();

  const attrs = useAttrs();

  const comMap = {
    entry: RenderEntry,
    instance: RenderInstance,
    resource_pool: ResourcePool,
    task: RenderTask,
    ticket: RenderTicket,
  };

  const renderCom = computed(() => {
    if (comMap[props.name as keyof typeof comMap]) {
      return comMap[props.name as keyof typeof comMap];
    }
    return 'div';
  });
</script>
