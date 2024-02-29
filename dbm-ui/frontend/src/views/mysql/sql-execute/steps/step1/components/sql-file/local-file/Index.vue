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
  <BkFormItem
    :label="t('SQL文件')"
    property="execute_sql_files"
    required
    :rules="rules">
    <template #labelAppend>
<<<<<<< HEAD
      <span style="font-size: 12px; font-weight: normal; color: #8a8f99;">
        （{{ t('最终执行结果以SQL文件内容为准') }}）
=======
      <span style="font-size: 12px; font-weight: normal; color: #8a8f99">
        （{{ $t('最终执行结果以SQL文件内容为准') }}）
>>>>>>> c3acfbeaf (style(frontend): 使用prettier代码格式化 #3408)
      </span>
    </template>
    <div class="sql-execute-local-file">
      <div style="margin-bottom: 16px">
        <BkButton @click="handleSelectLocalFile">
          <DbIcon
            style="margin-right: 3px"
            type="add" />
          <span>{{ t('添加文件') }}</span>
        </BkButton>
<<<<<<< HEAD
        <span style="margin-left: 12px; font-size: 12px; color: #8a8f99;">
          {{ t('仅支持_sql文件_文件名不能包含空格_上传后_SQL执行顺序默认为从上至下_可拖动文件位置_变换文件的执行顺序文件') }}
=======
        <span style="margin-left: 12px; font-size: 12px; color: #8a8f99">
          {{
            $t(
              '仅支持_sql文件_文件名不能包含空格_上传后_SQL执行顺序默认为从上至下_可拖动文件位置_变换文件的执行顺序文件',
            )
          }}
>>>>>>> c3acfbeaf (style(frontend): 使用prettier代码格式化 #3408)
        </span>
      </div>
      <div
        v-if="uploadFileNameList.length > 0"
        class="editor-layout">
        <div class="editor-layout-left">
          <RenderFileList
            v-model="selectFileName"
            :data="uploadFileNameList"
            :file-data="uploadFileDataMap"
            @remove="handleRemove"
            @sort="handleFileSortChange" />
        </div>
        <div class="editor-layout-right">
          <BkLoading
            class="content-loading"
            :loading="currentSelectFileData.isUploading || isContentLoading">
            <Editor
              :message-list="currentSelectFileData.messageList"
              :model-value="currentSelectFileData.content"
              readonly
              :title="selectFileName" />
            <CheckSuccess
              v-if="currentSelectFileData.messageList.length < 1 && !currentSelectFileData.isCheckFailded" />
            <CheckError :data="currentSelectFileData" />
          </BkLoading>
        </div>
      </div>
      <input
        ref="uploadRef"
        accept=".sql"
        multiple
        style="position: absolute; width: 0; height: 0"
        type="file"
        @change="handleStartUpdate" />
    </div>
  </BkFormItem>
</template>
<script setup lang="ts">
  import _ from 'lodash';
  import {
    computed,
    onActivated,
    onDeactivated,
    ref,
  } from 'vue';
  import { useI18n } from 'vue-i18n';

  import { grammarCheck } from '@services/source/sqlImport';
  import { getFileContent } from '@services/source/storage';

  import { getSQLFilename } from '@utils';

  import { updateFilePath } from '../../../Index.vue';
  import Editor from '../editor/Index.vue';

  import CheckError from './components/CheckError.vue';
  import CheckSuccess from './components/CheckSuccess.vue';
  import RenderFileList, {
    createFileData,
    type IFileData,
  } from './components/FileList.vue';

  interface Props {
    modelValue: string[]
  }

  interface Emits {
    (e: 'change', value: string[]): void;
    (e: 'grammar-check', doCheck: boolean, checkPass: boolean): void;
  }

  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();

  const { t } = useI18n();

  let isKeepAliveActive = false;

  const isContentLoading = ref(false);
  const uploadRef = ref();
  const selectFileName = ref('');
  const uploadFileNameList = shallowRef<Array<string>>([]);
  const uploadFileDataMap = shallowRef<Record<string, IFileData>>({});

  // 当前选择文件数据
  const currentSelectFileData = computed(() => uploadFileDataMap.value[selectFileName.value]);

  const rules = [
    {
      validator: () => {
        if (!isKeepAliveActive) {
          return true;
        }
        const uploadFileDataList = Object.values(uploadFileDataMap.value);
        for (let i = 0; i < uploadFileDataList.length; i++) {
          const {
            isUploadFailed,
            isCheckFailded,
          } = uploadFileDataList[i];
          if (isUploadFailed) {
            return false;
          }
          if (isCheckFailded) {
            return false;
          }
        }
        return true;
      },
      message: t('SQL文件无效'),
      trigger: 'change',
    },
  ];

  // 文件结果
  const getResultValue = () => uploadFileNameList.value
    .map(localFileName => uploadFileDataMap.value[localFileName].realFilePath);

  // 获取文件内容
  const fetchFileContent = (fileName: string) => {
    if (!updateFilePath.value) {
      return;
    }
    isContentLoading.value = true;
    const fileDataMap = { ...uploadFileDataMap.value };
    getFileContent({
      file_path: `${updateFilePath.value}/${fileName}`,
    })
      .then((data) => {
        fileDataMap[getSQLFilename(fileName)].content = data.content;
        uploadFileDataMap.value = fileDataMap;
      })
      .finally(() => {
        isContentLoading.value = false;
      });
  };

  let isInnerChange = false;

  // 同步外部值
  watch(() => props.modelValue, () => {
    if (isInnerChange) {
      isInnerChange = false;
      return;
    }
    if (props.modelValue.length < 1) {
      return;
    }
    const localFileNameList = [] as string[];
    const filePathMap = {} as Record<string, string>;

    props.modelValue.forEach((filePath: string) => {
      // 本地 SQL 文件上传后会拼接随机数前缀，需要解析正确的文件名
      const localFileName = getSQLFilename(filePath);
      localFileNameList.push(localFileName);
      filePathMap[localFileName] = filePath;
    });

    uploadFileNameList.value = localFileNameList;

    uploadFileDataMap.value = uploadFileNameList.value.reduce((result, localFileName) => ({
      ...result,
      [localFileName]: createFileData({
        isSuccess: true,
        isCheckFailded: false,
        realFilePath: filePathMap[localFileName],
      }),
    }), {} as Record<string, IFileData>);

    // 默认选中第一个文件
    [selectFileName.value] = uploadFileNameList.value;
    if (props.modelValue.length > 0) {
      fetchFileContent(uploadFileDataMap.value[selectFileName.value].realFilePath);
    }
  }, {
    immediate: true,
  });

  watch(selectFileName, () => {
    // 编辑状态不需要 SQL 文件检测，需要异步获取文件内容
    if (!selectFileName.value
      || uploadFileDataMap.value[selectFileName.value].content
      || uploadFileDataMap.value[selectFileName.value].grammarCheck) {
      return;
    }
    fetchFileContent(uploadFileDataMap.value[selectFileName.value].realFilePath);
  }, {
    immediate: true,
  });

  const triggerChange = () => {
    const uploadFileDataList = Object.values(uploadFileDataMap.value);
    for (let i = 0; i < uploadFileDataList.length; i++) {
      const {
        isUploadFailed,
        isCheckFailded,
      } = uploadFileDataList[i];
      if (isUploadFailed || isCheckFailded) {
        emits('grammar-check', false, false);
        return;
      }
    }
    emits('grammar-check', true, true);
    isInnerChange = true;
    emits('change', getResultValue());
  };

  // 开始选择本地文件
  const handleSelectLocalFile = () => {
    uploadRef.value.click();
  };

  // 开始上传本地文件
  const handleStartUpdate = (event: Event) => {
    const {
      files = [],
    } = event.target as HTMLInputElement;
    if (!files) {
      return;
    }
    const fileNameList: Array<string> = [];
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
          isCheckFailded: true,
          isUploadFailed: true,
          isUploading: false,
          uploadErrorMessage: t('文件上传失败——文件大小超过限制（最大为1GB）'),
          grammarCheck: undefined,

        };
        return;
      }
      params.append('sql_files', curFile);
    });

    uploadFileNameList.value = _.uniq([...uploadFileNameList.value, ...fileNameList]);
    uploadFileDataMap.value = {
      ...uploadFileDataMap.value,
      ...currentFileDataMap,
    };

    if (!selectFileName.value || !uploadFileDataMap.value[selectFileName.value]) {
      const [firstFileName] = fileNameList;
      selectFileName.value = firstFileName;
    }


    grammarCheck(params)
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
        triggerChange();
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
        emits('grammar-check', false, false);
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
      });
  };
  // 文件排序
  const handleFileSortChange = (list: string[]) => {
    uploadFileNameList.value = list;
    triggerChange();
  };
  // 删除文件
  const handleRemove = (fileName: string, index: number) => {
    const fileList = [...uploadFileNameList.value];
    const lastUploadFileDataMap = { ...uploadFileDataMap.value };

    fileList.splice(index, 1);
    uploadFileNameList.value = fileList;
    delete lastUploadFileDataMap[fileName];
    uploadFileDataMap.value = lastUploadFileDataMap;

    if (fileName === selectFileName.value
      && fileList.length > 0) {
      [selectFileName.value] = fileList;
    }
    triggerChange();
  };

  onActivated(() => {
    isKeepAliveActive = true;
    triggerChange();
  });

  onDeactivated(() => {
    isKeepAliveActive = false;
  });
</script>
<style lang="less">
  .sql-execute-local-file {
    .label-tips {
      position: absolute;
      top: 0;
      padding-left: 16px;
      font-weight: normal;
      color: @gray-color;
    }

    .editor-layout {
      display: flex;
      height: 500px;
      background: #2e2e2e;

      .editor-layout-left {
        width: 238px;
      }

      .editor-layout-right {
        position: relative;
        height: 100%;
        flex: 1;

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
          .bk-loading-mask {
            background: transparent !important;
          }
        }
      }
    }
  }
</style>
