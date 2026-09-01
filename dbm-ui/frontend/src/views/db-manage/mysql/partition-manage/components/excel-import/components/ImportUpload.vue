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
    <DbUpload
      :key="uploadKey"
      ref="uploadRef"
      :disabled="isImporting"
      :options="{
        accept: '.xlsx,.xls',
        draggable: true,
        fileIcon: 'excel',
        limit: 1,
        size: 2,
      }"
      @delete="handleDeleteFile"
      @error="handleUploadError"
      @success="handleUploadSuccess">
      <template #tip>
        <p class="upload-tip">
          {{ t('支持Excel文件_文件小于2M_下载') }}
          <a :href="templatePath">{{ t('模板文件') }}</a>
        </p>
      </template>
    </DbUpload>
  </div>
</template>

<script setup lang="ts">
  import { ref } from 'vue';
  import { useI18n } from 'vue-i18n';

  import DbUpload, { type UploadFile } from '@components/db-upload';

  interface Props {
    isImporting?: boolean;
  }

  type Emits = {
    (e: 'file-ready', file: File): void;
    (e: 'file-removed'): void;
    (e: 'uploading', val: boolean): void;
  };

  defineOptions({
    name: 'ImportUpload',
  });

  defineProps<Props>();
  const emit = defineEmits<Emits>();

  const { t } = useI18n();

  const uploadRef = ref();
  const uploadKey = ref(0);

  const templatePath = `${window.PROJECT_STATIC_PATH}cluster-partition-template.xlsx`;

  const handleUploadSuccess = (file: UploadFile) => {
    emit('uploading', false);
    emit('file-ready', file.raw);
  };

  const handleUploadError = () => {
    emit('uploading', false);
  };

  const handleDeleteFile = () => {
    emit('uploading', false);
    emit('file-removed');
  };

  const reset = () => {
    uploadRef.value?.clearFiles();
    uploadKey.value += 1;
  };

  defineExpose({ reset });
</script>

<style lang="less" scoped>
  @import '@styles/mixins.less';

  .upload-tip {
    padding-top: 4px;
  }
</style>
