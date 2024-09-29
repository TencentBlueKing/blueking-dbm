<template>
  <template v-if="data.type === FlowMode.TODO_TYPE_ITSM">
    <Component
      :is="renderCom"
      :data="data"
      :flow-data="flowData" />
  </template>
</template>
<script setup lang="ts">
  import FlowMode from '@services/model/ticket/flow';

  import StatusCommon from '../common';

  import StatusDoneFailed from './StatusDoneFailed.vue';
  import StatusTodo from './StatusTodo.vue';

  interface Props {
    data: FlowMode['todos'][number];
    flowData: FlowMode;
  }

  const props = defineProps<Props>();

  const renderCom = Object.assign({}, StatusCommon, {
    [FlowMode.TODO_STATUS_TODO]: StatusTodo,
    [FlowMode.TODO_STATUS_DONE_FAILED]: StatusDoneFailed,
  })[props.data.status];
</script>
