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
  <BkFormItem property="execute_sqls">
    <template #labelAppend>
      <span style="font-size: 12px; font-weight: normal; color: #8a8f99">
        （{{ t('最终执行结果以脚本内容为准') }}）
      </span>
    </template>
    <div class="sql-execute-manual-input">
      <Editor
        v-model="content"
        :message-list="[]"
        :title="t('脚本编辑器')"
        @change="handleContentChange" />
    </div>
  </BkFormItem>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import Editor from '../editor/Index.vue';

  interface Emits {
    (e: 'change', value: string): void;
  }

  interface Exposes {
    getValue: () => { name: string; content: string }[];
  }

  const emits = defineEmits<Emits>();

  const { t } = useI18n();

  const content = ref('');

  const handleContentChange = (value: string) => {
    emits('change', value);
  };

  defineExpose<Exposes>({
    getValue: () => [
      {
        name: '',
        content: content.value,
      },
    ],
  });
</script>
<style lang="less">
  .sql-execute-manual-input {
    position: relative;

    .footer-action {
      position: absolute;
      right: 0;
      bottom: 0;
      left: 0;
      z-index: 1;
      display: flex;
      height: 48px;
      padding-left: 16px;
      background: #212121;
      border-radius: 0 0 2px 2px;
      align-items: center;
    }

    .syntax-checking,
    .syntax-success,
    .syntax-error {
      position: absolute;
      right: 0;
      bottom: 0;
      left: 0;
    }
  }
</style>
