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
  <BkResizeLayout
    :border="false"
    class="sql-execute-file-local-file"
    :initial-divide="300"
    :min="240">
    <template #aside>
      <RenderFileList
        v-model="selectFileName"
        v-model:filename-list="uploadFileNameList"
        :file-data="uploadFileDataMap"
        @remove="handleRemove"
        @sort="handleFileSortChange">
        <div
          key="upload"
          class="upload-btn"
          @click="handleSelectLocalFile">
          <DbIcon
            class="mr-4"
            type="import" />
          {{ t('点击上传') }}
        </div>
      </RenderFileList>
    </template>
    <template #main>
      <BkLoading
        v-if="uploadFileNameList.length > 0"
        class="content-loading"
        :loading="selectFileData.isUploading || isContentLoading"
        :opacity="0.3"
        style="height: 100%">
        <Editor
          v-if="isShow"
          :message-list="selectFileData.messageList"
          :model-value="selectFileData.content"
          readonly
          :title="selectFileName" />
        <CheckSuccess v-if="selectFileData.messageList.length < 1 && !selectFileData.isCheckFailded" />
        <CheckError :data="selectFileData" />
      </BkLoading>
      <div
        v-else
        style="
          display: flex;
          height: 100%;
          align-items: center;
          justify-content: center;
          font-size: 12px;
          color: #c4c6cc;
        ">
        <DbIcon
          class="mr-4"
          type="attention" />
        {{ t('请选择本地 SQL 文件') }}
      </div>
    </template>
  </BkResizeLayout>
  <input
    ref="uploadRef"
    accept=".sql"
    multiple
    style="position: absolute; width: 0; height: 0"
    type="file"
    @change="handleStartUpdate" />
