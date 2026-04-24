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
  <DbSideslider
    v-model:is-show="isShow"
    class="partition-fail-log-sideslider"
    quick-close
    render-directive="show"
    :show-footer="false"
    :title="t(`查看失败日志`)"
    :width="1000">
    <template #header>
      <span>{{ t('查看失败日志') }}</span>
      <span class="sub-title">
        <span class="sub-title-item">
          <span class="sub-title-label">ID：</span>
          <span class="sub-title-value">{{ data?.id }}</span>
        </span>
        <span class="sub-title-item">
          <span class="sub-title-label">{{ t('执行时间') }}：</span>
          <span class="sub-title-value">{{ data?.execute_time || '--' }}</span>
        </span>
      </span>
    </template>
    <div
      ref="rootRef"
      class="fail-log-content"
      :class="{ 'is-full-screen': isFullscreen }">
      <div class="fail-log-actions">
        <CopyLog :content="localValue" />
        <FullScreen @change="handleChangeFullScreen" />
      </div>
      <div
        ref="editorRef"
        class="fail-log-editor" />
    </div>
  </DbSideslider>
</template>
<script setup lang="ts">
  import * as monaco from 'monaco-editor';
  import screenfull from 'screenfull';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import type PartitionModel from '@services/model/partition/partition';
  import { queryLog } from '@services/source/partitionManage';

  import CopyLog from './components/CopyLog.vue';
  import FullScreen from './components/FullScreen.vue';

  interface Props {
    data?: PartitionModel;
  }

  const props = defineProps<Props>();

  const isShow = defineModel<boolean>('isShow', {
    default: false,
  });

  let editor: monaco.editor.IStandaloneCodeEditor;

  const { t } = useI18n();

  const rootRef = ref();
  const editorRef = ref();
  const isFullscreen = ref(false);
  const localValue = ref('');

  const { run: queryLogData } = useRequest(queryLog, {
    manual: true,
    onSuccess: (result) => {
      editor?.setValue(result.exec_log);
      localValue.value = result.exec_log;
    },
  });

  const initEditor = () => {
    nextTick(() => {
      if (editorRef.value && !editor) {
        editor = monaco.editor.create(editorRef.value, {
          automaticLayout: true,
          fontSize: 16,
          language: 'py',
          lineNumbersMinChars: 3,
          minimap: {
            enabled: false,
          },
          padding: {
            top: 40,
          },
          readOnly: true,
          renderLineHighlight: 'none',
          scrollbar: {
            alwaysConsumeMouseWheel: false,
          },
          theme: 'vs-dark',
          wordWrap: 'on',
        });
        editor.onDidChangeModelContent(() => {
          const value = editor.getValue();
          if (value !== localValue.value) {
            localValue.value = value;
          }
        });
      }
    });
  };

  // 侧滑面板打开时请求日志数据
  watch(isShow, (newVal) => {
    if (newVal && props.data?.id) {
      initEditor();
      queryLogData({ config_id: props.data.id });
    }
  });

  const handleToggleScreenfull = () => {
    if (screenfull.isFullscreen) {
      isFullscreen.value = true;
    } else {
      isFullscreen.value = false;
    }
    editor?.layout();
  };

  const handleChangeFullScreen = () => {
    screenfull.toggle(rootRef.value);
  };

  onMounted(() => {
    screenfull.on('change', handleToggleScreenfull);
  });

  onBeforeUnmount(() => {
    editor?.dispose();
    screenfull.off('change', handleToggleScreenfull);
  });
</script>
<style lang="less" scoped>
  .partition-fail-log-sideslider {
    .sub-title {
      display: inline-flex;
      align-items: center;
      height: 22px;
      margin-left: 8px;
      padding-left: 8px;
      border-left: 1px solid #dcdee5;
      color: #979ba5;
      font-family: 'Microsoft YaHei';
      font-size: 14px;
      font-style: normal;
      font-weight: 400;
      line-height: 22px;
    }

    .sub-title-item {
      & + .sub-title-item {
        margin-left: 16px;
      }
    }

    .sub-title-label {
      margin-right: 4px;
    }

    .fail-log-content {
      position: relative;
      display: flex;
      height: calc(100vh - 60px);
      padding: 20px 24px;
      flex-direction: column;

      &.is-full-screen {
        height: 100vh;
        padding: 0;
      }
    }

    .fail-log-actions {
      position: absolute;
      top: 28px;
      right: 40px;
      z-index: 10;
      display: flex;
      align-items: center;
      gap: 4px;
      color: #979ba5;

      & > * {
        cursor: pointer;
      }
    }

    .fail-log-editor {
      flex: 1;
      overflow: hidden;
      background: #242424;
      border-radius: 2px;
    }
  }
</style>
