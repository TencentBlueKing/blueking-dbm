<template>
  <Component
    :is="renderCom"
    v-bind="attrs" />
</template>
<script setup lang="ts">
  import { computed, useAttrs } from 'vue';

  import RenderClusterDomain from './ClusterDomain.vue';
  import RenderClusterName from './ClusterName.vue';
  import RenderInstance from './Instance.vue';
  import RenderMachine from './Machine.vue';
  import RenderTask from './Task.vue';
  import RenderTicket from './Ticket.vue';

  interface Props {
    name: string;
  }

  const props = defineProps<Props>();

  const attrs = useAttrs();

  const comMap = {
    cluster_domain: RenderClusterDomain,
    cluster_name: RenderClusterName,
    instance: RenderInstance,
    machine: RenderMachine,
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
