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
    :width="600">
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
        :url="apiInfo.uploadLink"
        with-credentials
        @delete="handleInitExcelData">
        <template #tip>
          <p class="excel-authorize-tips">
            {{ t('支持Excel文件_文件小于2M_下载') }}
            <a :href="apiInfo.downloadTemplatePath">{{ t('模板文件') }}</a>
          </p>
        </template>
        <template #file="{ file }">
          <div class="excel-authorize-file">
            <DbIcon type="excel" />
            <div class="excel-authorize-file-text">
              <div
                v-overflow-tips
                class="text-overflow">
                {{ file.name }}
              </div>
              <p
                v-overflow-tips
                class="text-overflow excel-authorize-file-status"
                :class="[
                  { 'excel-authorize-file-status--fail': file.status === 'fail' }
                ]">
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
            <div class="excel-authorize-file-operations">
              <template v-if="file.status === 'fail'">
                <a
                  v-if="file.response?.data?.excel_url && file.response?.data?.pre_check === false"
                  :href="file.response.data.excel_url">
                  {{ t('下载错误模板') }}
                </a>
                <DbIcon
                  class="excel-authorize-file-icon"
                  type="refresh-2"
                  @click="handleUploadRetry(file)" />
              </template>
              <DbIcon
                class="excel-authorize-file-icon"
                type="delete"
                @click="handleUploadRemove(file)" />
            </div>
          </div>
        </template>
      </BkUpload>
    </div>
    <template #footer>
      <BkButton
        class="mr-8"
        :disabled="!excelState.importable"
        :loading="excelState.isLoading"
        theme="primary"
        @click="handleConfirmImport">
        {{ t('导入') }}
      </BkButton>
      <BkButton
        :disabled="excelState.isLoading"
        @click="handleCloseUpload">
        {{ t('取消') }}
      </BkButton>
    </template>
  </BkDialog>
</template>

<script setup lang="ts">
  import type { UploadFile } from 'bkui-vue/lib/upload/upload.type';
  import { useI18n } from 'vue-i18n';

  import { createTicket } from '@services/source/ticket';
  import type { BaseResponse } from '@services/types';
  import type {
    AuthorizePreCheckData,
    AuthorizePreCheckResult,
  } from '@services/types/permission';

  import { useTicketMessage } from '@hooks';

  import { useGlobalBizs } from '@stores';

  import {
    ClusterTypes,
    type ClusterTypesValues,
    TicketTypes,
    type TicketTypesStrings,
  } from '@common/const';

  interface Props {
    isShow: boolean,
    clusterType: ClusterTypesValues,
    ticketType?: TicketTypesStrings
  }

  interface Emits {
    (e: 'update:isShow', value: boolean): void
  }

  const props = withDefaults(defineProps<Props>(), {
    ticketType: TicketTypes.MYSQL_EXCEL_AUTHORIZE_RULES,
  });
  const emits = defineEmits<Emits>();

  const { t } = useI18n();
  const globalBizsStore = useGlobalBizs();
  const ticketMessage = useTicketMessage();

  const basePath = window.PROJECT_ENV.VITE_PUBLIC_PATH ? window.PROJECT_ENV.VITE_PUBLIC_PATH : '/';
  const excelState = reactive({
    isLoading: false,
    importable: false,
    precheck: {
      uid: '',
      excelUrl: '',
      authorizeDataList: [] as AuthorizePreCheckData[],
    },
  });
  const uploadRef = ref();

  const apiInfo = computed(() => {
    if ([ClusterTypes.MONGO_REPLICA_SET, ClusterTypes.MONGO_SHARED_CLUSTER].includes(props.clusterType)) {
      return {
        uploadLink: `/apis/mongodb/bizs/${globalBizsStore.currentBizId}/permission/authorize/pre_check_excel_rules/`,
        downloadTemplatePath: `${basePath}mongo_cluster_authorize.xlsx`,
      };
    }

    return {
      uploadLink: `/apis/mysql/bizs/${globalBizsStore.currentBizId}/permission/authorize/pre_check_excel_rules/`,
      downloadTemplatePath: `${basePath}cluster-authorize.xlsx`,
    };
  });

  const handleInitExcelData = () => {
    excelState.importable = false;
    excelState.precheck = {
      uid: '',
      excelUrl: '',
      authorizeDataList: [] as AuthorizePreCheckData[],
    };
  };

  const handleCloseUpload = () => {
    emits('update:isShow', false);
    handleInitExcelData();
  };

  const handleConfirmImport = () => {
    const params = {
      bk_biz_id: globalBizsStore.currentBizId,
      details: {
        authorize_uid: excelState.precheck.uid,
        excel_url: excelState.precheck.excelUrl,
        authorize_data_list: excelState.precheck.authorizeDataList.map((authorizeItem) => {
          const authorizeItemCopy = { ...authorizeItem };
          if ([ClusterTypes.MONGO_REPLICA_SET, ClusterTypes.MONGO_SHARED_CLUSTER].includes(props.clusterType)) {
            delete authorizeItemCopy.source_ips;
          }
          return authorizeItemCopy;
        }),
      },
      remark: '',
      ticket_type: props.ticketType,
    };
    excelState.isLoading = true;
    createTicket(params)
      .then((res) => {
        ticketMessage(res.id);
        handleCloseUpload();
      })
      .finally(() => {
        excelState.isLoading = false;
      });
  };

  /**
   * 自定义文件上传返回结果
   */
  const handleUploadResponse = (res: BaseResponse<AuthorizePreCheckResult>) => {
    const result = res.code === 0 ? res.data.pre_check : false;
    excelState.importable = result;
    excelState.precheck.uid = res.data?.authorize_uid ?? '';
    excelState.precheck.excelUrl = res.data?.excel_url ?? '';
    excelState.precheck.authorizeDataList = res.data?.authorize_data_list ?? [];
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
</script>

<style lang="less" scoped>
@import "@styles/mixins.less";

.excel-authorize {
  padding-bottom: 40px;
  font-size: @font-size-mini;

  .excel-authorize-tips {
    padding-top: 4px;
  }

  .excel-authorize-file {
    overflow: hidden;
    font-size: @font-size-mini;
    flex: 1;
    .flex-center();

    .db-icon-excel {
      margin-right: 16px;
      font-size: 26px;
      color: @success-color;
    }

    .excel-authorize-file-text {
      flex: 1;
      overflow: hidden;
    }

    .excel-authorize-file-status {
      color: @success-color;

      .excel-authorize-file-status--fail {
        color: @danger-color;
      }
    }

    .excel-authorize-file-icon {
      margin-left: 12px;
      font-size: @font-size-normal;
      cursor: pointer;
    }
  }
}
</style>
