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
  <div class="editor-resize-wrapper">
    <Editor ref="editorRef" />
  </div>
</template>
<script setup lang="ts">
  import Editor from './components/editor/Index.vue';

  const editorRef = ref<InstanceType<typeof Editor>>();

  defineExpose({
    getValue() {
      return editorRef.value!.getValue();
    },
    setValue(value: string) {
      return editorRef.value!.setValue(value);
    },
  });
</script>
<style lang="less">
  .editor-resize-wrapper {
    height: 500px !important;

    .bk-resize-layout-aside-content {
      height: auto !important;
      overflow: auto !important;
    }
  }
</style>
