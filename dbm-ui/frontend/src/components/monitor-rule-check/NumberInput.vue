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
  <div
    class="input-box"
    :class="{ 'is-input-empty': isEmpty }">
    <BkInput
      v-model.number="modelValue"
      class="input"
      :disabled="disabled"
      :placeholder="t('请输入')"
      type="number" />
    <span>{{ unit }}</span>
    <div class="up-down">
      <DbIcon
        class="icon"
        type="up-big"
        @click="handleClickUp" />
      <DbIcon
        class="icon"
        type="down-big"
        @click="handleClickDown" />
    </div>
  </div>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  interface Props {
    unit?: string;
    disabled?: boolean;
  }

  const props = withDefaults(defineProps<Props>(), {
    unit: '%',
    disabled: false,
  });

  const { t } = useI18n();

  interface Exposes {
    getValue: () => number;
  }

  const modelValue = defineModel<number>({
    default: 0,
  });

  const isEmpty = computed(() => typeof modelValue.value === 'string');

  watch(modelValue, () => {
    window.changeConfirm = true;
  });

  const handleClickUp = () => {
    if (props.disabled) {
      return;
    }
    modelValue.value = Number(modelValue.value) + 1;
  };

  const handleClickDown = () => {
    if (props.disabled) {
      return;
    }
    if (modelValue.value === 0) {
      return;
    }
    modelValue.value = Number(modelValue.value) - 1;
  };

  defineExpose<Exposes>({
    getValue() {
      return modelValue.value;
    },
  });
</script>
<style lang="less" scoped>
  .input-box {
    display: flex;
    width: 100%;
    align-items: center;
    border-bottom: 1px solid #c4c6cc;

    .input {
      width: 60px;
      border: none;
      outline: none;
      box-shadow: none;

      input {
        border: none;
        outline: none;
      }
    }

    .up-down {
      display: flex;
      width: 10px;
      margin-right: 5px;
      margin-left: 10px;
      flex-direction: column;
      cursor: pointer;

      .icon {
        font-size: 12px;
      }
    }

    :deep(.bk-input--number-control) {
      display: none;
    }
  }

  .is-input-empty {
    :deep(.bk-input--text) {
      background-color: #fff0f1;
    }
  }
</style>
