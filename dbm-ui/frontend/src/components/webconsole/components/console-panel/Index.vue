<template>
  <div
    ref="consolePanelRef"
    class="console-panel-main"
    :style="{
      fontSize: fontConfig.fontSize,
      lineHeight: fontConfig.lineHeight,
    }">
    <template
      v-for="(item, index) in panelRecords"
      :key="index">
      <div
        v-if="item.type !== 'normal'"
        class="input-line">
        <span v-if="item.type === 'command'"> </span>
        <span :class="{ 'error-text': item.type === 'error' }">{{ item.message }}</span>
      </div>
      <template v-else>
        <RenderMysqlMessage
          v-if="clusterType === 'mysql'"
          :data="item.message as Record<string, string>[]" />
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

  import { downloadText } from '@utils';

  import type { ClusterItem, Props as MainProps } from '../../Index.vue';

  import RenderMysqlMessage from './RenderMysqlMessage.vue';

  interface Props {
    clusterInfo: ClusterItem;
    fontConfig: {
      fontSize: string;
      lineHeight: string;
    };
    clusterType: MainProps['clusterType'];
  }

  interface Expose {
    clearCurrentScreen: (id?: number) => void;
    export: () => void;
  }

  interface PanelLine {
    message: string | Record<string, string>[];
    type: 'success' | 'error' | 'normal' | 'command';
  }

  const props = defineProps<Props>();

  const command = ref('');
  const panelRecords = ref<PanelLine[]>([]);
  const consolePanelRef = ref();
  const loading = ref(false);
  const inputRef = ref();
  const realHeight = ref('52px');

  const clusterId = computed(() => props.clusterInfo.id);

  const commandsInput: Record<number, string[]> = {};
  const panelsInput: Record<number, PanelLine[]> = {};
  let currentCommandIndex = 0;
  let inputPlaceholder = '';

  watch(
    clusterId,
    () => {
      if (clusterId.value) {
        inputPlaceholder = `${props.clusterInfo.immute_domain} > `;
        command.value = inputPlaceholder;

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
        });
      }
    },
    {
      immediate: true,
    },
  );

  // 回车输入指令
  const handleClickSendCommand = async (e: any) => {
    const cmd = e.target.value.trim() as string;
    if (cmd.length <= inputPlaceholder.length + 1) {
      command.value = inputPlaceholder;
      return;
    }

    loading.value = true;
    commandsInput[clusterId.value].push(cmd);
    currentCommandIndex = commandsInput[clusterId.value].length;
    const commandLine = {
      message: cmd,
      type: 'command' as const,
    };
    panelsInput[clusterId.value].push(commandLine);
    panelRecords.value.push(commandLine);
    command.value = inputPlaceholder;
    const executeResult = await queryWebconsole({
      cluster_id: props.clusterInfo.id,
      cmd: cmd.substring(inputPlaceholder.length),
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
  }

  // 输入
  const handleInputChange = (e: any) => {
    if (inputRef.value.selectionStart <= inputPlaceholder.length) {
      initInput();
      return
    }
    const { value } = e.target;
    if (value.length <= inputPlaceholder.length) {
      initInput();
      return;
    }

    command.value = value;

    setTimeout(() => {
      const { scrollHeight } = inputRef.value;
      realHeight.value = `${scrollHeight}px`;
    });
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
      if (id) {
        panelsInput[id] = [];
      } else {
        panelsInput[clusterId.value] = [];
      }
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
  });
</script>
<style lang="less">
  .console-panel-main {
    width: 100%;
    height: 100%;
    overflow-y: auto;
    font-size: 12px;
    padding: 14px 24px;
    color: #dcdee5;

    .input-line {
      display: flex;
      font-weight: 400;
      color: #94f5a4;
      line-height: 24px;
      word-break: break-all;

      .input-main {
        border: none;
        outline: none;
        background: #1a1a1a;
        flex: 1;
        resize: none;
        height: auto;
        overflow-y: hidden;
      }

      .error-text {
        color: #ff5656;
      }
    }
  }
</style>
