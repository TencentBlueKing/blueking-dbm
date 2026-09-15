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
  <TableColumn
    v-if="isClusterTypeVisible"
    col-key="cluster_type"
    ellipsis
    :filter="columnFilter['cluster_type']"
    :min-width="140"
    :title="t('架构版本')">
    <template #default="{ row }: { row: ResourceItem }">
      {{ row.cluster_type_name || '--' }}
    </template>
  </TableColumn>
  <TableColumn
    v-if="isInstanceVisible"
    col-key="masters"
    ellipsis
    :min-width="140"
    :title="t('实例')">
    <template #default="{ row }: { row: ResourceItem }">
      {{ row.masters?.map((item) => `${item.ip}:${item.port}`).join(',') || '--' }}
    </template>
  </TableColumn>
  <template v-if="isVersionVisible">
    <TableColumn
      col-key="major_version"
      ellipsis
      :filter="columnFilter['major_version']"
      :min-width="150"
      :title="t('版本')">
      <template #default="{ row }: { row: ResourceItem }">
        {{ row.major_version || '--' }}
      </template>
    </TableColumn>
    <TableColumn
      col-key="sync_mode"
      ellipsis
      :min-width="120"
      :title="t('同步模式')">
      <template #default="{ row }: { row: ResourceItem }">
        {{ row.sync_mode || '--' }}
      </template>
    </TableColumn>
  </template>
</template>

<script setup lang="ts">
  import type { PrimaryTableCol } from 'tdesign-vue-next';
  import { useI18n } from 'vue-i18n';

  import { ClusterTypes } from '@common/const';

  import { TableColumn } from '@components/tdesign-ui/table';

  import type { ResourceItem } from './tableConfig';

  interface Props {
    // tab id，与 tableConfigMap 的 key 一致，取值含 tendbhaSlave 这类非 ClusterTypes 的值
    activeTab: string;
    // 列筛选候选项，按字段名索引，没拉到候选项的字段取值为 undefined
    columnFilter: Record<string, PrimaryTableCol['filter']>;
  }

  const props = defineProps<Props>();
  // Redis 集群与主从共用一套列，两个 tab 都要展示架构版本
  const CLUSTER_TYPE_TABS: string[] = [ClusterTypes.REDIS, ClusterTypes.REDIS_INSTANCE];
  const VERSION_TABS: string[] = [
    ClusterTypes.ORACLE_PRIMARY_STANDBY,
    ClusterTypes.ORACLE_SINGLE_NONE,
    ClusterTypes.SQLSERVER_HA,
    ClusterTypes.SQLSERVER_SINGLE,
  ];

  const { t } = useI18n();

  const isClusterTypeVisible = computed(() => CLUSTER_TYPE_TABS.includes(props.activeTab));

  const isInstanceVisible = computed(() => props.activeTab === ClusterTypes.TENDBSINGLE);

  const isVersionVisible = computed(() => VERSION_TABS.includes(props.activeTab));
</script>
