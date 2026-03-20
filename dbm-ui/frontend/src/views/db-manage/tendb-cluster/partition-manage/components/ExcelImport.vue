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
  <BkDialog
    :esc-close="false"
    :is-show="isShow"
    :quick-close="false"
    :title="t('导入策略')"
    :width="600"
    @closed="handleCloseUpload">
    <div class="partition-excel-import">
      <BkAlert
        class="mb-12"
        closable
        theme="warning"
        :title="t('不存在的集群、DB、表在导入过程中将会被忽略，不执行导入')" />
      <BkUpload
        ref="uploadRef"
        accept=".xlsx,.xls"
        :before-upload="handleBeforeUpload"
        :handle-res-code="handleUploadResponse"
        :header="[
          {
            name: 'X-CSRFToken',
            value: Cookies.get('dbm_csrftoken'),
          },
        ]"
        :limit="1"
        :multiple="false"
        name="file"
        :size="2"
        :url="apiInfo.uploadLink"
        with-credentials
        @delete="handleInitExcelData"
        @done="handleDone">
        <template #tip>
          <p class="partition-excel-import-tips">
            {{ t('支持Excel文件_文件小于2M_下载') }}
            <a :href="apiInfo.downloadTemplatePath">{{ t('模板文件') }}</a>
          </p>
        </template>
        <template #file="{ file }">
          <div class="partition-excel-import-file">
            <DbIcon type="excel" />
            <div class="partition-excel-import-file-text">
              <div
                v-overflow-tips
                class="text-overflow">
                {{ file.name }}
              </div>
              <p
                v-overflow-tips
                class="text-overflow partition-excel-import-file-status"
                :class="[{ 'partition-excel-import-file-status--fail': file.status === 'fail' }]">
                <DbIcon
                  v-if="file.status === 'success'"
                  type="check-line" />
                {{ getFileStatusText(file) }}
              </p>
              <BkProgress
                v-if="file.status === 'uploading'"
                :percent="file.percentage"
                size="small"
                :title-style="{ fontSize: '12px' }" />
            </div>
            <div class="partition-excel-import-file-operations">
              <template v-if="file.status === 'fail'">
                <DbIcon
                  class="partition-excel-import-file-icon"
                  type="refresh-2"
                  @click="handleUploadRetry(file)" />
              </template>
              <DbIcon
                class="partition-excel-import-file-icon"
                type="delete"
                @click="handleUploadRemove(file)" />
            </div>
          </div>
        </template>
      </BkUpload>
      <BkAlert
        v-if="excelState.errorMessage"
        class="mt-12"
        closable
        theme="danger"
        :title="excelState.errorMessage" />
    </div>
    <template #footer>
      <BkButton @click="handleCloseUpload">
        {{ t('关闭') }}
      </BkButton>
    </template>
  </BkDialog>
</template>

