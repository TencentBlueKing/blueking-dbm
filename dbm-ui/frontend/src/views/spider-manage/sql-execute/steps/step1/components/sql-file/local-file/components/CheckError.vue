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
    v-if="(data.messageList.length < 1 && data.grammarCheck?.isError) || data.isUploadFailed"
    class="sql-execute-upload-check-error">
    <span v-if="data.grammarCheck?.isError">{{ t('SQL语法错误') }}</span>
    <span v-else-if="data.uploadErrorMessage">{{ data.uploadErrorMessage }}</span>
    <span v-else>{{ t('文件上传失败') }}</span>
  </div>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import type { IFileData } from './FileList.vue';

  interface Props {
    data: IFileData
  }

  defineProps<Props>();

  const { t } = useI18n();
</script>
<style lang="less">
  .sql-execute-upload-check-error {
    position: absolute;
    right: 0;
    bottom: 0;
    left: 0;
    display: flex;
    height: 48px;
    padding-left: 16px;
    font-size: 12px;
    color: #dcdee5;
    background: #212121;
    border-left: 4px solid #b34747;
    align-items: center;
  }
</style>
