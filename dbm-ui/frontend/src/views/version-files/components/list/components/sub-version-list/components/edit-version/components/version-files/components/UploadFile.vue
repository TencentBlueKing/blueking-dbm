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
  <BkUpload
    ref="uplodRef"
    :accept="acceptInfo.accept"
    :before-upload="handleBeforeUpload"
    class="version-upload-file"
    :custom-request="handleCustomRequest"
    :disabled="!version"
    :header="[
      {
        name: 'Content-Type',
        value: 'application/octet-stream',
      },
      {
        name: 'X-CSRFToken',
        value: Cookies.get('dbm_csrftoken'),
      },
      {
        name: 'X-BKREPO-OVERWRITE',
        value: true,
      },
    ]"
    method="put"
    :multiple="false"
    name=""
    :size="10240"
    :tip="acceptInfo.tips"
    :url="uploadUrl"
    @success="handleUpdateSuccess">
    <template #trigger>
      <BkButton
        v-bk-tooltips="{
          content: t('请先设置版本号'),
          disabled: !!version,
        }"
        :disabled="!version"
        :loading="uploadLoading"
        text
        theme="primary">
        <DbIcon type="plus-fill" />
        <span style="margin-left: 4px; font-size: 12px">{{ t('点击上传文件') }}</span>
      </BkButton>
    </template>
  </BkUpload>
</template>
<script setup lang="ts">
  import type { UploadProgressEvent, UploadRequestOptions } from 'bkui-vue/lib/upload/upload.type';
  import Cookies from 'js-cookie';
  import { useI18n } from 'vue-i18n';

  import { createBkrepoAccessToken } from '@services/source/storage';

  interface Props {
    dbType: string;
    pkgType: string;
    version: string;
  }

  type Emits = (
    e: 'success',
    fileInfo: {
      md5: string;
      name: string;
      path: string;
      size: number;
    },
  ) => void;

  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();

  const { t } = useI18n();

  const uplodRef = ref();
  const uploadUrl = ref('');
  const uploadLoading = ref(false);

  const acceptInfo = computed(() => {
    const limitTypes = ['mysql', 'mysql-proxy'];
    if (limitTypes.includes(props.pkgType)) {
      return {
        accept: '.tar.gz,.tar.xz',
        tips: t('支持上传tar_gz_xz压缩格式文件_文件大小不超过10GB'),
      };
    }
    return {
      accept: '',
      tips: t('文件大小不超过10GB'),
    };
  });

  /**
   * 上传前处理
   */
  const handleBeforeUpload = async (fileObj: File) => {
    uploadLoading.value = true;
    const dbType = props.dbType;
    const pkgType = props.pkgType;
    const filename = fileObj.name;
    const limitTypes = ['mysql', 'mysql-proxy'];
    if (limitTypes.includes(props.pkgType)) {
      if (!filename.endsWith('tar.gz') && !filename.endsWith('tar.xz')) {
        return;
      }
    }

    const filePath = `/${dbType}/${pkgType}/${props.version}/${filename}`;
    const tokenResult = await createBkrepoAccessToken({ file_path: filePath });
    const uploadDomain = import.meta.env.MODE === 'production' ? tokenResult.url : '/bkrepo_upload';
    uploadUrl.value = `${uploadDomain}/generic/temporary/upload/${tokenResult.project}/${tokenResult.repo}${tokenResult.path}?token=${tokenResult.token}`;
    return true;
  };

  const getRes = (xhr: XMLHttpRequest): XMLHttpRequestResponseType => {
    const res = xhr.responseText || xhr.response;
    if (!res) {
      return res;
    }

    try {
      return JSON.parse(res);
    } catch {
      return res;
    }
  };

  /**
   * 自定义请求
   */
  const handleCustomRequest = (option: UploadRequestOptions) => {
    if (typeof XMLHttpRequest === 'undefined') {
      throw new Error('XMLHttpRequest is undefined');
    }

    const xhr = new XMLHttpRequest();
    const { action } = option;

    if (xhr.upload) {
      xhr.upload.addEventListener('progress', (event) => {
        const progressEvent = event as unknown as UploadProgressEvent;
        progressEvent.percent = event.total > 0 ? (event.loaded / event.total) * 100 : 0;
        option.onProgress(progressEvent);
      });
    }

    xhr.addEventListener('error', () => {
      option.onError(new Error('An error occurred during upload'));
    });

    xhr.addEventListener('load', () => {
      if (xhr.status < 200 || xhr.status >= 300) {
        return option.onError(new Error('An error occurred during upload'));
      }
      option.onSuccess(getRes(xhr));
    });

    xhr.addEventListener('loadend', () => {
      option.onComplete();
    });

    xhr.open(option.method, action, true);

    if (option.withCredentials && 'withCredentials' in xhr) {
      xhr.withCredentials = true;
    }

    if (option.header) {
      if (Array.isArray(option.header)) {
        option.header.forEach((head) => {
          const headerKey = head.name;
          const headerVal = head.value;
          xhr.setRequestHeader(headerKey, headerVal);
        });
      } else {
        const headerKey = option.header.name;
        const headerVal = option.header.value;
        xhr.setRequestHeader(headerKey, headerVal);
      }
    }

    const headers = option.headers || {};
    if (headers instanceof Headers) {
      headers.forEach((value, key) => xhr.setRequestHeader(key, value));
    } else {
      for (const [key, value] of Object.entries(headers)) {
        if (value === null || typeof value === 'undefined') {
          continue;
        }
        xhr.setRequestHeader(key, String(value));
      }
    }

    xhr.send(option.file);
    return xhr;
  };

  /**
   * 文件上传成功
   */
  const handleUpdateSuccess = (file: any) => {
    const fileInfo = {
      md5: file?.data.md5,
      name: file?.data.name,
      path: file?.data.fullPath,
      size: file?.data.size,
    };
    // console.log('上传成功：', fileInfo);
    uploadLoading.value = false;
    emits('success', fileInfo);
  };
</script>
<style lang="less">
  .version-upload-file {
    .bk-upload-trigger {
      width: 150px;
      height: auto;
      background: #fff;
      border: none;
      border-radius: 0;
    }

    .bk-upload-list {
      display: none;
    }

    .bk-upload-trigger-btn {
      display: none;
    }

    .bk-upload__tip {
      display: none;
    }
  }
</style>