</template>
<script setup lang="ts">
  import _ from 'lodash';
  import { onActivated, ref } from 'vue';
  import { useI18n } from 'vue-i18n';

  import { useSqlImport } from '@stores';

  import Editor from '../editor/Index.vue';
  import useEditableFileContent from '../hooks/useEditableFileContent';
  import RenderFileList, { createFileData, type IFileData } from '../RenderFileList.vue';

  import CheckError from './components/CheckError.vue';
  import CheckSuccess from './components/CheckSuccess.vue';

  interface Props {
    clusterVersionList: string[];
    isShow: boolean;
  }

  interface Emits {
    (e: 'grammar-check', doCheck: boolean, checkPass: boolean): void;
  }

  interface Expose {
    getValue: () => Promise<string[]>;
  }

  const props = defineProps<Props>();

  const emits = defineEmits<Emits>();

  const { grammarCheckHandle, dbType: currentDbType } = useSqlImport();
  const { t } = useI18n();

  const modelValue = defineModel<string[]>({
    required: true,
  });

  const {
    isContentLoading,
    selectFileName,
    selectFileData,
    fileNameList: uploadFileNameList,
    fileDataMap: uploadFileDataMap,
    initEditableFile,
    fetchFileContentByFileName,
  } = useEditableFileContent(modelValue);

  const uploadRef = ref();

  let isInnerChange = false;

  // 同步外部值(编辑态)
  watch(
    modelValue,
    () => {
      if (isInnerChange) {
        isInnerChange = false;
        return;
      }
      if (modelValue.value.length < 1) {
        return;
      }

      initEditableFile();

      // 默认选中第一个文件
      [selectFileName.value] = uploadFileNameList.value;
      fetchFileContentByFileName(uploadFileDataMap.value[selectFileName.value].realFilePath);
      emits('grammar-check', true, true);
    },
    {
      immediate: true,
    },
  );

  const triggerChange = () => {
    window.changeConfirm = true;
    const uploadFileDataList = Object.values(uploadFileDataMap.value);

    if (_.some(uploadFileDataList, (item) => item.isUploadFailed || item.isCheckFailded)) {
      emits('grammar-check', false, false);
      return;
    }

    isInnerChange = true;
    if (uploadFileNameList.value.length) {
      modelValue.value = uploadFileNameList.value.map(
        (localFileName) => uploadFileDataMap.value[localFileName].realFilePath,
      );
    }

    emits('grammar-check', true, true);
  };

  // 开始选择本地文件
  const handleSelectLocalFile = () => {
    uploadRef.value.click();
  };

  // 开始上传本地文件
  const handleStartUpdate = (event: Event) => {
    const { files = [] } = event.target as HTMLInputElement;
    if (!files) {
      return;
    }
    const fileNameList: string[] = [];
    const currentFileDataMap = {} as Record<string, IFileData>;
    const params = new FormData();

    Array.from(files).forEach((curFile) => {
      fileNameList.push(curFile.name);
      currentFileDataMap[curFile.name] = createFileData({
        file: curFile,
        isUploading: true,
      });

      // 上传文件大小限制 1GB (1024 * 1024 * 1024 = 1073741824)
      if (curFile.size > 1073741824) {
        currentFileDataMap[curFile.name] = {
          ...currentFileDataMap[curFile.name],
          realFilePath: '/',
          isSuccess: true,
          content: '--',
          messageList: [],
          isCheckFailded: false,
          isUploadFailed: true,
          isUploading: false,
          uploadErrorMessage: t('文件上传失败——文件大小超过限制（最大为1GB）'),
          grammarCheck: undefined,
        };
        return;
      }
      params.append('sql_files', curFile);
    });

    // 同名文件覆盖(用新文件覆盖旧文件)
    uploadFileNameList.value = _.uniq([...uploadFileNameList.value, ...fileNameList]);
    uploadFileDataMap.value = {
      ...uploadFileDataMap.value,
      ...currentFileDataMap,
    };

    // 初始上传没有选中文件，默认选中第一个
    if (!selectFileName.value || !uploadFileDataMap.value[selectFileName.value]) {
      const [firstFileName] = fileNameList;
      selectFileName.value = firstFileName;
    }

    props.clusterVersionList.forEach((version, index) => {
      params.append(`versions[${index}]`, version);
    });

    params.append('cluster_type', currentDbType);

    grammarCheckHandle(params)
      .then((data) => {
        const lastUploadFileDataMap = { ...uploadFileDataMap.value };
        Object.keys(data).forEach((realFilePath) => {
          const grammarCheckResult = data[realFilePath];
          lastUploadFileDataMap[grammarCheckResult.raw_file_name] = {
            ...lastUploadFileDataMap[grammarCheckResult.raw_file_name],
            realFilePath,
            isSuccess: true,
            content: grammarCheckResult.content,
            messageList: grammarCheckResult.messageList,
            isCheckFailded: grammarCheckResult.isError,
            grammarCheck: grammarCheckResult,
          };
        });
        uploadFileDataMap.value = lastUploadFileDataMap;
      })
      .catch(() => {
        const lastUploadFileDataMap = { ...uploadFileDataMap.value };
        fileNameList.forEach((fileName) => {
          lastUploadFileDataMap[fileName] = {
            ...lastUploadFileDataMap[fileName],
            isUploadFailed: true,
          };
        });
        uploadFileDataMap.value = lastUploadFileDataMap;
      })
      .finally(() => {
        const lastUploadFileDataMap = { ...uploadFileDataMap.value };
        fileNameList.forEach((fileName) => {
          lastUploadFileDataMap[fileName] = {
            ...lastUploadFileDataMap[fileName],
            isUploading: false,
          };
        });
        uploadFileDataMap.value = lastUploadFileDataMap;
        uploadRef.value.value = '';
        triggerChange();
      });
  };
  // 文件排序
  const handleFileSortChange = (list: string[]) => {
    uploadFileNameList.value = list;
    triggerChange();
  };
  // 删除文件
  const handleRemove = (fileName: string) => {
    const lastUploadFileDataMap = { ...uploadFileDataMap.value };

    delete lastUploadFileDataMap[fileName];
    uploadFileDataMap.value = lastUploadFileDataMap;

    // // 如果删除的是当前选中的文件，则重新选择第一个文件
    if (fileName === selectFileName.value && uploadFileNameList.value.length > 0) {
      [selectFileName.value] = uploadFileNameList.value;
    } else {
      selectFileName.value = '';
    }
    triggerChange();
  };

  onActivated(() => {
    triggerChange();
    setTimeout(() => {
      window.changeConfirm = false;
    });
  });

  defineExpose<Expose>({
    getValue() {
      return Promise.resolve().then(() => Object.values(uploadFileDataMap.value).map((item) => item.realFilePath));
    },
  });
</script>
<style lang="less">
  .sql-execute-file-local-file {
    height: 100%;
    background: #1a1a1a;

    .bk-resize-layout-aside {
      border: none !important;
    }

    .editor-error-tips {
      position: absolute;
      right: 0;
      bottom: 0;
      left: 0;
      padding-left: 16px;
      background: #212121;
      border-left: 4px solid #b34747;
      border-radius: 0 0 2px 2px;
    }

    .content-loading {
      position: relative;
      height: 100%;

      .bk-loading-mask {
        background: transparent !important;
      }
    }

    .upload-btn {
      display: flex;
      height: 36px;
      padding: 0 8px;
      font-size: 12px;
      color: #c4c6cc;
      cursor: pointer;
      background: rgb(255 255 255 / 8%);
      border-radius: 2px;
      align-items: center;
      justify-content: center;

      &:hover {
        background: rgb(255 255 255 / 20%);
      }
    }
  }
</style>
