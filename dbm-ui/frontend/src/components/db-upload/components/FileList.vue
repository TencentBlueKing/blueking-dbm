<!--
 * TencentBlueKing is pleased to support the open source community by making
 * 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 *
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 *
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 *
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed
 * on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and limitations under the License.
-->

<!-- 文件列表子组件：渲染上传文件列表（进度条 / 状态 / 操作按钮） -->
<template>
  <TransitionGroup
    v-if="fileList.length > 0"
    class="db-upload-list"
    name="db-upload-list"
    tag="div">
    <div
      v-for="file in fileList"
      :key="file.uid"
      class="db-upload-list-item"
      :class="{
        'db-upload-list-item-fail': file.status === UploadStatus.FAIL,
        'db-upload-list-item-success': file.status === UploadStatus.SUCCESS,
        'db-upload-list-item-uploading': file.status === UploadStatus.UPLOADING,
      }">
      <!-- 文件图标 -->
      <div class="db-upload-list-item-icon">
        <DbIcon :type="fileIcon" />
      </div>

      <!-- 文件信息 -->
      <div class="db-upload-list-item-summary">
        <span
          class="db-upload-list-item-name"
          :title="file.name">
          {{ file.name }}
        </span>

        <!-- 上传中：进度条 + 百分比 -->
        <template v-if="file.status === UploadStatus.UPLOADING">
          <div class="db-upload-list-item-progress">
            <div class="db-upload-list-item-progress-bar">
              <div
                class="db-upload-list-item-progress-inner"
                :style="{ width: `${file.percentage ?? 0}%` }" />
            </div>
          </div>
          <span class="db-upload-list-item-speed">
            <span class="db-upload-list-item-speed-percent">{{ file.percentage ?? 0 }}%</span>
          </span>
        </template>

        <!-- 上传成功 -->
        <template v-else-if="file.status === UploadStatus.SUCCESS">
          <span class="db-upload-list-item-message db-upload-list-item-msg-success">
            <DbIcon type="check-line" />
            {{ t('上传成功') }}
          </span>
          <span class="db-upload-list-item-speed">{{ formatFileSize(file.size) }}</span>
        </template>

        <!-- 上传失败 -->
        <template v-else-if="file.status === UploadStatus.FAIL">
          <span class="db-upload-list-item-message db-upload-list-item-msg-fail">
            {{ file.errMsg || file.statusText || t('上传失败，请重试') }}
          </span>
        </template>

        <!-- 操作按钮（hover 显示） -->
        <div class="db-upload-list-item-actions">
          <DbIcon
            v-if="file.status === UploadStatus.FAIL"
            v-bk-tooltips="t('重试')"
            class="db-upload-list-item-retry-icon"
            type="refresh-2"
            @click="emit('retry', file)" />
          <DbIcon
            v-bk-tooltips="t('删除')"
            class="db-upload-list-item-del-icon"
            type="delete"
            @click="emit('remove', file)" />
        </div>
      </div>
    </div>
  </TransitionGroup>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import DbIcon from '@components/db-icon';

  import type { UploadFile } from '../types';
  import { UploadStatus } from '../types';
  import { formatFileSize } from '../utils';

  interface Props {
    /** 文件图标类型 */
    fileIcon?: string;
    /** 文件列表 */
    fileList: UploadFile[];
  }

  type Emits = {
    (e: 'remove', file: UploadFile): void;
    (e: 'retry', file: UploadFile): void;
  };

  defineOptions({
    name: 'DbUploadFileList',
  });

  withDefaults(defineProps<Props>(), {
    fileIcon: 'file',
  });

  const emit = defineEmits<Emits>();

  const { t } = useI18n();
</script>
