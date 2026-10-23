<template>
  <div
    ref="consolePanelRef"
    class="console-panel-main"
    @click="handleInputFocus">
    <div>
      <template
        v-for="(item, index) in panelInputMap[clusterId]"
        :key="index">
        <div
          v-if="item.type !== 'normal'"
          class="input-line">
          <span :class="{ 'error-text': item.type === 'error' }">{{ item.message }}</span>
        </div>
        <template v-else>
          <slot v-bind="{ message: item.message, rowsAffected: item.rowsAffected }" />
        </template>
      </template>
    </div>
    <div v-show="loading">Waiting...</div>
    <div
      v-show="!loading"
      class="input-line">
      <textarea
        ref="inputRef"
        class="input-main"
        :disabled="disabled || Boolean(selectedText)"
        :spellcheck="false"
        :style="{ height: realHeight }"
        :value="command"
        @input="handleInputChange"
        @keydown.enter="handleClickSendCommand"
        @keyup.down="handleClickDownBtn"
        @keyup.left="handleClickLeftBtn"
        @keyup.up="handleClickUpBtn" />
    </div>
  </div>
</template>
<script lang="ts">
  // 暂存，通常仅存一条
  const inputStash: Record<number, string[]> = {};
  const panelTokens: Record<number, object> = {};

  export function releaseConsoleTab(clusterId: number) {
    delete panelTokens[clusterId];
    delete panelInputMap[clusterId];
    delete inputStash[clusterId];
    delete executedCommands[clusterId];
  }

  // 已执行过的命令
  const executedCommands: Record<number, string[]> = {};

  const panelInputMap = reactive<
    Record<
      number,
      Array<{
        message: unknown;
        rowsAffected?: number;
        type: 'success' | 'error' | 'normal' | 'command' | string;
      }>
    >
  >({});

  export interface Props {
    checkLineBreak?: (value: string, cursorIndex: number) => boolean;
    cluster: ServiceReturnType<typeof queryAllTypeCluster>[number];
    disabled?: boolean;
    executeCommand?: (command: string) => Promise<ConsoleCommandResult>;
    options?: Record<string, unknown>;
    placeholder?: string;
    preCheck?: (value: string) => string;
  }

  type Emits = {
    (e: 'success', cmd: string, message: ServiceReturnType<typeof queryWebconsole>['query'], ...args: unknown[]): void;
    (e: 'loadingChange', value: boolean): void;
  };

  interface Expose {
    clearCurrentScreen: (id?: number) => void;
    export: () => void;
    isInputed: (id?: number) => boolean;
    updateCommand: () => void;
  }
