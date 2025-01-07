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
    :label="t('集群名称')"
    property="details.cluster_name"
    required
    :rules="rules">
    <BkInput
      v-model="modelValue"
      v-bk-tooltips="{
        trigger: 'click',
        placement: 'top',
        theme: 'light',
        content: clusterNamePlaceholder,
      }"
      class="item-input"
      :maxlength="63"
      :placeholder="clusterNamePlaceholder"
      show-word-limit />
  </BkFormItem>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import { nameRegx } from '@common/regex';

  const { t } = useI18n();

  const modelValue = defineModel<string>();

  const clusterNamePlaceholder = t('集群标识，支持小写字母、数字、连字符 -（连字符不可打头）');

  const rules = [
    {
      validator: (val: string) => nameRegx.test(val),
      message: clusterNamePlaceholder,
      trigger: 'blur',
    },
  ];
</script>
