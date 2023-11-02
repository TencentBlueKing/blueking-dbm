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
    :placeholder="$t('请选择')"
    :rules="rules"
    @change="(value) => handleChange(value as string)" />
</template>
<script setup lang="ts">
  import { ref } from 'vue';
  import { useI18n } from 'vue-i18n';

  import TableEditSelect from '@components/tools-table-select/index.vue';

  interface Props {
    modelValue: string
  }

  interface Exposes {
    getValue: () => Promise<Record<string, string>>
  }

  const props = defineProps<Props>();

  const { t } = useI18n();
  const rules = [
    {
      validator: (value: string) => Boolean(value),
      message: t('清档类型不能为空'),
    },
  ];

  const list = [
    {
      value: 'truncate_table',
      label: t('清除表数据_truncatetable'),
    },
    {
      value: 'drop_table',
      label: t('清除表数据和结构_droptable'),
    },
    {
      value: 'drop_database',
      label: t('删除整库_dropdatabase'),
    },
  ];

  const editSelectRef = ref();
  const localValue = ref('');

  watch(() => props.modelValue, () => {
    localValue.value = props.modelValue;
  }, {
    immediate: true,
  });
  const handleChange = (value: string) => {
    localValue.value = value;
  };

  defineExpose<Exposes>({
    getValue() {
      return editSelectRef.value.getValue()
        .then(() => ({
          truncate_data_type: localValue.value,
        }));
    },
  });
</script>
