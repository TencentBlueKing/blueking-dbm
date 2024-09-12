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
    v-model="localValue"
    :list="selectList"
    multiple
    :placeholder="t('请选择')"
    :rules="rules"
    show-select-all />
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import TableEditSelect, { type IListItem } from '@components/render-table/columns/select/index.vue';

  interface Props {
    list?: string[];
    data?: string[];
  }

  interface Exposes {
    getValue: () => Promise<string[]>;
  }

  const props = withDefaults(defineProps<Props>(), {
    list: () => [],
    data: () => [],
  });

  const { t } = useI18n();

  const editSelectRef = ref<InstanceType<typeof TableEditSelect>>();
  const localValue = ref<string[]>([]);
  const selectList = ref<IListItem[]>([]);

  const rules = [
    {
      validator: (list: string[]) => list.length > 0,
      message: t('请选择'),
    },
  ];

  watch(
    () => props.list,
    (list) => {
      selectList.value = list.map((item) => ({
        label: item,
        value: item,
      }));
    },
    {
      immediate: true,
    },
  );

  watch(
    () => props.data,
    () => {
      if (props.data.length > 0) {
        localValue.value = props.data;
      }
    },
    {
      immediate: true,
    },
  );

  defineExpose<Exposes>({
    getValue() {
      return editSelectRef.value!.getValue().then(() => localValue.value);
    },
  });
</script>
