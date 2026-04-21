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
    :class="{ 'db-upload-disabled': disabled }">
    <!-- 上传触发区域 -->
    <div
      class="db-upload-trigger db-upload-trigger-draggable"
      :class="{
        'db-upload-trigger-dragover': isDragover,
        'db-upload-trigger-disabled': disabled,
      }"
      @click="handleClick"
      @dragenter.prevent="handleDragEnter"
      @dragleave.prevent="handleDragLeave"
      @dragover.prevent="handleDragOver"
      @drop.prevent="handleDrop">
      <div class="db-upload-trigger-draggable-content">
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
          {{ t('将文件拖到此处或') }}<span class="db-upload-trigger-draggable-link">{{ t('点击上传') }}</span>
        </p>
      </div>
      <input
        ref="inputRef"
        :accept="accept"
        class="db-upload-trigger-input-file"
        :disabled="disabled"
        :multiple="multiple"
        type="file"
        @change="handleInputChange" />
    </div>

    <!-- 提示文本 -->
    <div
      v-if="tip || $slots.tip"
      class="db-upload-tip">
      <slot name="tip" />
      <template v-if="!$slots.tip">{{ tip }}</template>
    </div>

    <!-- 文件列表 -->
    <slot
      :file-list="fileList"
      :handle-remove="handleRemove"
      :handle-retry="handleRetry"
      name="file">
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
            'db-upload-list-item-success': file.status === UploadStatus.SUCCESS,
            'db-upload-list-item-fail': file.status === UploadStatus.FAIL,
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

            <!-- 上传中：显示进度条 + 百分比 -->
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
                {{ file.statusText || t('上传成功') }}
              </span>
              <span class="db-upload-list-item-speed">{{ formatFileSize(file.size) }}</span>
            </template>

            <!-- 上传失败 -->
            <template v-else-if="file.status === UploadStatus.FAIL">
              <span class="db-upload-list-item-message db-upload-list-item-msg-fail">
                {{ file.statusText || t('上传失败') }}
              </span>
            </template>

            <!-- 待上传 -->
            <template v-else>
              <span class="db-upload-list-item-speed">{{ formatFileSize(file.size) }}</span>
            </template>

            <!-- 操作按钮（hover 显示） -->
            <div class="db-upload-list-item-actions">
              <DbIcon
                v-if="file.status === UploadStatus.FAIL"
                class="db-upload-list-item-retry-icon"
                type="refresh-2"
                @click="handleRetry(file)" />
              <DbIcon
                class="db-upload-list-item-del-icon"
                type="delete"
                @click="handleRemove(file)" />
            </div>
          </div>
        </div>
      </TransitionGroup>
    </slot>
  </div>
</template>

