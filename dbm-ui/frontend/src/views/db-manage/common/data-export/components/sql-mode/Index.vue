<!--
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 *
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 *
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 *
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed
 * on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for
 * the specific language governing permissions and limitations under the License.
-->

<template>
  <BkLoading :loading="isReading">
    <DbForm
      ref="formRef"
      class="sql-export-form mb-20"
      form-type="vertical"
      :model="formModel">
      <FormItemWithHint
        :label="t('源集群')"
        :model="formData.clusterId"
        property="clusterId"
        required>
        <ClusterSelect
          v-model="formData.clusterId"
          :cluster-types="clusterTypesByDBType[dbType]"
          :db-type="dbType"
          :placeholder="t('请选择源集群')" />
      </FormItemWithHint>
      <DbFormItem
        :label="t('查询 SQL')"
        property="querySql"
        required
        :rules="sqlRules">
        <BkRadioGroup
          v-model="formData.sqlSource"
          class="sql-export-source-selector">
          <BkRadioButton label="manual">{{ t('手动输入') }}</BkRadioButton>
          <BkRadioButton label="file">{{ t('SQL 文件') }}</BkRadioButton>
        </BkRadioGroup>
        <div
          class="sql-export-editor"
          :class="{ 'is-dragover': isDragging }"
          @dragleave.self="isDragging = false"
          @dragover.prevent="isDragging = formData.sqlSource === 'file'"
          @drop.prevent="handleDropFile">
          <div
            v-if="formData.sqlSource === 'file' && formData.file.name"
            class="sql-export-file-header">
            <span
              class="sql-export-file-name"
              :title="formData.file.name">
              {{ formData.file.name }}
            </span>
            <span class="sql-export-file-meta">{{ fileSizeDisplay }}</span>
            <span class="sql-export-file-meta">{{ t('只读') }}</span>
            <div class="sql-export-file-actions">
              <BkButton
                class="sql-export-upload-button"
                size="small"
                @click="fileInputRef?.click()">
                {{ t('重新上传') }}
              </BkButton>
              <BkButton
                class="ml-8"
                size="small"
                text
                theme="primary"
                @click="handleRemoveFile">
                {{ t('删除') }}
              </BkButton>
            </div>
          </div>
          <template v-if="formData.sqlSource === 'manual'">
            <textarea
              v-model="formData.manualSql"
              :aria-label="t('查询 SQL')"
              class="sql-export-body"
              :placeholder="t('请输入查询 SQL，例如\nUSE game_main;\nSELECT id, name FROM user WHERE id < 100;')"
              :spellcheck="false" />
            <span class="sql-export-count">{{ manualSizeDisplay }}</span>
          </template>
          <pre
            v-else-if="formData.file.name"
            class="sql-export-body"
            >{{ formData.file.content }}</pre>
          <div
            v-else
            class="sql-export-empty">
            <div>
              <DbIcon
                class="mr-4"
                type="attention" />
              {{ t('请选择本地 SQL 文件') }}
            </div>
            <BkButton
              class="sql-export-upload-button"
              size="small"
              @click="fileInputRef?.click()">
              <DbIcon
                class="mr-4"
                type="import" />
              {{ t('点击上传') }}
            </BkButton>
            <span class="sql-export-file-hint">{{ t('支持拖拽；仅支持 .sql 文件，UTF-8 编码') }}</span>
          </div>
        </div>
        <div class="sql-export-helper">
          {{ t('语句仅支持 SELECT 与 USE，以分号分隔。表名写为 库.表，或在语句前用 USE 指定库。') }}
        </div>
        <BkAlert
          v-if="formData.sqlSource === 'file' && fileError"
          class="mt-8"
          theme="danger"
          :title="fileError" />
      </DbFormItem>
      <TicketPayload
        v-model="formData.payload"
        :width="560" />
    </DbForm>
  </BkLoading>
  <input
    ref="fileInputRef"
    accept=".sql"
    hidden
    type="file"
    @change="handleSelectFile" />
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import type { Mysql } from '@services/model/ticket/ticket';
  import { getFileContent } from '@services/source/storage';

  import { useTicketDetail } from '@hooks';

  import { clusterTypesByDBType, DBTypes, TicketTypes } from '@common/const';

  import { createBkrepoHeaders, createBkrepoUploadUrl, createXhrUpload } from '@components/db-upload/utils/bkrepo';
  import FormItemWithHint from '@components/form-item-with-hint/Index.vue';

  import ClusterSelect from '@views/db-manage/common/toolbox-field/cluster-select/Index.vue';
  import TicketPayload, {
    createTicketPayload,
  } from '@views/db-manage/common/toolbox-field/form-item/ticket-payload/Index.vue';

  import { random } from '@utils';

  interface Props {
    dbType: DBTypes.MYSQL | DBTypes.TENDBCLUSTER;
    restoreTicket: boolean;
  }

  const props = defineProps<Props>();

  const { t } = useI18n();
  const route = useRoute();
  const formRef = useTemplateRef('formRef');
  const fileInputRef = useTemplateRef<HTMLInputElement>('fileInputRef');
  // 与变更 SQL 执行保持同一大小限制。
  const maxSqlSize = 1073741824;
  const isReading = ref(false);
  const fileError = ref('');
  const isDragging = ref(false);
  let readVersion = 0;

  const formData = reactive({
    charset: 'default',
    clusterId: route.query.clusterId ? Number(route.query.clusterId) : (undefined as unknown as number),
    file: { content: '', name: '', path: '' },
    manualSql: '',
    payload: createTicketPayload(),
    resultFormat: 'txt' as 'txt' | 'csv',
    sqlSource: 'manual' as 'manual' | 'file',
  });

  const querySql = computed(() => (formData.sqlSource === 'manual' ? formData.manualSql : formData.file.content));
  const formModel = computed(() => ({ ...formData, querySql: querySql.value }));
  const formatSqlSize = (content: string) => {
    const size = new Blob([content]).size;
    if (size < 1024) return `${size} B`;
    if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)} KB`;
    return `${(size / (1024 * 1024)).toFixed(1)} MB`;
  };
  const fileSizeDisplay = computed(() => formatSqlSize(formData.file.content));
  const manualSizeDisplay = computed(() => formatSqlSize(formData.manualSql));
  const sqlRules = [
    { message: t('查询 SQL 不能为空'), validator: () => Boolean(querySql.value.trim()) },
    {
      message: t('文件上传失败——文件大小超过限制（最大为1GB）'),
      validator: () => new Blob([querySql.value]).size <= maxSqlSize,
    },
  ];

  const ticketType = props.dbType === DBTypes.MYSQL ? TicketTypes.MYSQL_DUMP_DATA : TicketTypes.TENDBCLUSTER_DUMP_DATA;
  useTicketDetail<Mysql.DumpData>(ticketType, {
    onSuccess({ details, ...ticketDetail }) {
      if (!props.restoreTicket || details.export_mode !== 'sql') return;
      Object.assign(formData, {
        charset: details.charset || 'default',
        clusterId: details.cluster_id,
        payload: createTicketPayload(ticketDetail),
        resultFormat: details.result_format || 'txt',
        // 协议未返回原始来源，克隆先按已存 SQL 文件回填；待 PEER 确认。
        sqlSource: 'file',
      });
      const version = ++readVersion;
      isReading.value = true;
      getFileContent({ file_path: `${details.sql_path}/${details.sql_filename}` })
        .then(({ content }) => {
          if (version !== readVersion) return;
          formData.file = { content, name: details.sql_filename, path: `${details.sql_path}/${details.sql_filename}` };
          formData.manualSql = content;
        })
        .catch(() => {
          if (version === readVersion) fileError.value = t('SQL 文件内容读取失败，请重新上传');
        })
        .finally(() => {
          if (version === readVersion) isReading.value = false;
        });
    },
  });

  const handleSelectFile = (event: Event) => {
    const input = event.target as HTMLInputElement;
    const file = input.files?.[0];
    input.value = '';
    if (file) readSqlFile(file);
  };

  const handleDropFile = (event: DragEvent) => {
    isDragging.value = false;
    if (formData.sqlSource !== 'file') return;
    const files = event.dataTransfer?.files;
    if (!files?.length) return;
    if (files.length > 1) {
      fileError.value = t('仅支持上传一个 SQL 文件');
      return;
    }
    readSqlFile(files[0]);
  };

  const readSqlFile = async (file: File) => {
    fileError.value = '';
    if (!file.name.endsWith('.sql')) {
      fileError.value = t('仅支持 .sql 文件');
      return;
    }
    if (file.size > maxSqlSize) {
      fileError.value = t('文件上传失败——文件大小超过限制（最大为1GB）');
      return;
    }
    const version = ++readVersion;
    isReading.value = true;
    try {
      const content = new TextDecoder('utf-8', { fatal: true }).decode(await file.arrayBuffer());
      if (version === readVersion) formData.file = { content, name: file.name, path: '' };
    } catch {
      if (version === readVersion) fileError.value = t('SQL 文件必须使用 UTF-8 编码');
    } finally {
      if (version === readVersion) isReading.value = false;
    }
  };

  const handleRemoveFile = () => {
    readVersion += 1;
    formData.file = { content: '', name: '', path: '' };
    fileError.value = '';
    isReading.value = false;
  };

  const getValue = async () => {
    const details = {
      charset: formData.charset,
      cluster_id: formData.clusterId,
      export_mode: 'sql' as const,
      result_format: formData.resultFormat,
    };
    let filePath = formData.sqlSource === 'file' ? formData.file.path : '';
    if (!filePath) {
      const filename =
        formData.sqlSource === 'file' && /^[A-Za-z0-9_.-]+\.sql$/.test(formData.file.name)
          ? formData.file.name
          : 'query.sql';
      // 上传前固定 SQL 和集群快照，避免等待凭证时输入变化导致提交内容错配。
      const file = new File([querySql.value], filename, { type: 'application/sql' });
      filePath = `mysql/sqlfile/${window.PROJECT_CONFIG.BIZ_ID}/${random()}/${filename}`;
      const url = await createBkrepoUploadUrl(`/${filePath}`);
      await new Promise<void>((resolve, reject) => {
        createXhrUpload({
          headers: createBkrepoHeaders(),
          onError: () => reject(new Error(t('SQL 文件上传失败，请重试'))),
          onProgress: () => {},
          onSuccess: () => resolve(),
          rawFile: file,
          url,
        });
      });
    }
    const separator = filePath.lastIndexOf('/');
    return {
      ...details,
      sql_filename: filePath.slice(separator + 1),
      sql_path: filePath.slice(0, separator),
    };
  };

  onBeforeUnmount(() => {
    readVersion += 1;
  });

  defineExpose({
    getPayload: () => formData.payload,
    getValue,
    validate: async () => {
      if (isReading.value) throw new Error(t('SQL 文件内容读取中，请稍后再提交'));
      await formRef.value!.validate();
    },
  });
</script>

<style lang="less" scoped>
  .sql-export-form {
    max-width: 1136px;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;

    :deep(.dbm-select) {
      max-width: 560px;
    }

    .sql-export-source-selector {
      display: flex;
      width: fit-content;
      margin-bottom: 8px;

      :deep(.bk-radio-button) {
        min-width: 150px;

        .bk-radio-button-label {
          height: 32px;
          padding: 0 16px;
          font-size: 14px;
          line-height: 30px;
          color: #63656e;
          background: #fff;
          border: 1px solid #dcdee5;
          border-radius: 0;
          box-sizing: border-box;
        }

        &:first-child .bk-radio-button-label {
          border-radius: 3px 0 0 3px;
        }

        &:last-child .bk-radio-button-label {
          border-radius: 0 3px 3px 0;
        }

        .bk-radio-button-label:hover {
          color: #3a84ff;
        }

        &.is-checked .bk-radio-button-label {
          color: #3a84ff;
          background: #e1ecff;
          border-color: #3a84ff;
        }
      }
    }

    .sql-export-editor {
      position: relative;
      display: flex;
      height: 360px;
      overflow: hidden;
      color: color-mix(in srgb, #fff 88%, transparent);
      background: color-mix(in srgb, #313238 70%, black);
      border-radius: 3px;
      flex-direction: column;

      &.is-dragover {
        box-shadow: inset 0 0 0 2px #3a84ff;
      }
    }

    .sql-export-body {
      width: 100%;
      min-height: 0;
      padding: 12px 16px;
      margin: 0;
      overflow: auto;
      font-family: Menlo, Consolas, monospace;
      font-size: 12px;
      line-height: 1.7;
      color: color-mix(in srgb, #fff 88%, transparent);
      white-space: pre;
      resize: none;
      background: transparent;
      border: 0;
      outline: 0;
      box-sizing: border-box;
      flex: 1;

      &::placeholder {
        color: color-mix(in srgb, #fff 55%, transparent);
        opacity: 1;
      }
    }

    .sql-export-count {
      position: absolute;
      right: 16px;
      bottom: 8px;
      font-size: 12px;
      line-height: 1.5;
      color: color-mix(in srgb, #fff 55%, transparent);
      pointer-events: none;
    }

    .sql-export-file-header {
      display: flex;
      height: 40px;
      padding: 0 16px;
      font-size: 12px;
      color: color-mix(in srgb, #fff 88%, transparent);
      background: color-mix(in srgb, #313238 85%, #fff);
      align-items: center;
      flex-shrink: 0;
      gap: 12px;
    }

    .sql-export-file-name {
      min-width: 0;
      overflow: hidden;
      font-weight: 500;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    .sql-export-file-meta {
      color: color-mix(in srgb, #fff 55%, transparent);
      flex-shrink: 0;
    }

    .sql-export-file-actions {
      display: flex;
      margin-left: auto;
      align-items: center;
      flex-shrink: 0;
    }

    .sql-export-upload-button {
      height: 28px;
      padding: 0 12px;
      font-size: 12px;
      color: color-mix(in srgb, #fff 88%, transparent);
      background: rgb(255 255 255 / 10%);
      border: none;
      border-radius: 3px;

      &:hover {
        color: color-mix(in srgb, #fff 88%, transparent);
        background: rgb(255 255 255 / 18%);
      }
    }

    .sql-export-empty {
      display: flex;
      height: 100%;
      font-size: 14px;
      color: color-mix(in srgb, #fff 55%, transparent);
      align-items: center;
      flex-direction: column;
      justify-content: center;
      gap: 12px;
    }

    .sql-export-file-hint {
      font-size: 12px;
    }

    .sql-export-helper {
      margin-top: 6px;
      font-size: 12px;
      line-height: 1.5;
      color: #979ba5;
    }
  }
</style>
