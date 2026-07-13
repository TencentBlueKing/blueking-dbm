<template>
  <div
    class="version-files-table-container"
    :class="{ 'is-valid-error': isValidError }">
    <table class="version-files-table">
      <thead>
        <tr>
          <th style="width: 340px">{{ t('文件') }}</th>
          <th style="width: 152px">OS</th>
          <th style="width: 356px">{{ t('OS版本') }}</th>
          <th style="width: 80px"></th>
        </tr>
      </thead>
      <tbody>
        <VersionRow
          v-for="(item, index) in tableData"
          :key="item.rowKey"
          ref="versionRowRefs"
          :data="item"
          :err-msg="item.errMsg"
          :is-applied="isApplied"
          :is-only-one-file="isOnlyOneFile"
          :percentage="item.percentage"
          :selected-systems="selectedSystems"
          :selected-versions="selectedVersions"
          :status="item.status"
          @delete="() => handleDeleteRow(index)"
          @replace="() => handleReplaceRow(index)"
          @retry="() => handleRetryRow(index)"
          @system-os-type-change="handleOsTypeChange"
          @system-os-version-change="handleOsVersionChange" />
      </tbody>
    </table>
    <UploadFile
      ref="uploadFileRef"
      :db-type="dbType"
      :pkg-type="pkgType"
      :uploaded-file-names="uploadedFileNames"
      :version="version" />
  </div>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import { random } from '@utils';

  import UploadFile from './components/UploadFile.vue';
  import VersionRow from './components/VersionRow.vue';

  type RowStatus = 'uploading' | 'staged' | 'failed';

  interface TableRow {
    errMsg?: string;
    id?: number;
    md5: string;
    name: string;
    path: string;
    percentage: number;
    permit_os?: string[];
    permit_os_type?: string;
    rowKey: string;
    size: number;
    status?: RowStatus;
    tempId: string;
    uid: number;
  }

  interface Props {
    data?: (Omit<TableRow, 'rowKey' | 'percentage' | 'uid' | 'status'>)[];
    dbType: string;
    isApplied?: boolean;
    pkgType: string;
    version: string;
  }

  type Emits = (e: 'valueChange') => void;

  interface Exposes {
    getValue: () => ReturnType<InstanceType<typeof VersionRow>['getValue']>[] | string;
  }

  const props = withDefaults(defineProps<Props>(), {
    data: undefined,
    isApplied: false,
  });

  const emits = defineEmits<Emits>();

  const { t } = useI18n();

  const uploadFileRef = ref<InstanceType<typeof UploadFile>>();
  const versionRowRefs = ref<InstanceType<typeof VersionRow>[]>([]);
  const selectedSystems = ref<Set<string>>(new Set());
  const selectedVersions = ref<Record<string, Set<string>>>({});
  const isValidError = ref(false);
  const tableData = ref<TableRow[]>([]);
  const uploadSyncedUids = new Set<number>();

  const uploadedFileNames = computed(() =>
    tableData.value.filter((item) => item.status === 'staged' || !item.status).map((item) => item.name),
  );
  const isOnlyOneFile = computed(
    () => tableData.value.filter((item) => item.status === 'staged' || !item.status).length === 1,
  );

  // Watch existing data from parent (edit mode)
  watch(
    () => props.data,
    () => {
      const existingRows = props.data
        ? props.data.map((item) => ({
            ...item,
            percentage: 100,
            rowKey: random(),
            status: undefined as RowStatus | undefined,
            uid: 0,
          }))
        : [];
      tableData.value = existingRows;
    },
    { immediate: true },
  );

  // Watch DbUpload's internal fileList for upload progress
  watch(
    () => {
      const list = uploadFileRef.value?.uploadRef?.fileList;
      if (!list || list.length === 0) return [];
      return list.map((f) => ({
        errMsg: f.errMsg,
        name: f.name,
        percentage: f.percentage,
        response: f.response,
        size: f.size,
        status: f.status,
        uid: f.uid,
      }));
    },
    (snapshots) => {
      if (!snapshots) return;

      let changed = false;

      snapshots.forEach((snap) => {
        // Skip uids we've already synced as success
        if (uploadSyncedUids.has(snap.uid)) return;

        const existingRowIndex = tableData.value.findIndex((row) => row.uid === snap.uid);

        if (snap.status === 'uploading') {
          changed = true;
          if (existingRowIndex >= 0) {
            // Update progress for existing upload row
            tableData.value[existingRowIndex].percentage = snap.percentage || 0;
          } else {
            // New upload
            tableData.value.push({
              errMsg: undefined,
              md5: '',
              name: snap.name || '',
              path: '',
              percentage: snap.percentage || 0,
              rowKey: random(),
              size: snap.size || 0,
              status: 'uploading',
              tempId: '',
              uid: snap.uid,
            });
          }
        } else if (snap.status === 'success') {
          changed = true;
          if (existingRowIndex >= 0) {
            const row = tableData.value[existingRowIndex];
            const responseData = (snap.response as { data?: { fullPath?: string; md5?: string; name?: string; size?: number } })?.data;
            row.md5 = responseData?.md5 ?? '';
            row.name = responseData?.name ?? snap.name;
            row.path = responseData?.fullPath ?? '';
            row.size = responseData?.size ?? snap.size;
            row.tempId = responseData?.fullPath ?? '';
            row.status = 'staged';
            row.percentage = 100;
            row.errMsg = undefined;
          }
          uploadSyncedUids.add(snap.uid);
          // Clean up from upload list
          nextTick(() => {
            const fileEntry = uploadFileRef.value?.uploadRef?.fileList?.find((f) => f.uid === snap.uid);
            if (fileEntry) uploadFileRef.value?.uploadRef?.handleRemove(fileEntry);
          });
        } else if (snap.status === 'fail') {
          changed = true;
          if (existingRowIndex >= 0) {
            const row = tableData.value[existingRowIndex];
            row.status = 'failed';
            row.errMsg = snap.errMsg || t('上传失败，请重试');
            row.percentage = 0;
          }
          // Keep FAIL entries in fileList for retry, but mark as synced
          uploadSyncedUids.add(snap.uid);
        }
      });

      if (changed) {
        emits('valueChange');
      }
    },
    { deep: true, immediate: true },
  );

  const handleOsTypeChange = (isInit: boolean) => {
    if (!isInit) {
      emits('valueChange');
    }
    selectedSystems.value.clear();
    selectedVersions.value = {};
    versionRowRefs.value.forEach((item) => {
      const system = item.getSelectedSystem();
      if (!system) {
        return;
      }

      if (!selectedVersions.value[system]) {
        selectedVersions.value[system] = new Set();
      }
      selectedSystems.value.add(system);
      const versions = item.getSelectedVersions();
      versions.forEach((version) => {
        selectedVersions.value[system].add(version);
      });
    });
  };

  const handleOsVersionChange = () => {
    emits('valueChange');
  };

  const handleDeleteRow = (index: number) => {
    const row = tableData.value[index];
    // If this was an uploading row, clean up from DbUpload's fileList
    if (row.uid && row.status !== 'staged' && row.status !== undefined) {
      const fileEntry = uploadFileRef.value?.uploadRef?.fileList?.find((f) => f.uid === row.uid);
      if (fileEntry) {
        uploadFileRef.value?.uploadRef?.handleRemove(fileEntry);
      }
      uploadSyncedUids.delete(row.uid);
    }
    tableData.value.splice(index, 1);
    if (tableData.value.length === 0) {
      selectedSystems.value.clear();
      selectedVersions.value = {};
    }
    emits('valueChange');
  };

  const handleReplaceRow = (index: number) => {
    // Remove the old row first, then trigger file input
    // The new upload will appear as a fresh row via the fileList watcher
    const row = tableData.value[index];
    // Clean up OS tracking for the old row
    const oldOsType = row.permit_os_type || '';
    if (oldOsType) {
      selectedSystems.value.delete(oldOsType);
    }
    if (oldOsType && selectedVersions.value[oldOsType]) {
      (row.permit_os || []).forEach((v: string) => {
        selectedVersions.value[oldOsType]?.delete(v);
      });
    }
    tableData.value.splice(index, 1);
    // Trigger file input on DbUpload
    uploadFileRef.value?.uploadRef?.inputRef?.click();
  };

  const handleRetryRow = (index: number) => {
    const row = tableData.value[index];
    if (!row.uid) return;

    // Find the original upload entry in fileList
    const fileEntry = uploadFileRef.value?.uploadRef?.fileList?.find((f) => f.uid === row.uid);
    if (fileEntry) {
      // Reset row state
      tableData.value[index] = {
        ...row,
        errMsg: undefined,
        percentage: 0,
        rowKey: random(),
        status: 'uploading',
      };
      // Allow the watch to process this uid again
      uploadSyncedUids.delete(row.uid);
      // Trigger retry in DbUpload
      nextTick(() => {
        uploadFileRef.value?.uploadRef?.handleRetry(fileEntry);
      });
    }
    emits('valueChange');
  };

  defineExpose<Exposes>({
    getValue() {
      isValidError.value = false;

      // Only count staged rows (or rows with no status, i.e., pre-existing data)
      const stagedRows = tableData.value.filter((item) => !item.status || item.status === 'staged');

      if (tableData.value.length === 0) {
        isValidError.value = true;
        return t('请至少添加 1 个版本文件');
      }

      if (tableData.value.some((item) => item.status === 'uploading')) {
        isValidError.value = true;
        return t('请等待文件上传完成');
      }

      if (tableData.value.some((item) => item.status === 'failed')) {
        isValidError.value = true;
        return t('存在失败文件，请重试或删除');
      }

      if (stagedRows.length === 0) {
        isValidError.value = true;
        return t('请至少添加 1 个版本文件');
      }

      const filesInfo = versionRowRefs.value.map((item) => item.getValue());
      if (filesInfo.some((item) => !item.permit_os.length || !item.permit_os_type)) {
        isValidError.value = true;
        return t('请补全版本文件信息');
      }

      return filesInfo;
    },
  });
</script>
<style lang="less">
  .version-files-table-container {
    width: 100%;
    border: 1px solid transparent;
    box-sizing: content-box;

    &.is-valid-error {
      border-color: #ed3f14;
    }

    .version-files-table {
      width: 100%;
      font-family: MicrosoftYaHei, sans-serif;
      font-size: 12px;
      table-layout: fixed;

      thead {
        border-bottom: 4px solid #fff;
      }

      th {
        padding-left: 16px;
        margin-bottom: 4px;
        font-weight: normal;
        color: #313238;
        background: #f0f1f5;
      }

      tbody {
        tr {
          border-bottom: 10px solid #fff;
        }
      }

      td {
        padding: 5px 16px;
        background: #f5f7fa;
      }
    }
  }
</style>
