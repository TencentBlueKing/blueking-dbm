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
    field="cluster_capacity"
    :label="t('当前容量')"
    :min-width="200">
    <CapacityCell
      v-if="cluster.id"
      :data="currentCapacity" />
    <EditableBlock
      v-else
      :placeholder="t('自动生成')" />
  </EditableColumn>
</template>
<script lang="ts" setup>
  import { useI18n } from 'vue-i18n';

  import RedisModel from '@services/model/redis/redis';

  import CapacityCell from './CapacityCell.vue';

  interface Props {
    cluster: RedisModel;
  }

  const props = defineProps<Props>();

  const { t } = useI18n();

  const currentCapacity = computed(() => ({
    capacity: props.cluster.cluster_capacity,
    clusterShardNum: props.cluster.cluster_shard_num,
    groupNum: props.cluster.machine_pair_cnt,
    spec: props.cluster.cluster_spec,
  }));
</script>
