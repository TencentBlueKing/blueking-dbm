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
    :disabled="!clusterData"
    :list="baseList"
    :model-value="localValue"
    :placeholder="t('请选择xx', [t('备份位置')])"
    :rules="rules"
    @change="(value: string) => handleChange(value)" />
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import { ClusterTypes } from '@common/const';

  import TableEditSelect from '@components/render-table/columns/select/index.vue';

  import type { IDataRow } from './Row.vue';

  interface Props {
    clusterData?: IDataRow['clusterData'];
    modelValue: string;
  }

  interface Exposes {
    getValue: () => Promise<{
      backup_local: string;
    }>;
  }

  const props = defineProps<Props>();

  const { t } = useI18n();
  const rules = [
    {
      validator: (value: string) => Boolean(value),
      message: t('不能为空'),
    },
  ];

  const editSelectRef = ref();
  const localValue = ref('');

  const baseList = computed(() => {
    const list: Record<'label' | 'value', string>[] = [
      {
        value: 'master',
        label: 'Master',
      },
    ];

    if (props.clusterData?.type === ClusterTypes.TENDBHA) {
      list.push({
        value: 'slave',
        label: 'Slave',
      });
    }

    return list;
  });

  watchEffect(() => {
    localValue.value = props.modelValue || 'master';
  });

  watch(
    () => props.clusterData?.type,
    () => {
      if (props.clusterData?.type === ClusterTypes.TENDBSINGLE) {
        localValue.value = 'master';
      }
    },
    {
      immediate: true,
    },
  );

  const handleChange = (value: string) => {
    localValue.value = value;
  };

  defineExpose<Exposes>({
    getValue() {
      return editSelectRef.value
        .getValue()
        .then(() => ({
          backup_local: localValue.value,
        }))
        .catch(() =>
          Promise.reject({
            backup_local: localValue.value,
          }),
        );
    },
  });
</script>
