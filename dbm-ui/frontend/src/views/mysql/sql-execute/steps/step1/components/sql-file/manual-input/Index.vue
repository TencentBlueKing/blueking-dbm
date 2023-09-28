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
    :label="$t('SQL 内容')"
    property="execute_sql_files"
    required
    :rules="rules">
    <template #labelAppend>
      <span style="font-size: 12px; font-weight: normal; color: #8a8f99;">
        （{{ $t('最终执行结果以 SQL 内容为准') }}）
      </span>
    </template>
    <div class="sql-execute-manual-input">
      <BkLoading :loading="isLoading">
        <Editor
          v-model="content"
          :message-list="inputContentCheckResult.messageList"
          :title="$t('SQL编辑器')"
          @change="handleEditorChange" />
        <div
          v-if="!isSubmited"
          class="footer-action">
          <BkButton
            :disabled="!content"
            size="small"
            theme="primary"
            @click="handleGrammarCheck">
            <DbIcon type="right-shape" />
            <span style="margin-left: 4px;">{{ $t('语法检测') }}</span>
          </BkButton>
        </div>
        <template v-else>
          <SyntaxChecking
            v-if="isChecking"
            class="syntax-checking" />
          <SyntaxError
            v-else-if="isCheckError"
            class="syntax-error" />
          <SyntaxSuccess
            v-else-if="inputContentCheckResult.messageList.length < 1"
            class="syntax-success" />
        </template>
      </BkLoading>
    </div>
  </BkFormItem>
</template>
<script setup lang="ts">
  import {
    onActivated,
    onDeactivated,
    ref,
    shallowRef,
    watch,
  } from 'vue';
  import { useI18n } from 'vue-i18n';

  import type GrammarCheckModel from '@services/model/sql-import/grammar-check';
  import { grammarCheck } from '@services/sqlImport';
  import { getFileContent } from '@services/storage';

  import { useGlobalBizs } from '@stores';

  import { updateFilePath } from '../../../Index.vue';
  import Editor from '../editor/Index.vue';

  import SyntaxChecking from './components/SyntaxChecking.vue';
  import SyntaxError from './components/SyntaxError.vue';
  import SyntaxSuccess from './components/SyntaxSuccess.vue';

  interface Props {
    modelValue: string[]
  }
  interface Emits {
    (e: 'change', value: string[]): void;
    (e: 'grammar-check', doCheck: boolean, checkPass: boolean): void;
  }

  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();

  const { currentBizId } = useGlobalBizs();
  const { t } = useI18n();

  let isKeepAliveActive = false;

  const isLoading = ref(false);
  const content = ref('');
  const isSubmited = ref(false);
  const isChecking = ref(false);
  const isCheckError = ref(false);

  const inputContentCheckResult = shallowRef({} as GrammarCheckModel);

  let grammarCheckData: Record<string, GrammarCheckModel>;

  const rules = [
    {
      validator: () => {
        if (!isKeepAliveActive) {
          return true;
        }
        const { content, isError } = inputContentCheckResult.value;
        return content && !isError;
      },
      message: t('SQL内容无效'),
      trigger: 'change',
    },
  ];

  // 更具文件路径获取文件内容
  const fetchFileContent = () => {
    if (!updateFilePath.value) {
      return;
    }
    isLoading.value = true;
    getFileContent({
      file_path: `${updateFilePath.value}/${props.modelValue[0]}`,
    })
      .then((data) => {
        content.value = data.content;
      })
      .finally(() => {
        isLoading.value = false;
      });
  };

  watch(content, () => {
    inputContentCheckResult.value = {} as GrammarCheckModel;
  });

  let isInnerChange = false;
  // 内容回填时需要根据文件名获取文件内容
  watch(() => props.modelValue, () => {
    if (isInnerChange) {
      isInnerChange = false;
      return;
    }
    if (props.modelValue.length < 1) {
      return;
    }
    fetchFileContent();
  }, {
    immediate: true,
  });

  const triggerChange = () => {
    if (!grammarCheckData) {
      return;
    }
    isInnerChange = true;
    const [fileName] = Object.keys(grammarCheckData);
    const [checkResult] = Object.values(grammarCheckData);
    inputContentCheckResult.value = checkResult;
    emits('change', [fileName]);
    emits('grammar-check', true, !checkResult.isError);
  };

  const handleGrammarCheck = () => {
    isSubmited.value = true;
    isChecking.value = true;
    isCheckError.value = false;
    const params = new FormData();
    params.append('sql_content', content.value);
    grammarCheck({
      bk_biz_id: currentBizId,
      body: params,
    }).then((data) => {
      grammarCheckData = data;
      triggerChange();
    })
      .catch(() => {
        isCheckError.value = true;
        emits('grammar-check', true, false);
      })
      .finally(() => {
        isChecking.value = false;
      });
  };

  const handleEditorChange = () => {
    isSubmited.value = false;
    inputContentCheckResult.value = {} as GrammarCheckModel;
    emits('grammar-check', false, false);
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
  .sql-execute-manual-input {
    position: relative;

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
