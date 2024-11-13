<template>
  <ConsoleInput
    ref="consoleInputRef"
    :cluster="cluster"
    :ext-params="{
      dbNum,
      raw,
    }"
    :placeholder="placeholder"
    @success="handleSuccess">
    <template #default="{ message }">
      <RenderMessage :data="message" />
    </template>
  </ConsoleInput>
</template>

<script setup lang="ts">
  import type { queryAllTypeCluster, queryWebconsole } from '@services/source/dbbase';

  import ConsoleInput from '../components/ConsoleInput.vue';

  import RenderMessage from './components/RenderMessage.vue';

  interface Props {
    cluster: ServiceReturnType<typeof queryAllTypeCluster>[number];
    raw: boolean;
  }

  const props = defineProps<Props>();

  const consoleInputRef = ref<typeof ConsoleInput>();
  const dbNum = ref(0);

  const placeholder = computed(() => `${props.cluster.immute_domain}[${dbNum.value}] > `);

  const handleSuccess = (cmd: string, message: ServiceReturnType<typeof queryWebconsole>['query']) => {
    // 切换数据库索引
    if (/^\s*select\s+.*$/.test(cmd) && /^OK/.test(message as string)) {
      dbNum.value = Number(cmd.substring('select '.length));
      consoleInputRef.value!.updateCommand();
    }
  };

  defineExpose({
    isInputed: (clusterId: number) => consoleInputRef.value!.isInputed(clusterId),
    clearCurrentScreen: (clusterId: number) => consoleInputRef.value!.clearCurrentScreen(clusterId),
    export: () => consoleInputRef.value!.export(),
  });
</script>
