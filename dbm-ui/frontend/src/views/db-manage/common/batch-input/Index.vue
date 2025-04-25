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
  <BkButton
    class="checksum-batch"
    @click="() => (isShow = true)">
    <i class="db-icon-add" />
    {{ t('批量录入') }}
  </BkButton>
  <BkDialog
    :is-show="isShow"
    :quick-close="false"
    :title="t('xx_批量录入', { title: route.meta.navName })"
    :width="1200"
    @closed="handleClose">
    <div class="batch-input">
      <div class="batch-input-format">
        <div
          v-for="(item, index) in props.config"
          :key="index"
          class="batch-input-format-item">
          <strong
            v-bk-tooltips="{
              content: t('正则校验格式'),
              disabled: !item.regExp,
            }"
            :class="{
              'is-regexp': !!item.regExp,
            }">
            {{ item.label }}
          </strong>
          <span
            v-if="item.required"
            class="required" />
          <p class="pt-8">{{ item.case }}</p>
        </div>
        <DbIcon
          v-bk-tooltips="t('复制格式')"
          class="batch-input-copy"
          type="copy"
          @click="handleCopy" />
      </div>
      <BkInput
        ref="inputRef"
        v-model="state.values"
        class="batch-input-textarea"
        :placeholder="
          t(
            '1. 多个字段以空白符（空格、制表符）分割_2. 列留空，请输入 NULL_3. 日期时间使用T分割。如：2025-03-11T10:26:13_4. 单元格内换行，用\\n 分割。如：我是第一行\\n我是第二行_5. 枚举类型，请输入选项值',
          )
        "
        type="textarea"
        @input="handleInput" />
      <div class="batch-input-errors">
        <span
          v-if="state.formatError.show"
          class="mr-8">
          <I18nT
            keypath="n处错误_检查字段是否必填_是否符合规则"
            tag="span">
            <strong>{{ state.formatError.count }}</strong>
          </I18nT>
          <DbIcon
            v-bk-tooltips="t('标记错误')"
            class="batch-input-errors-icon"
            type="audit"
            @click="handleSelectionError" />
        </span>
      </div>
    </div>
    <template #footer>
      <BkButton
        class="mr-8 w-88"
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

  import { useCopy } from '@hooks';

  interface Props {
    /**
     * @description 批量输入配置
     * @example [{ regExp: RegExp // 正则表达式, key: 'db_name', label: 'DB 名称', required: true, case: 'db1 db2 db3' }]
     * @default []
     */
    config: {
      case: string;
      key: string;
      label: string;
      regExp?: RegExp;
      required: boolean;
    }[];
  }

  type Emits = (e: 'change', data: Record<string, any>[]) => void;

  const props = defineProps<Props>();

  const emits = defineEmits<Emits>();

  const isShow = defineModel<boolean>('isShow', {
    default: false,
  });

  const { t } = useI18n();
  const copy = useCopy();
  const route = useRoute();

  const inputRef = ref();

  const state = reactive({
    formatError: {
      count: 0,
      selectionEnd: 0,
      selectionStart: 0,
      show: false,
    },
    values: '',
  });

  /**
   * 复制格式
   */
  function handleCopy() {
    copy(props.config.map((item) => `${item.case}`).join('\t'));
  }

  /**
   * 标记错误信息
   */
  function handleSelectionError() {
    const { selectionEnd, selectionStart } = state.formatError;
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
    state.formatError = {
      count: 0,
      selectionEnd: 0,
      selectionStart: 0,
      show: false,
    };
    isShow.value = false;
  }

  function handleConfirm() {
    if (state.values === '') {
      handleClose();
      return;
    }

    const newLines: string[] = [];
    const lines = state.values.split(/\n|\\n/).filter((text) => text);

    const getContents = (value: string) => {
      const contents = value
        .trim() // 清除前后空格
        .replace(/\s+/g, ' ') // 替换多余空格
        .split(' '); // 通过空格分割
      return contents;
    };

    for (const [columnIndex, configItem] of props.config.entries()) {
      const { regExp, required } = configItem;
      for (const [rowIndex, row] of lines.entries()) {
        const contents = getContents(row);
        const item = contents[columnIndex];
        // 非空校验
        if (required && !item) {
          const remove = lines.splice(rowIndex, 1);
          newLines.push(...remove);
        }
        // 正则表达式校验
        if (regExp && !regExp.test(item)) {
          const remove = lines.splice(rowIndex, 1);
          newLines.push(...remove);
        }
      }
    }

    state.formatError.count = newLines.length;
    state.formatError.selectionStart = 0;
    state.formatError.selectionEnd = newLines.join('\n').length;
    state.formatError.show = newLines.length > 0;

    // 将调整好的内容回填显示
    newLines.push(...lines); // 没有错误内容回填
    state.values = newLines.join('\n');

    if (state.formatError.show) {
      return;
    }

    const result = newLines.map((item) => {
      const contents = getContents(item);
      return props.config.reduce<Record<string, any>>((acc, cur, index) => {
        const value = contents[index];
        Object.assign(acc, {
          [cur.key]: value === 'NULL' ? '' : value,
        });
        return acc;
      }, {});
    });

    emits('change', result);
    handleClose();
  }
</script>

<style lang="less" scoped>
  .checksum-batch {
    .db-icon-add {
      margin-right: 4px;
      color: @gray-color;
    }
  }

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

    .is-regexp {
      border-bottom: 1px dashed #666;
    }

    .required::after {
      position: relative;
      left: 4px;
      color: @danger-color;
      content: '*';
    }

    .batch-input-copy {
      position: relative;
      top: 26px;
      width: 16px;
      height: 16px;
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
