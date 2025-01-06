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
    field="drop_type"
    :label="t('清档类型')"
    required
    :width="200">
    <EditableSelect
      v-model="modelValue"
      :clearable="false"
      :list="list" />
  </EditableColumn>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  const modelValue = defineModel<string>({
    required: true,
    default: 'drop_collection',
  });

  const { t } = useI18n();

  const list = [
    {
      value: 'drop_collection',
      label: t('直接删除表'),
    },
    {
      value: 'rename_collection',
      label: t('将表暂时重命名，用于需要快速恢复的情况'),
    },
  ];
</script>
