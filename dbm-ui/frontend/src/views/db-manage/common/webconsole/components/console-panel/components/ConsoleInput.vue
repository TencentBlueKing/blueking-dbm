<template>
  <div
    ref="consolePanelRef"
    class="console-panel-main"
    @click="handleInputFocus">
    <div @mousedown="handleFreezeTextarea">
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
    <div class="input-line">
      <textarea
        ref="inputRef"
        class="input-main"
        :disabled="loading || isFrozenTextarea"
        :style="{ height: realHeight }"
        :value="command"
        @blur="handleInputBlur"
        @input="handleInputChange"
        @keyup.down="handleClickDownBtn"
        @keyup.enter.stop="handleClickSendCommand"
        @keyup.left="handleClickLeftBtn"
        @keyup.up="handleClickUpBtn" />
    </div>
  </div>
</template>
<script lang="ts">
  // 未执行的命令
  const noExecuteCommand: Record<number, string> = {};
  // 已执行过的命令
  const executedCommands: Record<number, string[]> = {};

  const panelInputMap = reactive<
    Record<
      number,
      Array<{
        message: string | Record<string, string>[];
        type: 'success' | 'error' | 'normal' | 'command' | string;
      }>
    >
  >({});
</script>
<script setup lang="ts">
  import _ from 'lodash';

  import { queryAllTypeCluster, queryWebconsole } from '@services/source/dbbase';

  import { downloadText } from '@utils';

  export interface Props {
    cluster: ServiceReturnType<typeof queryAllTypeCluster>[number];
    placeholder?: string;
    extParams?: Record<string, unknown>;
    preCheck?: (value: string) => string;
  }

  interface Emits {
    (e: 'success', cmd: string, message: ServiceReturnType<typeof queryWebconsole>['query'], ...args: unknown[]): void;
  }

  interface Expose {
    updateCommand: () => void;
    export: () => void;
    isInputed: (id?: number) => boolean;
    clearCurrentScreen: (id?: number) => void;
  }

  const props = withDefaults(defineProps<Props>(), {
    placeholder: '',
    extParams: () => ({}),
    preCheck: () => '',
  });

  const emits = defineEmits<Emits>();

  const command = ref('');
  const consolePanelRef = ref();
  const loading = ref(false);
  const isFrozenTextarea = ref(false);
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
        command.value = localPlaceholder.value + (noExecuteCommand[clusterId.value] ?? '');

        if (!executedCommands[clusterId.value]) {
          executedCommands[clusterId.value] = [];
          commandIndex = 0;
        } else {
          commandIndex = executedCommands[clusterId.value].length;
        }

        if (!panelInputMap[clusterId.value]) {
          panelInputMap[clusterId.value] = [];
        } else {
          panelInputMap[clusterId.value] = _.cloneDeep(panelInputMap[clusterId.value]);
        }

        setTimeout(() => {
          handleInputFocus();
        });
      }
    },
    {
      immediate: true,
    },
  );

  const handleInputFocus = () => {
    isFrozenTextarea.value = false;
    inputRef.value.focus();
    checkCursorPosition();
  };

  const handleFreezeTextarea = () => {
    isFrozenTextarea.value = true;
  };

  // 回车输入指令
  const handleClickSendCommand = async (e: any) => {
    // 输入预处理
    const inputValue = e.target.value.trim() as string;
    const isInputed = inputValue.length > localPlaceholder.value.length;

    // 截取输入的命令
    const cmd = inputValue.substring(localPlaceholder.value.length);
    executedCommands[clusterId.value].push(cmd);
    commandIndex = executedCommands[clusterId.value].length;
    command.value = localPlaceholder.value;

    // 命令行渲染
    const commandLine = {
      message: isInputed ? inputValue : localPlaceholder.value,
      type: 'command',
    };
    panelInputMap[clusterId.value].push(commandLine);

    if (!isInputed) {
      return;
    }

    // 语句预检
    const preCheckResult = props.preCheck(cmd);
    if (preCheckResult) {
      const errorLine = {
        message: preCheckResult,
        type: 'error',
      };
      panelInputMap[clusterId.value].push(errorLine);
      return;
    }

    // 开始请求
    try {
      loading.value = true;
      const executeResult = await queryWebconsole({
        ...props.extParams,
        cluster_id: clusterId.value,
        cmd,
      });

      // 请求结果渲染
      if (executeResult.error_msg) {
        // 错误消息
        const errorLine = {
          message: executeResult.error_msg,
          type: 'error',
        };
        panelInputMap[clusterId.value].push(errorLine);
      } else {
        // 正常消息
        const normalLine = {
          message: executeResult.query,
          type: 'normal',
        };
        panelInputMap[clusterId.value].push(normalLine);

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

  // 当前tab有未执行的command暂存，切换回来回显
  const handleInputBlur = () => {
    if (command.value.length > localPlaceholder.value.length) {
      noExecuteCommand[clusterId.value] = command.value.substring(localPlaceholder.value.length);
    }
  };

  // 键盘 ↑ 键
  const handleClickUpBtn = () => {
    if (executedCommands[clusterId.value].length === 0 || commandIndex === 0) {
      checkCursorPosition(true);
      return;
    }

    commandIndex = commandIndex - 1;
    command.value = localPlaceholder.value + executedCommands[clusterId.value][commandIndex];
    const cursorIndex = command.value.length;
    inputRef.value.setSelectionRange(cursorIndex, cursorIndex);
  };

  // 键盘 ↓ 键
  const handleClickDownBtn = () => {
    if (executedCommands[clusterId.value].length === 0 || commandIndex === executedCommands[clusterId.value].length) {
      return;
    }

    commandIndex = commandIndex + 1;
    command.value = localPlaceholder.value + (executedCommands[clusterId.value][commandIndex] ?? '');
  };

  // 键盘 ← 键
  const handleClickLeftBtn = () => {
    checkCursorPosition();
  };

  // 校正光标位置
  const checkCursorPosition = (isStartToTextEnd = false) => {
    if (inputRef.value.selectionStart <= localPlaceholder.value.length) {
      const cursorIndex = isStartToTextEnd ? command.value.length : localPlaceholder.value.length;
      inputRef.value.setSelectionRange(cursorIndex, cursorIndex);
    }
  };

  defineExpose<Expose>({
    updateCommand() {
      nextTick(() => {
        command.value = localPlaceholder.value;
      });
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
      return executedCommands[currentClusterId]?.some(Boolean) || noExecuteCommand[currentClusterId]?.length > 0;
    },
    clearCurrentScreen(id?: number) {
      const currentClusterId = id ?? clusterId.value;
      panelInputMap[currentClusterId] = [];
      executedCommands[currentClusterId] = [];
      noExecuteCommand[currentClusterId] = '';
      command.value = localPlaceholder.value;
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
