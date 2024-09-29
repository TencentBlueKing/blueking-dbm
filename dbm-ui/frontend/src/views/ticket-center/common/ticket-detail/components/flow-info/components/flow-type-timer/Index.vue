<template>
  <Component
    :is="renderCom"
    :data="data" />
</template>
<script setup lang="ts">
  import FlowMode from '@services/model/ticket/flow';

  import FlowTypeCommon from '../flow-type-common/index';

  import StatusRunning from './StatusRunning.vue';

  interface Props {
    data: FlowMode<{
      run_time: string;
    }>;
  }

  const props = defineProps<Props>();

  defineOptions({
    name: FlowMode.TYPE_TIMER,
    inheritAttrs: false,
  });

  const statusModule = Object.assign({}, FlowTypeCommon, {
    [FlowMode.STATUS_RUNNING]: StatusRunning,
  });

  const renderCom = statusModule[props.data.status] || '';
</script>
