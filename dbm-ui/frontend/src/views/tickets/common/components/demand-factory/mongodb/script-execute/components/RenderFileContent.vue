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
    <div
      ref="editorRef"
      style="height: calc(100% - 40px)" />
  </div>
</template>
<script setup lang="ts">
  import * as monaco from 'monaco-editor';
  import screenfull from 'screenfull';
  import { onBeforeUnmount, onMounted, ref, watch } from 'vue';

  import { getSQLFilename } from '@utils';

  interface Props {
    modelValue: string;
    title: string;
    readonly?: boolean;
  }

  interface Emits {
    (e: 'update:modelValue', value: string): void;
    (e: 'change', value: string): void;
  }

  const props = withDefaults(defineProps<Props>(), {
    readonly: false,
    messageList: () => [],
    syntaxChecking: false,
  });
  const emits = defineEmits<Emits>();

  const rootRef = ref();
  const editorRef = ref();
  const isFullscreen = ref(false);

  let editor: monaco.editor.IStandaloneCodeEditor;

  watch(
    () => props.modelValue,
    () => {
      setTimeout(() => {
        if (props.modelValue !== editor.getValue()) {
          editor.setValue(props.modelValue);
        }
      });
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
      language: 'sql',
      theme: 'vs-dark',
      readOnly: props.readonly,
      minimap: {
        enabled: false,
      },
      wordWrap: 'bounded',
      scrollbar: {
        alwaysConsumeMouseWheel: false,
      },
      automaticLayout: true,
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
    flex: 1;
    height: 100%;

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
  }
</style>