<script setup lang="ts">
  import { Message } from 'bkui-vue';
  import type { UploadFile } from 'bkui-vue/lib/upload/upload.type';
  import Cookies from 'js-cookie';
  import { h } from 'vue';
  import { useI18n } from 'vue-i18n';

  import { messageError, messageSuccess } from '@utils';

  // Excel 导入接口响应类型
  interface ImportFromExcelResult {
    failed_count: number;
    failed_items: Record<string, string>[];
    success_count: number;
  }

  interface Props {
    isShow: boolean;
  }

  interface Emits {
    (e: 'update:isShow', value: boolean): void;
    (e: 'success'): void;
  }

  defineProps<Props>();

  const emits = defineEmits<Emits>();

  const { t } = useI18n();

  const uploadRef = ref();
  const excelState = reactive({
    errorMessage: '',
    result: {
      failedCount: 0,
      failedItems: [] as Record<string, string>[],
      successCount: 0,
    },
  });

  const apiInfo = {
    downloadTemplatePath: `${window.PROJECT_ENV.VITE_PUBLIC_PATH || '/'}cluster-partition-template.xlsx`,
    uploadLink: `${window.PROJECT_ENV.VITE_AJAX_URL_PREFIX || '/'}apis/partition/import_from_excel/`,
  };

  const handleInitExcelData = () => {
    excelState.errorMessage = '';
    excelState.result = {
      failedCount: 0,
      failedItems: [],
      successCount: 0,
    };
  };

  const handleBeforeUpload = () => {
    handleInitExcelData();
    return true;
  };

  const handleCloseUpload = () => {
    emits('update:isShow', false);
    // 如果有成功导入的数据，通知父组件刷新列表
    if (excelState.result.successCount > 0) {
      emits('success');
    }
    handleInitExcelData();
  };

  /**
   * 自定义文件上传返回结果
   */
  const handleUploadResponse = (res: Record<string, any>) => {
    const result = res.code === 0 && res.data?.failed_count === 0;
    excelState.result.failedCount = res.data?.failed_count ?? 0;
    excelState.result.failedItems = res.data?.failed_items ?? [];
    excelState.result.successCount = res.data?.success_count ?? 0;
    return result;
  };

  const handleDone = () => {
    const { failedCount, successCount } = excelState.result;

    // 全部导入失败
    if (failedCount > 0 && successCount === 0) {
      messageError(t('全部导入失败'));
      return;
    }

    // 全部导入成功
    if (failedCount === 0 && successCount > 0) {
      messageSuccess(t('全部导入成功'));
      return;
    }

    // 部分成功部分失败
    if (failedCount > 0 && successCount > 0) {
      Message({
        message: h('span', {}, [
          t('成功导入'),
          ' ',
          h('span', { style: { color: '#2dcb56', fontWeight: 'bold' } }, successCount),
          ' ',
          t('条'),
          '，',
          t('失败'),
          ' ',
          h('span', { style: { color: '#ea3636', fontWeight: 'bold' } }, failedCount),
          ' ',
          t('条'),
        ]),
        theme: 'warning',
      });
    }
  };

  /**
   * 获取上传文件返回结果提示文案
   */
  const getFileStatusText = (file: UploadFile) => {
    if (file.status === 'fail') {
      const response = file.response as { data?: ImportFromExcelResult };

      if (response?.data?.failed_count && response.data.failed_count > 0) {
        excelState.errorMessage = response.data.failed_items.map((item) => item.error).join('、');
        return t('部分数据导入失败');
      }

      return file.statusText || t('上传失败');
    }

    if (file.status === 'uploading') {
      return '';
    }

    const response = file.response as { data?: ImportFromExcelResult };
    if (response?.data?.success_count && response.data.success_count > 0) {
      return t('导入成功 n 条', { n: response.data.success_count });
    }

    return t('上传成功');
  };

  /**
   * 文件上传重试
   */
  const handleUploadRetry = (file: UploadFile) => {
    uploadRef.value?.handleRetry(file);
  };

  /**
   * 移除文件
   */
  const handleUploadRemove = (file: UploadFile) => {
    uploadRef.value?.handleRemove(file);
  };
</script>

<style lang="less" scoped>
  @import '@styles/mixins.less';

  .partition-excel-import {
    padding-bottom: 40px;
    font-size: @font-size-mini;

    .partition-excel-import-tips {
      padding-top: 4px;
    }

    .partition-excel-import-file {
      overflow: hidden;
      font-size: @font-size-mini;
      flex: 1;
      .flex-center();

      .db-icon-excel {
        margin-right: 16px;
        font-size: 26px;
        color: @success-color;
      }

      .partition-excel-import-file-text {
        flex: 1;
        overflow: hidden;
      }

      .partition-excel-import-file-status {
        color: @success-color;
      }

      .partition-excel-import-file-status--fail {
        color: @danger-color;
      }

      .partition-excel-import-file-icon {
        margin-left: 12px;
        font-size: @font-size-normal;
        cursor: pointer;
      }
    }
  }
</style>
