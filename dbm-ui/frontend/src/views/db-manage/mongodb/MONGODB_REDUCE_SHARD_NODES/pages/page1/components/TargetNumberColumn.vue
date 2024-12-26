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
    :append-rules="rules"
    field="target_num"
    :label="t('缩容至（节点数）')"
    required
    :width="200">
    <EditInput
      v-model="modelValue"
      :disabled="disabled"
      :max="max"
      :min="3"
      type="number" />
  </EditableTableColumn>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import { Column as EditableTableColumn, Input as EditInput } from '@components/editable-table/Index.vue';

  interface Props {
    disabled: boolean;
    max?: number;
  }

  const props = withDefaults(defineProps<Props>(), {
    max: Number.MAX_SAFE_INTEGER,
  });

  const modelValue = defineModel<number>();

  const { t } = useI18n();

  const rules = [
    {
      validator: (value: number) => value < props.max,
      trigger: 'change',
      message: t('必须小于当前节点数'),
    },
    {
      validator: (value: number) => value >= 3,
      trigger: 'change',
      message: t('不能少于n台', { n: 3 }),
    },
  ];
</script>
