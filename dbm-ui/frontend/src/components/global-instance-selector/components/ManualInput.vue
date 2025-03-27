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
  <div class="global-instance-selector-manual-input">
    <BkInput
      ref="inputRef"
      v-model.trim="inputState.values"
      class="manual-input-textarea"
      :placeholder="inputState.placeholder"
      type="textarea"
      @input="handleInput" />
    <div class="manual-input-errors">
      <span
        v-if="errorState.format.show"
        class="mr-8">
        <I18nT
          keypath="n处格式错误"
          tag="span">
          <strong>{{ errorState.format.count }}</strong>
        </I18nT>
        <DbIcon
          v-bk-tooltips="$t('标记错误')"
          class="manual-input-icons"
          type="audit"
          @click="handleSelectionError('format')" />
      </span>
      <span v-if="errorState.instance.show">
        <I18nT
          keypath="n处IP_Port不存在"
          tag="span">
          <strong>{{ errorState.instance.count }}</strong>
        </I18nT>
        <DbIcon
          v-bk-tooltips="$t('标记错误')"
          class="manual-input-icons"
          type="audit"
          @click="handleSelectionError('instance')" />
      </span>
    </div>
    <div class="manual-input-buttons">
      <BkButton
        class="mr-8"
        :disabled="!inputState.values"
        :loading="inputState.isLoading"
        outline
        size="small"
        theme="primary"
        @click="handleParsingValues">
        {{ $t('解析并添加') }}
      </BkButton>
      <BkButton
        class="w-88"
        size="small"
        @click="handleClear">
        {{ $t('清空') }}
      </BkButton>
    </div>
  </div>
</template>
<script setup lang="ts">
  import _ from 'lodash';
  import { useI18n } from 'vue-i18n';

  import { getGlobalInstance } from '@services/source/dbbase';

  import { ipPort } from '@common/regex';

  interface Props {
    params: ServiceParameters<typeof getGlobalInstance>;
  }

  type Emits = (
    e: 'change',
    params: {
      instance?: string;
    },
  ) => void;

  const props = defineProps<Props>();

  const emits = defineEmits<Emits>();

  const { t } = useI18n();
  const inputRef = ref();

  const inputState = reactive({
    isLoading: false,
    placeholder: t('请输入IP_Port_如_1_1_1_1_10000_多个可使用换行_空格或_分隔'),
    values: '',
  });
  const errorState = reactive({
    format: {
      count: 0,
      selectionEnd: 0,
      selectionStart: 0,
      show: false,
    },
    instance: {
      count: 0,
      selectionEnd: 0,
      selectionStart: 0,
      show: false,
    },
  });

  const handleInput = () => {
    errorState.format.show = false;
    errorState.instance.show = false;
  };

  /**
   * 标记错误
   */
  const handleSelectionError = (key: 'format' | 'instance') => {
    const { selectionEnd, selectionStart } = errorState[key];
    const textarea = inputRef.value?.$el?.getElementsByTagName?.('textarea')?.[0];
    if (textarea) {
      (textarea as HTMLInputElement).focus();
      (textarea as HTMLInputElement).setSelectionRange(selectionStart, selectionEnd);
    }
  };

  /**
   * 处理分隔内容，过滤空内容
   */
  const getValues = () =>
    inputState.values
      .replace(/\s+|[；，｜]/g, ' ') // 将空格 换行符 ；，｜符号统一为空格
      .split(' ')
      .filter((value) => value);

  /**
   * 解析输入内容
   */
  const handleParsingValues = async () => {
    const newLines: string[] = [];
    const lines = getValues();

    // 处理格式错误
    for (let i = lines.length - 1; i >= 0; i--) {
      const value = lines[i];
      if (!ipPort.test(value)) {
        const remove = lines.splice(i, 1);
        newLines.push(...remove);
      }
    }
    const count = newLines.length;
    errorState.format.count = count;
    errorState.format.selectionStart = 0;
    errorState.format.selectionEnd = newLines.join('\n').length;

    // 检查 IP:Port 是否存在
    inputState.isLoading = true;
    try {
      const { results } = await getGlobalInstance({
        ...props.params,
        instance_address: lines.join(','),
      });
      // 去重
      const uniqRes = _.uniqBy(results, 'instance_address');

      const legalInstances = [];
      for (let i = lines.length - 1; i >= 0; i--) {
        const item = lines[i];
        const remove = lines.splice(i, 1);
        const isExisted = uniqRes.find((cur) => cur.instance_address === item);
        if (!isExisted) {
          newLines.push(...remove);
        } else {
          legalInstances.push(item);
        }
      }
      errorState.instance.count = newLines.length - count;
      const { selectionEnd } = errorState.format;
      errorState.instance.selectionStart = selectionEnd === 0 ? 0 : selectionEnd + 1;
      errorState.instance.selectionEnd = newLines.join('\n').length;

      // 合法实例作为参数回传
      emits('change', {
        instance: legalInstances.join(','),
      });
    } catch (_) {
      console.error(_);
    }
    errorState.format.show = count > 0;
    errorState.instance.show = newLines.slice(count).length > 0;
    inputState.isLoading = false;

    // 将调整好的内容回填显示
    newLines.push(...lines); // 没有错误内容回填
  };

  const handleClear = () => {
    inputState.values = '';
    errorState.format.show = false;
    errorState.instance.show = false;
  };
</script>

<style lang="less">
  .global-instance-selector-manual-input {
    height: 570px;
    padding: 0 16px;

    .manual-input-textarea {
      height: 508px;
      margin-bottom: 8px;

      textarea {
        height: 100%;

        &::selection {
          background-color: #fdd;
        }
      }
    }

    .manual-input-errors {
      font-size: @font-size-mini;
      color: @danger-color;
    }

    .manual-input-icons {
      font-size: @font-size-large;
      color: @gray-color;
      cursor: pointer;

      &:hover {
        color: @default-color;
      }
    }

    .manual-input-buttons {
      display: flex;
      align-items: center;
      margin-top: 5px;

      .bk-button {
        &:first-child {
          flex: 1;
        }
      }
    }
  }
</style>
