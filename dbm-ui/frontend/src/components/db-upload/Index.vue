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

<template>
  <div
    class="db-upload"
    :class="{ 'db-upload-disabled': options.disabled }">
    <!-- 文件列表在上（listPosition = top） -->
    <FileList
      v-if="options.showFileList !== false && options.listPosition === 'top'"
      :file-icon="options.fileIcon"
      :file-list="fileList"
      @remove="handleRemove"
      @retry="handleRetry" />

    <!-- 上传触发区域 -->
    <div
      class="db-upload-trigger"
      :class="{
        'db-upload-trigger-disabled': options.disabled,
        'db-upload-trigger-draggable': options.draggable,
        'db-upload-trigger-dragover': isDragover,
      }"
      v-on="dragListeners"
      @click="handleClick">
      <!-- 拖拽模式 -->
      <div
        v-if="options.draggable"
        class="db-upload-trigger-draggable-content">
        <svg
          class="db-upload-trigger-draggable-icon"
          viewBox="0 0 64 64"
          xmlns="http://www.w3.org/2000/svg">
          <g>
            <path
              d="M56.1,26.4c-1.7-1.7-3.9-3-6.3-3.6C48,13.1,38.7,6.5,28.9,8.2c-7.5,1.3-13.3,7.2-14.6,14.6C8.2,24.3,4,29.7,4,35.9v0.6C4,44,10,50,17.4,50H20v-4h-2.6C12.2,46,8,41.8,8,36.6v-0.6c0-5.2,4.2-9.4,9.4-9.4H18c0-0.2,0-0.3,0-0.5l0,0c0-0.1,0-0.2,0-0.3v-0.1c0-0.1,0-0.2,0-0.3c0,0,0,0,0-0.1c0-0.1,0-0.2,0-0.3v-0.1c0-0.1,0-0.2,0-0.2c0-0.1,0-0.1,0-0.2c0,0,0-0.1,0-0.1c0.1-0.6,0.2-1.3,0.4-1.9l0,0c1.9-7.5,9.6-12,17-10.1c4.9,1.3,8.8,5.1,10.1,10.1l0,0c0.2,0.6,0.3,1.3,0.3,1.9c0,0,0,0.1,0,0.1c0,0,0,0.1,0,0.2c0,0.1,0,0.2,0,0.2V25c0,0.1,0,0.2,0,0.2v0.1c0,0.1,0,0.2,0,0.3v0.1c0,0.1,0,0.2,0,0.3l0,0c0,0.2,0,0.3,0,0.5h0.6c5.2-0.1,9.5,4.1,9.6,9.3c0,0.1,0,0.1,0,0.2v0.6c0,5.2-4.2,9.4-9.4,9.4l0,0H44v4h2.6C54,50,60,44,60,36.6v-0.6C60,32.4,58.6,29,56.1,26.4z" />
            <path d="M23.5,37.7 26.3,40.5 30,36.8 30,56 34,56 34,36.8 37.7,40.5 40.5,37.7 32,29.2z" />
          </g>
        </svg>
        <p class="db-upload-trigger-draggable-text">
          {{ t('将文件拖到此或') }}<span class="db-upload-trigger-draggable-link">{{ t('点击上传') }}</span>
        </p>
      </div>
      <!-- 点击模式 -->
      <template v-else>
        <slot
          :loading="isUploading"
          name="trigger">
          <DbIcon type="plus" />
          <span>{{ t('点击上传文件') }}</span>
          <span
            v-if="options.multiple"
            class="db-upload-trigger-hint">
            {{ t('支持多选') }}
          </span>
        </slot>
      </template>
      <!-- 重名提示 -->
      <Transition name="db-upload-tip-fade">
        <div
          v-if="duplicateTip"
          class="db-upload-duplicate-tip">
          <DbIcon type="exclamation-triangle" />
          <span>{{ duplicateTip }}</span>
        </div>
      </Transition>
    </div>

    <!-- 提示文本 -->
    <div
      v-if="options.tip || $slots.tip"
      class="db-upload-tip">
      <slot name="tip" />
      <template v-if="!$slots.tip">{{ options.tip }}</template>
    </div>

    <!-- 文件列表在下（listPosition = bottom，默认） -->
    <FileList
      v-if="options.showFileList !== false && options.listPosition !== 'top'"
      :file-icon="options.fileIcon"
      :file-list="fileList"
      @remove="handleRemove"
      @retry="handleRetry" />

    <!-- 隐藏的文件 input -->
    <input
      ref="inputRef"
      :accept="options.accept"
      class="db-upload-trigger-input-file"
      :disabled="options.disabled"
      :multiple="options.multiple"
      type="file"
      @change="handleInputChange" />
  </div>
</template>

