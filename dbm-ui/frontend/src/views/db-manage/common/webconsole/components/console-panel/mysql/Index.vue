<template>
  <ConsoleInput
    ref="consoleInputRef"
    :cluster="cluster"
    :pre-check="preCheck">
    <template #default="{ message }">
      <RenderMessage :data="message" />
    </template>
  </ConsoleInput>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import type { queryAllTypeCluster } from '@services/source/dbbase';

  import ConsoleInput from '../components/ConsoleInput.vue';

  import RenderMessage from './components/RenderMessage.vue';

  interface Props {
    cluster: ServiceReturnType<typeof queryAllTypeCluster>[number];
  }

  defineProps<Props>();

  const { t } = useI18n();

  const consoleInputRef = ref<typeof ConsoleInput>();

  const preCheck = (cmd: string) => {
    if (/^\s*use\s+.*$/.test(cmd)) {
      return t('暂不支持 use 语句，请使用 db.table 指定 database');
    }
    return '';
  };

  defineExpose({
    isInputed: (clusterId: number) => consoleInputRef.value!.isInputed(clusterId),
    clearCurrentScreen: (clusterId: number) => consoleInputRef.value!.clearCurrentScreen(clusterId),
    export: () => consoleInputRef.value!.export(),
  });
</script>
