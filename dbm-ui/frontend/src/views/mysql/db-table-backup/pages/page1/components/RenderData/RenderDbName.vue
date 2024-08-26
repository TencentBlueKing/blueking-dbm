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
  <TableEditTag
    ref="tagRef"
    :model-value="modelValue"
    :placeholder="t('请输入DB名称_支持通配符_含通配符的仅支持单个')"
    :rules="rules"
    @change="handleChange" />
</template>
<script setup lang="ts">
  import _ from 'lodash';
  import { ref, watch } from 'vue';
  import { useI18n } from 'vue-i18n';

  import TableEditTag from '@components/render-table/columns/db-table-name/Index.vue';

  interface Props {
    modelValue?: string[];
    clusterId: number;
  }

  interface Exposes {
    getValue: (field: string) => Promise<Record<string, string[]>>;
  }

  const props = defineProps<Props>();

  const { t } = useI18n();
  const rules = [
    {
      validator: (value: string[]) => value && value.length > 0,
      message: t('DB名不能为空'),
    },
    {
      validator: (value: string[]) => {
        const hasAllMatch = _.find(value, (item) => /%$/.test(item));
        return !(value.length > 1 && hasAllMatch);
      },
      message: t('一格仅支持单个_对象'),
    },
  ];

  const tagRef = ref();
  const localValue = ref(props.modelValue);

  // 集群改变时 DB 需要重置
  watch(
    () => props.clusterId,
    () => {
      localValue.value = [];
    },
  );

  watch(
    () => props.modelValue,
    () => {
      if (props.modelValue) {
        localValue.value = props.modelValue;
      } else {
        localValue.value = [];
      }
    },
    {
      immediate: true,
    },
  );

  const handleChange = (value: string[]) => {
    localValue.value = value;
  };

  defineExpose<Exposes>({
    getValue(field: string) {
      return tagRef.value.getValue().then(() => ({
        [field]: localValue.value,
      }));
    },
  });
</script>
