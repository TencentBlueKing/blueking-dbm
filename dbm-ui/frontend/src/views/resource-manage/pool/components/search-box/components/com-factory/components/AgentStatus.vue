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
  <BkSelect
    :model-value="defaultValue"
    :placeholder="t('请选择 Agent 状态')"
    @change="handleChange">
    <BkOption
      :label="t('正常')"
      :value="1" />
    <BkOption
      :label="t('异常')"
      :value="0" />
  </BkSelect>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  interface Props {
    defaultValue?: number;
  }

  interface Emits {
    (e: 'change', value: number): void;
    (e: 'submit'): void;
    (e: 'cancel'): void;
  }

  withDefaults(defineProps<Props>(), {
    defaultValue: undefined,
    simple: false,
  });

  const emits = defineEmits<Emits>();

  defineOptions({
    inheritAttrs: false,
  });

  const { t } = useI18n();

  const handleChange = (value: number) => {
    emits('change', value);
  };
</script>
