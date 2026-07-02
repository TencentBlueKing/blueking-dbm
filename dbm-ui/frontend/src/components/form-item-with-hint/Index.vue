<!--
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 *
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 *
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 *
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed
 * on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for
 * the specific language governing permissions and limitations under the License.
-->

<template>
  <BkFormItem
    ref="formItemRef"
    class="form-item-with-hint"
    :label="label"
    :property="property"
    :required="required"
    :rules="mergedRules"
    :show-label="showLabel"
    v-bind="$attrs">
    <slot />
    <template #error="message">
      <span
        v-if="message"
        class="bk-form-error">
        {{ message }}
      </span>
    </template>
    <div
      v-if="isShowHint"
      class="form-item-hint">
      <slot name="hint">{{ hint }}</slot>
    </div>
  </BkFormItem>
</template>

<script setup lang="ts">
  interface Props {
    hint?: string;
    label?: string;
    model?: any;
    property: string;
    required?: boolean;
    rules?: Record<string, any>[];
    showLabel?: boolean;
  }

  const props = withDefaults(defineProps<Props>(), {
    hint: '',
    label: '',
    model: undefined,
    required: false,
    rules: () => [],
    showLabel: true,
  });

  const formItemRef = ref<any>(null);
  const isShowHint = ref(true);

  // 有错误信息时隐藏 hint
  watch(
    () => formItemRef.value?.errorMessage,
    (errorMessage) => {
      isShowHint.value = !errorMessage;
    },
    {
      immediate: true,
    },
  );

  // 值变化时清除校验态，恢复 hint 显示
  watch(
    () => props.model,
    () => {
      formItemRef.value?.clearValidate?.();
    },
  );

  // 合并规则：为空校验仅显示红框、不显示文字（validator 返回 '' 走 string reject 分支，
  // errorMessage 为空故无文字；return false 会被 mergeRules 用默认"验证出错"文案覆盖）
  const mergedRules = computed(() => {
    const rules = props.rules || [];
    if (props.required) {
      return [
        {
          message: '',
          required: true,
          trigger: 'blur',
          validator: (value: any) => {
            if (value !== undefined && value !== null && value !== '' && (!Array.isArray(value) || value.length > 0)) {
              return true;
            }
            return '';
          },
        },
        ...rules,
      ];
    }
    return rules;
  });

  const validate = (trigger?: string) => formItemRef.value?.validate?.(trigger);
  const clearValidate = () => formItemRef.value?.clearValidate?.();

  defineExpose({
    clearValidate,
    validate,
  });
</script>

<style lang="less" scoped>
  .form-item-with-hint {
    position: relative;

    /* bkui 的 .is-error .bk-tag-input 红框无效：bk-tag-input 外层无 border，
       可见 border 在 .bk-tag-input-trigger 上，故此处补红框 */
    &.is-error {
      :deep(.bk-tag-input-trigger) {
        border-color: #ea3636;
        transition: all 0.15s;
      }

      :deep(.db-tag-input-panel) {
        border-color: #ea3636;
        transition: all 0.15s;
      }
    }

    :deep(.bk-form-error) {
      width: 100%;
      padding-top: 0;
      line-height: 20px;
    }

    /* hint 绝对定位在表单项下方，不占高度 */
    .form-item-hint {
      position: absolute;
      left: 0;
      font-size: 12px;
      line-height: 20px;
      color: #979ba5;
      white-space: nowrap;
    }
  }
</style>
