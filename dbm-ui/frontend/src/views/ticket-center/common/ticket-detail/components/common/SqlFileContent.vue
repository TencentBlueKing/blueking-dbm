<!--
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 *
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 *
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License athttps://opensource.org/licenses/MIT
 *
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed
 * on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for
 * the specific language governing permissions and limitations under the License.
-->

<template>
  <div
    ref="rootRef"
    class="ticket-import-sql-file-render">
    <div class="editor-layout-header">
      <span>{{ getSQLFilename(title) }}</span>
      <div class="editro-action-box">
        <DbIcon
          type="arrow-down"
          @click="handleDownload" />
        <DbIcon
          v-if="isFullscreen"
          type="un-full-screen"
          @click="handleExitFullScreen" />
        <DbIcon
          v-else
          type="full-screen"
          @click="handleFullScreen" />
      </div>
    </div>
    <BkResizeLayout
      :border="false"
      class="resize-wrapper"
      :class="{
        'resize-disabled': isMessageListFolded,
      }"
      :disabled="isMessageListFolded"
      :initial-divide="resizeLayoutInitialDivide"
      :max="300"
      :min="0"
      placement="bottom">
      <template #main>
        <div
          ref="editorRef"
          style="height: 100%" />
      </template>
      <template #aside>
        <RenderMessageList
          v-model="isMessageListFolded"
          class="editor-error"
          :data="messageList" />
      </template>
    </BkResizeLayout>
  </div>