<script setup lang="ts">
  import { computed, ref } from 'vue';
  import { useI18n } from 'vue-i18n';

  import DbIcon from '@components/db-icon';

  import FileList from './components/FileList.vue';
  import { useUpload } from './hooks/useUpload';
  import type { DbUploadOptions, DuplicateChecker, UploadFile } from './types';
  import { UploadStatus } from './types';
  import {
    BKREPO_DEFAULT_HEADERS,
    createBkrepoUploadUrl,
    createXhrUpload,
    isExcelAccept,
    parseExcelFile,
  } from './utils/index';

  interface Props {
    /** 同表重名规则，选择即拦截 */
    duplicateChecker?: DuplicateChecker;
    /** 上传配置 */
    options?: DbUploadOptions;
  }

  type Emits = {
    (e: 'delete', file: UploadFile, fileList: UploadFile[]): void;
    (e: 'duplicate-rejected', names: string[]): void;
    (e: 'error', file: UploadFile, fileList: UploadFile[]): void;
    (e: 'success', file: UploadFile, fileList: UploadFile[]): void;
  };

  defineOptions({
    name: 'DbUpload',
  });

  const props = withDefaults(defineProps<Props>(), {
    duplicateChecker: undefined,
    options: () => ({}),
  });

  const emit = defineEmits<Emits>();

  const { t } = useI18n();

  const inputRef = ref<HTMLInputElement>();
  const uploadUrlMap = new Map<number, string>();

  const mergedOptions = computed<DbUploadOptions>(() => ({
    accept: '',
    basePath: '',
    disabled: false,
    draggable: false,
    fileIcon: 'file',
    listPosition: 'bottom',
    mode: 'bkrepo',
    multiple: false,
    showFileList: true,
    tip: '',
    ...props.options,
  }));

  const handlers = computed(() => {
    // bkrepo 模式（有 basePath）：内置 beforeUpload + XHR 直传
    if (mergedOptions.value.basePath) {
      return {
        beforeUpload: (async (file: File) => {
          const filePath = `${mergedOptions.value.basePath}/${file.name}`;
          const url = await createBkrepoUploadUrl(filePath);
          uploadUrlMap.set((file as unknown as { uid: number }).uid, url);
          return true;
        }) as (file: File) => boolean | Promise<boolean>,
        customRequest: ((option: {
          onError: (error: Error) => void;
          onProgress: (event: ProgressEvent) => void;
          onSuccess: (res: unknown) => void;
          rawFile: { uid: number } & File;
        }) => {
          const url = uploadUrlMap.get(option.rawFile.uid);
          uploadUrlMap.delete(option.rawFile.uid);
          if (!url) {
            option.onError(new Error('Upload URL not found'));
            return;
          }
          createXhrUpload({
            headers: { ...BKREPO_DEFAULT_HEADERS },
            onError: option.onError,
            onProgress: option.onProgress,
            onSuccess: option.onSuccess,
            rawFile: option.rawFile,
            url,
          });
        }) as (option: Record<string, any>) => void,
        duplicateChecker: props.duplicateChecker,
      };
    }
    // Excel accept 模式：内置 parseExcelFile 解析 + 前端模拟进度
    if (isExcelAccept(mergedOptions.value.accept)) {
      return {
        customRequest: ((option: {
          onError: (error: Error) => void;
          onProgress: (event: ProgressEvent) => void;
          onSuccess: (res: unknown) => void;
          rawFile: { uid: number } & File;
        }) => {
          option.onProgress({ lengthComputable: true, loaded: 10, total: 100 } as ProgressEvent);
          parseExcelFile(option.rawFile)
            .then((data) => {
              option.onProgress({ lengthComputable: true, loaded: 100, total: 100 } as ProgressEvent);
              option.onSuccess(data);
            })
            .catch((err: Error) => option.onError(err));
        }) as (option: Record<string, any>) => void,
        duplicateChecker: props.duplicateChecker,
      };
    }
    return { duplicateChecker: props.duplicateChecker };
  });

  const {
    clearDuplicateTip,
    clearFiles,
    duplicateTip,
    fileList,
    handleDragleave,
    handleDragover,
    handleDrop,
    handleFiles,
    handleRemove,
    handleRetry,
    isDragover,
  } = useUpload(mergedOptions, handlers, {
    onDelete: (file, list) => emit('delete', file, list),
    onDuplicateRejected: (names) => emit('duplicate-rejected', names),
    onError: (file, list) => emit('error', file, list),
    onSuccess: (file, list) => emit('success', file, list),
  });

  const isUploading = computed(() => fileList.value.some((f) => f.status === UploadStatus.UPLOADING));

  const dragListeners = computed(() =>
    mergedOptions.value.draggable
      ? { dragleave: handleDragleave, dragover: handleDragover, drop: handleDrop }
      : {},
  );

  const handleClick = () => {
    if (mergedOptions.value.disabled) return;
    inputRef.value?.click();
  };

  const handleInputChange = (event: Event) => {
    const target = event.target as HTMLInputElement;
    if (target.files) {
      handleFiles(Array.from(target.files));
    }
    if (inputRef.value) {
      inputRef.value.value = '';
    }
  };

  defineExpose({
    clearDuplicateTip,
    clearFiles,
    fileList,
    handleRemove,
    handleRetry,
    inputRef,
  });
</script>

<style lang="less">
  @import './index.less';
</style>
