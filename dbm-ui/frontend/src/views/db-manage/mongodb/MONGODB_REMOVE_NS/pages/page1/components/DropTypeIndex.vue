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
  <EditableTableColumn
    ref="editableTableColumn"
    field="drop_index"
    :label="t('索引处理')"
    required
    :width="200">
    <EditSelect
      v-model="modelValue"
      :clearable="false"
      :list="list" />
  </EditableTableColumn>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import { Column as EditableTableColumn, Select as EditSelect } from '@components/editable-table/Index.vue';

  const modelValue = defineModel<string>({
    required: true,
    default: 'keep',
  });

  const { t } = useI18n();

  const list = [
    {
      value: 'keep',
      label: t('保留索引'),
    },
    {
      value: 'delete',
      label: t('删除索引'),
    },
  ];
</script>
