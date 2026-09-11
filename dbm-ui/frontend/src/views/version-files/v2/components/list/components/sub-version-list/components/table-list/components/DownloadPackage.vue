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
  <BkButton
    class="ml-12"
    :loading="downloadSinglePackageLoading"
    size="small"
    text
    theme="primary"
    @click="handleDownloadClick">
    {{ t('下载') }}
  </BkButton>
  <BkDialog
    v-model:is-show="isShow"
    class="download-package-dialog"
    quick-close
    render-directive="if"
    :title="t('下载版本文件')"
    :width="480"
    @closed="handleDialogClosed">
    <div class="package-list">
      <BkCheckbox
        v-model="isSelectAll"
        @change="handleSelectAllChange">
        {{ t('全选') }}
      </BkCheckbox>
      <BkCheckboxGroup v-model="checkedPackages">
        <BkCheckbox
          v-for="item in data.packages"
          :key="item.id"
          :label="item.path">
          {{ item.name }}
        </BkCheckbox>
      </BkCheckboxGroup>
    </div>
    <template #footer>
      <BkButton
        class="mr-8"
        :disabled="!checkedPackages.length"
        :loading="downloadPackagesLoading"
        theme="primary"
        @click="handleDownloadPackages">
        {{ t('下载') }}
      </BkButton>
      <BkButton @click="handleCancel">
        {{ t('取消') }}
      </BkButton>
    </template>
  </BkDialog>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import DbVersionModel from '@services/model/version-file/db-version';
  import { batchCreateBkrepoAccessToken, createBkrepoAccessToken } from '@services/source/storage';

  import { downloadUrl, generateBkRepoDownloadUrl, messageSuccess } from '@utils';

  interface Props {
    data: DbVersionModel;
  }

  const props = defineProps<Props>();

  const { t } = useI18n();

  const isShow = ref(false);
  const downloadPackagesLoading = ref(false);
  const downloadSinglePackageLoading = ref(false);
  const checkedPackages = ref<string[]>([]);
  const isSelectAll = ref(false);

  watch(
    checkedPackages,
    () => {
      isSelectAll.value = checkedPackages.value.length === props.data.packages.length;
    },
    {
      immediate: true,
    },
  );

  const handleSelectAllChange = (isSelectAll: boolean) => {
    if (isSelectAll) {
      checkedPackages.value = props.data.packages.map((item) => item.path) || [];
    } else {
      checkedPackages.value = [];
    }
  };

  const handleDownloadClick = async () => {
    if (props.data.packages?.length > 1) {
      checkedPackages.value = props.data.packages.map((item) => item.path);
      isSelectAll.value = true;
      isShow.value = true;
      return;
    }

    try {
      downloadSinglePackageLoading.value = true;
      const tokenResult = await createBkrepoAccessToken({ file_path: props.data.packages[0].path });
      const url = generateBkRepoDownloadUrl(tokenResult);
      downloadUrl(url);
      messageSuccess(t('下载成功'));
    } finally {
      downloadSinglePackageLoading.value = false;
    }
  };

  const handleDownloadPackages = async () => {
    if (!checkedPackages.value.length) {
      return;
    }

    try {
      downloadPackagesLoading.value = true;
      const tokenResult = await batchCreateBkrepoAccessToken({ file_path_list: checkedPackages.value });
      const urls = tokenResult.map((item) => generateBkRepoDownloadUrl(item));
      urls.forEach((url) => downloadUrl(url));
      messageSuccess(t('下载成功'));
      isShow.value = false;
    } finally {
      downloadPackagesLoading.value = false;
    }
  };

  const handleCancel = () => {
    isShow.value = false;
  };

  const handleDialogClosed = () => {
    checkedPackages.value = [];
    isSelectAll.value = false;
  };
</script>

<style lang="less">
  .download-package-dialog {
    .package-list {
      display: flex;
      flex-direction: column;
      gap: 12px;
      max-height: 320px;
      overflow-y: auto;

      .bk-checkbox {
        margin-left: 0 !important;
      }

      .bk-checkbox-group {
        display: flex;
        flex-direction: column;
        gap: 12px;
      }
    }
  }
</style>
