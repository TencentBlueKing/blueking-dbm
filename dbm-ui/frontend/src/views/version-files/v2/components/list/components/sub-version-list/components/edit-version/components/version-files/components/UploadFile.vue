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
  <DbUpload
    ref="uploadRef"
    class="version-upload-file"
    :duplicate-checker="handleDuplicateCheck"
    :options="uploadOptions"
    @error="handleUploadError"
    @success="handleUpdateSuccess">
    <template #trigger>
      <BkButton
        v-bk-tooltips="{
          content: t('请先设置版本号'),
          disabled: !!version,
        }"
        :disabled="!version"
        text
        theme="primary">
        <DbIcon type="plus-fill" />
        <span style="margin-left: 4px; font-size: 12px">{{ t('点击上传文件') }}</span>
      </BkButton>
    </template>
  </DbUpload>
</template>
<script setup lang="ts">
  import type { Ref } from 'vue';
  import { useI18n } from 'vue-i18n';

  import type { UploadFile } from '@components/db-upload';
  import DbUpload from '@components/db-upload';

  interface Props {
    dbType: string;
    pkgType: string;
    uploadedFileNames: string[];
    version: string;
  }

  type Emits = {
    (e: 'error', fileName: string, errMsg: string): void;
    (
      e: 'success',
      fileInfo: {
        md5: string;
        name: string;
        path: string;
        size: number;
        tempId: string;
      },
    ): void;
  };

  interface Exposes {
    triggerFileInput: () => void;
    uploadRef: Ref<InstanceType<typeof DbUpload> | undefined>;
  }

  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();

  const { t } = useI18n();

  const uploadRef = ref<InstanceType<typeof DbUpload>>();

  const uploadOptions = computed(() => ({
    accept: ['mysql', 'mysql-proxy'].includes(props.pkgType) ? '.tar.gz,.tar.xz' : '',
    basePath: `/${props.dbType}/${props.pkgType}/${props.version}`,
    disabled: !props.version,
    mode: 'bkrepo' as const,
    multiple: true,
    showFileList: false,
    size: 10240,
  }));

  const handleDuplicateCheck = (file: File) => props.uploadedFileNames.includes(file.name);

  const handleUpdateSuccess = (file: UploadFile) => {
    const data = (file.response as { data?: { fullPath?: string; md5?: string; name?: string; size?: number } })?.data;
    const fileInfo = {
      md5: data?.md5 ?? '',
      name: data?.name ?? '',
      path: data?.fullPath ?? '',
      size: data?.size ?? 0,
      tempId: data?.fullPath ?? '',
    };
    emits('success', fileInfo);
  };

  const handleUploadError = (file: UploadFile) => {
    emits('error', file.name, file.errMsg || t('上传失败，请重试'));
  };

  const triggerFileInput = () => {
    // Exposed: triggers the hidden file input click for replace flows
    uploadRef.value?.inputRef?.click();
  };

  defineExpose<Exposes>({
    triggerFileInput,
    uploadRef,
  });
</script>
<style lang="less">
  .version-upload-file {
    padding: 0 16px;

    .db-upload-trigger {
      position: relative;
      display: flex;
      height: auto;
      background: #fff;
      border: none;
      border-radius: 0;
    }
  }
</style>
