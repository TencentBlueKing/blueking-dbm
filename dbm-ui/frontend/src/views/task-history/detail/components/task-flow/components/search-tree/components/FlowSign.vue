<template>
  <DbIcon
    v-if="iconType"
    class="flow-sign-icon-main"
    :style="{ color: iconColor }"
    :type="iconType" />
  <div
    v-else
    style="width: 24px">
    <StatusSign
      class="ml-4 mr-12"
      :data="status" />
  </div>
</template>
<script setup lang="ts">
  import { FlowTypes } from '@services/source/taskflow';

  import StatusSign from './StatusSign.vue';

  interface Props {
    status?: string;
    type?: string;
  }

  const props = withDefaults(defineProps<Props>(), {
    status: '',
    type: '',
  });

  const colorMap = {
    // 待执行
    CREATED: '#C4C6CC',
    // 执行失败
    FAILED: '#EA3636',
    // 执行成功
    FINISHED: '#2CAF5E',
    // 执行中
    RUNNING: '#3A84FF',
    // 待继续
    TODO: '#F59500',
  };

  const flowTypeIconMap = {
    [FlowTypes.ConditionalParallelGateway]: 'branch-gateway',
    [FlowTypes.ConvergeGateway]: 'converge-gateway',
    [FlowTypes.EmptyEndEvent]: 'jieshu',
    [FlowTypes.EmptyStartEvent]: 'kaishi',
    [FlowTypes.ParallelGateway]: 'parallel-gateway',
    [FlowTypes.SubProcess]: 'liuchengsheji',
  };

  const iconType = computed(() => flowTypeIconMap[props.type as keyof typeof flowTypeIconMap]);

  const iconColor = computed(() => {
    if (props.type === FlowTypes.EmptyStartEvent) {
      return '#2CAF5E';
    }
    if (props.type === FlowTypes.EmptyEndEvent) {
      return '#979BA5';
    }

    return colorMap[props.status as keyof typeof colorMap] || '#2CAF5E';
  });
</script>
<style lang="less">
  .flow-sign-icon-main {
    margin-right: 7px;
    font-size: 18px;
  }
</style>
