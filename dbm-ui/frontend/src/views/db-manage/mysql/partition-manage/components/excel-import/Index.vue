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
  const filePath = ref('');
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

  const handleFileReady = (path: string) => {
    hasFile.value = true;
    filePath.value = path;
  };

  const handleFileRemoved = () => {
    hasFile.value = false;
    filePath.value = '';
  };

  const handleImport = async () => {
    isImporting.value = true;
    try {
      const res = await importFromExcel({ file_path: filePath.value });
      Object.assign(result, res);
      phase.value = 'after';
    } catch {
      phase.value = 'after';
    } finally {
      isImporting.value = false;
    }
  };

  const handleReUpload = () => {
    phase.value = 'before';
    hasFile.value = false;
    filePath.value = '';
    resetResult();
    nextTick(() => uploadRef.value?.reset());
  };

  const handleDownloadFailed = () => {
    exportImportFailed({
      failed_items: result.failed_items.map((item) => ({
        error: item.error,
        row: item.row,
      })),
      file_path: filePath.value,
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
      filePath.value = '';
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
