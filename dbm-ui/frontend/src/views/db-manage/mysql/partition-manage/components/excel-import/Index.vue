<!--
 * 导入策略弹窗
 * 状态流转：before（上传+导入） → after（结果展示）
-->

<template>
  <BkDialog
    :esc-close="false"
    :is-show="isShow"
    :quick-close="false"
    :title="t('导入策略')"
    :width="dialogWidth"
    @closed="handleClose">
    <!-- 导入前：上传 + 导入按钮 -->
    <template v-if="phase === 'before'">
      <ImportUpload
        ref="uploadRef"
        :is-importing="isImporting"
        @file-ready="handleFileReady"
        @file-removed="handleFileRemoved"
        @uploading="isUploading = $event" />
    </template>

    <!-- 导入后：结果展示 + 操作按钮 -->
    <template v-else>
      <ImportResult
        :data="result"
        :type="resultType" />
    </template>

    <template #footer>
      <!-- 导入前 -->
      <template v-if="phase === 'before'">
        <BkButton
          :disabled="!hasFile || isUploading"
          :loading="isImporting"
          theme="primary"
          @click="handleImport">
          {{ t('导入') }}
        </BkButton>
        <BkButton
          :disabled="isImporting"
          @click="handleClose">
          {{ t('取消') }}
        </BkButton>
      </template>

      <!-- 导入后 -->
      <template v-else>
        <BkButton
          v-if="resultType !== 'success'"
          @click="handleDownloadFailed">
          <DbIcon type="import" />
          {{ t('下载失败详情') }}
        </BkButton>
        <BkButton
          v-if="resultType === 'allFail'"
          @click="handleReUpload">
          {{ t('重新上传') }}
        </BkButton>
        <BkButton
          theme="primary"
          @click="handleClose">
          {{ t('关闭') }}
        </BkButton>
      </template>
    </template>
  </BkDialog>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import { exportImportFailed, importFromExcel } from '@services/source/partitionManage';

  import ImportResult from './components/ImportResult.vue';
  import ImportUpload from './components/ImportUpload.vue';

  const emit = defineEmits<(e: 'success') => void>();

  const isShow = defineModel<boolean>('isShow');

  const { t } = useI18n();

  const phase = ref<'after' | 'before'>('before');
  const uploadRef = ref<InstanceType<typeof ImportUpload>>();
  const hasFile = ref(false);
  const rawFile = ref<File | null>(null);
  const isUploading = ref(false);
  const isImporting = ref(false);

  const result = reactive<ServiceReturnType<typeof importFromExcel>>({
    failed_count: 0,
    failed_items: [],
    success_count: 0,
  });

  const resultType = computed<'allFail' | 'partial' | 'success'>(() => {
    if (result.failed_count === 0) return 'success';
    if (result.success_count > 0) return 'partial';
    return 'allFail';
  });

  const dialogWidth = computed(() => {
    if (phase.value === 'after' && resultType.value !== 'success') return 720;
    return 480;
  });

  const resetResult = () => {
    result.failed_count = 0;
    result.failed_items = [];
    result.success_count = 0;
  };

  const handleFileReady = (file: File) => {
    hasFile.value = true;
    rawFile.value = file;
  };

  const handleFileRemoved = () => {
    hasFile.value = false;
    rawFile.value = null;
  };

  const handleImport = async () => {
    if (!rawFile.value) return;

    isImporting.value = true;
    try {
      const res = await importFromExcel(rawFile.value);
      // 校验响应有效性（防止 502 等错误被静默处理）
      if (!res || typeof res.success_count !== 'number') {
        result.failed_count = 1;
        result.failed_items = [];
        result.success_count = 0;
        phase.value = 'after';
        return;
      }
      Object.assign(result, res);
      phase.value = 'after';
    } catch {
      result.failed_count = 1;
      result.failed_items = [];
      result.success_count = 0;
      phase.value = 'after';
    } finally {
      isImporting.value = false;
    }
  };

  const handleReUpload = () => {
    phase.value = 'before';
    hasFile.value = false;
    rawFile.value = null;
    resetResult();
    nextTick(() => uploadRef.value?.reset());
  };

  const handleDownloadFailed = () => {
    exportImportFailed({
      failed_items: result.failed_items,
    });
  };

  const handleClose = () => {
    isShow.value = false;
    if (result.success_count > 0) {
      emit('success');
    }
    nextTick(() => {
      phase.value = 'before';
      hasFile.value = false;
      rawFile.value = null;
      isUploading.value = false;
      isImporting.value = false;
      resetResult();
      nextTick(() => uploadRef.value?.reset());
    });
  };
</script>

<style lang="less" scoped>
  :deep(.bk-dialog-footer) {
    display: flex;
    align-items: center;
    justify-content: flex-end;

    .bk-button + .bk-button {
      margin-left: 8px;
    }

    .db-icon {
      vertical-align: middle;
    }
  }
</style>
