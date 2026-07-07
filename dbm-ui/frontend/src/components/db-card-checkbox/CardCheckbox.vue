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
    v-bk-tooltips="{
      disabled: !disabled || !disabledTooltips,
      content: disabledTooltips,
    }"
    class="card-checkbox"
    :class="statusClass"
    :style="{
      minWidth: `${minWidth}px`,
    }"
    @click="handleChange">
    <div
      v-if="icon"
      class="card-checkbox-icon">
      <DbIcon :type="icon" />
    </div>
    <div class="card-checkbox-content">
      <strong class="card-checkbox-title">{{ title }}</strong>
      <template v-if="descList.length">
        <p
          v-for="item in descList"
          :key="item"
          class="card-checkbox-desc">
          {{ item }}
        </p>
      </template>
      <p
        v-else
        class="card-checkbox-desc">
        {{ desc }}
      </p>
    </div>
  </div>
</template>

<script setup lang="ts">
  interface Props {
    checked?: boolean;
    desc?: string;
    descList?: string[];
    disabled?: boolean;
    disabledTooltips?: string;
    falseValue?: boolean | string;
    icon?: string;
    minWidth?: number;
    modelValue?: boolean | string;
    title?: string;
    trueValue?: boolean | string;
  }

  type Emits = (e: 'update:modelValue', value: boolean | string) => void;

  const props = withDefaults(defineProps<Props>(), {
    checked: false,
    desc: 'desc',
    descList: () => [],
    disabled: false,
    disabledTooltips: '',
    falseValue: false,
    icon: '',
    minWidth: 362,
    modelValue: false,
    title: 'title',
    trueValue: true,
  });

  const emits = defineEmits<Emits>();

  const statusClass = computed(() => ({
    'card-checkbox--disabled': props.disabled,
    'card-checkbox--selected': props.modelValue === props.trueValue || props.checked,
    'card-checkbox-initial-height': props.descList.length > 0,
  }));

  const handleChange = () => {
    if (props.disabled || props.modelValue === props.trueValue) {
      return;
    }

    const isSelected = props.modelValue === props.trueValue;
    emits('update:modelValue', isSelected ? props.falseValue : props.trueValue);
  };
</script>

<style lang="less" scoped>
  .card-checkbox {
    position: relative;
    display: inline-flex;
    height: 64px;
    color: @gray-color;
    border: 1px solid #c4c6cc;
    border-radius: 2px;

    .card-checkbox-icon {
      display: flex;
      width: 56px;
      font-size: 32px;
      line-height: 62px;
      text-align: center;
      background-color: #fafbfd;
      flex-shrink: 0;
      align-items: center;
      justify-content: center;
    }

    .card-checkbox-content {
      padding: 8px 12px;
      font-size: @font-size-mini;
      line-height: 20px;
      border-left: 1px solid #c4c6cc;
    }

    .card-checkbox-title {
      display: inline-block;
      color: @title-color;
    }

    .card-checkbox-desc {
      padding-top: 4px;
    }

    &:not(&.card-checkbox--disabled) {
      cursor: pointer;
    }

    &.card-checkbox--disabled {
      color: @disable-color;
      cursor: not-allowed;
      border-color: @border-disable;

      .card-checkbox-icon {
        background-color: #fafbfd;
      }

      .card-checkbox-title {
        color: @gray-color;
      }

      .card-checkbox-content {
        border-color: @border-disable;
      }
    }

    &:hover:not(&.card-checkbox--disabled),
    &.card-checkbox--selected {
      background-color: #f5f7fa;
      border-color: @border-primary;

      .card-checkbox-icon {
        color: @primary-color;
        background-color: #e1ecff;
      }

      .card-checkbox-content {
        border-color: @border-primary;
      }
    }

    &.card-checkbox--selected {
      &::before {
        position: absolute;
        top: 0;
        right: 0;
        border: 18px solid transparent;
        border-top-color: @border-primary;
        border-right-color: @border-primary;
        content: '';
      }

      &::after {
        position: absolute;
        top: 2px;
        right: 8px;
        width: 5px;
        height: 10px;
        border-top: 2px solid white;
        border-left: 2px solid white;
        content: '';
        transform: rotate(-135deg);
      }
    }
  }

  .card-checkbox-initial-height {
    height: initial;
  }
</style>
