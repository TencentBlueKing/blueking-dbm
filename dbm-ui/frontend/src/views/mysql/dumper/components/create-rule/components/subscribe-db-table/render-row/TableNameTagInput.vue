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
  <TableTagInput
    ref="tagRef"
    :model-value="localValue"
    :placeholder="t('请输入表名，支持通配符')"
    :rules="rules"
    @change="handleTagValueChange">
    <template #tip>
      <p>{{ t('%：匹配任意长度字符串，如 a%， 不允许独立使用') }}</p>
    </template>
  </TableTagInput>
</template>
<script setup lang="ts">
  import _ from 'lodash';
  import { useI18n } from 'vue-i18n';

  import TableTagInput from '@components/render-table/columns/tag-input/index.vue';

  interface Exposes {
    getValue: () => Promise<string[]>;
  }

  const { t } = useI18n();

  const tagRef = ref();
  const localValue = ref<string[]>([]);

  const rules = [
    {
      validator: (value: string[]) => value && value.length > 0,
      message: t('不能为空'),
    },
    {
      validator: (value: string[]) => _.every(value, (item) => !/^%$/.test(item)),
      message: t('% 不允许单独使用'),
      trigger: 'change',
    },
    {
      validator: (value: string[]) => _.some(value, (item) => /^[a-zA-Z0-9_%]+$/.test(item)),
      message: t('不合法的输入'),
      trigger: 'change',
    },
  ];

  const handleTagValueChange = (value: string[]) => {
    localValue.value = value;
  };

  defineExpose<Exposes>({
    getValue() {
      return tagRef.value.getValue().then(() => {
        if (!localValue.value) {
          return Promise.reject();
        }
        return localValue.value;
      });
    },
  });
</script>
