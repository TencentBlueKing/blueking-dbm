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
    class="card-checkbox"
    :class="statusClass"
    @click="handleChange">
    <div class="card-checkbox__icon">
      <DbIcon :type="icon" />
    </div>
    <div class="card-checkbox__content">
      <strong class="card-checkbox__title">{{ title }}</strong>
      <p class="card-checkbox__desc">
        {{ desc }}
      </p>
    </div>
  </div>
</template>

<script setup lang="ts">
  interface Props {
    title: string;
    desc: string;
    icon: string;
    disabled?: boolean;
    trueValue?: boolean | string;
    falseValue?: boolean | string;
    modelValue?: boolean | string;
    checked?: boolean;
  }

  interface Emits {
    (e: 'update:modelValue', value: boolean | string): void;
  }

  const props = withDefaults(defineProps<Props>(), {
    title: 'title',
    desc: 'desc',
    icon: 'rebuild',
    disabled: false,
    trueValue: true,
    falseValue: false,
    checked: false,
    modelValue: false,
  });

  const emits = defineEmits<Emits>();

  const statusClass = computed(() => ({
    'card-checkbox--selected': props.modelValue === props.trueValue || props.checked,
    'card-checkbox--disabled': props.disabled,
  }));

  function handleChange() {
    if (props.disabled) {
      return;
    }

    const isSelected = props.modelValue === props.trueValue;
    emits('update:modelValue', isSelected ? props.falseValue : props.trueValue);
  }
</script>

<style lang="less" scoped>
  .card-checkbox {
    position: relative;
    display: inline-flex;
    height: 64px;
    min-width: 362px;
    color: @gray-color;
    border: 1px solid #c4c6cc;
    border-radius: 2px;

    &__icon {
      width: 56px;
      font-size: 32px;
      line-height: 62px;
      text-align: center;
      background-color: #fafbfd;
      flex-shrink: 0;
    }

    &__content {
      padding: 8px 12px;
      font-size: @font-size-mini;
      line-height: 20px;
      border-left: 1px solid #c4c6cc;
    }

    &__title {
      display: inline-block;
      color: @title-color;
    }

    &__desc {
      padding-top: 4px;
    }

    &:not(&--disabled) {
      cursor: pointer;
    }

    &--disabled {
      color: @disable-color;
      cursor: not-allowed;
      border-color: @border-disable;

      .card-checkbox__icon {
        background-color: #fafbfd;
      }

      .card-checkbox__title {
        color: @gray-color;
      }

      .card-checkbox__content {
        border-color: @border-disable;
      }
    }

    &:hover:not(&--disabled),
    &--selected {
      border-color: @border-primary;

      .card-checkbox__icon {
        color: @primary-color;
        background-color: #e1ecff;
      }

      .card-checkbox__content {
        border-color: @border-primary;
      }
    }

    &--selected {
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
</style>
