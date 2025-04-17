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
    field="currentCapacity.spec_name"
    :label="t('当前容量')"
    :min-width="200">
    <EditableBlock :placeholder="t('自动生成')">
      <div v-if="cluster?.cluster_spec?.spec_name">
        <p>{{ t('规格') }}：{{ cluster.cluster_spec.spec_name || '--' }}</p>
        <p>{{ t('机器组数') }}：{{ cluster.machine_pair_cnt || '--' }}</p>
        <p>{{ t('集群分片数') }}：{{ cluster.cluster_shard_num || '--' }}</p>
        <p>
          {{ t('容量') }}：
          <span
            v-if="cluster.cluster_capacity"
            style="font-weight: bold">
            {{ cluster.cluster_capacity }} G
          </span>
          <span v-else>--</span>
        </p>
      </div>
      <div v-else></div>
    </EditableBlock>
  </EditableColumn>
  <EditableColumn
    field="targetCapacity.spec_name"
    :label="t('目标容量')"
    :min-width="200"
    required>
    <EditableBlock @click="handleShow">
      <template #append>
        <DbIcon type="down-big" />
      </template>
      <div v-if="modelValue.spec_name">
        <p>{{ t('规格') }}：{{ modelValue.spec_name || '--' }}</p>
        <p>{{ t('机器组数') }}：{{ modelValue.machine_pair || '--' }}</p>
        <p>{{ t('集群分片数') }}：{{ cluster.cluster_shard_num || '--' }}</p>
        <p>
          {{ t('容量') }}：
          <span
            v-if="modelValue.cluster_capacity"
            style="font-weight: bold">
            {{ modelValue.cluster_capacity }} G
          </span>
          <span v-else>--</span>
        </p>
      </div>
      <div v-else></div>
    </EditableBlock>
  </EditableColumn>
  <CapacityChange
    v-model="modelValue"
    v-bind="props"
    v-model:is-show="isShow" />
</template>

<script lang="ts" setup>
  import { useI18n } from 'vue-i18n';

  import TendbClusterModel from '@services/model/tendbcluster/tendbcluster';

  import CapacityChange, { type TicketSpecInfo } from './CapacityChange.vue';

  interface Props {
    cluster: Pick<
      TendbClusterModel,
      | 'id'
      | 'master_domain'
      | 'bk_cloud_id'
      | 'cluster_capacity'
      | 'cluster_shard_num'
      | 'cluster_spec'
      | 'db_module_id'
      | 'machine_pair_cnt'
      | 'remote_shard_num'
      | 'disaster_tolerance_level'
    >;
  }

  const props = defineProps<Props>();

  const modelValue = defineModel<TicketSpecInfo>({
    default: () => ({
      cluster_capacity: 0,
      machine_pair: 0,
      spec_id: 0,
      spec_name: '',
    }),
  });

  const { t } = useI18n();

  const isShow = ref(false);

  const handleShow = () => {
    isShow.value = true;
  };
</script>
