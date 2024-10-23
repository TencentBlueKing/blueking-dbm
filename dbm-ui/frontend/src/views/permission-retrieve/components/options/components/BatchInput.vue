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
  <div class="permission-retrieve-input">
    <div class="input-box">
      <BkInput
        v-model="modelValue"
        autosize
        :placeholder="t('请输入，多个英文逗号或换行分隔，最多n个', { n: maxCount })"
        :resize="false"
        type="textarea"
        @blur="handleBlur"
        @focus="handleFocus">
      </BkInput>
    </div>
    <BkButton
      v-bk-tooltips="t('批量选择')"
      class="input-suffix"
      text
      @click="handleIconClick">
      <DbIcon :type="iconType" />
    </BkButton>
  </div>
</template>

<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';

  import { batchSplitRegex } from '@common/regex';

  interface Props {
    iconType: string;
    maxCount: number;
  }

  interface Emits {
    (e: 'icon-click'): void;
  }

  defineProps<Props>();
  const emits = defineEmits<Emits>();

  const modelValue = defineModel<string>({
    required: true,
  });

  const { t } = useI18n();

  const isFocused = ref(false);

  const handleFocus = () => {
    isFocused.value = true;
    modelValue.value = modelValue.value.replace(batchSplitRegex, '\n');
  };

  const handleBlur = () => {
    isFocused.value = false;
    modelValue.value = modelValue.value.replace(batchSplitRegex, ' | ');
  };

  const handleIconClick = () => {
    emits('icon-click');
  };
</script>

<style lang="less" scoped>
  .permission-retrieve-input {
    position: relative;
    display: flex;

    .input-box {
      position: absolute;
      top: -1px;
      left: 0;
      z-index: 10;
      width: calc(100% - 32px);
      height: 32px;
      flex: 1;

      :deep(.bk-textarea) {
        border-radius: 2px 0 0 2px;

        textarea {
          height: 30px !important;
          min-height: 30px !important;
        }

        &.is-focused {
          textarea {
            max-height: 500px;
            min-height: 100px !important;
          }
        }
      }
    }

    .input-suffix {
      display: flex;
      width: 32px;
      height: 32px;
      margin-left: auto;
      border: 1px solid #c4c6cc;
      border-left: none;
      border-radius: 0 2px 2px 0;
      align-items: center;
      justify-content: center;
    }
  }
</style>
