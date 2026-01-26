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
  <div class="editor-resize-wrapper">
    <Editor
      v-model="uploadFileData.content"
      @change="handleEditorChange" />
    <div
      v-if="!uploadFileData.grammarCheck"
      class="footer-action">
      <span
        v-bk-tooltips="{
          content: submitButtonTips,
          disabled: !submitButtonTips,
        }">
        <BkButton
          :disabled="Boolean(submitButtonTips)"
          size="small"
          theme="primary"
          @click="handleGrammarCheck">
          <DbIcon type="right-shape" />
          <span class="ml-4">{{ t('语法检测') }}</span>
        </BkButton>
      </span>
    </div>
    <template v-else>
      <SyntaxChecking
        v-if="uploadFileData.state === SqlFileModel.CHECKING"
        class="syntax-checking" />
      <SyntaxError
        v-else-if="uploadFileData.state === SqlFileModel.UPLOAD_FAIL"
        class="syntax-error" />
      <SyntaxSuccess
        v-else-if="uploadFileData.state === SqlFileModel.SUCCESS"
        class="syntax-success" />
    </template>
  </div>
</template>
<script setup lang="ts">
  import dayjs from 'dayjs';
  import { useI18n } from 'vue-i18n';

  import { grammarCheck } from '@services/source/sqlserverSqlImport';

  import { DBTypes } from '@common/const';

  import SqlFileModel from '@views/db-manage/common/model/sql-file/SqlFile';

  import Editor from './components/editor/Index.vue';
  import SyntaxChecking from './components/syntax-result/SyntaxChecking.vue';
  import SyntaxError from './components/syntax-result/SyntaxError.vue';
  import SyntaxSuccess from './components/syntax-result/SyntaxSuccess.vue';

  interface Props {
    clusterList: {
      major_version: string;
    }[];
  }

  type Emits = (e: 'grammar-check', doCheck: boolean, checkPass: boolean) => void;

  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();

  const submitButtonTips = computed(() => {
    if (props.clusterList.length < 1) {
      return t('请选择集群');
    }

    if (uploadFileData.value.content.length < 1) {
      return t('请输入 SQL 语句');
    }

    return '';
  });

  const { t } = useI18n();

  const uploadFileData = ref<SqlFileModel>(
    new SqlFileModel({
      content: '',
      realFilePath: `SQLSERVER_DATA_EXPORT_${dayjs().format('YYYY-MM-DD')}.sql`,
    }),
  );

  const handleEditorChange = () => {
    uploadFileData.value.reEdit();
    emits('grammar-check', false, false);
  };

  const handleGrammarCheck = () => {
    const params = new FormData();

    params.append('sql_content', uploadFileData.value.content);
    props.clusterList.forEach(({ major_version: version }, index) => {
      params.append(`versions[${index}]`, version);
    });
    params.append('cluster_type', DBTypes.SQLSERVER);

    uploadFileData.value.grammarCheckStart();
    grammarCheck(params)
      .then((data) => {
        const [fileCheckResult] = Object.values(data);

        if (!fileCheckResult) {
          uploadFileData.value.uploadFailed();
          return Promise.reject();
        }

        if (fileCheckResult.isError) {
          uploadFileData.value.grammarCheckFailed(data);
        } else {
          uploadFileData.value.grammarCheckSuccessed(data);
        }

        emits('grammar-check', true, true);
      })
      .catch(() => {
        uploadFileData.value.uploadFailed();
        emits('grammar-check', true, false);
      });
  };

  defineExpose({
    getValue() {
      return uploadFileData.value.realFilePath;
    },
    reEdit() {
      handleEditorChange();
    },
    setValue(value: string) {
      uploadFileData.value.content = value;
    },
  });
</script>
<style lang="less">
  .editor-resize-wrapper {
    height: 500px !important;
    position: relative;

    .bk-resize-layout-aside-content {
      height: auto !important;
      overflow: auto !important;
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
