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
          class="batch-input-format-item"
          v-for="(item, index) in props.config"
          :key="index">
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
        :placeholder="placeholder"
        type="textarea"
        @input="handleInput" />
      <div class="batch-input-errors">
        <span
          v-if="state.rowError.show"
          class="mr-8">
          <I18nT
            keypath="n处录入格式错误_检查是否缺少字段"
            tag="span">
            <strong>{{ state.rowError.count }}</strong>
          </I18nT>
          <DbIcon
            v-bk-tooltips="t('标记错误')"
            class="batch-input-errors-icon"
            type="audit"
            @click="handleSelectionError('rowError')" />
        </span>
        <span
          v-if="state.cellError.show"
          class="mr-8">
          <I18nT
            keypath="n处字段值格式错误_检查字段值是否必填_是否符合规则"
            tag="span">
            <strong>{{ state.cellError.count }}</strong>
          </I18nT>
          <DbIcon
            v-bk-tooltips="t('标记错误')"
            class="batch-input-errors-icon"
            type="audit"
            @click="handleSelectionError('cellError')" />
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
      regExp?: RegExp;
      key: string;
      label: string;
      required: boolean;
      case: string;
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
    rowError: {
      count: 0,
      selectionEnd: 0,
      selectionStart: 0,
      show: false,
    },
    cellError: {
      count: 0,
      selectionEnd: 0,
      selectionStart: 0,
      show: false,
    },
    values: '',
  });

  const placeholder = computed(() =>
    t('请输入label_如: case_多个对象_换行分隔_非必填用null代替', {
      label: props.config.map((item) => item.label).join('、'),
      case: props.config.map((item) => item.case).join('、'),
    }),
  );

  /**
   * 复制格式
   */
  function handleCopy() {
    copy(props.config.map((item) => `${item.case}`).join('\t'));
  }

  /**
   * 标记错误信息
   */
  function handleSelectionError(key: 'rowError' | 'cellError') {
    const { selectionEnd, selectionStart } = state[key];
    const textarea = inputRef.value?.$el?.getElementsByTagName?.('textarea')?.[0];
    if (textarea) {
      (textarea as HTMLInputElement).focus();
      (textarea as HTMLInputElement).setSelectionRange(selectionStart, selectionEnd);
    }
  }

  function handleInput() {
    state.rowError.show = false;
  }

  function handleClose() {
    const init = {
      count: 0,
      selectionEnd: 0,
      selectionStart: 0,
      show: false,
    };
    state.rowError = { ...init };
    state.values = '';
    isShow.value = false;
  }

  function handleConfirm() {
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

    // 行格式错误
    for (let i = lines.length - 1; i >= 0; i--) {
      const contents = getContents(lines[i]);
      if (contents.length !== props.config.length || contents.some((text) => !text)) {
        const remove = lines.splice(i, 1);
        newLines.push(...remove);
      }
    }
    const count = newLines.length;
    state.rowError.count = count;
    state.rowError.selectionStart = 0;
    state.rowError.selectionEnd = newLines.join('\n').length;
    state.rowError.show = count > 0;

    // 单元格格式错误
    for (let i = lines.length - 1; i >= 0; i--) {
      getContents(lines[i]).forEach((item, index) => {
        // 正则表达式校验
        const regExp = props.config[index].regExp;
        if (regExp && !regExp.test(item)) {
          const remove = lines.splice(i, 1);
          newLines.push(...remove);
        }
        // 非空校验
        const required = props.config[index].required;
        if (required && item === 'null') {
          const remove = lines.splice(i, 1);
          newLines.push(...remove);
        }
      });
    }
    state.cellError.count = newLines.length - count;
    state.cellError.selectionStart = state.rowError.selectionEnd === 0 ? 0 : state.rowError.selectionEnd + 1;
    state.cellError.selectionEnd = newLines.join('\n').length;
    state.cellError.show = newLines.slice(count).length > 0;

    // 将调整好的内容回填显示
    newLines.push(...lines); // 没有错误内容回填
    state.values = newLines.join('\n');

    if (state.rowError.show || state.cellError.show) {
      return;
    }

    const res = newLines.map((item) => {
      const contents = getContents(item);
      return props.config.reduce<Record<string, any>>((acc, cur, index) => {
        const value = contents[index];
        acc[cur.key] = value === 'null' ? '' : value;
        return acc;
      }, {});
    });
    emits('change', res);
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