</template>
<script setup lang="ts">
  import * as monaco from 'monaco-editor';
  import screenfull from 'screenfull';
  import { onBeforeUnmount, onMounted, ref, watch } from 'vue';

  import type { Mysql } from '@services/model/ticket/ticket';
  import { grammarCheck as mysqlGrammarCheck } from '@services/source/mysqlSqlImport';
  import { grammarCheck as oracleGrammarCheck } from '@services/source/oracleSqlImport';
  import { grammarCheck as sqlserverGrammarCheck } from '@services/source/sqlserverSqlImport';

  import { DBTypes } from '@common/const';

  import { getSQLFilename } from '@utils';

  import RenderMessageList, { type IMessageList } from './MessageList.vue';

  interface Props {
    dbTypes: keyof typeof grammarCheckMap;
    // eslint-disable-next-line vue/require-default-prop
    executeObject?: Mysql.ImportSqlFile['execute_objects'][number];
    modelValue: string;
    readonly?: boolean;
    title: string;
    // eslint-disable-next-line vue/require-default-prop
    versionList?: string[];
  }

  interface Emits {
    (e: 'update:modelValue', value: string): void;
    (e: 'change', value: string): void;
  }

  const props = withDefaults(defineProps<Props>(), {
    messageList: () => [],
    readonly: false,
    syntaxChecking: false,
  });

  const emits = defineEmits<Emits>();

  const grammarCheckMap = {
    [DBTypes.MONGODB]: undefined,
    [DBTypes.MYSQL]: mysqlGrammarCheck,
    [DBTypes.ORACLE]: oracleGrammarCheck,
    [DBTypes.SQLSERVER]: sqlserverGrammarCheck,
    [DBTypes.TENDBCLUSTER]: mysqlGrammarCheck,
  };

  const handleGrammarCheck = () => {
    const grammarCheckApi = grammarCheckMap[props.dbTypes];
    if (!grammarCheckApi) {
      return;
    }
    isChecking.value = true;
    const params = new FormData();
    params.append('sql_filenames[0]', props.title);
    params.append('cluster_type', props.dbTypes);
    if (props.versionList) {
      props.versionList.forEach((version, index) => {
        params.append(`versions[${index}]`, version);
      });
    }
    if (props.executeObject) {
      params.append(
        'execute_objects',
        JSON.stringify([
          {
            dbnames: props.executeObject.dbnames,
            ignore_dbnames: props.executeObject.ignore_dbnames,
            line_id: 1,
            sql_files: ['/'],
          },
        ]),
      );
    }
    grammarCheckApi(params)
      .then((data) => {
        const grammarCheckData = data;
        if (!grammarCheckData) {
          return;
        }

        const [checkResult] = Object.values(grammarCheckData);
        messageList.value = checkResult.messageList;
        if (checkResult.messageList.length > 0) {
          isMessageListFolded.value = false;
        }
      })
      .finally(() => {
        isChecking.value = false;
      });
  };

  const rootRef = ref();
  const editorRef = ref();
  const isFullscreen = ref(false);
  const isMessageListFolded = ref(true);
  const isChecking = ref(true);
  const resizeLayoutInitialDivide = ref(0);
  const messageList = ref<IMessageList>([]);

  let editor: monaco.editor.IStandaloneCodeEditor;

  watch(
    () => props.modelValue,
    () => {
      if (!props.modelValue) {
        return;
      }

      handleGrammarCheck();
      setTimeout(() => {
        if (props.modelValue !== editor.getValue()) {
          editor.setValue(props.modelValue);
          isMessageListFolded.value = true;
        }
      });
    },
    {
      immediate: true,
    },
  );

  watch(
    isMessageListFolded,
    () => {
      if (isMessageListFolded.value && messageList.value.length === 0) {
        resizeLayoutInitialDivide.value = 0;
        return;
      }
      resizeLayoutInitialDivide.value = Math.min(24 + messageList.value.length * 24, 200);
    },
    {
      immediate: true,
    },
  );

  const handleToggleScreenfull = () => {
    if (screenfull.isFullscreen) {
      isFullscreen.value = true;
    } else {
      isFullscreen.value = false;
    }
    editor.layout();
  };

  const handleReize = () => {
    editor.layout();
  };

  const handleDownload = () => {
    const link = document.createElement('a');
    link.download = `${props.title.replace(/\s/g, '')}.sql`;
    link.style.display = 'none';
    // 字符内容转变成blob地址
    const blob = new Blob([props.modelValue], { type: 'sql' });
    link.href = URL.createObjectURL(blob);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const handleFullScreen = () => {
    screenfull.toggle(rootRef.value);
  };

  const handleExitFullScreen = () => {
    screenfull.toggle(rootRef.value);
  };

  onMounted(() => {
    editor = monaco.editor.create(editorRef.value, {
      automaticLayout: true,
      language: 'sql',
      minimap: {
        enabled: false,
      },
      readOnly: props.readonly,
      scrollbar: {
        alwaysConsumeMouseWheel: false,
      },
      theme: 'vs-dark',
      wordWrap: 'bounded',
    });
    editor.onDidChangeModelContent(() => {
      const value = editor.getValue();
      emits('update:modelValue', value);
      emits('change', value);
    });
    screenfull.on('change', handleToggleScreenfull);
    window.addEventListener('resize', handleReize);
  });

  onBeforeUnmount(() => {
    editor.dispose();
    screenfull.off('change', handleToggleScreenfull);
    window.removeEventListener('resize', handleReize);
  });
</script>
<style lang="less">
  .ticket-import-sql-file-render {
    position: relative;
    z-index: 0;
    height: calc(100vh - 80px);

    .editor-layout-header {
      display: flex;
      align-items: center;
      height: 40px;
      padding-right: 16px;
      padding-left: 25px;
      font-size: 14px;
      color: #c4c6cc;
      background: #2e2e2e;

      .editro-action-box {
        margin-left: auto;
        color: #979ba5;

        & > * {
          margin-left: 12px;
          cursor: pointer;
        }
      }
    }

    .resize-wrapper {
      height: calc(100% - 40px);
      background: #212121;

      &.resize-disabled {
        :deep(.bk-resize-layout-aside) {
          &::after {
            display: none;
          }
        }
      }
    }

    .editor-error {
      position: absolute;
      inset: 0;
    }

    .syntax-checking {
      position: absolute;
      right: 0;
      bottom: 0;
      left: 0;
    }
  }
</style>
