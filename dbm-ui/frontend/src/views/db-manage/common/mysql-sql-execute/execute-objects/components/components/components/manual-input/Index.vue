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
    class="sql-execute-file-manual-input"
    :initial-divide="300"
    :min="240">
    <template #aside>
      <RenderFileList
        v-model="selectFileName"
        v-model:filename-list="uploadFileNameList"
        :file-data="uploadFileDataMap"
        @remove="handleRemoveFile">
        <div
          key="upload"
          class="create-file-btn mr-4"
          @click="handleCreateFile">
          <DbIcon type="add" />
          {{ t('点击添加') }}
        </div>
      </RenderFileList>
    </template>
    <template #main>
      <BkLoading
        v-if="uploadFileNameList.length > 0"
        :loading="isContentLoading"
        :style="styles">
        <template v-if="selectFileData">
          <Editor
            v-if="isShow"
            :key="selectFileName"
            v-model="selectFileData.content"
            :message-list="selectFileData.messageList"
            :title="selectFileName"
            @change="handleEditorChange" />
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
            <SyntaxChecking
              v-if="selectFileData.state === SqlFileModel.CHECKING"
              class="syntax-checking" />
            <SyntaxError
              v-else-if="selectFileData.state === SqlFileModel.UPLOAD_FAIL"
              class="syntax-error" />
            <SyntaxSuccess
              v-else-if="selectFileData.state === SqlFileModel.SUCCESS"
              class="syntax-success" />
          </template>
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
        {{ t('请添加 SQL 文件') }}
      </div>
    </template>
  </BkResizeLayout>
</template>
<script setup lang="ts">
  import { onActivated } from 'vue';
  import { useI18n } from 'vue-i18n';

  import { useSqlImport } from '@stores';

  import SqlFileModel from '@views/db-manage/common/mysql-sql-execute/model/SqlFile';

  import Editor from '../editor/Index.vue';
  import useEditableFileContent from '../hooks/useEditableFileContent';
  import RenderFileList from '../RenderFileList.vue';

  import SyntaxChecking from './components/SyntaxChecking.vue';
  import SyntaxError from './components/SyntaxError.vue';
  import SyntaxSuccess from './components/SyntaxSuccess.vue';

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

  const genFilename = ((initIndex: number) => {
    let index = initIndex;
    return () => {
      index = index + 1;
      return `sql_${index}.sql`;
    };
  })(modelValue.value.length);

  const { dbType: currentDbType, grammarCheckHandle } = useSqlImport();
  const { t } = useI18n();

  const {
    fileDataMap: uploadFileDataMap,
    fileNameList: uploadFileNameList,
    isContentLoading,
    selectFileData,
    selectFileName,
  } = useEditableFileContent();

  const styles = shallowRef({});

  const grammarCheckDisabled = computed(() => props.dbNames.length === 0);

  const triggerChange = () => {
    window.changeConfirm = true;
    modelValue.value = Object.values(uploadFileDataMap.value).map((item) => item.realFilePath);
  };

  const triggerGramarCheckChange = () => {
    let doCheck = true;
    let checkPass = true;
    Object.values(uploadFileDataMap.value).forEach((item) => {
      if (!item.grammarCheck && item.content) {
        doCheck = false;
        return;
      }
      if (item.state === SqlFileModel.CHECK_FAIL) {
        checkPass = false;
      }
    });
    emits('grammar-check', doCheck, checkPass);
  };

  const handleCreateFile = () => {
    const fileName = genFilename();

    uploadFileNameList.value = [...uploadFileNameList.value, fileName];
    uploadFileDataMap.value[fileName] = new SqlFileModel({
      content: '-- Please enter the SQL statement\n\n',
      realFilePath: fileName,
    });
    selectFileName.value = fileName;
    emits('grammar-check', false, false);
    triggerChange();
  };

  const handleRemoveFile = (filename: string) => {
    const lastUploadFileDataMap = { ...uploadFileDataMap.value };

    delete lastUploadFileDataMap[filename];
    uploadFileDataMap.value = lastUploadFileDataMap;

    // 如果删除的是当前选中的文件，则重新选择第一个文件
    if (filename === selectFileName.value && uploadFileNameList.value.length > 0) {
      [selectFileName.value] = uploadFileNameList.value;
    } else {
      selectFileName.value = '';
    }

    triggerGramarCheckChange();
    triggerChange();
  };

  const handleGrammarCheck = () => {
    const currentFileData = uploadFileDataMap.value[selectFileName.value];
    const params = new FormData();

    params.append('sql_content', currentFileData.content);
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
        triggerGramarCheckChange();
        triggerChange();
      });
  };

  const handleEditorChange = () => {
    selectFileData.value.reEdit();
    triggerGramarCheckChange();
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
      position: 'relative',
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
      triggerChange();
      emits('grammar-check', true, true);
    },
    setStateToUncheck() {
      Object.values(uploadFileDataMap.value).forEach((item) => {
        item.reEdit();
      });
      triggerGramarCheckChange();
    },
  });
</script>
<style lang="less">
  .sql-execute-file-manual-input {
    position: relative;
    height: 100%;
    background: #1a1a1a;

    .bk-resize-layout-aside {
      border: none;
    }

    .create-file-btn {
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

    .syntax-checking,
    .syntax-success,
    .syntax-error {
      position: absolute;
      right: 0;
      bottom: 0;
      left: 0;
    }
  }
</style>
