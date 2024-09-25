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
  <BkDialog
    :is-show="isShow"
    :quick-close="false"
    :title="t('新建开区_批量录入')"
    :width="800"
    @closed="handleClose">
    <div class="batch-input">
      <div class="batch-input-format">
        <div class="batch-input-format-item">
          <strong>{{ t('目标集群') }}</strong>
          <p class="pt-8">target-cluster.db</p>
        </div>
        <div
          v-for="variableName in variableList"
          :key="variableName"
          class="batch-input-format-item">
          <strong>{{ variableName }}</strong>
          <p class="pt-8">test</p>
        </div>
        <div class="batch-input-format-item">
          <strong>{{ t('授权IP') }}</strong>
          <p class="pt-8">
            null
            <DbIcon
              v-bk-tooltips="t('复制格式')"
              class="batch-input-copy"
              type="copy"
              @click="handleCopy" />
          </p>
        </div>
      </div>
      <BkInput
        ref="inputRef"
        v-model="state.values"
        class="batch-input-textarea"
        :placeholder="placeholder"
        :rows="20"
        style="height: 320px; margin: 12px 0 30px"
        type="textarea"
        @input="handleInput" />
      <div class="batch-input-errors">
        <span
          v-if="state.formatError.show"
          class="mr-8">
          <I18nT
            keypath="n处录入格式错误"
            tag="span">
            <strong>{{ state.formatError.count }}</strong>
          </I18nT>
          <DbIcon
            v-bk-tooltips="t('标记错误')"
            class="batch-input-errors-icon"
            type="audit"
            @click="handleSelectionError('formatError')" />
        </span>
      </div>
    </div>
    <template #footer>
      <BkButton
        class="mr-8 w-88"
        :disabled="loading"
        :loading="loading"
        theme="primary"
        @click="handleConfirm">
        {{ t('确定') }}
      </BkButton>
      <BkButton
        class="w-88"
        @click="handleClose">
        {{ t('取消') }}
      </BkButton>
    </template>
  </BkDialog>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import { getTendbClusterList } from '@services/source/tendbcluster';

  import { useCopy } from '@hooks';

  import type { IData } from './Row.vue';

  interface Emits {
    (e: 'change', value: Array<IData>): void;
  }

  interface Props {
    variableList: string[];
  }

  type SpiderModel = ServiceReturnType<typeof getTendbClusterList>['results'][number];

  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();

  const isShow = defineModel<boolean>({
    default: false,
  });

  const { t } = useI18n();
  const copy = useCopy();

  const inputRef = ref();
  const loading = ref(false);

  const state = reactive({
    values: '',
    formatError: {
      show: false,
      selectionStart: 0,
      selectionEnd: 0,
      count: 0,
    },
  });

  const placeholder = t(
    '请分别输入目标集群（单个），一个或多个变量值，授权IP（可为多个英文逗号分隔）\n多个对象 ，换行分隔',
  );

  /**
   * 复制格式
   */
  const handleCopy = () => {
    copy(`target-cluster.db ${props.variableList.join(' ')} null`);
  };

  /**
   * 标记错误信息
   */
  const handleSelectionError = (key: 'formatError') => {
    const { selectionStart, selectionEnd } = state[key];
    const textarea = inputRef.value?.$el?.getElementsByTagName?.('textarea')?.[0];
    if (textarea) {
      (textarea as HTMLInputElement).focus();
      (textarea as HTMLInputElement).setSelectionRange(selectionStart, selectionEnd);
    }
  };

  const handleInput = () => {
    state.formatError.show = false;
  };

  const handleClose = () => {
    const init = {
      show: false,
      selectionStart: 0,
      selectionEnd: 0,
      count: 0,
    };
    state.formatError = { ...init };
    state.values = '';
    isShow.value = false;
  };

  const handleConfirm = async () => {
    if (state.values === '') {
      handleClose();
      return;
    }

    const newLines: string[] = [];
    const lines = state.values.split('\n').filter((text) => text);

    const getContents = (value: string) => {
      const contents = value
        .trim() // 清除前后空格
        .replace(/\s+/g, ' ') // 替换多余空格
        .split(' '); // 通过空格分割
      return contents;
    };

    // 处格式错误
    for (let i = lines.length - 1; i >= 0; i--) {
      const contents = getContents(lines[i]);
      if (contents.length !== props.variableList.length + 2 || contents.some((text) => !text)) {
        const remove = lines.splice(i, 1);
        newLines.push(...remove);
      }
    }
    const count = newLines.length;
    state.formatError.count = count;
    state.formatError.selectionStart = 0;
    state.formatError.selectionEnd = newLines.join('\n').length;
    state.formatError.show = count > 0;

    // 将调整好的内容回填显示
    newLines.push(...lines); // 没有错误内容回填
    state.values = newLines.join('\n');

    if (state.formatError.show) {
      return;
    }

    loading.value = true;
    const newLineInfos = newLines.map((item) => getContents(item));
    const clusters = newLineInfos.map((item) => item[0]);
    const clusterInfoResults = await getTendbClusterList({
      offset: 0,
      limit: -1,
      domain: clusters.join(','),
    }).finally(() => {
      loading.value = false;
    });
    const clusterInfoMap = clusterInfoResults.results.reduce(
      (results, item) => {
        Object.assign(results, {
          [item.master_domain]: item,
        });
        return results;
      },
      {} as Record<string, SpiderModel>,
    );
    const res = newLineInfos.map((rowValues) => {
      const domain = rowValues[0];
      const ips = rowValues[rowValues.length - 1];
      const rowInfo = {
        clusterData: {
          id: clusterInfoMap[domain].id,
          master_domain: domain,
          bk_biz_id: clusterInfoMap[domain].bk_biz_id,
          bk_cloud_id: clusterInfoMap[domain].bk_cloud_id,
          bk_cloud_name: clusterInfoMap[domain].bk_cloud_name,
        },
        vars: {},
        authorizeIps: ips === 'null' ? [] : ips.split(','),
      };
      const varValues = rowValues.slice(1, rowValues.length - 1);
      props.variableList.forEach((varName, index) => {
        Object.assign(rowInfo.vars, {
          [varName]: varValues[index],
        });
      });
      return rowInfo;
    });
    emits('change', res);
    handleClose();
  };
</script>

<style lang="less" scoped>
  .batch-input {
    position: relative;

    .batch-input-format {
      display: flex;
      padding: 16px;
      background-color: #f5f7fa;
      border-radius: 2px;

      .batch-input-format-item {
        margin-right: 24px;
        font-size: @font-size-mini;
      }
    }

    .batch-input-copy {
      color: @primary-color;
      cursor: pointer;
    }

    .batch-input-textarea {
      height: 310px;
      margin: 16px 0 30px;

      :deep(textarea) {
        &::selection {
          background-color: #fdd;
        }
      }
    }

    .batch-input-errors {
      position: absolute;
      bottom: 8px;
      font-size: @font-size-mini;
      color: @danger-color;

      .batch-input-errors-icon {
        font-size: @font-size-large;
        color: @gray-color;
        cursor: pointer;

        &:hover {
          color: @default-color;
        }
      }
    }
  }
</style>
