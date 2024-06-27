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
        <span v-if="item.type === 'command'"> {{ clusterInfo.immute_domain }} > </span>
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
      <span> {{ clusterInfo.immute_domain }} > </span>
      <input
        ref="inputRef"
        v-model="command"
        class="input-main ml-5"
        :disabled="loading"
        @keyup.down="handleClickDownBtn"
        @keyup.enter="handleClickSendCommand"
        @keyup.up="handleClickUpBtn" />
    </div>
  </div>
</template>
<script setup lang="ts">
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

  const clusterId = computed(() => props.clusterInfo.id);

  const commandsInput: Record<number, string[]> = {};
  const panelsInput: Record<number, PanelLine[]> = {};
  let currentCommandIndex = 0;

  watch(
    clusterId,
    () => {
      if (clusterId.value) {
        command.value = '';

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
          panelRecords.value = panelsInput[clusterId.value];
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

  const handleClickSendCommand = async (e: any) => {
    loading.value = true;
    const cmd = e.target.value as string;
    commandsInput[clusterId.value].push(cmd);
    currentCommandIndex = commandsInput[clusterId.value].length;
    const commandLine = {
      message: cmd,
      type: 'command' as const,
    };
    panelsInput[clusterId.value].push(commandLine);
    panelRecords.value.push(commandLine);
    command.value = '';

    const executeResult = await queryWebconsole({
      cluster_id: props.clusterInfo.id,
      cmd,
    }).finally(() => {
      loading.value = false;
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

  // 键盘 ↑ 键
  const handleClickUpBtn = () => {
    if (commandsInput[clusterId.value].length === 0 || currentCommandIndex === 0) {
      return;
    }

    currentCommandIndex = currentCommandIndex - 1;
    command.value = commandsInput[clusterId.value][currentCommandIndex];
  };

  // 键盘 ↓ 键
  const handleClickDownBtn = () => {
    if (commandsInput[clusterId.value].length === 0 || currentCommandIndex === commandsInput[clusterId.value].length) {
      return;
    }

    currentCommandIndex = currentCommandIndex + 1;
    command.value = commandsInput[clusterId.value][currentCommandIndex];
  };

  defineExpose<Expose>({
    clearCurrentScreen(id?: number) {
      if (id) {
        panelsInput[id] = [];
      } else {
        panelsInput[clusterId.value] = [];
      }
      panelRecords.value = [];
      command.value = '';
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
    padding: 14px 24px;
    overflow-y: auto;
    font-size: 12px;
    color: #dcdee5;

    .input-line {
      display: flex;
      font-weight: 400;
      line-height: 24px;
      color: #94f5a4;

      .input-main {
        background: #1a1a1a;
        border: none;
        outline: none;
        flex: 1;
      }

      .error-text {
        color: #ff5656;
      }
    }
  }
</style>
