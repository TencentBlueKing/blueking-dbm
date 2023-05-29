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
    ref="editorRef"
    class="settings-editor"
    style="height: 500px; margin-bottom: 24px;" />
</template>

<script setup lang="ts">
  import * as monaco from 'monaco-editor';

  interface Props {
    value: string
  }

  const props = defineProps<Props>();

  const editorRef = ref();
  let editor: monaco.editor.IStandaloneCodeEditor;

  onMounted(() => {
    editor = monaco.editor.create(editorRef.value, {
      language: 'xml',
      theme: 'vs-dark',
      readOnly: true,
      minimap: {
        enabled: false,
      },
      wordWrap: 'bounded',
      scrollbar: {
        alwaysConsumeMouseWheel: false,
      },
      automaticLayout: true,
    });
    editor.setValue(props.value);
  });

  watch(() => props.value, () => {
    editor.setValue(props.value);
  });
</script>

<style lang="less" scoped>
.settings-editor {
  padding: 12px 0;
  background-color: #1e1e1e;
}
</style>
