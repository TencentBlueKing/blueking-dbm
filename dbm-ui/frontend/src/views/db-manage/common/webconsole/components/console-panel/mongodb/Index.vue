<template>
  <ConsoleInput
    ref="consoleInputRef"
    :check-line-break="checkLineBreak"
    :cluster="cluster"
    :options="{
      session_time: sessionTime,
    }"
    :pre-check="preCheck">
    <template #default="{ message }">
      <RenderMessage :data="message" />
    </template>
  </ConsoleInput>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import type { queryAllTypeCluster } from '@services/source/dbbase';

  import { useTimeZoneFormat } from '@hooks';

  import { validateBrackets } from '@utils';

  import ConsoleInput from '../components/ConsoleInput.vue';

  import RenderMessage from './components/RenderMessage.vue';

  interface Props {
    cluster: ServiceReturnType<typeof queryAllTypeCluster>[number];
  }

  defineProps<Props>();

  const { format: formatDateToUTC } = useTimeZoneFormat();
  const { t } = useI18n();

  const consoleInputRef = ref<typeof ConsoleInput>();
  const sessionTime = ref(formatDateToUTC(new Date().toString()));

  // 是否换行
  const checkLineBreak = (cmd: string, cursorIndex: number) => {
    const stack: string[] = [];
    for (let i = 0; i < cursorIndex; i++) {
      const char = cmd[i];
      if ('({['.includes(char)) {
        stack.push(char);
      } else if (')}]'.includes(char)) {
        const last = stack.pop();
        if ((char === ')' && last !== '(') || (char === '}' && last !== '{') || (char === ']' && last !== '[')) {
          return false;
        }
      }
    }
    if (stack.length > 0) {
      return true;
    }
    return false;
  };

  const preCheck = (cmd: string) => {
    return !validateBrackets(cmd) ? t('不是正确的脚本语句，请检查语法') : '';
  };

  defineExpose({
    clearCurrentScreen: (clusterId: number) => consoleInputRef.value!.clearCurrentScreen(clusterId),
    export: () => consoleInputRef.value!.export(),
    isInputed: (clusterId: number) => consoleInputRef.value!.isInputed(clusterId),
  });
</script>
