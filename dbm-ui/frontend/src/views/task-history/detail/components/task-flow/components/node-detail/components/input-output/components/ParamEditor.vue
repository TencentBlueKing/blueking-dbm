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
    ref="edtorMainRef"
    class="params-editor-main">
    <div class="editor-header">
      <div class="title">{{ title }}</div>
      <div class="operations">
        <DbIcon
          class="icon"
          type="copy"
          @click="handleClickCopy" />
        <DbIcon
          class="icon"
          :type="isFullscreen ? 'un-full-screen' : 'full-screen'"
          @click="handleToggle" />
      </div>
    </div>
    <div
      ref="editorRef"
      class="editor-main"
      :class="{ 'editor-main-fullscreen': isFullscreen }" />
  </div>
</template>
<script setup lang="ts">
  import * as monaco from 'monaco-editor';

  import { execCopy } from '@utils';

  import { useFullscreen } from '@vueuse/core';

  interface Props {
    data?: string;
    title?: string;
  }

  const props = withDefaults(defineProps<Props>(), {
    data: '',
    title: '',
  });

  const edtorMainRef = ref();
  const editorRef = ref();

  const { isFullscreen, toggle } = useFullscreen(edtorMainRef);

  let editor: monaco.editor.IStandaloneCodeEditor;

  // 初始内容在 onMounted 里随编辑器一起给，这里只处理挂载之后的数据变化
  watch(
    () => props.data,
    () => {
      editor?.setValue(props.data);
    },
  );

  const handleClickCopy = () => {
    execCopy(props.data);
  };

  const handleToggle = async () => {
    await toggle();
    editor?.layout();
  };

  onMounted(() => {
    editor = monaco.editor.create(editorRef.value, {
      automaticLayout: true,
      fontSize: 13,
      language: 'json',
      lineNumbersMinChars: 3,
      minimap: {
        enabled: false,
      },
      readOnly: true,
      renderLineHighlight: 'none',
      scrollbar: {
        alwaysConsumeMouseWheel: false,
      },
      theme: 'vs-dark',
      value: props.data,
      wordWrap: 'on',
    });
  });

  onBeforeUnmount(() => {
    editor?.dispose();
  });
</script>
<style lang="less">
  .params-editor-main {
    .editor-header {
      display: flex;
      align-items: center;
      height: 40px;
      background: #242424;
      border-radius: 2px 2px 0 0;

      .title {
        margin-left: 25px;
        font-size: 14px;
        color: #c4c6cc;
      }

      .operations {
        display: flex;
        margin-left: auto;

        .icon {
          margin-right: 18px;
          font-size: 12px;
          color: #979ba5;
          cursor: pointer;
        }
      }
    }

    .editor-main {
      width: 100%;
      height: 100%;
      height: 320px;
      max-height: 600px;

      &.editor-main-fullscreen {
        height: calc(100vh - 40px);
        max-height: calc(100vh - 40px);
      }
    }
  }
</style>
