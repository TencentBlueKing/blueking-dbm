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
    clearable
    :disabled="disabled"
    :placeholder="placeholder"
    :rules="rules"
    :single="single"
    @change="handleValueChange">
    <template #tip>
      <div class="db-table-tag-tip">
        <p style="font-weight: 700;">{{ t('库表输入说明') }}：</p>
        <p>
          <div class="circle-dot"></div>
          <span>{{ t('不允许输入系统库和特殊库，如mysql、sys 等') }}</span>
        </p>
        <p>
          <div class="circle-dot"></div>
          <span>{{ t('DB名、表名不允许为空，忽略DB名、忽略表名不允许为 *') }}</span>
        </p>
        <p>
          <div class="circle-dot"></div>
          <span>{{ t('支持 %（指代任意长度字符串）, ?（指代单个字符串）, *（指代全部）三个通配符') }}</span>
        </p>
        <p>
          <div class="circle-dot"></div>
          <span>{{ t('单元格可同时输入多个对象，使用换行，空格或；，｜分隔，按 Enter 或失焦完成内容输入') }}</span>
        </p>
        <p>
          <div class="circle-dot"></div>
          <span>{{ t('包含通配符时, 每一单元格只允许输入单个对象。% ? 不能独立使用， * 只能单独使用') }}</span>
        </p>
      </div>
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
<style lang="less" scoped>
  .db-table-tag-tip {
    display: flex;
    flex-direction: column;
    line-height: 24px;
    padding: 3px 7px;

    p {
      display: flex;
      align-items: center;

      .circle-dot {
        width: 4px;
        height: 4px;
        background-color: #63656E;
        border-radius: 50%; 
        display: inline-block;
        margin-right: 6px;
      }
    }
  }
</style>
