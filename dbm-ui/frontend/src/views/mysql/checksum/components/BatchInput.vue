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
    :title="$t('数据校验修复_批量录入') "
    :width="1200"
    @closed="handleClose">
    <div class="batch-input">
      <div class="batch-input-format">
        <div class="batch-input-format__item">
          <strong>{{ $t('目标集群') }}</strong>
          <p class="pt-8">
            target-cluster.db
          </p>
        </div>
        <div class="batch-input-format__item">
          <strong>{{ $t('校验主库') }}</strong>
          <p class="pt-8">
            127.0.0.1:10000
          </p>
        </div>
        <div class="batch-input-format__item">
          <strong>{{ $t('校验从库') }}</strong>
          <p class="pt-8">
            127.0.0.2:20000
          </p>
        </div>
        <div class="batch-input-format__item">
          <strong>{{ $t('校验DB') }}</strong>
          <p class="pt-8">
            testDB,mysqlDB
          </p>
        </div>
        <div class="batch-input-format__item">
          <strong>{{ $t('校验表名') }}</strong>
          <p class="pt-8">
            test%
          </p>
        </div>
        <div class="batch-input-format__item">
          <strong>{{ $t('忽略DB名') }}</strong>
          <p class="pt-8">
            null
          </p>
        </div>
        <div class="batch-input-format__item">
          <strong>{{ $t('忽略表名') }}</strong>
          <p class="pt-8">
            null
            <DbIcon
              v-bk-tooltips="$t('复制格式')"
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
            v-bk-tooltips="$t('标记错误')"
            class="batch-input-errors__icon"
            type="audit"
            @click="handleSelectionError('formatError')" />
        </span>
        <span
          v-if="state.instError.show"
          class="mr-8">
          <I18nT
            keypath="n处IP_Port格式错误"
            tag="span">
            <strong>{{ state.instError.count }}</strong>
          </I18nT>
          <DbIcon
            v-bk-tooltips="$t('标记错误')"
            class="batch-input-errors__icon"
            type="audit"
            @click="handleSelectionError('instError')" />
        </span>
      </div>
    </div>
    <template #footer>
      <BkButton
        class="mr-8 w-88"
        theme="primary"
        @click="handleConfirm">
        {{ $t('确定') }}
      </BkButton>
      <BkButton
        class="w-88"
        @click="handleClose">
        {{ $t('取消') }}
      </BkButton>
    </template>
  </BkDialog>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import { useCopy } from '@hooks';

  import { ipPort } from '@common/regex';

  import type { InputItem } from '../common/types';

  interface Emits {
    (e: 'update:isShow', value: boolean): void
    (e: 'change', value: Array<InputItem>): void
  }

  interface Props {
    isShow: boolean,
  }

  defineProps<Props>();
  const emits = defineEmits<Emits>();

  const { t } = useI18n();
  const copy = useCopy();
  const inputRef = ref();
  const placeholder = t('请分别输入目标集群_校验主库_校验从库_校验DB_校验表名_忽略DB名_忽略表名_多个对象_换行分隔');

  const state = reactive({
    values: '',
    formatError: {
      show: false,
      selectionStart: 0,
      selectionEnd: 0,
      count: 0,
    },
    instError: {
      show: false,
      selectionStart: 0,
      selectionEnd: 0,
      count: 0,
    },
  });

  /**
   * 复制格式
   */
  function handleCopy() {
    copy('target-cluster.db    127.0.0.1:10000    127.0.0.2:20000    testDB,mysqlDB    test%    null    null');
  }

  /**
   * 标记错误信息
   */
  function handleSelectionError(key: 'formatError' | 'instError') {
    const { selectionStart, selectionEnd } = state[key];
    const textarea = inputRef.value?.$el?.getElementsByTagName?.('textarea')?.[0];
    if (textarea) {
      (textarea as HTMLInputElement).focus();
      (textarea as HTMLInputElement).setSelectionRange(selectionStart, selectionEnd);
    }
  }

  function handleInput() {
    state.formatError.show = false;
  }

  function handleClose() {
    const init = {
      show: false,
      selectionStart: 0,
      selectionEnd: 0,
      count: 0,
    };
    state.formatError = { ...init };
    state.values = '';
    emits('update:isShow', false);
  }

  function handleConfirm() {
    if (state.values === '') {
      handleClose();
      return;
    }

    const newLines: string[] = [];
    const lines = state.values.split('\n').filter(text => text);
    const getContents = (value: string) => {
      const contents = value.trim() // 清除前后空格
        .replace(/\s+/g, ' ') // 替换多余空格
        .split(' '); // 通过空格分割
      return contents;
    };

    // 处格式错误
    for (let i = lines.length - 1; i >= 0; i--) {
      const contents = getContents(lines[i]);
      if (contents.length !== 7 || contents.some(text => !text)) {
        const remove = lines.splice(i, 1);
        newLines.push(...remove);
      }
    }
    const count = newLines.length;
    state.formatError.count = count;
    state.formatError.selectionStart = 0;
    state.formatError.selectionEnd = newLines.join('\n').length;
    state.formatError.show = count > 0;

    // IP:Port 格式错误
    for (let i = lines.length - 1; i >= 0; i--) {
      const contents = getContents(lines[i]);
      const slaves = (contents[2] || '').split(',');
      if (ipPort.test(contents[1]) === false || slaves.some(inst => ipPort.test(inst) === false)) {
        const remove = lines.splice(i, 1);
        newLines.push(...remove);
      }
    }
    state.instError.count = newLines.length - count;
    state.instError.selectionStart = state.formatError.selectionEnd === 0 ? 0 : state.formatError.selectionEnd + 1;
    state.instError.selectionEnd = newLines.join('\n').length;
    state.instError.show = newLines.slice(count).length > 0;

    // 将调整好的内容回填显示
    newLines.push(...lines); // 没有错误内容回填
    state.values = newLines.join('\n');

    if (state.formatError.show || state.instError.show) return;

    const getValue = (value: string) => value.split(',');
    const res = newLines.map((item) => {
      const [cluster, master, slaves, dbs, tables, ignoreDBs, ignoreTables] = getContents(item);
      return {
        cluster,
        master,
        slaves: slaves.split(',').filter(inst => ipPort.test(inst)),
        dbs: getValue(dbs),
        ignoreDBs: ignoreDBs === 'null' ? [] : getValue(ignoreDBs),
        tables: getValue(tables),
        ignoreTables: ignoreTables === 'null' ? [] : getValue(ignoreTables),
      };
    });
    emits('change', res);
    handleClose();
  }
</script>

<style lang="less" scoped>
.batch-input {
  position: relative;

  .batch-input-format {
    display: flex;
    padding: 16px;
    background-color: #f5f7fa;
    border-radius: 2px;

    .batch-input-format__item {
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

    .batch-input-errors__icon {
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
