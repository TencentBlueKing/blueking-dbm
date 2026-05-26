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
  <div class="sql-execute-file-manual-input">
    <BkLoading :loading="isContentLoading">
      <Editor
        v-model="fileData.content"
        :message-list="fileData.messageList"
        :title="t('脚本编辑器')"
        @change="handleEditorChange" />
      <div
        v-if="fileData.state === SqlFileModel.UNCHEKED"
        class="footer-action">
        <BkButton
          v-bk-tooltips="{
            content: t('请先输入内容'),
            disabled: !grammarCheckDisabled,
          }"
          v-test="{ type: 'button', value: 'grammarCheck' }"
          :disabled="grammarCheckDisabled"
          size="small"
          theme="primary"
          @click="handleGrammarCheck">
          <DbIcon type="right-shape" />
          <span class="ml-4">{{ t('语法检测') }}</span>
        </BkButton>
      </div>
      <template v-else>
        <SyntaxSuccess
          v-if="fileData.state === SqlFileModel.SUCCESS"
          class="syntax-success" />
        <SyntaxChecking
          v-if="fileData.state === SqlFileModel.CHECKING"
          class="syntax-checking" />
        <SyntaxError
          v-else-if="fileData.state === SqlFileModel.UPLOAD_FAIL"
          class="syntax-error" />
        <MessageList
          v-else-if="
            fileData.state === SqlFileModel.SUCCESS &&
            fileData.messageList.filter((m: { type: string }) => m.type === 'error').length === 0 &&
            fileData.messageList.filter((m: { type: string }) => m.type === 'warning').length === 0
          "
          :data="fileData.messageList"
          model-value />
      </template>
    </BkLoading>
  </div>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { useSqlImport } from '@stores';

  import SqlFileModel from '@views/db-manage/common/model/sql-file/SqlFile';

  import { getFileContent } from '@/services/source/storage.ts';

  import Editor from '../editor/Index.vue';
  import MessageList from '../editor/MessageList.vue';

  import SyntaxChecking from './components/SyntaxChecking.vue';
  import SyntaxError from './components/SyntaxError.vue';
  import SyntaxSuccess from './components/SyntaxSuccess.vue';

  type Emits = {
    (e: 'change', value: string[]): void;
    (e: 'grammar-check', doCheck: boolean, result: boolean | string): void;
  };

  interface Expose {
    getFileData: () => Record<string, SqlFileModel>;
    getValue: () => string[];
    setInit: (cacheData: Record<string, SqlFileModel>) => void;
    setStateToUncheck: () => void;
  }

  const emits = defineEmits<Emits>();

  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  const modelValue = defineModel<string[]>({
    default: () => [],
  });

  let isTicketCloneChange = false;
  const FILE_NAME = 'script.js';

  const { grammarCheckHandle } = useSqlImport();
  const { t } = useI18n();

  // 单文件模式：直接使用一个 SqlFileModel 实例
  const fileData = ref(
    new SqlFileModel({
      content: '',
      realFilePath: FILE_NAME,
    }),
  );

  const grammarCheckDisabled = computed(() => {
    return fileData.value.content.trim().length === 0;
  });

  const { loading: isContentLoading, run: runGetFileContent } = useRequest(getFileContent, {
    manual: true,
    onSuccess(data, params) {
      fileData.value.content = data.content;
      fileData.value.file = new File([data.content], params[0].file_path);
      isTicketCloneChange = true;
    },
  });

  const triggerChange = () => {
    window.changeConfirm = true;
    const fileNameList = [fileData.value.realFilePath || 'FILE_NAME'];
    emits('change', fileNameList);
  };

  const triggerGramarCheckChange = () => {
    let doCheck = true;
    let checkPass = true;
    let totalErrorNum = 0;

    const item = fileData.value;
    if (!item.grammarCheck && item.content) {
      doCheck = false;
    }
    if (item.state === SqlFileModel.CHECK_FAIL || item.state === SqlFileModel.UPLOAD_FAIL) {
      checkPass = false;
    }
    if (item.messageList?.length) {
      totalErrorNum += item.messageList.filter((msg) => msg.type === 'error').length;
    }

    if (!checkPass && totalErrorNum > 0) {
      emits('grammar-check', doCheck, t('请先修复n个错误后再提交', { n: totalErrorNum }));
    } else {
      emits('grammar-check', doCheck, checkPass);
    }
  };

  const handleGrammarCheck = () => {
    const params = new FormData();

    params.append('script_content', fileData.value.content);

    fileData.value.grammarCheckStart();
    grammarCheckHandle(params)
      .then((data) => {
        const [fileCheckResult] = Object.values(data);
        const checkItem = {
          [fileCheckResult.sql_path]: fileCheckResult,
        };

        if (!fileCheckResult) {
          fileData.value.uploadFailed();
          return Promise.reject();
        }

        if (fileCheckResult.isError) {
          fileData.value.grammarCheckFailed(checkItem);
        } else {
          fileData.value.grammarCheckSuccessed(checkItem);
        }
      })
      .catch(() => {
        fileData.value.uploadFailed();
        emits('grammar-check', true, false);
      })
      .finally(() => {
        triggerGramarCheckChange();
        triggerChange();
      });
  };

  const handleEditorChange = () => {
    if (isTicketCloneChange) {
      isTicketCloneChange = false;
      return;
    }
    fileData.value.reEdit();
    triggerGramarCheckChange();
  };

  onActivated(() => {
    triggerChange();
    setTimeout(() => {
      window.changeConfirm = false;
    });
  });

  defineExpose<Expose>({
    getFileData() {
      return { FILE_NAME: fileData.value };
    },
    getValue() {
      return [fileData.value.realFilePath];
    },
    setInit(cacheData: Record<string, SqlFileModel>) {
      // 单文件模式：取第一个缓存数据
      const keys = Object.keys(cacheData);
      if (keys.length > 0) {
        fileData.value = cacheData[keys[0]];
      }
      runGetFileContent({
        file_path: fileData.value.realFilePath,
      });
      triggerChange();
      emits('grammar-check', true, true);
    },
    setStateToUncheck() {
      fileData.value.reEdit();
      triggerGramarCheckChange();
    },
  });
</script>

<style lang="less">
  .sql-execute-file-manual-input {
    position: relative;
    height: 100%;
    background: #1a1a1a;

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
