<template>
  <div
    ref="consolePanelRef"
    class="console-panel-main"
    @click="handleInputFocus">
    <template
      v-for="(item, index) in panelRecords"
      :key="index">
      <div
        v-if="item.type !== 'normal'"
        class="input-line">
        <span :class="{ 'error-text': item.type === 'error' }">{{ item.message }}</span>
      </div>
      <template v-else>
        <Component
          :is="consoleConfig.renderMessage"
          :data="item.message" />
      </template>
    </template>
    <div v-show="loading">Waiting...</div>
    <div class="input-line">
      <textarea
        ref="inputRef"
        class="input-main"
        :disabled="loading"
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
<script setup lang="ts">
  import _ from 'lodash';

  import { queryWebconsole } from '@services/source/dbbase';

  import { DBTypes } from '@common/const';

  import { downloadText } from '@utils';

  import type { ClusterItem, Props as MainProps } from '../../Index.vue';

  import RenderMysqlMessage from './components/RenderMysqlMessage.vue';
  import RenderRedisMessage, {
    getDbOwnParams as getRedisOwnParams,
    getInputPlaceholder as getRedisPlaceholder,
  } from './components/RenderRedisMessage.vue';

  interface Props {
    clusterInfo: ClusterItem;
    dbType: MainProps['dbType'];
    raw?: boolean;
  }

  interface Expose {
    clearCurrentScreen: (id: number) => void;
    export: () => void;
    isInputed: (id?: number) => boolean;
  }

  interface PanelLine {
    message: string | Record<string, string>[];
    type: 'success' | 'error' | 'normal' | 'command';
  }

  interface ConsoleParams {
    cluster_id: number;
    cmd?: string;
    [key: string]: unknown;
  }

  interface ConsoleConfig {
    // 渲染组件
    renderMessage: any;
    // cmd前缀
    getInputPlaceholder?: (clusterId: number, domain: string) => string;
    // db独有参数
    getDbOwnParmas?: (clusterId: number, cmd: string) => Record<string, unknown>;
  }

  const props = defineProps<Props>();

  const command = ref('');
  const panelRecords = ref<PanelLine[]>([]);
  const consolePanelRef = ref();
  const loading = ref(false);
  const inputRef = ref();
  const realHeight = ref('52px');

  const clusterId = computed(() => props.clusterInfo.id);
  const consoleConfig = computed(() => configMap[props.dbType as DBTypes]);

  const commandsInput: Record<number, string[]> = {};
  const noExecuteCommand: Record<number, string> = {};
  const panelsInput: Record<number, PanelLine[]> = {};
  let currentCommandIndex = 0;
  let inputPlaceholder = '';
  let recentOnceInput = '';
  let baseParams: ConsoleParams;
  const configMap: Record<string, ConsoleConfig> = {
    [DBTypes.MYSQL]: {
      renderMessage: RenderMysqlMessage,
    },
    [DBTypes.TENDBCLUSTER]: {
      renderMessage: RenderMysqlMessage,
    },
    [DBTypes.REDIS]: {
      renderMessage: RenderRedisMessage,
      getInputPlaceholder: getRedisPlaceholder,
      getDbOwnParmas: getRedisOwnParams,
    },
  };

  watch(
    () => props.raw,
    () => {
      if (typeof props.raw === 'boolean') {
        baseParams = {
          ...baseParams,
          raw: props.raw,
        };
      }
    },
    {
      immediate: true,
    },
  );

  watch(
    clusterId,
    () => {
      if (clusterId.value) {
        const domain = props.clusterInfo.immute_domain;
        inputPlaceholder = consoleConfig.value.getInputPlaceholder
          ? consoleConfig.value.getInputPlaceholder(clusterId.value, domain)
          : `${domain} > `;
        baseParams = {
          ...baseParams,
          cluster_id: clusterId.value,
        };
        command.value = noExecuteCommand[clusterId.value] ?? inputPlaceholder;

        if (!commandsInput[clusterId.value]) {
          commandsInput[clusterId.value] = [];
          currentCommandIndex = 0;
        } else {
          currentCommandIndex = commandsInput[clusterId.value].length;
        }

        if (!panelsInput[clusterId.value]) {
          panelsInput[clusterId.value] = [];
          panelRecords.value = [];
        } else {
          panelRecords.value = _.cloneDeep(panelsInput[clusterId.value]);
        }

        setTimeout(() => {
          inputRef.value.focus();
          checkCursorPosition();
        });
      }
    },
    {
      immediate: true,
    },
  );

  const handleInputFocus = () => {
    inputRef.value.focus();
  };

  // 回车输入指令
  const handleClickSendCommand = async (e: any) => {
    let cmd = e.target.value.trim() as string;
    const isInputed = cmd.length > inputPlaceholder.length;
    const commandLine = {
      message: isInputed ? cmd : inputPlaceholder,
      type: 'command' as const,
    };
    commandsInput[clusterId.value].push(cmd);
    currentCommandIndex = commandsInput[clusterId.value].length;
    panelsInput[clusterId.value].push(commandLine);
    console.log(panelsInput, 'panelsInput');

    panelRecords.value.push(commandLine);
    command.value = inputPlaceholder;
    if (!isInputed) {
      return;
    }
    loading.value = true;
    cmd = cmd.substring(inputPlaceholder.length);
    const executeResult = await queryWebconsole({
      ...baseParams,
      cmd,
    }).finally(() => {
      loading.value = false;
      setTimeout(() => {
        inputRef.value.focus();
      });
    });

    if (executeResult.error_msg) {
      // 错误消息
      const errorLine = {
        message: executeResult.error_msg,
        type: 'error' as const,
      };
      panelsInput[clusterId.value].push(errorLine);
      panelRecords.value.push(errorLine);
    } else {
      // 正常消息
      const normalLine = {
        message: executeResult.query,
        type: 'normal' as const,
      };
      panelsInput[clusterId.value].push(normalLine);
      panelRecords.value.push(normalLine);

      if (consoleConfig.value.getDbOwnParmas) {
        baseParams = Object.assign(baseParams, consoleConfig.value.getDbOwnParmas(clusterId.value, cmd));
        if (consoleConfig.value.getInputPlaceholder) {
          inputPlaceholder = consoleConfig.value.getInputPlaceholder(clusterId.value, props.clusterInfo.immute_domain);
          command.value = inputPlaceholder;
        }
      }
    }

    setTimeout(() => {
      consolePanelRef.value.scrollTop = consolePanelRef.value.scrollHeight - consolePanelRef.value.clientHeight;
    });
  };

  const initInput = () => {
    command.value = '';
    nextTick(() => {
      command.value = inputPlaceholder;
    });
  };

  // 恢复最近一次输入并矫正光标
  const resetRecentOnceInput = () => {
    recentOnceInput = command.value;
    command.value = '';
    nextTick(() => {
      command.value = recentOnceInput;
    });
    setTimeout(() => {
      const cursorIndex = inputPlaceholder.length;
      inputRef.value.setSelectionRange(cursorIndex, cursorIndex);
    });
  };

  // 输入
  const handleInputChange = (e: any) => {
    if (inputRef.value.selectionStart === inputPlaceholder.length - 1) {
      resetRecentOnceInput();
      return;
    }
    if (inputRef.value.selectionStart < inputPlaceholder.length) {
      initInput();
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
    if (command.value.length > inputPlaceholder.length) {
      noExecuteCommand[clusterId.value] = command.value;
    }
  };

  // 键盘 ↑ 键
  const handleClickUpBtn = () => {
    if (commandsInput[clusterId.value].length === 0 || currentCommandIndex === 0) {
      checkCursorPosition(true);
      return;
    }

    currentCommandIndex = currentCommandIndex - 1;
    command.value = commandsInput[clusterId.value][currentCommandIndex];
    const cursorIndex = command.value.length;
    inputRef.value.setSelectionRange(cursorIndex, cursorIndex);
  };

  // 键盘 ↓ 键
  const handleClickDownBtn = () => {
    if (commandsInput[clusterId.value].length === 0 || currentCommandIndex === commandsInput[clusterId.value].length) {
      return;
    }

    currentCommandIndex = currentCommandIndex + 1;
    command.value = commandsInput[clusterId.value][currentCommandIndex] ?? inputPlaceholder;
  };

  // 键盘 ← 键
  const handleClickLeftBtn = () => {
    checkCursorPosition();
  };

  // 校正光标位置
  const checkCursorPosition = (isStartToTextEnd = false) => {
    if (inputRef.value.selectionStart <= inputPlaceholder.length) {
      const cursorIndex = isStartToTextEnd ? command.value.length : inputPlaceholder.length;
      inputRef.value.setSelectionRange(cursorIndex, cursorIndex);
    }
  };

  defineExpose<Expose>({
    clearCurrentScreen(id?: number) {
      const currentClusterId = id ?? clusterId.value;
      commandsInput[currentClusterId] = [];
      noExecuteCommand[currentClusterId] = '';
      panelsInput[currentClusterId] = [];
      panelRecords.value = [];
      command.value = inputPlaceholder;
    },
    export() {
      const lines = panelsInput[clusterId.value].map((item) => item.message);
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

      const fileName = `${props.clusterInfo.immute_domain}.txt`;
      downloadText(fileName, exportTxt);
    },
    isInputed(id?: number) {
      const currentClusterId = id ?? clusterId.value;
      return (
        commandsInput[currentClusterId]?.some((cmd) => cmd.length > inputPlaceholder.length) ||
        noExecuteCommand[currentClusterId]?.substring(inputPlaceholder.length).length > 0
      );
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
