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
  <EditableColumn
    :append-rules="rules"
    :field="field"
    :label="label"
    required
    :width="200">
    <EditableInput
      v-model="modelValue"
      :placeholder="t('请输入单个(IP 或 域名):Port')" />
  </EditableColumn>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import { domainPort, ipPort } from '@common/regex';

  interface Props {
    field: string;
    label: string;
  }

  defineProps<Props>();
  const modelValue = defineModel<string>();

  const { t } = useI18n();

  const rules = [
    {
      message: t('格式不正确'),
      trigger: 'change',
      validator: (value: string) => ipPort.test(value) || domainPort.test(value),
    },
  ];
</script>
