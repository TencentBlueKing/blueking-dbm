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
    ref="editableTableColumn"
    field="target_cluster_type"
    :label="t('目标集群类型')"
    required
    :width="200">
    <EditableSelect
      v-model="modelValue"
      :clearable="false"
      :disabled="!cluster.id"
      :list="selectList" />
  </EditableColumn>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import { ClusterTypes } from '@common/const';

  interface Props {
    cluster: {
      cluster_type?: string;
      id?: number;
    };
  }

  const props = defineProps<Props>();

  const modelValue = defineModel<string>();

  const { t } = useI18n();

  const typeList = [
    {
      label: 'TendisCache',
      value: ClusterTypes.TWEMPROXY_REDIS_INSTANCE,
    },
    {
      label: 'TendisSSD',
      value: ClusterTypes.TWEMPROXY_TENDIS_SSD_INSTANCE,
    },
    {
      label: 'Tendisplus',
      value: ClusterTypes.PREDIXY_TENDISPLUS_CLUSTER,
    },
    {
      label: 'RedisCluster',
      value: ClusterTypes.PREDIXY_REDIS_CLUSTER,
    },
  ];

  const selectList = computed(() => typeList.filter((item) => item.value !== props.cluster.cluster_type));
</script>
