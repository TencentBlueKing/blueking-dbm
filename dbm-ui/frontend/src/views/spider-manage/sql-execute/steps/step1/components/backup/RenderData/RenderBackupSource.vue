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
  <TableEditSelect
    ref="editSelectRef"
    :list="list"
    :model-value="modelValue"
    :placeholder="t('请选择备份源')"
    :rules="rules"
    @change="(value) => handleChange(value as string)" />
</template>
<script setup lang="ts">
  import { ref } from 'vue';
  import { useI18n } from 'vue-i18n';

  import TableEditSelect from '@views/mysql/common/edit/Select.vue';

  interface Props {
    modelValue: string
  }

  interface Emits {
    (e: 'change', value: string): void
  }

  interface Exposes {
    getValue: (field: string) => Promise<Record<string, string>>
  }

  defineProps<Props>();
  const emits = defineEmits<Emits>();

  const { t } = useI18n();
  const rules = [
    {
      validator: (value: string) => Boolean(value),
      message: t('备份源不能为空'),
    },
  ];

  const list = [
    {
      id: 'remote',
      name: 'remote',
    },
  ];

  const editSelectRef = ref();
  const localValue = ref('');

  const handleChange = (value: string) => {
    localValue.value = value;
    emits('change', value);
  };

  defineExpose<Exposes>({
    getValue(field: string) {
      return editSelectRef.value.getValue()
        .then(() => ({
          [field]: localValue.value,
        }));
    },
  });
</script>
