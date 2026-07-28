<template>
  <Component
    :is="renderCom"
    v-bind="attrs"
    @to-result="handleToResult" />
</template>
<script setup lang="ts">
  import { computed, useAttrs } from 'vue';

  import RenderCluster from './Cluster.vue';
  import RenderInstance from './Instance.vue';
  import Machine from './Machine.vue';
  import RenderTask from './Task.vue';
  import RenderTicket from './Ticket.vue';

  interface Props {
    name: string;
  }

  type Emits = (e: 'to-result', resourceType: string) => void;

  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();

  const attrs = useAttrs();

  const comMap = {
    cluster: RenderCluster,
    instance: RenderInstance,
    machine: Machine,
    task: RenderTask,
    ticket: RenderTicket,
  };

  const renderCom = computed(() => {
    if (comMap[props.name as keyof typeof comMap]) {
      return comMap[props.name as keyof typeof comMap];
    }
    return 'div';
  });

  const handleToResult = (resourceType: string) => {
    emits('to-result', resourceType);
  };
</script>
