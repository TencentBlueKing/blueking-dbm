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
      accept=".xlsx,.xls"
      :custom-request="handleCustomUpload"
      :disabled="isImporting"
      file-icon="excel"
      :limit="1"
      :size="2"
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
  import { useI18n } from 'vue-i18n';
  import * as XLSX from 'xlsx';

  import DbUpload, { type UploadFile, type UploadRequestOptions } from '@components/db-upload';

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

  /** Excel 最大行数限制 */
  const MAX_EXCEL_ROWS = 1000;

  const { t } = useI18n();

  const uploadRef = ref();
  const uploadKey = ref(0);

  const templatePath = `${window.PROJECT_ENV.VITE_PUBLIC_PATH}cluster-partition-template.xlsx`;

  /** 模拟进度事件 */
  const mockProgressEvent = (percent: number): ProgressEvent =>
    ({
      lengthComputable: true,
      loaded: percent,
      total: 100,
    }) as ProgressEvent;

  /** 纯前端解析 Excel 文件，校验行数 */
  const parseExcelFile = (file: File): Promise<unknown[]> => {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = (e) => {
        try {
          const data = new Uint8Array(e.target?.result as ArrayBuffer);
          const workbook = XLSX.read(data, { type: 'array' });
          // 取第一个 sheet 的数据
          const firstSheetName = workbook.SheetNames[0];
          const worksheet = workbook.Sheets[firstSheetName];
          const jsonData = XLSX.utils.sheet_to_json(worksheet, { header: 1 });

          // 校验行数（含表头）
          if (jsonData.length > MAX_EXCEL_ROWS + 1) {
            reject(new Error(t('Excel文件行数超过限制_最大允许_n_行', [MAX_EXCEL_ROWS])));
            return;
          }

          resolve(jsonData);
        } catch {
          reject(new Error(t('Excel文件解析失败')));
        }
      };
      reader.onerror = () => {
        reject(new Error(t('Excel文件读取失败')));
      };
      reader.readAsArrayBuffer(file);
    });
  };

  /** 自定义上传处理：纯前端解析 + 校验 */
  const handleCustomUpload = (options: UploadRequestOptions): void => {
    options.onProgress(mockProgressEvent(10));

    parseExcelFile(options.file)
      .then((jsonData) => {
        options.onProgress(mockProgressEvent(100));
        // 上传成功，将解析后的 Excel 数据传给父组件
        options.onSuccess(jsonData);
      })
      .catch((err: Error) => {
        options.onError(err);
      });
  };

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
  .upload-tip {
    padding-top: 4px;
  }
</style>
