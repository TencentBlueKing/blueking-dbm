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
      :placeholder="t('至少3台_且必须为奇数')"
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
    currentNodeNum: number;
  }

  interface Exposes {
    getValue: () => Promise<number>;
  }

  const props = withDefaults(defineProps<Props>(), {
    data: '',
    isLoading: false,
  });

  const { t } = useI18n();

  const localValue = ref(props.data);
  const editRef = ref();

  const rules = [
    {
      validator: (value: number) => value % 2 === 1,
      message: t('必须为奇数'),
    },
    {
      validator: (value: number) => value > props.currentNodeNum,
      message: t('必须大于当前节点数'),
    },
    {
      validator: (value: number) => value >= 3,
      message: t('不能少于n台', { n: 3 }),
    },
  ];

  defineExpose<Exposes>({
    getValue() {
      return editRef.value.getValue().then(() => Number(localValue.value));
    },
  });
</script>
