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
    filterable
    :loading="loading"
    :model-value="modelValue"
    :placeholder="placeholder"
    @change="handleChange">
    <BkOption
      v-for="cluster in clusterList"
      :key="cluster.id"
      :label="cluster.master_domain"
      :value="cluster.id" />
  </BkSelect>
</template>

<script lang="ts" setup>
  import { filterClusters } from '@services/source/dbbase';

  import { ClusterTypes, DBTypes } from '@common/const';

  interface Props {
    clusterTypes?: ClusterTypes[];
    dbType?: DBTypes;
    placeholder?: string;
  }

  const props = withDefaults(defineProps<Props>(), {
    clusterTypes: () => [ClusterTypes.TENDBCLUSTER],
    dbType: DBTypes.TENDBCLUSTER,
    disabled: false,
    placeholder: '',
  });

  const modelValue = defineModel<number>();

  const loading = ref(false);
  const clusterList = ref<any[]>([]);

  const fetchClusterList = async () => {
    try {
      loading.value = true;
      const data = await filterClusters({
        bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
        cluster_type: props.clusterTypes.join(','),
        db_type: props.dbType,
      });
      clusterList.value = data;
    } finally {
      loading.value = false;
    }
  };

  const handleChange = (value: number) => {
    modelValue.value = value;
  };

  onMounted(() => {
    fetchClusterList();
  });
</script>
