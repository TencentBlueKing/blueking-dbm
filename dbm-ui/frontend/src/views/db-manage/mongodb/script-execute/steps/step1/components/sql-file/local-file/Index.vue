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
    :label="t('脚本文件')"
    property="execute_sqls"
    required>
    <div class="sql-execute-local-file">
      <div style="margin-bottom: 16px">
        <BkButton @click="handleSelectLocalFile">
          <DbIcon
            style="margin-right: 3px"
            type="add" />
          <span>{{ t('添加文件') }}</span>
        </BkButton>
        <span style="margin-left: 12px; font-size: 12px; color: #8a8f99">
          {{ t('上传_js文件，由上至下执行，可拖动文件调整执行顺序件') }}
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
            :loading="isContentLoading">
            <Editor
              v-model="currentSelectFileData.content"
              :message-list="currentSelectFileData.messageList"
              readonly
              :title="selectFileName"
              @change="triggerChange" />
          </BkLoading>
        </div>
      </div>
      <input
        ref="uploadRef"
        accept=".js"
        multiple
        style="position: absolute; width: 0; height: 0"
        type="file"
        @change="handlePreviewFile" />
    </div>
  </BkFormItem>
</template>
<script setup lang="ts">
  import _ from 'lodash';
  import { useI18n } from 'vue-i18n';

  import Editor from '../editor/Index.vue';

  import RenderFileList, { createFileData, type IFileData } from './components/FileList.vue';

  interface Emits {
    (e: 'change', value: string[]): void;
  }

  interface Exposes {
    getValue: () => { name: string; content: string }[];
  }

  const emits = defineEmits<Emits>();

  const { t } = useI18n();

  const isContentLoading = ref(false);
  const uploadRef = ref();
  const selectFileName = ref('');
  const uploadFileDataMap = ref<Record<string, IFileData>>({});

  const uploadFileNameList = shallowRef<Array<string>>([]);

  // 当前选择文件数据
  const currentSelectFileData = computed(() => uploadFileDataMap.value[selectFileName.value]);

  // 文件结果
  const getResultValue = () =>
    uploadFileNameList.value.map((localFileName) => ({
      name: localFileName,
      content: uploadFileDataMap.value[localFileName].content,
    }));

  watch(
    uploadFileNameList,
    () => {
      if (uploadFileNameList.value.length > 0) {
        uploadFileNameList.value.forEach((item) => {
          getFileContent(uploadFileDataMap.value[item]);
        });
      }
    },
    {
      immediate: true,
    },
  );

  const triggerChange = () => {
    const list = getResultValue();
    emits(
      'change',
      list.map((item) => item.content),
    );
  };

  const getFileContent = (fileInfo: IFileData) =>
    new Promise((resove, reject) => {
      const reader = new FileReader();
      reader.onloadend = function (evt) {
        if (evt?.target?.readyState === FileReader.DONE) {
          Object.assign(fileInfo, {
            content: evt.target.result,
          });
          resove(evt.target.result);
        } else {
          reject();
        }
      };
      reader.readAsText(fileInfo.file!);
    });

  // 开始选择本地文件
  const handleSelectLocalFile = () => {
    uploadRef.value.click();
  };

  // 开始预览本地文件
  const handlePreviewFile = (event: Event) => {
    const { files = [] } = event.target as HTMLInputElement;
    if (!files) {
      return;
    }
    const fileNameList: Array<string> = [];
    const fileDataMap = {} as Record<string, IFileData>;

    Array.from(files).forEach((curFile) => {
      fileNameList.push(curFile.name);
      fileDataMap[curFile.name] = createFileData({
        file: curFile,
      });
    });

    uploadFileNameList.value = _.uniq([...uploadFileNameList.value, ...fileNameList]);
    uploadFileDataMap.value = {
      ...uploadFileDataMap.value,
      ...fileDataMap,
    };

    if (!selectFileName.value || !uploadFileDataMap.value[selectFileName.value]) {
      const [firstFileName] = fileNameList;
      selectFileName.value = firstFileName;
    }
    triggerChange();
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

    if (fileName === selectFileName.value && fileList.length > 0) {
      [selectFileName.value] = fileList;
    }
    triggerChange();
  };

  defineExpose<Exposes>({
    getValue: () => getResultValue(),
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
