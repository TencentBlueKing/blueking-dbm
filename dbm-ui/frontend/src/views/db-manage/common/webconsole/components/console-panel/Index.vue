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
          <Component
            :is="consoleConfig.renderMessage"
            :data="item.message" />
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
<script setup lang="ts">
  import _ from 'lodash';

  import { queryAllTypeCluster, queryWebconsole } from '@services/source/dbbase';

  import { DBTypes } from '@common/const';

  import { downloadText } from '@utils';

  import RenderMysqlMessage from './components/RenderMysqlMessage.vue';
  import RenderRedisMessage, {
    getInputPlaceholder as getRedisPlaceholder,
    switchDbIndex,
  } from './components/RenderRedisMessage.vue';

  type ClusterItem = ServiceReturnType<typeof queryAllTypeCluster>[number];

  interface Props {
    modelValue: ClusterItem;
    dbType: DBTypes;
    raw?: boolean;
  }

  interface Expose {
    clearCurrentScreen: (id?: number) => void;
    export: () => void;
    isInputed: (id?: number) => boolean;
  }

  const props = defineProps<Props>();

  const command = ref('');
  const consolePanelRef = ref();
  const loading = ref(false);
  const isFrozenTextarea = ref(false);
  const inputRef = ref();
  const realHeight = ref('52px');
  const panelInputMap = reactive<
    Record<
      number,
      Array<{
        message: string | Record<string, string>[];
        type: 'success' | 'error' | 'normal' | 'command';
      }>
    >
  >({});

  const commandInputMap: Record<number, string[]> = {};
  const noExecuteCommand: Record<number, string> = {};
  let currentCommandIndex = 0;
  let inputPlaceholder = '';
  let baseParams: {
    cluster_id: number;
    cmd?: string;
    [key: string]: unknown;
  };
  const configMap: Record<
    string,
    {
      renderMessage: any;
      getInputPlaceholder?: (clusterId: number, domain: string) => string;
      switchDbIndex?: (params: { clusterId: number; cmd: string; queryResult: string; commandInputs: string[] }) => {
        dbIndex: number;
        commandInputs: string[];
      };
    }
  > = {
    [DBTypes.MYSQL]: {
      renderMessage: RenderMysqlMessage,
    },
    [DBTypes.TENDBCLUSTER]: {
      renderMessage: RenderMysqlMessage,
    },
    [DBTypes.REDIS]: {
      renderMessage: RenderRedisMessage,
      getInputPlaceholder: getRedisPlaceholder,
      switchDbIndex,
    },
  };

  const clusterId = computed(() => props.modelValue.id);
  const consoleConfig = computed(() => configMap[props.dbType as keyof typeof configMap]);

  watch(
    clusterId,
    () => {
      if (clusterId.value) {
        const domain = props.modelValue.immute_domain;
        inputPlaceholder = consoleConfig.value.getInputPlaceholder
          ? consoleConfig.value.getInputPlaceholder(clusterId.value, domain)
          : `${domain} > `;
        baseParams = {
          ...baseParams,
          cluster_id: clusterId.value,
        };
        command.value = noExecuteCommand[clusterId.value] ?? inputPlaceholder;

        if (!commandInputMap[clusterId.value]) {
          commandInputMap[clusterId.value] = [];
          currentCommandIndex = 0;
        } else {
          currentCommandIndex = commandInputMap[clusterId.value].length;
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
    let cmd = e.target.value.trim() as string;
    const isInputed = cmd.length > inputPlaceholder.length;
    const commandLine = {
      message: isInputed ? cmd : inputPlaceholder,
      type: 'command' as const,
    };
    commandInputMap[clusterId.value].push(cmd);
    currentCommandIndex = commandInputMap[clusterId.value].length;
    panelInputMap[clusterId.value].push(commandLine);
    command.value = inputPlaceholder;
    if (!isInputed) {
      return;
    }
    loading.value = true;
    cmd = cmd.substring(inputPlaceholder.length);
    if (typeof props.raw === 'boolean') {
      baseParams = {
        ...baseParams,
        raw: props.raw,
      };
    }
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
      panelInputMap[clusterId.value].push(errorLine);
    } else {
      // 正常消息
      const normalLine = {
        message: executeResult.query,
        type: 'normal' as const,
      };
      panelInputMap[clusterId.value].push(normalLine);

      const config = consoleConfig.value;
      if (config.switchDbIndex) {
        const { dbIndex, commandInputs } = config.switchDbIndex({
          clusterId: clusterId.value,
          cmd,
          queryResult: executeResult.query as string,
          commandInputs: commandInputMap[clusterId.value],
        });
        baseParams = {
          ...baseParams,
          db_num: dbIndex,
        };
        commandInputMap[clusterId.value] = commandInputs;
        if (config.getInputPlaceholder) {
          command.value = config.getInputPlaceholder(clusterId.value, props.modelValue.immute_domain);
        }
      }
    }

    setTimeout(() => {
      consolePanelRef.value.scrollTop = consolePanelRef.value.scrollHeight - consolePanelRef.value.clientHeight;
    });
  };

  // 恢复最近一次输入并矫正光标
  const restoreInput = (isRestore = true) => {
    const recentOnceInput = command.value;
    command.value = '';
    nextTick(() => {
      command.value = isRestore ? recentOnceInput : inputPlaceholder;
    });
    setTimeout(() => {
      const cursorIndex = inputPlaceholder.length;
      inputRef.value.setSelectionRange(cursorIndex, cursorIndex);
    });
  };

  // 输入
  const handleInputChange = (e: any) => {
    if (inputRef.value.selectionStart === inputPlaceholder.length - 1) {
      restoreInput();
      return;
    }
    if (inputRef.value.selectionStart < inputPlaceholder.length) {
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
    if (command.value.length > inputPlaceholder.length) {
      noExecuteCommand[clusterId.value] = command.value;
    }
  };

  // 键盘 ↑ 键
  const handleClickUpBtn = () => {
    if (commandInputMap[clusterId.value].length === 0 || currentCommandIndex === 0) {
      checkCursorPosition(true);
      return;
    }

    currentCommandIndex = currentCommandIndex - 1;
    command.value = commandInputMap[clusterId.value][currentCommandIndex];
    const cursorIndex = command.value.length;
    inputRef.value.setSelectionRange(cursorIndex, cursorIndex);
  };

  // 键盘 ↓ 键
  const handleClickDownBtn = () => {
    if (
      commandInputMap[clusterId.value].length === 0 ||
      currentCommandIndex === commandInputMap[clusterId.value].length
    ) {
      return;
    }

    currentCommandIndex = currentCommandIndex + 1;
    command.value = commandInputMap[clusterId.value][currentCommandIndex] ?? inputPlaceholder;
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
      panelInputMap[currentClusterId] = [];
      commandInputMap[currentClusterId] = [];
      noExecuteCommand[currentClusterId] = '';
      command.value = inputPlaceholder;
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

      const fileName = `${props.modelValue.immute_domain}.txt`;
      downloadText(fileName, exportTxt);
    },
    isInputed(id?: number) {
      const currentClusterId = id ?? clusterId.value;
      return (
        commandInputMap[currentClusterId]?.some((cmd) => cmd.length > inputPlaceholder.length) ||
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
