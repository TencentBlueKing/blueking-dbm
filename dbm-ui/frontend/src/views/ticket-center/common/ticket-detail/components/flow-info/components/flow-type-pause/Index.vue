<template>
  <Component
    :is="renderCom"
    :data="data">
    <template #title>
      <I18nT
        keypath="确认是否执行 n"
        scope="global">
        {{ data.flow_type_display }}
      </I18nT>
    </template>
  </Component>
</template>
<script setup lang="ts">
  import FlowMode from '@services/model/ticket/flow';

  import FlowTypeCommon from '../flow-type-common/index';

  import StatusFailed from './StatusFailed.vue';
  import StatusRunning from './StatusRunning.vue';
  import StatusSucceeded from './StatusSucceeded.vue';
  import StatusTerminated from './StatusTerminated.vue';

  interface Props {
    data: FlowMode<unknown>;
  }

  const props = defineProps<Props>();

  defineOptions({
    name: FlowMode.TYPE_PAUSE,
    inheritAttrs: false,
  });

  const statusModule = Object.assign({}, FlowTypeCommon, {
    [FlowMode.STATUS_SUCCEEDED]: StatusSucceeded,
    [FlowMode.STATUS_RUNNING]: StatusRunning,
    [FlowMode.STATUS_TERMINATED]: StatusTerminated,
    [FlowMode.STATUS_FAILED]: StatusFailed,
  });

  const renderCom = statusModule[props.data.status] || 'div';
</script>
