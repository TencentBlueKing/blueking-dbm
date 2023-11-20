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
    confirm-text="导入"
    :esc-close="false"
    :is-show="isShow"
    :quick-close="false"
    :title="t('导入授权')"
    :width="600"
    @closed="handleClosed">
    <div class="excel-authorize">
      <BkAlert
        class="mb-12"
        closable
        theme="warning"
        :title="t('重复的授权在导入过程中将会被忽略_不执行导入')" />
      <BkUpload
        ref="uploadRef"
        accept=".xlsx,.xls"
        :form-data-attributes="[{ name: 'cluster_type', value: clusterType }]"
        :handle-res-code="handleUploadResponse"
        :limit="1"
        :multiple="false"
        name="authorize_file"
        :size="2"
        :url="uploadLink"
        with-credentials
        @delete="handleInitExcelData">
        <template #tip>
          <p class="authorize-tips">
            {{ t('支持Excel文件_文件小于2M_下载') }}
            <a :href="downloadTemplate">{{ t('模板文件') }}</a>
          </p>
        </template>
        <template #file="{ file }">
          <div class="authorize-file">
            <i class="db-icon-excel" />
            <div class="authorize-file-text">
              <div
                v-overflow-tips
                class="text-overflow">
                {{ file.name }}
              </div>
              <p
                v-overflow-tips
                class="text-overflow authorize-file-status"
                :class="[
                  { 'authorize-file-status-fail': file.status === 'fail' }
                ]">
                <i
                  v-if="file.status === 'success'"
                  class="db-icon-check-line" />
                {{ getFileStatusText(file) }}
              </p>
              <BkProgress
                v-if="file.status === 'uploading'"
                :percent="file.percentage"
                size="small"
                :title-style="{ fontSize: '12px' }" />
            </div>
            <div class="authorize-file-operations">
              <template v-if="file.status === 'fail'">
                <a
                  v-if="file.response?.data?.excel_url && file.response?.data?.pre_check === false"
                  :href="file.response.data.excel_url">
                  {{ t('下载错误模板') }}
                </a>
                <i
                  class="db-icon-refresh-2 authorize-file-icon"
                  @click="handleUploadRetry(file)" />
              </template>
              <i
                class="db-icon-delete authorize-file-icon"
                @click="handleUploadRemove(file)" />
            </div>
          </div>
        </template>
      </BkUpload>
    </div>
    <template #footer>
      <BkButton
        class="mr-8"
        :disabled="!importable"
        :loading="isLoading"
        theme="primary"
        @click="handleConfirmImport">
        {{ t('导入') }}
      </BkButton>
      <BkButton
        :disabled="isLoading"
        @click="handleCloseUpload">
        {{ t('取消') }}
      </BkButton>
    </template>
  </BkDialog>
</template>

<script setup lang="ts">
  import type { UploadFile } from 'bkui-vue/lib/upload/upload.type';
  import { useI18n } from 'vue-i18n';

  import { createTicket } from '@services/ticket';
  import type { BaseResponse } from '@services/types';
  import type {
    AuthorizePreCheckData,
    AuthorizePreCheckResult,
  } from '@services/types/permission';

  import { useGlobalBizs } from '@stores';

  import {
    type ClusterTypesValues,
    TicketTypes,
  } from '@common/const';

  import { useTicketMessage } from '@/hooks';

  interface Props {
    clusterType: ClusterTypesValues
  }

  defineProps<Props>();
  const isShow = defineModel<boolean>({
    required: true,
    default: false,
  });

  const { t } = useI18n();
  const globalBizsStore = useGlobalBizs();
  const ticketMessage = useTicketMessage();

  const basePath = window.PROJECT_ENV.VITE_PUBLIC_PATH ? window.PROJECT_ENV.VITE_PUBLIC_PATH : '/';
  const downloadTemplate = `${basePath}cluster-authorize.xlsx`;
  let precheck = {
    uid: '',
    excelUrl: '',
    authorizeDataList: [] as AuthorizePreCheckData[],
  };

  const isLoading = ref(false);
  const importable = ref(false);
  const uploadRef = ref();
  const uploadLink = computed(() => `/apis/mysql/bizs/${globalBizsStore.currentBizId}/permission/authorize/pre_check_excel_rules/`);

  const handleInitExcelData = () => {
    importable.value = false;
    precheck = {
      uid: '',
      excelUrl: '',
      authorizeDataList: [] as AuthorizePreCheckData[],
    };
  };

  const handleCloseUpload = () =>  {
    isShow.value = false;
    handleInitExcelData();
  };

  const handleConfirmImport = () => {
    const params = {
      bk_biz_id: globalBizsStore.currentBizId,
      details: {
        authorize_uid: precheck.uid,
        excel_url: precheck.excelUrl,
        authorize_data_list: precheck.authorizeDataList,
      },
      remark: '',
      ticket_type: TicketTypes.MYSQL_EXCEL_AUTHORIZE_RULES,
    };
    isLoading.value = true;
    createTicket(params)
      .then((res) => {
        ticketMessage(res.id);
        handleCloseUpload();
      })
      .finally(() => {
        isLoading.value = false;
      });
  };

  /**
   * 自定义文件上传返回结果
   */
  const handleUploadResponse = (res: {
    code: number;
    data: AuthorizePreCheckResult;
    message: string;
  }) => {
    const result = res.code === 0 ? res.data.pre_check : false;
    importable.value = result;
    precheck.uid = res.data?.authorize_uid ?? '';
    precheck.excelUrl = res.data?.excel_url ?? '';
    precheck.authorizeDataList = res.data?.authorize_data_list ?? [];
    return result;
  };

  /**
   * 获取上传文件返回结果提示文案
   */
  const getFileStatusText = (file: UploadFile) => {
    if (file.status === 'fail') {
      const { response } = file;

      if ((response as BaseResponse<AuthorizePreCheckResult>)?.data?.pre_check === false) {
        return t('上传失败_文件内容校验不通过');
      }

      return file.statusText;
    }

    if (file.status === 'uploading') {
      return '';
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

  const handleClosed = () => {
    isShow.value = false;
  };
</script>

<style lang="less" scoped>
@import "@styles/mixins.less";

.excel-authorize {
  padding-bottom: 40px;
  font-size: @font-size-mini;

  .authorize-tips {
    padding-top: 4px;
  }

  .authorize-file {
    overflow: hidden;
    font-size: @font-size-mini;
    flex: 1;
    .flex-center();

    .db-icon-excel {
      margin-right: 16px;
      font-size: 26px;
      color: @success-color;
    }
  }

  .authorize-file-text {
    flex: 1;
    overflow: hidden;
  }

  .authorize-file-status {
    color: @success-color;
  }

  .authorize-file-status-fail {
    color: @danger-color;
  }

  .authorize-file-icon {
    margin-left: 12px;
    font-size: @font-size-normal;
    cursor: pointer;
  }
}
</style>
