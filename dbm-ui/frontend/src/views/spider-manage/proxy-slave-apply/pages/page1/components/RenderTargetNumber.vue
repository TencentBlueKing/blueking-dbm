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
  <BkLoading :loading="isLoading">
    <TableEditInput
      ref="editRef"
      v-model="localValue"
      :placeholder="$t('请输入')"
      :rules="rules" />
  </BkLoading>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import TableEditInput from '@components/tools-table-input/index.vue';

  import type { IDataRow } from './Row.vue';

  interface Props {
    modelValue?: IDataRow['targetNum'];
    isLoading?: boolean;
  }

  interface Exposes {
    getValue: () => Promise<number>
  }

  const props = withDefaults(defineProps<Props>(), {
    modelValue: '',
    min: 0,
  });

  const { t } = useI18n();
  const localValue = ref(props.modelValue);
  const editRef = ref();

  const nonInterger = /\D/g;

  const rules = [
    {
      validator: (value: string) => Boolean(value),
      message: t('目标台数不能为空'),
    },
    {
      validator: (value: string) => !nonInterger.test(value),
      message: t('格式有误，请输入数字'),
    },
    {
      validator: (value: string) => {
        const num = Number(value);
        return num >= 1 && num <= 1024;
      },
      message: `${t('台数范围')}: 1 - 1024`,
    },
  ];

  defineExpose<Exposes>({
    getValue() {
      return editRef.value
        .getValue()
        .then(() => ({ count: Number(localValue.value) }));
    },
  });

</script>
