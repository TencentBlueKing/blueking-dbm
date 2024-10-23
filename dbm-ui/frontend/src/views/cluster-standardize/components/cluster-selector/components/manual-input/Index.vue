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
  <div class="selector-manual-input">
    <BkResizeLayout
      :border="false"
      collapsible
      initial-divide="480px"
      :max="600"
      :min="420">
      <template #aside>
        <div class="manual-input-wrapper">
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
                v-bk-tooltips="t('标记错误')"
                class="manual-input-icons"
                type="audit"
                @click="handleSelectionError('format')" />
            </span>
            <span v-if="errorState.domain.show">
              <I18nT
                keypath="n处domain不存在"
                tag="span">
                <strong>{{ errorState.domain.count }}</strong>
              </I18nT>
              <DbIcon
                v-bk-tooltips="t('标记错误')"
                class="manual-input-icons"
                type="audit"
                @click="handleSelectionError('domain')" />
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
              {{ t('解析并添加') }}
            </BkButton>
            <BkButton
              class="w-88"
              size="small"
              @click="handleClear">
              {{ t('清空') }}
            </BkButton>
          </div>
        </div>
      </template>
      <template #main>
        <BkLoading :loading="inputState.isLoading">
          <Table
            :checked="checkedMap"
            :table-data="tableData"
            @change="handleChange" />
        </BkLoading>
      </template>
    </BkResizeLayout>
  </div>
</template>
<script setup lang="ts" generic="T extends TendbhaModel">
  import { useI18n } from 'vue-i18n';

  import type TendbhaModel from '@services/model/mysql/tendbha';
  import { checkDomains } from '@services/source/mysql';

  import { domainRegex } from '@common/regex';

  import Table from './Table.vue';

  interface Props {
    checked: Record<string, T>;
    checkKey?: string;
  }

  interface Emits {
    (e: 'change', value: Props['checked']): void;
  }
  const props = withDefaults(defineProps<Props>(), {
    checkKey: 'master_domain',
  });
  const emits = defineEmits<Emits>();

  const { t } = useI18n();
  const inputRef = ref();
  const checkedMap = computed(() => props.checked);

  const inputState = reactive({
    values: '',
    placeholder: t('请输入访问入口_多个可使用换行_空格或_分隔'),
    isLoading: false,
  });
  const tableData = shallowRef<T[]>([]);
  const errorState = reactive({
    format: {
      show: false,
      selectionStart: 0,
      selectionEnd: 0,
      count: 0,
    },
    domain: {
      show: false,
      selectionStart: 0,
      selectionEnd: 0,
      count: 0,
    },
  });

  const handleChange = (checked: Props['checked']) => {
    emits('change', checked);
  };

  const handleInput = () => {
    errorState.format.show = false;
    errorState.domain.show = false;
  };

  /**
   * 标记错误
   */
  const handleSelectionError = (key: 'format' | 'domain') => {
    const { selectionStart, selectionEnd } = errorState[key];
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
    // 不合法的输入行
    const legalLines: string[] = [];
    const lines = getValues();

    // 处理格式错误
    for (let i = lines.length - 1; i >= 0; i--) {
      const value = lines[i];
      if (!domainRegex.test(value)) {
        const remove = lines.splice(i, 1);
        legalLines.push(...remove);
      }
    }
    const count = legalLines.length;
    errorState.format.count = count;
    errorState.format.selectionStart = 0;
    errorState.format.selectionEnd = legalLines.join('\n').length;

    // 检查 domain 是否存在
    inputState.isLoading = true;
    try {
      const params = {
        domains: lines,
      };
      const results = await checkDomains(params);
      const legalDomains: T[] = [];
      for (let i = lines.length - 1; i >= 0; i--) {
        const item = lines[i];
        const infos = results[i];
        const remove = lines.splice(i, 1);
        const isExisted = results.find((existItem) => existItem[props.checkKey as keyof TendbhaModel] === item);
        if (!isExisted) {
          legalLines.push(...remove);
        } else {
          legalDomains.push(infos as T);
        }
      }
      tableData.value.splice(0, tableData.value.length, ...legalDomains);
      errorState.domain.count = legalLines.length - count;
      const { selectionEnd } = errorState.format;
      errorState.domain.selectionStart = selectionEnd === 0 ? 0 : selectionEnd + 1;
      errorState.domain.selectionEnd = legalLines.join('\n').length;

      // 解析完成后选中
      const checked = { ...props.checked };
      for (const item of tableData.value) {
        const domain = item.master_domain;
        checked[domain] = item as T;
      }
      emits('change', checked);
    } catch (_) {
      console.error(_);
    }
    errorState.format.show = count > 0;
    errorState.domain.show = legalLines.slice(count).length > 0;
    inputState.isLoading = false;

    // 将调整好的内容回填显示
    legalLines.push(...lines); // 没有错误内容回填
    inputState.values = legalLines.join('\n');
  };

  const handleClear = () => {
    inputState.values = '';
    errorState.format.show = false;
    errorState.domain.show = false;
  };
</script>

<style lang="less">
  .selector-manual-input {
    height: 585px;
    padding-top: 16px;

    .bk-resize-layout {
      height: 100%;
    }

    .manual-input-wrapper {
      padding: 0 16px;
    }

    .manual-input-textarea {
      height: 508px;
      margin-bottom: 8px;

      textarea {
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
