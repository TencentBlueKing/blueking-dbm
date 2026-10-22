<template>
  <ConsoleInput
    ref="consoleInputRef"
    :cluster="cluster"
    :disabled="disabled"
    :execute-command="executeCommand"
    :options="{
      charset,
      timezone,
      role,
    }"
    :placeholder="placeholder"
    :pre-check="preCheck"
    @loading-change="(busy) => emits('loadingChange', busy)">
    <template #default="{ message, rowsAffected }">
      <RenderMessage
        :data="message"
        :rows-affected="rowsAffected" />
    </template>
  </ConsoleInput>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import type { queryAllTypeCluster } from '@services/source/dbbase';

  import type { ConsoleCommandResult } from '@views/db-manage/common/webconsole/hooks/useWebconsoleSession';

  import ConsoleInput from '../components/ConsoleInput.vue';

  import RenderMessage from './components/RenderMessage.vue';

  interface Props {
    charset: string;
    cluster: ServiceReturnType<typeof queryAllTypeCluster>[number];
    disabled?: boolean;
    executeCommand?: (command: string) => Promise<ConsoleCommandResult>;
    role: keyof typeof roleDisplay;
    timezone: string;
  }

  const props = withDefaults(defineProps<Props>(), {
    disabled: false,
    executeCommand: undefined,
  });

  type Emits = (e: 'loadingChange', value: boolean) => void;

  const emits = defineEmits<Emits>();

  const { t } = useI18n();

  const consoleInputRef = ref<InstanceType<typeof ConsoleInput>>();

  const roleDisplay = {
    backend_master: 'Master',
    backend_slave: 'Slave',
    orphan: 'Orphan',
  };

  const placeholder = computed(() => `${props.cluster.immute_domain}[${roleDisplay[props.role]}] > `);

  const preCheck = (cmd: string) => {
    if (!props.executeCommand && /^\s*use\s+.*$/.test(cmd)) {
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
