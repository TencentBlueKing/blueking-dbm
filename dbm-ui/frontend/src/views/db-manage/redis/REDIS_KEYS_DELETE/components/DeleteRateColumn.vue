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
  <EditableColumn
    field="delete_rate"
    :label="t('每秒删除 Key 个数')"
    required
    :width="150">
    <EditableSelect
      v-model="modelValue"
      :clearable="false"
      :list="list" />
  </EditableColumn>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import RedisModel from '@services/model/redis/redis';

  interface Props {
    cluster: {
      delete_rate: RedisModel['delete_rate'];
      id: number;
    };
  }

  const props = defineProps<Props>();

  const modelValue = defineModel<number | string>({
    required: true,
  });

  const { t } = useI18n();

  const list = shallowRef<
    {
      label: number;
      value: number;
    }[]
  >([]);

  watch(
    () => props.cluster.id,
    () => {
      if (props.cluster.id) {
        if (modelValue.value === '') {
          modelValue.value = props.cluster.delete_rate.default;
        }
        list.value = props.cluster.delete_rate.rate_list.map((item) => ({
          label: item,
          value: item,
        }));
      } else {
        modelValue.value = '';
        list.value = [];
      }
    },
    {
      immediate: true,
    },
  );
</script>
