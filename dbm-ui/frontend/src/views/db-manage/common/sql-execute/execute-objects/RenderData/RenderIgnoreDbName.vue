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
  <TableEditTag
    ref="editTagRef"
    :model-value="modelValue"
    :placeholder="t('请输入DB名称_支持通配符_含通配符的仅支持单个')"
    :rules="rules"
    @change="handleChange" />
</template>
<script setup lang="ts">
  import _ from 'lodash';
  import { useI18n } from 'vue-i18n';

  import TableEditTag from '@components/render-table/columns/db-table-name/Index.vue';

  interface Exposes {
    getValue: () => Promise<string[]>;
  }

  const modelValue = defineModel<string[]>({
    required: true,
  });

  const { t } = useI18n();

  const rules = [
    {
      validator: (value: string[]) => {
        const hasAllMatch = _.find(value, (item) => /%$/.test(item));
        return !(value.length > 1 && hasAllMatch);
      },
      message: t('一格仅支持单个_对象'),
    },
  ];

  const editTagRef = ref<InstanceType<typeof TableEditTag>>();

  const handleChange = (value: string[]) => {
    modelValue.value = value;
  };

  defineExpose<Exposes>({
    getValue() {
      return editTagRef.value!.getValue().then(() => modelValue.value);
    },
  });
</script>
