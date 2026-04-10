<!--
 * 导入策略 - 上传阶段
 * 状态：待上传 / 已上传 / 导入中
-->

<template>
  <div class="import-upload">
    <BkAlert
      class="mb-12"
      closable
      theme="warning"
      :title="t('不存在的集群、DB、表在导入过程中将会被忽略，不执行导入')" />
    <BkUpload
      ref="uploadRef"
      accept=".xlsx,.xls"
      :before-upload="handleBeforeUpload"
      :disabled="isImporting"
      :form-data-attributes="[{ name: 'bk_biz_id', value: String(bizId) }]"
      :handle-res-code="handleUploadResponse"
      :header="[{ name: 'X-CSRFToken', value: Cookies.get('dbm_csrftoken') }]"
      :limit="1"
      :multiple="false"
      name="file"
      :size="2"
      :url="uploadUrl"
      with-credentials
      @delete="handleDeleteFile"
      @done="handleUploadDone">
      <template #tip>
        <p class="upload-tip">
          {{ t('支持Excel文件_文件小于2M_下载') }}
          <a :href="templatePath">{{ t('模板文件') }}</a>
        </p>
      </template>
      <template #file="{ file }">
        <div class="uploaded-file">
          <DbIcon type="excel" />
          <div class="uploaded-file-info">
            <div
              v-overflow-tips
              class="text-overflow">
              {{ file.name }}
            </div>
            <p
              v-if="file.status !== 'uploading'"
              class="uploaded-file-status"
              :class="{ 'is-fail': file.status === 'fail' }">
              <DbIcon
                v-if="file.status === 'success'"
                type="check-line" />
              {{ file.status === 'success' ? t('上传成功') : file.statusText || t('上传失败') }}
            </p>
            <BkProgress
              v-if="file.status === 'uploading'"
              :percent="file.percentage"
              size="small"
              :title-style="{ fontSize: '12px' }" />
          </div>
          <div class="uploaded-file-actions">
            <DbIcon
              v-if="file.status === 'fail'"
              class="action-icon"
              type="refresh-2"
              @click="handleRetry(file)" />
            <DbIcon
              class="action-icon"
              type="delete"
              @click="uploadRef?.handleRemove(file)" />
          </div>
        </div>
      </template>
    </BkUpload>
  </div>
</template>

<script setup lang="ts">
  import Cookies from 'js-cookie';
  import urlJoin from 'url-join';
  import { useI18n } from 'vue-i18n';

  defineProps<{
    isImporting?: boolean;
  }>();

  const emit = defineEmits<{
    (e: 'file-ready', filePath: string): void;
    (e: 'file-removed'): void;
    (e: 'uploading', val: boolean): void;
  }>();

  const { t } = useI18n();

  const uploadRef = ref();
  const filePath = ref('');

  const bizId = window.PROJECT_CONFIG.BIZ_ID;
  const uploadUrl = urlJoin(window.PROJECT_ENV.VITE_AJAX_URL_PREFIX, `/apis/partition/upload_import_file/`);
  const templatePath = `${window.PROJECT_ENV.VITE_PUBLIC_PATH}cluster-partition-template.xlsx`;

  const handleBeforeUpload = () => {
    emit('uploading', true);
    return true;
  };

  const handleUploadResponse = (res: Record<string, any>) => {
    emit('uploading', false);
    if (res.code === 0) {
      filePath.value = res.data?.file_path ?? '';
      return true;
    }
    return false;
  };

  const handleUploadDone = () => {
    emit('uploading', false);
    emit('file-ready', filePath.value);
  };

  const handleDeleteFile = () => {
    emit('uploading', false);
    filePath.value = '';
    emit('file-removed');
  };

  const handleRetry = (file: any) => {
    emit('uploading', true);
    uploadRef.value?.handleRetry(file);
  };

  const reset = () => {
    uploadRef.value?.handleRemoveAll?.();
  };

  defineExpose({ reset });
</script>

<style lang="less" scoped>
  @import '@styles/mixins.less';

  .upload-tip {
    padding-top: 4px;
  }

  .uploaded-file {
    display: flex;
    align-items: center;
    flex: 1;
    overflow: hidden;
    font-size: @font-size-mini;

    .db-icon-excel {
      margin-right: 16px;
      font-size: 26px;
      color: @success-color;
    }
  }

  .uploaded-file-info {
    flex: 1;
    overflow: hidden;
  }

  .uploaded-file-status {
    color: @success-color;

    &.is-fail {
      color: @danger-color;
    }
  }

  .uploaded-file-actions {
    display: flex;
    align-items: center;
  }

  .action-icon {
    margin-left: 12px;
    font-size: @font-size-normal;
    cursor: pointer;
  }
</style>
