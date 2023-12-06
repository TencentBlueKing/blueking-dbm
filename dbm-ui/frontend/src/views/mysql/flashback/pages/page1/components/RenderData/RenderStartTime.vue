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
  <TableEditDateTime
    ref="editRef"
    v-model="modelValue"
    :disabled-date="disableDate"
    :placeholder="t('请选择')"
    :rules="rules"
    type="datetime" />
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import TableEditDateTime from '@views/spider-manage/common/edit/DateTime.vue';

  interface Exposes {
    getValue: (field: string) => Promise<Record<'start_time', string>>
  }

  const modelValue = defineModel<string>({
    required: false,
  });

  const { t } = useI18n();
  const editRef = ref();

  const disableDate = (date: Date) => date && date.valueOf() > Date.now();

  const rules = [
    {
      validator: (value: string) => Boolean(value),
      message: t('开始时间不能为空'),
    },
  ];

  defineExpose<Exposes>({
    getValue() {
      return editRef.value.getValue()
        .then(() => ({
          start_time: modelValue.value,
        }));
    },
  });
</script>
