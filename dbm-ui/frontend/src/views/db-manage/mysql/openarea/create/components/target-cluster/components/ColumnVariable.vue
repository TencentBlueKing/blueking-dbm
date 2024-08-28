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
    :placeholder="t('请输入')"
    :rules="rules" />
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import TableEditInput from '@components/render-table/columns/input/index.vue';

  interface Props {
    name: string;
    data?: string;
  }
  interface Exposes {
    getValue: () => Promise<Record<string, string>>;
  }

  const props = withDefaults(defineProps<Props>(), {
    data: '',
  });

  const { t } = useI18n();

  const localValue = ref(props.data);
  const editRef = ref();

  const rules = [
    {
      validator: (value: string) => Boolean(value),
      message: t('变量名name不能为空', { name: props.name }),
    },
  ];

  watch(
    () => props.data,
    () => {
      localValue.value = props.data;
    },
    {
      immediate: true,
    },
  );

  defineExpose<Exposes>({
    getValue() {
      return (editRef.value as InstanceType<typeof TableEditInput>)
        .getValue()
        .then(() => ({
          [props.name]: localValue.value,
        }))
        .catch(() =>
          Promise.reject({
            [props.name]: localValue.value,
          }),
        );
    },
  });
</script>
