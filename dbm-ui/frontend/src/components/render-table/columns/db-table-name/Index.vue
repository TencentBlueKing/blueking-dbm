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
  <TagInput
    ref="tagInputRef"
    v-model="modelValue"
    :disabled="disabled"
    :placeholder="placeholder"
    :rules="rules"
    :single="single"
    @change="handleValueChange">
    <template #tip>
      <p>{{ t('%：匹配任意长度字符串，如 a%， 不允许独立使用') }}</p>
      <p>{{ t('？： 匹配任意单一字符，如 a%?%d') }}</p>
      <p>{{ t('* ：专门指代 ALL 语义, 只能独立使用') }}</p>
      <p>{{ t('注：含通配符的单元格仅支持输入单个对象') }}</p>
      <p>{{ t('按Enter或失焦可完成内容输入') }}</p>
      <p>{{ t('粘贴多个对象可用换行，空格或；，｜分隔') }}</p>
    </template>
  </TagInput>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import { type Rules } from '../../hooks/useValidtor';
  import TagInput from '../tag-input/index.vue';

  interface Props {
    placeholder?: string;
    single?: boolean;
    rules?: Rules;
    disabled?: boolean;
  }

  interface Emits {
    (e: 'change', value: string[]): void;
  }

  interface Exposes {
    getValue: () => Promise<string[]>;
  }

  withDefaults(defineProps<Props>(), {
    placeholder: '',
    single: false,
    rules: undefined,
    disabled: false,
  });

  const emits = defineEmits<Emits>();

  const modelValue = defineModel<string[]>({
    default: [],
  });

  const { t } = useI18n();

  const tagInputRef = ref<InstanceType<typeof TagInput>>();

  const handleValueChange = (value: string[]) => {
    emits('change', value);
  };

  defineExpose<Exposes>({
    getValue() {
      return tagInputRef.value!.getValue().then(() => modelValue.value);
    },
  });
</script>
