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
  <div class="instance-selector-manual-input">
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
              class="w88"
              size="small"
              @click="() => inputState.values = ''">
              {{ $t('清空') }}
            </BkButton>
          </div>
        </div>
      </template>
      <template #main>
        <BkLoading :loading="inputState.isLoading">
          <RenderManualHost
            :last-values="lastValues"
            :role="role"
            :table-data="inputState.tableData"
            :table-settings="tableSettings"
            @change="handleHostChange" />
        </BkLoading>
      </template>
    </BkResizeLayout>
  </div>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import { checkInstances } from '@services/clusters';
  import type { InstanceInfos } from '@services/types/clusters';

  import { useGlobalBizs } from '@stores';

  import { DBTypes } from '@common/const';
  import { ipPort } from '@common/regex';

  import type { InstanceSelectorValues } from '../Index.vue';

  import RenderManualHost from './RenderManualHost.vue';

  import type { TableProps } from '@/types/bkui-vue';

  interface Props {
    role?: string,
    lastValues: InstanceSelectorValues,
    tableSettings: TableProps['settings'],
  }

  interface Emits {
    (e: 'change', value: InstanceSelectorValues): void
  }
  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();

  const { t } = useI18n();
  const { currentBizId } = useGlobalBizs();
  const inputRef = ref();

  const inputState = reactive({
    values: '',
    placeholder: t('请输入IP_Port_如_1_1_1_1_10000_多个可使用换行_空格或_分隔'),
    isLoading: false,
    tableData: [] as InstanceInfos[],
  });
  const errorState = reactive({
    format: {
      show: false,
      selectionStart: 0,
      selectionEnd: 0,
      count: 0,
    },
    instance: {
      show: false,
      selectionStart: 0,
      selectionEnd: 0,
      count: 0,
    },
  });

  const handleHostChange = (values: InstanceSelectorValues) => {
    emits('change', values);
  };

  const handleInput = () => {
    errorState.format.show = false;
    errorState.instance.show = false;
  };

  /**
   * 标记错误
   */
  const handleSelectionError = (key: 'format' | 'instance') => {
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
  const getValues = () => inputState.values
    .replace(/\s+|[；，｜]/g, ' ') // 将空格 换行符 ；，｜符号统一为空格
    .split(' ')
    .filter(value => value);

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
      const res = await checkInstances(currentBizId, { instance_addresses: lines });
      const legalInstances: InstanceInfos[] = [];
      for (let i = lines.length - 1; i >= 0; i--) {
        const item = lines[i];
        const infos = res[i];
        const remove = lines.splice(i, 1);
        const isExisted = res.find(existItem => (
          // existItem.instance_address === item && (!props.role || props.role === existItem.role)
          existItem.instance_address === item
        ));
        if (!isExisted) {
          newLines.push(...remove);
        } else {
          legalInstances.push(infos);
        }
      }
      inputState.tableData.splice(0, inputState.tableData.length, ...legalInstances);
      errorState.instance.count = newLines.length - count;
      const { selectionEnd } = errorState.format;
      errorState.instance.selectionStart = selectionEnd === 0 ? 0 : selectionEnd + 1;
      errorState.instance.selectionEnd = newLines.join('\n').length;

      // 解析完成后选中
      const lastValues = { ...props.lastValues };
      for (const item of inputState.tableData) {
        const list = lastValues.idleHosts;
        const isExisted = list.find(i => `${i.ip}_${i.bk_cloud_id}` === `${item.ip}_${item.bk_cloud_id}`);
        if (!isExisted) {
          item.cluster_domain = item.master_domain;
          lastValues.idleHosts.push(item);
        }
      }
      emits('change', {
        ...props.lastValues,
        ...lastValues,
      });
    } catch (_) {
      console.log(_);
    }
    console.log('ip格式错误', count);
    errorState.format.show = count > 0;
    errorState.instance.show = newLines.slice(count).length > 0;
    inputState.isLoading = false;

    // 将调整好的内容回填显示
    newLines.push(...lines); // 没有错误内容回填
    inputState.values = newLines.join('\n');
  };
</script>

<style lang="less">
  .instance-selector-manual-input {
    height: 600px;
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
      margin-top: 12px;

      .bk-button {
        &:first-child {
          flex: 1;
        }
      }
    }
  }
</style>
