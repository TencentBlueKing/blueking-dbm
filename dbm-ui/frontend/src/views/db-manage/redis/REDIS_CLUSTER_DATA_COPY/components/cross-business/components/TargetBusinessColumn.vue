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
    field="dst_bk_biz_id"
    :label="t('目标业务')"
    required
    :width="200">
    <EditableSelect
      v-model="modelValue"
      :clearable="false"
      filterable
      :list="list" />
  </EditableColumn>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import { useGlobalBizs } from '@stores';

  const modelValue = defineModel<number>();

  const { bizs } = useGlobalBizs();

  const { t } = useI18n();

  const list = computed(() =>
    bizs.map((item) => ({
      label: item.name,
      value: item.bk_biz_id,
    })),
  );
</script>