</script>
<script setup lang="ts">
  import _ from 'lodash';
  import { useI18n } from 'vue-i18n';

  import { queryAllTypeCluster, queryWebconsole } from '@services/source/dbbase';

  import { WebconsoleError } from '@services/source/webconsoleWs';

  import type { ConsoleCommandResult } from '@views/db-manage/common/webconsole/types';

  import { downloadText } from '@utils';

  import { useTextSelection } from './hooks/useTextSelection';

  const props = withDefaults(defineProps<Props>(), {
    checkLineBreak: () => false,
    disabled: false,
    executeCommand: undefined,
    options: () => ({}),
    placeholder: '',
    preCheck: () => '',
  });

  const emits = defineEmits<Emits>();

  const { selectedText } = useTextSelection();
  const { t } = useI18n();

  const command = ref('');
  const consolePanelRef = ref();
  const loading = ref(false);
  const inputRef = ref();
  const realHeight = ref('52px');
  // 用于查找命令的索引
  let commandIndex = 0;
  let panelToken: object;
  let active = true;
  let disposed = false;

  const clusterId = computed(() => props.cluster.id);
  const localPlaceholder = computed(() => props.placeholder || `${props.cluster.immute_domain} > `);

  watch(localPlaceholder, (newValue, oldValue) => {
    command.value = command.value.replace(oldValue, newValue);
  });

  watch(
    clusterId,
    () => {
      if (clusterId.value) {
        panelToken = {};
        panelTokens[clusterId.value] = panelToken;
        // 初始化暂存区
        if (!inputStash[clusterId.value]) {
          inputStash[clusterId.value] = [];
          command.value = localPlaceholder.value;
        } else {
          command.value = inputStash[clusterId.value].pop() || localPlaceholder.value;
        }

        // 初始化已执行命令区
        if (!executedCommands[clusterId.value]) {
          executedCommands[clusterId.value] = [];
          commandIndex = 0;
        } else {
          commandIndex = executedCommands[clusterId.value].length;
        }

        // 初始化命令行渲染区
        if (!panelInputMap[clusterId.value]) {
          panelInputMap[clusterId.value] = [];
        } else {
          panelInputMap[clusterId.value] = _.cloneDeep(panelInputMap[clusterId.value]);
        }

        nextTick(() => {
          if (active && !disposed && panelTokens[clusterId.value] === panelToken) {
            inputRef.value?.focus();
          }
        });
      }
    },
    {
      immediate: true,
    },
  );

  const handleInputFocus = () => {
    nextTick(() => {
      if (active && !disposed) {
        inputRef.value?.focus();
      }
    });
  };

  /*
   * cmd执行之后，更新数据
   */
  const commandExcuted = (cmd: string, result: (typeof panelInputMap)[number][0]) => {
    panelInputMap[clusterId.value].push(result);
    executedCommands[clusterId.value].push(cmd);
    commandIndex = executedCommands[clusterId.value].length;
    command.value = localPlaceholder.value;
  };

  // 回车输入指令
  const handleClickSendCommand = async (e: KeyboardEvent) => {
    if (props.disabled || loading.value || panelTokens[clusterId.value] !== panelToken) {
      e.preventDefault();
      return;
    }
    // 输入预处理
    const inputValue = (e.target as HTMLTextAreaElement).value.trim();
    const isInputed = inputValue.length > localPlaceholder.value.length;

    // 截取输入的命令
    const cmd = inputValue.substring(localPlaceholder.value.length);

    // 光标位置
    const cursorIndex = inputRef.value.selectionStart - localPlaceholder.value.length;

    const isBreakLine = props.checkLineBreak(cmd, cursorIndex);

    // 是否换行
    if (isBreakLine) {
      return;
    }

    // 命令行渲染
    const commandLine = {
      message: isInputed ? inputValue : localPlaceholder.value,
      type: 'command',
    };
    panelInputMap[clusterId.value].push(commandLine);

    if (!isInputed || loading.value) {
      command.value = localPlaceholder.value;
      e.preventDefault();
      return;
    }

    e.preventDefault();

    // 语句预检
    const preCheckResult = props.preCheck(cmd);
    if (preCheckResult && !isBreakLine) {
      commandExcuted(cmd, {
        message: preCheckResult,
        type: 'error',
      });
      return;
    }

    // 固定发起 tab 与显示区；关闭、清屏或重开后丢弃旧结果。
    const requestClusterId = clusterId.value;
    const requestToken = panelToken;
    const requestLines = panelInputMap[requestClusterId];
    const executeCommand = props.executeCommand;
    const isCurrentRequest = () =>
      !disposed && panelTokens[requestClusterId] === requestToken && panelInputMap[requestClusterId] === requestLines;
    try {
      loading.value = true;
      emits('loadingChange', true);
      const httpResult = executeCommand
        ? undefined
        : await queryWebconsole({
            cluster_id: requestClusterId,
            cmd,
            options: props.options,
          });
      const executeResult: ConsoleCommandResult = httpResult || (await executeCommand!(cmd));
      if (!isCurrentRequest()) {
        return;
      }
      if (executeResult.error_msg) {
        commandExcuted(cmd, { message: executeResult.error_msg, type: 'error' });
      } else {
        commandExcuted(cmd, {
          message: executeResult.query,
          rowsAffected: executeResult.rows_affected,
          type: 'normal',
        });
        if (httpResult) {
          emits('success', cmd, httpResult.query);
        }
      }
    } catch (error: unknown) {
      // HTTP 错误仍由原请求层处理，WS 错误只展示在命令起因处。
      if (executeCommand && isCurrentRequest() && !(error instanceof WebconsoleError && error.cancelled)) {
        commandExcuted(cmd, {
          message: error instanceof Error ? error.message : String(error),
          type: 'error',
        });
      }
    } finally {
      loading.value = false;
      emits('loadingChange', false);
      if (isCurrentRequest()) {
        handleInputFocus();
        nextTick(() => {
          if (active && !disposed && consolePanelRef.value) {
            consolePanelRef.value.scrollTop = consolePanelRef.value.scrollHeight - consolePanelRef.value.clientHeight;
          }
        });
      }
    }
  };

  // 恢复最近一次输入并矫正光标
  const restoreInput = (isRestore = true) => {
    const recentOnceInput = command.value;
    command.value = '';
    nextTick(() => {
      command.value = isRestore ? recentOnceInput : localPlaceholder.value;
    });
    setTimeout(() => {
      const cursorIndex = localPlaceholder.value.length;
      inputRef.value.setSelectionRange(cursorIndex, cursorIndex);
    });
  };

  // 输入
  const handleInputChange = (e: any) => {
    if (inputRef.value.selectionStart === localPlaceholder.value.length - 1) {
      restoreInput();
      return;
    }
    if (inputRef.value.selectionStart < localPlaceholder.value.length) {
      restoreInput(false);
      return;
    }
    command.value = e.target.value as string;
    setTimeout(() => {
      const { scrollHeight } = inputRef.value;
      realHeight.value = `${scrollHeight}px`;
    });
  };

  // 键盘 ↑ 键
  const handleClickUpBtn = () => {
    // 光标位置
    const cursorPosition = inputRef.value.selectionStart;

    // 如果光标在命令行的起始位置，切换到上一条命令
    if (cursorPosition === 0) {
      // 先暂存当前输入的命令
      if (commandIndex === executedCommands[clusterId.value].length) {
        inputStash[clusterId.value].push(command.value);
      }
      commandIndex = Math.max(0, commandIndex - 1);
      const cmd = executedCommands[clusterId.value][commandIndex] || '';
      command.value = localPlaceholder.value + cmd;
      checkCursorPosition();
    }
  };

  // 键盘 ↓ 键
  const handleClickDownBtn = () => {
    // 光标位置
    const cursorPosition = inputRef.value.selectionStart;

    // 如果光标在命令行的末尾，切换到下一条命令
    if (cursorPosition === command.value.length) {
      // 暂存弹出
      if (commandIndex === executedCommands[clusterId.value].length - 1 && inputStash[clusterId.value].length === 1) {
        command.value = inputStash[clusterId.value].pop() as string;
        checkCursorPosition();
        return;
      }
      commandIndex = Math.min(executedCommands[clusterId.value].length, commandIndex + 1);
      const cmd = executedCommands[clusterId.value][commandIndex] || '';
      command.value = localPlaceholder.value + cmd;
      checkCursorPosition();
    }
  };

  // 键盘 ← 键
  const handleClickLeftBtn = () => {
    checkCursorPosition();
  };

  // 校正光标位置
  const checkCursorPosition = () => {
    if (inputRef.value.selectionStart < localPlaceholder.value.length) {
      const cursorIndex = localPlaceholder.value.length;
      inputRef.value.setSelectionRange(cursorIndex, cursorIndex);
    }
  };

  /**
   * 当前窗口全局键盘输入事件
   * @param {KeyboardEvent} event
   */
  const handleKeyDown = (event: KeyboardEvent) => {
    if (!active || disposed || props.disabled || loading.value || panelTokens[clusterId.value] !== panelToken) {
      return;
    }
    if (event.key === 'Tab') {
      event.preventDefault();
    }
    if (event.key === 'Home') {
      event.preventDefault();
      inputRef.value.focus();
      const cursorIndex = localPlaceholder.value.length;
      inputRef.value.setSelectionRange(cursorIndex, cursorIndex);
    }
    if (event.key === 'Enter') {
      // 当前textarea失焦则禁止默认行为重新聚集
      if (document.activeElement !== inputRef.value) {
        event.preventDefault();
        inputRef.value.focus();
      }
      const inputEvent = new KeyboardEvent('keyup', { key: 'Enter' });
      inputRef.value.dispatchEvent(inputEvent);
    }
  };

  onMounted(() => {
    window.addEventListener('keydown', handleKeyDown);
  });

  onBeforeUnmount(() => {
    window.removeEventListener('keydown', handleKeyDown);
    disposed = true;
    const currentClusterId = clusterId.value;
    if (panelTokens[currentClusterId] === panelToken) {
      releaseConsoleTab(currentClusterId);
    }
  });

  onActivated(() => {
    active = true;
    window.addEventListener('keydown', handleKeyDown);
    handleInputFocus();
  });

  onDeactivated(() => {
    active = false;
    window.removeEventListener('keydown', handleKeyDown);
    if (panelTokens[clusterId.value] === panelToken && command.value.length > localPlaceholder.value.length) {
      inputStash[clusterId.value].push(command.value);
    }
  });

  defineExpose<Expose>({
    clearCurrentScreen(id?: number) {
      const currentClusterId = id ?? clusterId.value;
      panelInputMap[currentClusterId] = [];
      inputStash[currentClusterId] = [];
      if (currentClusterId === clusterId.value) {
        command.value = localPlaceholder.value;
      }
    },
    export() {
      const lines = (panelInputMap[clusterId.value] || []).map((item) => item.message);
      let exportTxt = '';
      lines.forEach((item) => {
        if (
          Array.isArray(item) &&
          item.every((row: unknown) => typeof row === 'object' && row !== null && !Array.isArray(row))
        ) {
          // mysql 数据表
          const titles = item[0] ? Object.keys(item[0]) : [];
          exportTxt += titles.join('\t');
          exportTxt += '\n';
          item.forEach((row) => {
            const rowValues = titles.reduce((results, title) => {
              const value: unknown = row[title];
              results.push(
                value === null ? 'NULL' : typeof value === 'object' ? JSON.stringify(value) : String(value ?? ''),
              );
              return results;
            }, [] as string[]);
            exportTxt += rowValues.join('\t');
            exportTxt += '\n';
          });
        } else {
          // 普通字符串
          exportTxt += typeof item === 'object' && item !== null ? JSON.stringify(item) : String(item ?? '');
          exportTxt += '\n';
        }
      });

      const fileName = `${props.cluster.immute_domain}.txt`;
      downloadText(fileName, exportTxt);
    },
    isInputed(id?: number) {
      const currentClusterId = id ?? clusterId.value;
      return (
        (currentClusterId === clusterId.value && (loading.value || command.value.length > localPlaceholder.value.length)) ||
        executedCommands[currentClusterId]?.some(Boolean) ||
        inputStash[currentClusterId]?.length > 0
      );
    },
    updateCommand() {
      nextTick(() => {
        command.value = localPlaceholder.value;
      });
    },
  });
</script>
<style lang="less">
  .console-panel-main {
    width: 100%;
    height: 100%;
    padding: 14px 24px;
    overflow-y: auto;
    font-size: 12px;
    color: #dcdee5;

    .input-line {
      display: flex;
      font-weight: 400;
      line-height: 24px;
      color: #94f5a4;
      word-break: break-all;

      .input-main {
        height: auto;
        padding: 0;
        overflow-y: hidden;
        background: #1a1a1a;
        border: none;
        outline: none;
        resize: none;
        flex: 1;
      }

      .error-text {
        color: #ff5656;
      }
    }
  }
</style>
