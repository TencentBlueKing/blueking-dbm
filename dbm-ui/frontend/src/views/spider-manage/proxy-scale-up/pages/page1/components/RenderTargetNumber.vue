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
  import _ from 'lodash';
  import { useI18n } from 'vue-i18n';

  import TableEditInput from '@views/spider-manage/common/edit/Input.vue';

  import type { IDataRow } from './Row.vue';

  interface Props {
    data?: IDataRow['targetNum'];
    min?: number;
    isLoading?: boolean;
  }

  interface Exposes {
    getValue: () => Promise<number>
  }

  const props = withDefaults(defineProps<Props>(), {
    data: '',
    min: 0,
  });

  const { t } = useI18n();
  const localValue = ref(props.data);
  const editRef = ref();

  const nonInterger = /\D/g;

  const rules = [
    {
      validator: (value: string) => Boolean(_.trim(value)),
      message: t('目标台数不能为空'),
    },
    {
      validator: (value: string) => !nonInterger.test(_.trim(value)),
      message: t('格式有误，请输入数字'),
    },
    {
      validator: (value: string) => Number(_.trim(value)) > props.min,
      message: t('必须大于当前台数'),
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
