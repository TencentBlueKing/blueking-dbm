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
  <Column
    field="switchMode"
    :label="t('切换模式')"
    :min-width="150">
    <Select
      v-model="modelValue"
      :disabled="disabled"
      :input-search="false"
      :list="options" />
  </Column>
</template>
<script lang="ts" setup>
  import { useI18n } from 'vue-i18n';

  import { Column, Select } from '@components/editable-table/Index.vue';

  interface Props {
    disabled?: boolean;
  }

  withDefaults(defineProps<Props>(), {
    disabled: false,
  });

  const modelValue = defineModel<string>({
    default: '',
  });

  const { t } = useI18n();

  const options = [
    {
      value: 'user_confirm',
      label: t('需人工确认'),
    },
    {
      value: 'no_confirm',
      label: t('无需确认'),
    },
  ];
</script>
