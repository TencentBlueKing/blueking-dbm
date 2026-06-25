<!--
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 *
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 *
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 *
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed
 * on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for
 * the specific language governing permissions and limitations under the License.
-->

<template>
  <BkSelect
    :clearable="!disabled"
    :disabled="disabled"
    filterable
    :loading="loading"
    :max-data="maxData"
    :model-value="modelValue"
    multiple
    multiple-mode="tag"
    :placeholder="placeholder"
    @change="handleChange">
    <BkOption
      v-for="option in options"
      :key="option.value"
      :label="option.label"
      :value="option.value" />
  </BkSelect>
</template>

<script lang="ts" setup>
  import { getClusterDatabaseNameList } from '@services/source/remoteService';

  interface Props {
    clusterId?: number;
    disabled?: boolean;
    maxData?: number;
    placeholder?: string;
  }

  const props = withDefaults(defineProps<Props>(), {
    clusterId: undefined,
    disabled: false,
    maxData: 5,
    placeholder: '',
  });

  const modelValue = defineModel<string[]>();

  const loading = ref(false);
  const options = ref<{ label: string; value: string }[]>([]);

  const fetchDatabases = async () => {
    if (!props.clusterId) {
      options.value = [];
      return;
    }

    try {
      loading.value = true;
      const data = await getClusterDatabaseNameList({
        cluster_ids: [props.clusterId],
      });
      // data is Array<{ cluster_id: number; databases: string[]; system_databases: string[] }>
      const clusterData = data.find((item) => item.cluster_id === props.clusterId);
      const dbNames = clusterData ? [...clusterData.databases, ...clusterData.system_databases] : [];
      options.value = dbNames.map((name) => ({
        label: name,
        value: name,
      }));
    } catch {
      options.value = [];
    } finally {
      loading.value = false;
    }
  };

  const handleChange = (value: string[]) => {
    modelValue.value = value;
  };

  // 监听 clusterId 变化，重新获取 DB 列表
  watch(
    () => props.clusterId,
    () => {
      fetchDatabases();
    },
    { immediate: true },
  );
</script>
