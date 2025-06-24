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
          <slot :message="item.message" />
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
        :disabled="Boolean(selectedText)"
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
  // 已执行过的命令
  const executedCommands: Record<number, string[]> = {};

  const panelInputMap = reactive<
    Record<
      number,
      Array<{
        message: any;
        type: 'success' | 'error' | 'normal' | 'command' | string;
      }>
    >
  >({});
</script>
<script setup lang="ts">
  import _ from 'lodash';

  import { queryAllTypeCluster, queryWebconsole } from '@services/source/dbbase';

  import { downloadText } from '@utils';

  import { useTextSelection } from './hooks/useTextSelection';

  export interface Props {
    checkLineBreak?: (value: string, cursorIndex: number) => boolean;
    cluster: ServiceReturnType<typeof queryAllTypeCluster>[number];
    options?: Record<string, unknown>;
    placeholder?: string;
    preCheck?: (value: string) => string;
  }

  type Emits = (
    e: 'success',
    cmd: string,
    message: ServiceReturnType<typeof queryWebconsole>['query'],
    ...args: unknown[]
  ) => void;

  interface Expose {
    clearCurrentScreen: (id?: number) => void;
    export: () => void;
    isInputed: (id?: number) => boolean;
    updateCommand: () => void;
  }

  const props = withDefaults(defineProps<Props>(), {
    checkLineBreak: () => false,
    options: () => ({}),
    placeholder: '',
    preCheck: () => '',
  });

  const emits = defineEmits<Emits>();

  const { selectedText } = useTextSelection();

  const command = ref('');
  const consolePanelRef = ref();
  const loading = ref(false);
  const inputRef = ref();
  const realHeight = ref('52px');
  // 用于查找命令的索引
  let commandIndex = 0;

  const clusterId = computed(() => props.cluster.id);
  const localPlaceholder = computed(() => props.placeholder || `${props.cluster.immute_domain} > `);

  watch(
    clusterId,
    () => {
      if (clusterId.value) {
        // 初始化暂存区
        if (!inputStash[clusterId.value]) {
          inputStash[clusterId.value] = [];
          command.value = localPlaceholder.value;
        } else {
          command.value = inputStash[clusterId.value].pop() as string;
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

        setTimeout(() => {
          inputRef.value.focus();
        });
      }
    },
    {
      immediate: true,
    },
  );

  const handleInputFocus = () => {
    setTimeout(() => {
      inputRef.value.focus();
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
  const handleClickSendCommand = async (e: any) => {
    // 输入预处理
    const inputValue = e.target.value.trim() as string;
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

    // 语句预检
    const preCheckResult = props.preCheck(cmd);
    if (preCheckResult && !isBreakLine) {
      commandExcuted(cmd, {
        message: preCheckResult,
        type: 'error',
      });
      return;
    }

    // 开始请求
    try {
      loading.value = true;
      const executeResult = await queryWebconsole({
        cluster_id: clusterId.value,
        cmd,
        options: props.options,
      });

      // 请求结果渲染
      if (executeResult.error_msg) {
        // 错误消息
        commandExcuted(cmd, {
          message: executeResult.error_msg,
          type: 'error',
        });
      } else {
        // 正常消息
        commandExcuted(cmd, {
          message: executeResult.query,
          type: 'normal',
        });

        emits('success', cmd, executeResult.query);
      }
    } finally {
      loading.value = false;
      setTimeout(() => {
        inputRef.value.focus();
        consolePanelRef.value.scrollTop = consolePanelRef.value.scrollHeight - consolePanelRef.value.clientHeight;
      });
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
    const currentClusterId = clusterId.value;
    delete panelInputMap[currentClusterId];
    delete inputStash[currentClusterId];
    delete executedCommands[currentClusterId];
  });

  onActivated(() => {
    handleInputFocus();
  });

  onDeactivated(() => {
    if (command.value.length > localPlaceholder.value.length) {
      inputStash[clusterId.value].push(command.value);
    }
  });

  defineExpose<Expose>({
    clearCurrentScreen(id?: number) {
      const currentClusterId = id ?? clusterId.value;
      panelInputMap[currentClusterId] = [];
      inputStash[currentClusterId] = [];
      command.value = localPlaceholder.value;
    },
    export() {
      const lines = panelInputMap[clusterId.value].map((item) => item.message);
      let exportTxt = '';
      lines.forEach((item) => {
        if (Array.isArray(item)) {
          // mysql 数据表
          const titles = Object.keys(item[0]);
          exportTxt += titles.join('\t');
          exportTxt += '\n';
          item.forEach((row) => {
            const rowValues = titles.reduce((results, title) => {
              results.push(row[title]);
              return results;
            }, [] as string[]);
            exportTxt += rowValues.join('\t');
            exportTxt += '\n';
          });
        } else {
          // 普通字符串
          exportTxt += item;
          exportTxt += '\n';
        }
      });

      const fileName = `${props.cluster.immute_domain}.txt`;
      downloadText(fileName, exportTxt);
    },
    isInputed(id?: number) {
      const currentClusterId = id ?? clusterId.value;
      return executedCommands[currentClusterId]?.some(Boolean) || inputStash[currentClusterId]?.length > 0;
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
