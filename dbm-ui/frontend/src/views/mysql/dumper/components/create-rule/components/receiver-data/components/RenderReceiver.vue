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
  <TableEditInput
    ref="editRef"
    v-model="localValue"
    :placeholder="$t('如n', {n: '（IP或集群）:10000'})"
    :rules="rules" />
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import { domainPort } from '@common/regex';

  import TableEditInput from '@components/render-table/columns/input/index.vue';

  interface Props {
    data: string
  }

  interface Exposes {
    getValue: () => Promise<string>
  }


  const props = defineProps<Props>();

  const { t } = useI18n();
  const localValue = ref('');
  const editRef = ref();

  const rules = [
    {
      validator: (value: string) => Boolean(value),
      message: t('不能为空'),
    },
    {
      validator: (value: string) => domainPort.test(value),
      message: t('输入格式有误'),
    },
  ];

  watch(() => props.data, (value) => {
    localValue.value = value;
  }, {
    immediate: true,
  });

  defineExpose<Exposes>({
    getValue() {
      return editRef.value
        .getValue()
        .then(() => (localValue.value));
    },
  });
</script>
