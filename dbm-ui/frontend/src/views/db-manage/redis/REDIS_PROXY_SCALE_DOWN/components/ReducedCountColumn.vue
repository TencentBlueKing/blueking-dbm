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
    field="count"
    :label="t('缩容数量（台）')"
    :min-width="150">
    <div
      v-bk-tooltips="{
        content: t('手动选择主机不需要设置缩容数量'),
        disabled: !disabled,
      }"
      style="flex: 1">
      <Input
        v-model="modelValue"
        :disabled="disabled"
        :min="0"
        type="number" />
    </div>
  </Column>
</template>
<script lang="ts" setup>
  import { useI18n } from 'vue-i18n';

  import { Column, Input } from '@components/editable-table/Index.vue';

  interface Props {
    disabled?: boolean;
  }

  withDefaults(defineProps<Props>(), {
    disabled: false,
  });

  const { t } = useI18n();

  const modelValue = defineModel<string>({
    default: '',
  });
</script>
