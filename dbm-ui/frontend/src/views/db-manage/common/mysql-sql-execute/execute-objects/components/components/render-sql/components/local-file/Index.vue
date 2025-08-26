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
        :loading="selectFileData.state === SqlFileModel.CHECKING || isContentLoading"
        :opacity="0.3"
        :style="styles">
        <Editor
          v-if="isShow"
          :key="renderKey"
          :message-list="selectFileData.messageList"
          :model-value="selectFileData.content"
          readonly
          :title="selectFileName" />
        <div
          v-if="selectFileData.state === SqlFileModel.UNCHEKED"
          class="footer-action">
          <BkButton
            v-bk-tooltips="{
              content: t('请先输入变更 DB'),
              disabled: !grammarCheckDisabled,
            }"
            :disabled="grammarCheckDisabled"
            size="small"
            theme="primary"
            @click="handleGrammarCheck">
            <DbIcon type="right-shape" />
            <span class="ml-4">{{ t('语法检测') }}</span>
          </BkButton>
        </div>
        <template v-else>
          <Checking v-if="selectFileData.state === SqlFileModel.CHECKING" />
          <CheckSuccess
            v-if="selectFileData.messageList.length < 1 && selectFileData.state !== SqlFileModel.CHECK_FAIL" />
          <CheckError :data="selectFileData" />
        </template>
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

  import SqlFileModel from '@views/db-manage/common/mysql-sql-execute/model/SqlFile';

  import Editor from '../editor/Index.vue';
  import useEditableFileContent from '../hooks/useEditableFileContent';
  import RenderFileList from '../RenderFileList.vue';

  import CheckError from './components/CheckError.vue';
  import Checking from './components/Checking.vue';
  import CheckSuccess from './components/CheckSuccess.vue';

  interface Props {
    clusterVersionList: string[];
    dbNames: string[];
    ignoreDbnames: string[];
    isShow: boolean;
  }

  type Emits = (e: 'grammar-check', doCheck: boolean, checkPass: boolean) => void;

  interface Expose {
    getFileData: () => Record<string, SqlFileModel>;
    getValue: () => Promise<string[]>;
    setInit: (cacheData: Record<string, SqlFileModel>) => void;
    setStateToUncheck: () => void;
  }

  const props = defineProps<Props>();

  const emits = defineEmits<Emits>();

  const modelValue = defineModel<string[]>({
    required: true,
  });
  const { dbType: currentDbType, grammarCheckHandle } = useSqlImport();
  const { t } = useI18n();

  const {
    fileDataMap: uploadFileDataMap,
    fileNameList: uploadFileNameList,
    isContentLoading,
    selectFileData,
    selectFileName,
  } = useEditableFileContent();

  const uploadRef = ref();
  const renderKey = ref(1);

  const styles = shallowRef({});

  const grammarCheckDisabled = computed(() => props.dbNames.length === 0);

  const triggerChange = () => {
    window.changeConfirm = true;
    const uploadFileDataList = Object.values(uploadFileDataMap.value);

    if (
      _.some(uploadFileDataList, (item) => [SqlFileModel.CHECK_FAIL, SqlFileModel.UPLOAD_FAIL].includes(item.state))
    ) {
      emits('grammar-check', false, false);
      return;
    }

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

  const getFileContent = (fileInfo: SqlFileModel): Promise<string> => {
    return new Promise((resolve, reject) => {
      if (!fileInfo.file) {
        reject(new Error('No file provided'));
        return;
      }

      const reader = new FileReader();

      reader.onload = (event) => {
        const result = event.target?.result as string;
        resolve(result);
      };

      reader.onerror = () => {
        reject(new Error('Failed to read file'));
      };

      reader.readAsText(fileInfo.file);
    });
  };

  // 开始上传本地文件
  const handleStartUpdate = (event: Event) => {
    const { files = [] } = event.target as HTMLInputElement;
    if (!files) {
      return;
    }
    const isAutoUpload = props.dbNames.length > 0;
    const fileNameList: string[] = [];
    const currentFileDataMap = {} as Record<string, SqlFileModel>;
    const params = new FormData();

    Array.from(files).forEach((curFile, fileIndex) => {
      fileNameList.push(curFile.name);
      currentFileDataMap[curFile.name] = new SqlFileModel({
        file: curFile,
      });

      if (isAutoUpload) {
        currentFileDataMap[curFile.name].grammarCheckStart();

        // 上传文件大小限制 1GB (1024 * 1024 * 1024 = 1073741824)
        if (curFile.size > 1073741824) {
          currentFileDataMap[curFile.name].uploadFailed({
            content: '--',
            realFilePath: '/',
            uploadErrorMessage: t('文件上传失败——文件大小超过限制（最大为1GB）'),
          });
          return;
        }
        params.append(`sql_files[${fileIndex}]`, curFile);
      } else {
        getFileContent(currentFileDataMap[curFile.name]).then((fileContent) => {
          Object.assign(currentFileDataMap[curFile.name], { content: fileContent });
          renderKey.value = renderKey.value + 1;
        });
      }
    });

    // 同名文件覆盖(用新文件覆盖旧文件)
    uploadFileNameList.value = _.uniq(uploadFileNameList.value.concat(fileNameList));
    Object.assign(uploadFileDataMap.value, currentFileDataMap);

    // 初始上传没有选中文件，默认选中第一个
    if (!selectFileName.value || !uploadFileDataMap.value[selectFileName.value]) {
      const [firstFileName] = fileNameList;
      selectFileName.value = firstFileName;
    }

    if (!isAutoUpload) {
      return;
    }

    props.clusterVersionList.forEach((version, index) => {
      params.append(`versions[${index}]`, version);
    });
    params.append('cluster_type', currentDbType);
    params.append(
      'execute_objects',
      JSON.stringify([
        {
          dbnames: props.dbNames,
          ignore_dbnames: props.ignoreDbnames,
          line_id: 1,
          sql_files: ['/'],
        },
      ]),
    );

    grammarCheckHandle(params)
      .then((data) => {
        Object.keys(data).forEach((realFilePath) => {
          const grammarCheckResult = data[realFilePath];
          if (grammarCheckResult.isError) {
            uploadFileDataMap.value[grammarCheckResult.raw_file_name].grammarCheckFailed(data);
          } else {
            uploadFileDataMap.value[grammarCheckResult.raw_file_name].grammarCheckSuccessed(data);
          }
        });
      })
      .catch(() => {
        uploadFileNameList.value.forEach((fileName) => {
          uploadFileDataMap.value[fileName].uploadFailed();
        });
      })
      .finally(() => {
        uploadRef.value.value = '';
        triggerChange();
      });
  };

  const handleGrammarCheck = () => {
    const currentFileData = uploadFileDataMap.value[selectFileName.value];
    const params = new FormData();

    params.append('sql_files[0]', currentFileData.file!);
    props.clusterVersionList.forEach((version, index) => {
      params.append(`versions[${index}]`, version);
    });
    params.append('cluster_type', currentDbType);
    params.append(
      'execute_objects',
      JSON.stringify([
        {
          dbnames: props.dbNames,
          ignore_dbnames: props.ignoreDbnames,
          line_id: 1,
          sql_files: ['/'],
        },
      ]),
    );

    currentFileData.grammarCheckStart();
    grammarCheckHandle(params)
      .then((data) => {
        const [fileCheckResult] = Object.values(data);

        if (!fileCheckResult) {
          currentFileData.uploadFailed();
          return Promise.reject();
        }

        if (fileCheckResult.isError) {
          currentFileData.grammarCheckFailed(data);
        } else {
          currentFileData.grammarCheckSuccessed(data);
        }
      })
      .catch(() => {
        currentFileData.uploadFailed();
        emits('grammar-check', true, false);
      })
      .finally(() => {
        // triggerGramarCheckChange();
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

    // 如果删除的是当前选中的文件，则重新选择第一个文件
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

  onMounted(() => {
    const offsetTop = 250;
    styles.value = {
      height: `${window.innerHeight - offsetTop - 60}px`,
    };
  });

  defineExpose<Expose>({
    getFileData() {
      return uploadFileDataMap.value;
    },
    getValue() {
      return Promise.resolve().then(() => Object.values(uploadFileDataMap.value).map((item) => item.realFilePath));
    },
    setInit(cacheData: Record<string, SqlFileModel>) {
      uploadFileDataMap.value = cacheData;
      uploadFileNameList.value = Object.keys(cacheData);
      [selectFileName.value] = uploadFileNameList.value;
      emits('grammar-check', true, true);
    },
    setStateToUncheck() {
      Object.values(uploadFileDataMap.value).forEach((item) => {
        item.reEdit();
      });
      emits('grammar-check', false, false);
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

    .footer-action {
      position: absolute;
      right: 0;
      bottom: 0;
      left: 0;
      z-index: 1;
      display: flex;
      height: 48px;
      padding-left: 16px;
      background: #212121;
      border-radius: 0 0 2px 2px;
      align-items: center;
    }
  }
</style>
