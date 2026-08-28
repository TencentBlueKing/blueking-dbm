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
  <DbSelect
    collapse-tags
    :model-value="defaultValue"
    multiple
    multiple-mode="tag"
    :placeholder="t('请选择资源状态')"
    show-selected-icon
    @change="handleChange">
    <DbOption
      v-for="item in statusList"
      :key="item.value"
      :label="item.label"
      :value="item.value" />
  </DbSelect>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import DbResourceModel from '@services/model/db-resource/DbResource';

  interface Props {
    defaultValue?: string[];
  }

  type Emits = (e: 'change', value: Props['defaultValue']) => void;

  defineOptions({
    inheritAttrs: false,
  });

  defineProps<Props>();

  const emits = defineEmits<Emits>();

  const { t } = useI18n();

  const statusList = Object.entries(DbResourceModel.ResourceStatusDisplayMap).map(([value, label]) => ({
    label,
    value,
  }));

  const handleChange = (value: Props['defaultValue']) => {
    emits('change', value);
  };
</script>
