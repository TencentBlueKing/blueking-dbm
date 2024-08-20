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
      :max="max"
      :min="1"
      :rules="rules"
      type="number" />
  </BkLoading>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import TableEditInput from '@components/render-table/columns/input/index.vue';

  import type { IDataRow } from './Row.vue';

  interface Props {
    data?: IDataRow['targetNum'];
    isLoading?: boolean;
    count?: number;
    role?: string;
    disabled?: boolean;
  }

  interface Exposes {
    getValue: () => Promise<{ spider_reduced_to_count: string }>;
  }

  const props = withDefaults(defineProps<Props>(), {
    data: '',
    count: 0,
    role: 'spider_slave',
    isLoading: false,
    disabled: false,
  });

  const { t } = useI18n();

  const localValue = ref('');
  const editRef = ref();

  // const placeholder = computed(() => (props.role === 'spider_master' ? t('至少2台') : t('请输入')));

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
      validator: (value: number) => {
        if (props.role === 'spider_master') {
          return props.count - value >= 2;
        }
        return true;
      },
      message: t('缩容后不能少于2台'),
    },
    {
      validator: (value: number) => {
        if (props.role === 'spider_slave') {
          return props.count - value >= 1;
        }
        return true;
      },
      message: t('缩容后不能少于1台'),
    },
  ];

  const max = computed(() => {
    if (props.role === 'spider_master') {
      return props.count - 2;
    }
    return props.count - 1;
  });

  watch(
    () => props.data,
    () => {
      localValue.value = props.data;
    },
    {
      immediate: true,
    },
  );

  // watch(localValue, (value) => {
  //   if (props.role === 'spider_master') {
  //     if (Number(value) < 2) {
  //       nextTick(() => {
  //         localValue.value = '2';
  //         editRef.value.getValue();
  //       });
  //     }
  //   }
  // }, {
  //   immediate: true,
  // });

  defineExpose<Exposes>({
    getValue() {
      return editRef.value
        .getValue()
        .then(() => ({ spider_reduced_to_count: props.count - Number(localValue.value) }))
        .catch(() =>
          Promise.reject({
            spider_reduced_to_count: Number(localValue.value),
          }),
        );
    },
  });
</script>
