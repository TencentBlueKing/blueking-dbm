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
  <BkFormItem
    :label="$t('集群ID')"
    property="details.cluster_name"
    required
    :rules="rules">
    <BkInput
      class="item-input"
      :maxlength="64"
      :model-value="modelValue"
      :placeholder="$t('以小写英文字符开头_且只能包含英文字母_数字_连字符')"
      show-word-limit
      @change="handleChange" />
  </BkFormItem>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import { nameRegx } from '@common/regex';

  interface Props {
    modelValue: string
  }
  interface Emits {
    (e: 'update:modelValue', value: string): void
  }

  defineProps<Props>();
  const emits = defineEmits<Emits>();

  const { t } = useI18n();

  const rules = [
    {
      validator: (val: string) => nameRegx.test(val),
      message: t('以小写英文字母开头_且只能包含英文字母_数字_连字符'),
      trigger: 'blur',
    },
  ];

  const handleChange = (value: string) => {
    emits('update:modelValue', value);
  };
</script>