<script setup lang="ts">
  import { ref } from 'vue';
  import { useI18n } from 'vue-i18n';

  import DbIcon from '@components/db-icon';

  import type {
    BeforeRemoveHook,
    BeforeUploadHook,
    MaxSize,
    UploadFile,
    UploadRawFile,
    UploadRequestHandler,
    UploadRequestOptions,
  } from './types';
  import { UploadStatus } from './types';

  interface Props {
    /** 接受的文件类型 */
    accept?: string;
    /** 是否自动上传（选择文件后立即上传） */
    autoUpload?: boolean;
    /** 删除前钩子，返回 false 阻止删除 */
    beforeRemove?: BeforeRemoveHook;
    /** 上传前钩子，返回 false 阻止上传 */
    beforeUpload?: BeforeUploadHook;
    /** 自定义上传方法 */
    customRequest?: UploadRequestHandler;
    /** 额外 FormData 数据 */
    data?: Record<string, string | Blob>;
    /** 是否禁用 */
    disabled?: boolean;
    /** 文件列表中的文件图标类型 */
    fileIcon?: string;
    /** 响应码判断 */
    handleResCode?: (res: Record<string, any>) => boolean;
    /** 自定义请求头 */
    headers?: Record<string, string>;
    /** 最大文件数量限制 */
    limit?: number;
    /** HTTP 方法 */
    method?: string;
    /** 是否支持多选 */
    multiple?: boolean;
    /** 文件字段名 */
    name?: string;
    /** 文件大小限制（MB），可传数字或对象 */
    size?: number | MaxSize;
    /** 提示文本 */
    tip?: string;
    /** 上传地址，非必传，不传则不自动上传 */
    url?: string;
    /** 是否携带凭证 */
    withCredentials?: boolean;
  }

  type Emits = {
    (e: 'change', fileList: UploadFile[]): void;
    (e: 'delete', file: UploadFile, fileList: UploadFile[]): void;
    (e: 'done', file: UploadFile, fileList: UploadFile[]): void;
    (e: 'error', file: UploadFile, fileList: UploadFile[]): void;
    (e: 'exceed', files: File[], fileList: UploadFile[]): void;
    (e: 'progress', file: UploadFile, fileList: UploadFile[]): void;
    (e: 'success', file: UploadFile, fileList: UploadFile[]): void;
  };

  defineOptions({
    name: 'DbUpload',
  });

  const props = withDefaults(defineProps<Props>(), {
    accept: '',
    autoUpload: true,
    beforeRemove: undefined,
    beforeUpload: undefined,
    customRequest: undefined,
    data: undefined,
    disabled: false,
    fileIcon: 'file',
    handleResCode: undefined,
    headers: undefined,
    limit: undefined,
    method: 'POST',
    multiple: false,
    name: 'file',
    size: undefined,
    tip: '',
    url: '',
    withCredentials: false,
  });

  const emit = defineEmits<Emits>();

  const { t } = useI18n();

  const inputRef = ref<HTMLInputElement>();
  const isDragover = ref(false);
  const fileList = ref<UploadFile[]>([]);
  let tempIndex = 0;

  /** 格式化文件大小 */
  const formatFileSize = (size: number): string => {
    if (size === 0) return '0 B';
    const units = ['B', 'KB', 'MB', 'GB'];
    const k = 1024;
    const i = Math.floor(Math.log(size) / Math.log(k));
    return `${parseFloat((size / k ** i).toFixed(2))} ${units[i]}`;
  };

  /** 获取最大文件大小限制（MB） */
  const getMaxSize = (file: File): number | undefined => {
    if (props.size === undefined) return undefined;
    if (typeof props.size === 'number') return props.size;
    return file.type.startsWith('image/') ? props.size.maxImgSize : props.size.maxFileSize;
  };

  /** 校验文件格式 */
  const validateAccept = (file: File): boolean => {
    if (!props.accept) return true;
    const extensions = props.accept
      .split(',')
      .map((ext) => ext.trim().toLowerCase())
      .filter(Boolean);
    if (extensions.length === 0) return true;

    const fileName = file.name.toLowerCase();
    const hasExtMatch = extensions.some((ext) => fileName.endsWith(ext));

    // 同时检查 MIME 类型
    const hasMimeMatch = extensions.some((ext) => {
      if (!ext.includes('/')) return false;
      return file.type === ext;
    });

    return hasExtMatch || hasMimeMatch;
  };

  /** 校验文件大小 */
  const validateSize = (file: File): boolean => {
    const maxSize = getMaxSize(file);
    if (maxSize === undefined) return true;
    return file.size / 1024 / 1024 <= maxSize;
  };

  /** 更新文件列表中的文件属性 */
  const updateFile = (uid: number, updates: Partial<UploadFile>) => {
    const index = fileList.value.findIndex((f) => f.uid === uid);
    if (index !== -1) {
      fileList.value[index] = { ...fileList.value[index], ...updates };
    }
  };

  /** 添加文件到列表 */
  const addFile = (rawFile: UploadRawFile): UploadFile => {
    const uploadFile: UploadFile = {
      name: rawFile.name,
      percentage: 0,
      raw: rawFile,
      size: rawFile.size,
      status: UploadStatus.NEW,
      uid: rawFile.uid,
    };
    fileList.value.push(uploadFile);
    return uploadFile;
  };

  /** 将原始 File 转为 UploadRawFile */
  const genUid = (): number => Date.now() + tempIndex++;

  const wrapFile = (file: File): UploadRawFile => {
    const rawFile = file as UploadRawFile;
    rawFile.uid = genUid();
    return rawFile;
  };

  /** 校验并上传单个文件（格式/大小/beforeUpload） */
  const validateAndUpload = (rawFile: UploadRawFile): void => {
    // 格式校验
    if (!validateAccept(rawFile)) {
      updateFile(rawFile.uid, {
        status: UploadStatus.FAIL,
        statusText: t('文件格式不支持'),
      });
      const file = fileList.value.find((f) => f.uid === rawFile.uid);
      if (file) {
        emit('error', file, fileList.value);
      }
      return;
    }

    // 大小校验
    if (!validateSize(rawFile)) {
      const maxSize = getMaxSize(rawFile);
      updateFile(rawFile.uid, {
        status: UploadStatus.FAIL,
        statusText: t('文件大小超出限制', [maxSize]),
      });
      const file = fileList.value.find((f) => f.uid === rawFile.uid);
      if (file) {
        emit('error', file, fileList.value);
      }
      return;
    }

    // beforeUpload 钩子
    if (props.beforeUpload) {
      const result = props.beforeUpload(rawFile, fileList.value);
      if (result === false) {
        handleRemove(fileList.value.find((f) => f.uid === rawFile.uid)!);
        return;
      }
    }

    upload(rawFile);
  };

  /** 处理文件选择 */
  const handleFiles = (files: File[]) => {
    if (props.disabled) return;

    const postFiles = Array.from(files);

    // 数量限制校验
    if (props.limit !== undefined && fileList.value.length + postFiles.length > props.limit) {
      emit('exceed', postFiles, fileList.value);
      return;
    }

    postFiles.forEach((file) => {
      const rawFile = wrapFile(file);
      addFile(rawFile);

      if (props.autoUpload) {
        validateAndUpload(rawFile);
      }

      emit('change', fileList.value);
    });
  };

  /** 执行上传 */
  const upload = (rawFile: UploadRawFile) => {
    updateFile(rawFile.uid, {
      percentage: 0,
      status: UploadStatus.UPLOADING,
    });

    if (!props.url && !props.customRequest) {
      // 无 url 且无自定义上传：直接标记成功
      updateFile(rawFile.uid, {
        percentage: 100,
        status: UploadStatus.SUCCESS,
      });
      const file = fileList.value.find((f) => f.uid === rawFile.uid);
      if (file) {
        emit('success', file, fileList.value);
        emit('done', file, fileList.value);
      }
      return;
    }

    if (props.customRequest) {
      doCustomUpload(rawFile);
    } else {
      doAjaxUpload(rawFile);
    }
  };

  /** 自定义上传 */
  const doCustomUpload = (rawFile: UploadRawFile) => {
    if (!props.customRequest) return;

    const options: UploadRequestOptions = {
      action: props.url,
      data: props.data,
      file: rawFile,
      filename: props.name,
      headers: props.headers,
      method: props.method,
      onError: (error: Error) => {
        updateFile(rawFile.uid, {
          status: UploadStatus.FAIL,
          statusText: error.message || t('上传失败'),
        });
        const file = fileList.value.find((f) => f.uid === rawFile.uid);
        if (file) {
          emit('error', file, fileList.value);
        }
      },
      onProgress: (event: ProgressEvent) => {
        const percentage = event.lengthComputable ? Math.round((event.loaded / event.total) * 100) : 0;
        updateFile(rawFile.uid, { percentage });
        const file = fileList.value.find((f) => f.uid === rawFile.uid);
        if (file) {
          emit('progress', file, fileList.value);
        }
      },
      onSuccess: (res: unknown) => {
        updateFile(rawFile.uid, {
          percentage: 100,
          response: res,
          status: UploadStatus.SUCCESS,
        });
        const file = fileList.value.find((f) => f.uid === rawFile.uid);
        if (file) {
          emit('success', file, fileList.value);
          emit('done', file, fileList.value);
        }
      },
      withCredentials: props.withCredentials,
    };

    props.customRequest(options);
  };

  /** XMLHttpRequest 上传 */
  const doAjaxUpload = (rawFile: UploadRawFile) => {
    const xhr = new XMLHttpRequest();
    const formData = new FormData();

    if (props.data) {
      Object.entries(props.data).forEach(([key, value]) => {
        formData.append(key, value);
      });
    }

    formData.append(props.name, rawFile);

    xhr.open(props.method, props.url, true);

    if (props.withCredentials) {
      xhr.withCredentials = true;
    }

    if (props.headers) {
      Object.entries(props.headers).forEach(([key, value]) => {
        xhr.setRequestHeader(key, value);
      });
    }

    xhr.upload.addEventListener('progress', (event) => {
      const percentage = event.lengthComputable ? Math.round((event.loaded / event.total) * 100) : 0;
      updateFile(rawFile.uid, { percentage });
      const file = fileList.value.find((f) => f.uid === rawFile.uid);
      if (file) {
        emit('progress', file, fileList.value);
      }
    });

    xhr.addEventListener('load', () => {
      if (xhr.status < 200 || xhr.status >= 300) {
        updateFile(rawFile.uid, {
          status: UploadStatus.FAIL,
          statusText: t('上传失败'),
        });
        const file = fileList.value.find((f) => f.uid === rawFile.uid);
        if (file) {
          emit('error', file, fileList.value);
        }
        return;
      }

      let response: unknown;
      try {
        response = JSON.parse(xhr.responseText);
      } catch {
        response = xhr.responseText;
      }

      // handleResCode 校验
      if (props.handleResCode) {
        if (!props.handleResCode(response as Record<string, any>)) {
          updateFile(rawFile.uid, {
            response,
            status: UploadStatus.FAIL,
            statusText: t('上传失败'),
          });
          const file = fileList.value.find((f) => f.uid === rawFile.uid);
          if (file) {
            emit('error', file, fileList.value);
          }
          return;
        }
      }

      updateFile(rawFile.uid, {
        percentage: 100,
        response,
        status: UploadStatus.SUCCESS,
      });
      const file = fileList.value.find((f) => f.uid === rawFile.uid);
      if (file) {
        emit('success', file, fileList.value);
        emit('done', file, fileList.value);
      }
    });

    xhr.addEventListener('error', () => {
      updateFile(rawFile.uid, {
        status: UploadStatus.FAIL,
        statusText: t('上传失败'),
      });
      const file = fileList.value.find((f) => f.uid === rawFile.uid);
      if (file) {
        emit('error', file, fileList.value);
      }
    });

    xhr.send(formData);
  };

  /** 点击上传区域 */
  const handleClick = () => {
    if (props.disabled) return;
    inputRef.value?.click();
  };

  /** input change 事件 */
  const handleInputChange = (event: Event) => {
    const target = event.target as HTMLInputElement;
    if (target.files) {
      handleFiles(Array.from(target.files));
    }
    // 重置 input，允许重复选择同一文件
    if (inputRef.value) {
      inputRef.value.value = '';
    }
  };

  /** 拖拽相关事件 */
  const handleDragEnter = () => {
    if (props.disabled) return;
    isDragover.value = true;
  };

  const handleDragLeave = () => {
    isDragover.value = false;
  };

  const handleDragOver = () => {
    if (props.disabled) return;
    isDragover.value = true;
  };

  const handleDrop = (event: DragEvent) => {
    if (props.disabled) return;
    isDragover.value = false;
    if (event.dataTransfer?.files) {
      handleFiles(Array.from(event.dataTransfer.files));
    }
  };

  /** 删除文件 */
  const handleRemove = async (file: UploadFile) => {
    if (props.beforeRemove) {
      const result = await props.beforeRemove(file, fileList.value);
      if (result === false) return;
    }

    const index = fileList.value.findIndex((f) => f.uid === file.uid);
    if (index !== -1) {
      fileList.value.splice(index, 1);
      emit('delete', file, fileList.value);
      emit('change', fileList.value);
    }
  };

  /** 重试上传（重新走完整校验流程） */
  const handleRetry = (file: UploadFile) => {
    const rawFile = file.raw;
    if (rawFile) {
      updateFile(file.uid, {
        percentage: 0,
        status: UploadStatus.NEW,
        statusText: '',
      });
      validateAndUpload(rawFile);
    }
  };

  /** 手动提交上传（autoUpload=false 时使用） */
  const submit = () => {
    fileList.value
      .filter((file) => file.status === UploadStatus.NEW)
      .forEach((file) => {
        upload(file.raw);
      });
  };

  /** 清空文件列表 */
  const clearFiles = () => {
    fileList.value = [];
    emit('change', fileList.value);
  };

  defineExpose({
    clearFiles,
    fileList,
    handleRemove,
    handleRetry,
    submit,
  });
</script>

<style lang="less">
  @import './index.less';
</style>
