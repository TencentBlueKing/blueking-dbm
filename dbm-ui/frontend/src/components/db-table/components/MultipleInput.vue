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
  <div class="t-input__wrap">
    <BkInput
      ref="input"
      v-model="localValue"
      :autosize="{
        minRows: 3,
        maxRows: 100,
      }"
      clearable
      :placeholder="placeholder"
      :resize="false"
      type="textarea"
      @input="handleInput" />
    <div
      class="mt-4"
      style="line-height: 22px">
      <span>{{ t('支持输入多个值， ”Enter“ 换行') }}</span>
    </div>
  </div>
</template>
<script setup lang="ts">
  import _ from 'lodash';
  import { useI18n } from 'vue-i18n';

  export interface Props {
    placeholder?: string;
    value?: string;
  }
  type Emits = (e: 'change', value: string) => void;

  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();

  const { t } = useI18n();

  const inputRef = useTemplateRef('input');
  const localValue = ref('');

  let isInnerSelfChange = false;
  watch(
    () => props.value,
    () => {
      if (isInnerSelfChange) {
        isInnerSelfChange = false;
        return;
      }
      if (!props.value) {
        localValue.value = '';
        return;
      }
      localValue.value = props.value.split(',').join('\n');
    },
    {
      immediate: true,
    },
  );

  const handleInput = (value: string) => {
    isInnerSelfChange = true;
    emits('change', _.uniq(_.filter(value.split(/[ \r\n\t,，;；|｜]/g), (item) => Boolean(_.trim(item)))).join(','));
  };

  onMounted(() => {
    setTimeout(() => {
      // @ts-expect-error fix 类型报错，实际存在 focus 方法
      inputRef.value?.focus();
    }, 100);
  });
</script>
