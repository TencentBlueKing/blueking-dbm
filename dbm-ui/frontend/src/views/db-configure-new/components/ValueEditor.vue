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
  <!-- 下拉单选 (ENUM) -->
  <BkSelect
    v-if="typeSub === ConstraintType.ENUM"
    ref="enumSelectRef"
    :clearable="false"
    :disabled="props.disabled"
    :model-value="modelValue"
    :style="{ flex: 1 }"
    @change="handleChange">
    <BkOption
      v-for="opt in options"
      :key="opt"
      :label="opt"
      :value="opt" />
  </BkSelect>

  <!-- 下拉多选 (ENUMS) -->
  <BkSelect
    v-else-if="typeSub === ConstraintType.ENUMS"
    ref="enumSMultipleSelectRef"
    :clearable="false"
    :disabled="props.disabled"
    :model-value="enumSValue"
    multiple
    :style="{ flex: 1 }"
    @change="handleEnumSChange">
    <BkOption
      v-for="opt in options"
      :key="opt"
      :label="opt"
      :value="opt" />
  </BkSelect>

  <!-- 数字输入框 (RANGE) -->
  <BkInput
    v-else-if="typeSub === ConstraintType.RANGE"
    ref="numberInputRef"
    v-model="modelValue"
    :disabled="props.disabled"
    type="number" />

  <!-- 多行文本框 (JSON / MAP / LIST) -->
  <BkInput
    v-else-if="isMultiLineType(typeSub)"
    ref="textareaRef"
    v-model="modelValue"
    :disabled="props.disabled"
    type="textarea" />

  <!-- 文本输入框 / 密码输入框（BYTES / DURATION / REGEX / GOVALIDATE / 无约束 / 加密参数） -->
  <BkInput
    v-else
    ref="textInputRef"
    v-model="modelValue"
    :disabled="props.disabled"
    :placeholder="props.disabled ? t('请先选择参数') : props.isEncrypted ? '请输入新值' : undefined"
    :type="props.isEncrypted ? 'password' : 'text'" />
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import { batchSplitRegex } from '@common/regex';

  // 约束类型枚举
  enum ConstraintType {
    ENUM = 'ENUM',
    ENUMS = 'ENUMS',
    RANGE = 'RANGE',
  }

  interface Props {
    /** 是否禁用 */
    disabled?: boolean;
    /** 是否为加密参数 */
    isEncrypted?: boolean;
    /** 约束值（用于下拉选项） */
    valueAllowed?: string;
    /** 默认值 */
    valueDefault?: string;
    /** 约束类型 */
    valueTypeSub?: string;
  }

  const props = withDefaults(defineProps<Props>(), {
    disabled: false,
    isEncrypted: false,
    valueAllowed: '',
    valueDefault: '',
    valueTypeSub: '',
  });

  const modelValue = defineModel<string>({
    default: '',
  });

  const { t } = useI18n();

  const typeSub = computed(() => props.valueTypeSub?.toUpperCase() || '');

  /** 输入组件ref */
  const enumSelectRef = ref();
  const enumSMultipleSelectRef = ref();
  const numberInputRef = ref();
  const textareaRef = ref();
  const textInputRef = ref();

  /** 判断是否为多行文本类型 */
  const isMultiLineType = (subType: string): boolean => {
    return ['JSON', 'LIST', 'MAP'].includes(subType);
  };

  /** 组件渲染时默认聚焦 */
  onMounted(() => {
    nextTick(() => {
      if (typeSub.value === ConstraintType.ENUM) {
        enumSelectRef.value?.focus();
      } else if (typeSub.value === ConstraintType.ENUMS) {
        enumSMultipleSelectRef.value?.focus();
      } else if (typeSub.value === ConstraintType.RANGE) {
        numberInputRef.value?.focus();
      } else if (isMultiLineType(typeSub.value)) {
        textareaRef.value?.focus();
      } else {
        textInputRef.value?.focus();
      }
    });
  });

  /** 根据约束类型解析 value_allowed 为选项列表 */
  const options = computed(() => {
    if (!props.valueAllowed) return [];
    return props.valueAllowed
      .split(batchSplitRegex)
      .map((item) => item.trim())
      .filter(Boolean);
  });

  /** ENUMS 多选值 */
  const enumSValue = computed(() => {
    if (modelValue.value) {
      return modelValue.value.split(',');
    }
    return [];
  });

  watch(
    () => props.valueDefault,
    (val) => {
      // 加密参数不带入原值，由用户输入新值
      if (!props.isEncrypted && props.valueDefault) {
        modelValue.value = val;
      }
    },
    { immediate: true },
  );

  /** 下拉单选变更 */
  const handleChange = (val: string | number | Record<string, unknown> | Array<string | number>) => {
    modelValue.value = String(val);
  };

  /** 下拉多选变更 */
  const handleEnumSChange = (val: string | number | Record<string, unknown> | Array<string | number>) => {
    if (Array.isArray(val)) {
      modelValue.value = (val as string[]).join(',');
    }
  };
</script>
