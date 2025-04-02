<template>
  <ConsoleInput
    ref="consoleInputRef"
    :cluster="cluster"
    :ext-params="{
      session_time: sessionTime,
    }">
    <template #default="{ message }">
      <RenderMessage :data="message" />
    </template>
  </ConsoleInput>
</template>

<script setup lang="ts">
  import type { queryAllTypeCluster } from '@services/source/dbbase';

  import { useTimeZoneFormat } from '@hooks';

  import ConsoleInput from '../components/ConsoleInput.vue';

  import RenderMessage from './components/RenderMessage.vue';

  interface Props {
    cluster: ServiceReturnType<typeof queryAllTypeCluster>[number];
  }

  defineProps<Props>();

  const { format: formatDateToUTC } = useTimeZoneFormat();

  const consoleInputRef = ref<typeof ConsoleInput>();
  const sessionTime = ref(formatDateToUTC(new Date().toString()));

  defineExpose({
    clearCurrentScreen: (clusterId: number) => consoleInputRef.value!.clearCurrentScreen(clusterId),
    export: () => consoleInputRef.value!.export(),
    isInputed: (clusterId: number) => consoleInputRef.value!.isInputed(clusterId),
  });
</script>
