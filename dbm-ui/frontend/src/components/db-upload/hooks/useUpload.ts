/*
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
 */

import type { Ref } from 'vue';
import { computed, isRef, onBeforeUnmount, ref } from 'vue';
import { useI18n } from 'vue-i18n';

import type { DbUploadOptions, DuplicateChecker, UploadFile, UploadRawFile } from '../types';
import { UploadStatus } from '../types';
import { getMaxSize, validateAccept, validateSize } from '../utils';

interface Handlers {
  beforeUpload?: (file: File) => boolean | Promise<boolean>;
  customRequest?: (option: Callbacks) => void;
  duplicateChecker?: DuplicateChecker;
}

interface Callbacks {
  onError: (error: Error) => void;
  onProgress: (event: ProgressEvent) => void;
  onSuccess: (res: unknown) => void;
  rawFile: { uid: number } & File;
}

interface Emits {
  onDelete: (file: UploadFile, fileList: UploadFile[]) => void;
  onDuplicateRejected: (names: string[]) => void;
  onError: (file: UploadFile, fileList: UploadFile[]) => void;
  onSuccess: (file: UploadFile, fileList: UploadFile[]) => void;
}

export const useUpload = (options: DbUploadOptions | Ref<DbUploadOptions>, handlers: Handlers | Ref<Handlers>, emits: Emits) => {
  const { t } = useI18n();

  const opts = computed(() => (isRef(options) ? options.value : options));
  const hs = computed(() => (isRef(handlers) ? handlers.value : handlers));

  const fileList = ref<UploadFile[]>([]);
  const duplicateTip = ref('');
  let duplicateTipTimer: ReturnType<typeof setTimeout> | undefined;
  let tempIndex = 0;
  const isDragover = ref(false);

  const updateFile = (uid: number, updates: Partial<UploadFile>) => {
    const index = fileList.value.findIndex((f) => f.uid === uid);
    if (index !== -1) {
      fileList.value[index] = { ...fileList.value[index], ...updates };
    }
  };

  const genUid = (): number => Date.now() + tempIndex++;

  const wrapFile = (file: File): UploadRawFile => {
    const rawFile = file as UploadRawFile;
    rawFile.uid = genUid();
    return rawFile;
  };

  const showDuplicateTip = (names: string[]) => {
    if (names.length === 1) {
      duplicateTip.value = t('已存在同名文件「x」，如需覆盖请用「替换」操作', { x: names[0] });
    } else {
      duplicateTip.value = t('已忽略 n 个同名文件', { n: names.length });
    }
    if (duplicateTipTimer) clearTimeout(duplicateTipTimer);
    duplicateTipTimer = setTimeout(() => {
      duplicateTip.value = '';
    }, 4500);
  };

  const clearDuplicateTip = () => {
    duplicateTip.value = '';
    if (duplicateTipTimer) {
      clearTimeout(duplicateTipTimer);
      duplicateTipTimer = undefined;
    }
  };

  const validateAndUpload = (rawFile: UploadRawFile): void => {
    if (!validateAccept(rawFile, opts.value.accept)) {
      updateFile(rawFile.uid, { errMsg: t('文件格式不支持'), status: UploadStatus.FAIL });
      const file = fileList.value.find((f) => f.uid === rawFile.uid);
      if (file) emits.onError(file, fileList.value);
      return;
    }

    if (!validateSize(rawFile, opts.value.size)) {
      const maxSize = getMaxSize(rawFile, opts.value.size);
      updateFile(rawFile.uid, { errMsg: t('文件大小超出限制', [maxSize]), status: UploadStatus.FAIL });
      const file = fileList.value.find((f) => f.uid === rawFile.uid);
      if (file) emits.onError(file, fileList.value);
      return;
    }

    if (hs.value.beforeUpload) {
      Promise.resolve(hs.value.beforeUpload(rawFile)).then((passed) => {
        if (passed === false) {
          const index = fileList.value.findIndex((f) => f.uid === rawFile.uid);
          if (index >= 0) fileList.value.splice(index, 1);
          return;
        }
        startUpload(rawFile);
      });
      return;
    }

    startUpload(rawFile);
  };

  const handleFiles = (files: File[]) => {
    if (opts.value.disabled) return;
    clearDuplicateTip();

    const postFiles = Array.from(files);

    if (opts.value.limit !== undefined && fileList.value.length + postFiles.length > opts.value.limit) {
      const remaining = opts.value.limit - fileList.value.length;
      if (remaining <= 0) return;
      postFiles.splice(remaining);
    }

    // 重名拦截
    const accepted: File[] = [];
    const rejectedNames: string[] = [];
    if (hs.value.duplicateChecker) {
      postFiles.forEach((file) => {
        const result = hs.value.duplicateChecker!(file, fileList.value);
        if (result === true) {
          rejectedNames.push(file.name);
        } else if (Array.isArray(result) && result.length > 0) {
          rejectedNames.push(...result);
        } else {
          accepted.push(file);
        }
      });
    } else {
      accepted.push(...postFiles);
    }

    if (rejectedNames.length > 0) {
      showDuplicateTip(rejectedNames);
      emits.onDuplicateRejected(rejectedNames);
    }

    accepted.forEach((file) => {
      const rawFile = wrapFile(file);
      fileList.value.push({
        name: rawFile.name,
        percentage: 0,
        raw: rawFile,
        size: rawFile.size,
        status: UploadStatus.UPLOADING,
        uid: rawFile.uid,
      });
      validateAndUpload(rawFile);
    });
  };

  const startUpload = (rawFile: UploadRawFile) => {
    updateFile(rawFile.uid, { percentage: 0, status: UploadStatus.UPLOADING });

    if (hs.value.customRequest) {
      hs.value.customRequest({
        onError: (error: Error) => {
          updateFile(rawFile.uid, { errMsg: error.message || t('上传失败，请重试'), status: UploadStatus.FAIL });
          const file = fileList.value.find((f) => f.uid === rawFile.uid);
          if (file) emits.onError(file, fileList.value);
        },
        onProgress: (event: ProgressEvent) => {
          const percentage = event.lengthComputable ? Math.round((event.loaded / event.total) * 100) : 0;
          updateFile(rawFile.uid, { percentage });
        },
        onSuccess: (res: unknown) => {
          updateFile(rawFile.uid, { percentage: 100, response: res, status: UploadStatus.SUCCESS });
          const file = fileList.value.find((f) => f.uid === rawFile.uid);
          if (file) emits.onSuccess(file, fileList.value);
        },
        rawFile,
      });
    } else {
      updateFile(rawFile.uid, { percentage: 100, status: UploadStatus.SUCCESS });
      const file = fileList.value.find((f) => f.uid === rawFile.uid);
      if (file) emits.onSuccess(file, fileList.value);
    }
  };

  const handleDragover = (event: DragEvent) => {
    if (opts.value.disabled) return;
    event.preventDefault();
    isDragover.value = true;
  };

  const handleDragleave = (event: DragEvent) => {
    if (opts.value.disabled) return;
    event.preventDefault();
    isDragover.value = false;
  };

  const handleDrop = (event: DragEvent) => {
    if (opts.value.disabled) return;
    event.preventDefault();
    isDragover.value = false;
    if (event.dataTransfer?.files) {
      handleFiles(Array.from(event.dataTransfer.files));
    }
  };

  const handleRemove = (file: UploadFile) => {
    const index = fileList.value.findIndex((f) => f.uid === file.uid);
    if (index !== -1) {
      fileList.value.splice(index, 1);
      emits.onDelete(file, fileList.value);
    }
  };

  const handleRetry = (file: UploadFile) => {
    const rawFile = file.raw;
    if (rawFile) {
      updateFile(file.uid, { errMsg: undefined, percentage: 0, status: UploadStatus.UPLOADING, statusText: '' });
      validateAndUpload(rawFile);
    }
  };

  const clearFiles = () => {
    fileList.value = [];
  };

  onBeforeUnmount(() => {
    if (duplicateTipTimer) clearTimeout(duplicateTipTimer);
  });

  return {
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
  };
};
