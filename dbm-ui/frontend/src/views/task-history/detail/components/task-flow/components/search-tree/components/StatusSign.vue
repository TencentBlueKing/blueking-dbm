<template>
  <TextAll
    v-if="data === 'ALL'"
    style="font-size: 12px; color: #3a84ff" />
  <DbIcon
    v-else-if="isRunning"
    style="color: #3a84ff"
    svg
    type="sync-pending" />
  <div
    v-else-if="currentStatus"
    class="status-round-main"
    :style="{ background: currentStatus.background, borderColor: currentStatus.borderColor }" />
  <span v-else />
</template>
<script setup lang="ts">
  import { TextAll } from 'bkui-vue/lib/icon';

  interface Props {
    data?: string;
  }

  const props = withDefaults(defineProps<Props>(), {
    data: '',
  });

  const statusStyleMap = {
    // 待执行
    CREATED: {
      background: '#F0F1F5',
      borderColor: '#C4C6CC',
    },
    // 执行失败
    FAILED: {
      background: '#FFDDDD',
      borderColor: '#EA3636',
    },
    // 执行成功
    FINISHED: {
      background: '#CBF0DA',
      borderColor: '#2CAF5E',
    },
    // 执行中
    // RUNNING: {
    //   background: '#E1ECFF',
    //   borderColor: '#3A84FF',
    // },
    // 待继续
    TODO: {
      background: '#FCE5C0',
      borderColor: '#F59500',
    },
  };

  const currentStatus = computed(() => statusStyleMap[props.data as keyof typeof statusStyleMap]);

  const isRunning = computed(() => props.data === 'RUNNING');
</script>
<style lang="less">
  .status-round-main {
    width: 8px;
    height: 8px;
    border: 1px solid transparent;
    border-radius: 4px;
  }
</style>
