<template>
  <ConsoleInput
    ref="consoleInputRef"
    :cluster="cluster"
    :options="{
      charset,
      timezone,
      role,
    }"
    :placeholder="placeholder"
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
  import RenderMessage from '../mysql/components/RenderMessage.vue';

  interface Props {
    charset: string;
    cluster: ServiceReturnType<typeof queryAllTypeCluster>[number];
    role: string;
    timezone: string;
  }

  const props = defineProps<Props>();

  const { t } = useI18n();

  const consoleInputRef = ref<typeof ConsoleInput>();

  const placeholder = computed(() => `${props.cluster.immute_domain}[${props.role}] > `);

  const preCheck = (cmd: string) => {
    if (/^\s*use\s+.*$/.test(cmd)) {
      return t('暂不支持 use 语句，请使用 db.table 指定 database');
    }
    return '';
  };

  defineExpose({
    clearCurrentScreen: (clusterId: number) => consoleInputRef.value!.clearCurrentScreen(clusterId),
    export: () => consoleInputRef.value!.export(),
    isInputed: (clusterId: number) => consoleInputRef.value!.isInputed(clusterId),
  });
</script>
