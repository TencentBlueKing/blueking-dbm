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
      :disabled="disabled"
      :placeholder="placeholder"
      :rules="rules"
      type="number" />
  </BkLoading>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import TableEditInput from '@components/tools-table-input/index.vue';

  import type { IDataRow } from './Row.vue';

  interface Props {
    data?: IDataRow['targetNum'];
    isLoading?: boolean;
    max?: number;
    role?: string;
    disabled?: boolean;
  }

  interface Exposes {
    getValue: () => Promise<string>
  }

  const props = withDefaults(defineProps<Props>(), {
    data: '',
    max: 1,
    role: 'spider_slave',
    isLoading: false,
    disabled: false,
  });

  const { t } = useI18n();

  const localValue = ref(props.data);
  const editRef = ref();

  const placeholder = computed(() => (props.role === 'spider_master' ? t('至少2台') : t('请输入')));

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
      validator: (value: string) => Number(value) > 1 && Number(value) < props.max,
      message: t('必须小于当前台数且大于1'),
    },
  ];

  watch(localValue, (value) => {
    if (props.role === 'spider_master') {
      if (Number(value) < 2) {
        nextTick(() => {
          localValue.value = '2';
          editRef.value.getValue();
        });
      }
    }
  }, {
    immediate: true,
  });

  defineExpose<Exposes>({
    getValue() {
      return editRef.value
        .getValue()
        .then(() => ({ spider_reduced_to_count: Number(localValue.value) }))
        .catch((e: Error) => console.error(e));
    },
  });

</script>
